"""Interface, system-failure, demo and unit-test cases of the manual test map (E to H).

They run the real command line (in-process with a fake terminal, or as a subprocess) and, where the
case needs a conversation, the real model. Each function returns None when it passes or a message.
"""

import dataclasses
import os
import re
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ai_assistant import ui_text
from ai_assistant.cli import main
from ai_assistant.config import Settings
from ai_assistant.model import DeepSeekClient
from ai_assistant.ui_style import CLEAR_LINE, Style
from qa.harness import SETTINGS

ROOT = Path(__file__).resolve().parent.parent
ANSI = re.compile("\x1b\\[")
REPORT = "XYZ789 caminhão quebrou na BR-116 km 80, 3 pacotes atrasados, motorista Pedro avisou 14h"


class Terminal:
    """A fake terminal that feeds scripted input and records what is printed."""

    def __init__(self, lines):
        self.lines = list(lines)
        self.out = []

    def input(self, prompt=""):
        self.out.append(prompt)
        if not self.lines:
            raise EOFError
        item = self.lines.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item

    def print(self, *parts):
        self.out.append(" ".join(str(p) for p in parts))

    def write(self, text):
        self.out.append(text)

    @property
    def text(self):
        return "\n".join(self.out)


def cli(lines, argv=(), settings=None, model_factory=None, style=None) -> tuple[int, str]:
    terminal = Terminal(lines)
    code = main(
        list(argv),
        input_fn=terminal.input,
        print_fn=terminal.print,
        write_fn=terminal.write,
        style=style or Style(),
        settings=settings or SETTINGS,
        model_factory=model_factory,
    )
    return code, terminal.text


def flat(text: str) -> str:
    return " ".join(text.split())


def subprocess_cli(args=(), stdin="", env=None) -> subprocess.CompletedProcess:
    environment = {**os.environ, **(env or {})}
    return subprocess.run(
        [sys.executable, "-m", "ai_assistant", *args],
        input=stdin,
        capture_output=True,
        text=True,
        cwd=ROOT,
        env=environment,
        timeout=120,
    )


# --- E: interface ---------------------------------------------------------------------------


def e1():
    _, text = cli(["1", "/resumo", "/sair", "0"])
    return (
        None if ui_text.SUMMARY_EMPTY in text else "o /resumo vazio não mostrou a mensagem esperada"
    )


def e2():
    _, text = cli(["1", "meu pacote ABC123 não chegou", "/resumo", "/sair", "0"])
    ok = "Código: ABC123 (informado)" in text and "Nome do cliente: ausente" in text
    return None if ok else "o /resumo não mostrou os campos (código informado, nome ausente)"


def e3():
    _, text = cli(["1", "meu pacote ABC123 não chegou", "/novo", "/resumo", "/sair", "0"])
    after_new = text.split(ui_text.NEW_CONVERSATION)[-1]
    ok = ui_text.NEW_CONVERSATION in text and ui_text.SUMMARY_EMPTY in after_new
    return None if ok else "o /novo não zerou o registro"


def e4():
    _, text = cli(["1", "/sair", "0"])
    return None if text.count(ui_text.MENU_TITLE) == 2 else "o /sair não voltou ao menu"


def e5():
    _, text = cli(["1", "", "   ", "/sair", "0"])
    return None if ui_text.ASSISTANT_PREFIX not in text else "linha em branco gerou resposta"


def e6():
    _, text = cli(["9", "abc", "0"])
    return (
        None if text.count(ui_text.INVALID_OPTION) == 2 else "opções inválidas não foram avisadas"
    )


def e7():
    for end in (EOFError(), KeyboardInterrupt()):
        code, text = cli(["1", end])
        if code != 0 or ui_text.GOODBYE not in text or "Traceback" in text:
            return f"{type(end).__name__} não encerrou limpo (código {code})"
    return None


def _operator_cli(answer, after):
    return cli(["2", REPORT, answer, *after, "0"])


def e8():
    _, yes = _operator_cli("s", ["/sair"])
    if ui_text.ASK_CONTINUE.strip() not in flat(yes) or ui_text.CONTINUE_HINT not in flat(yes):
        return "depois do repasse não houve a pergunta ou a dica ao responder 's'"
    if ui_text.CONCLUDED in yes:
        return "respondendo 's' a conversa foi encerrada"
    _, no = _operator_cli("n", [])
    return None if ui_text.CONCLUDED in no else "respondendo 'n' a conversa não foi encerrada"


def e9():
    for env in ({"NO_COLOR": "1"}, {}):
        done = subprocess_cli(["--demo"], "1\n0\n", env)
        if ANSI.search(done.stdout):
            return f"saída em pipe com códigos de cor (env={env})"
    return None


def e10():
    done = subprocess_cli(["--demo"], "1\n0\n", {"COLUMNS": "50"})
    widest = max(len(line) for line in done.stdout.splitlines())
    return None if widest <= 50 else f"linha com {widest} colunas (limite 50)"


def e11():
    style = Style(color=True, interactive=True, width=80)
    _, text = cli(["1", "meu pacote ABC123 não chegou", "/sair", "0"], style=style)
    ok = ui_text.WORKING in text and CLEAR_LINE in text
    return None if ok else "o indicador 'IA está respondendo…' não apareceu ou não foi apagado"


# --- F: system failures ---------------------------------------------------------------------


def _expects_failure_message(code, text, secret=""):
    if ui_text.FAILED not in text:
        return "não mostrou a mensagem de falha esperada"
    if "Traceback" in text:
        return "mostrou traceback"
    if secret and secret in text:
        return "a chave apareceu na tela"
    return None


def f1():
    code, text = cli(["0"], settings=Settings(api_key=None))
    if code != 2 or "DEEPSEEK_API_KEY" not in text:
        return f"esperado código 2 e instrução da chave (veio {code})"
    return None


def f2():
    bad = "sk-invalida-0000000000000000"
    code, text = cli(["1", "oi", "0"], settings=Settings(api_key=bad))
    return _expects_failure_message(code, text, bad)


def f3():
    def offline(_profile):
        return DeepSeekClient("sk-x", url="http://127.0.0.1:9/chat/completions", timeout=2)

    code, text = cli(["1", "oi", "0"], model_factory=offline)
    return _expects_failure_message(code, text)


def f4():
    started = time.time()
    code, text = cli(["1", "oi", "0"], settings=dataclasses.replace(SETTINGS, timeout=0.01))
    if time.time() - started > 10:
        return "o timeout curto demorou demais para falhar"
    return _expects_failure_message(code, text)


def f5():
    done = subprocess_cli([], "0\n", {"DEEPSEEK_TIMEOUT": "abc"})
    ok = done.returncode == 1 and "Configuração inválida" in done.stdout
    return None if ok else f"esperado código 1 e 'Configuração inválida' (veio {done.returncode})"


def f6():
    settings = dataclasses.replace(SETTINGS, thinking=True)
    code, text = cli(["1", "meu pacote ABC123 não chegou", "/sair", "0"], settings=settings)
    if code != 0 or ui_text.FAILED in text or "IA:" not in text:
        return "com raciocínio ligado a conversa não funcionou"
    return None


# --- G and H --------------------------------------------------------------------------------


def g1():
    done = subprocess_cli(["--demo"], "1\n2\n3\n4\n0\n", {"NO_COLOR": "1"})
    out = done.stdout
    problems = []
    if done.returncode != 0:
        problems.append(f"código de saída {done.returncode}")
    if out.count(ui_text.SUMMARY_TITLE) != 4:
        problems.append(f"{out.count(ui_text.SUMMARY_TITLE)} registros (esperado 4)")
    if ui_text.ASK_CONTINUE in out:
        problems.append("a demo perguntou '(s/n)'")
    if ui_text.ESCALATED not in out:
        problems.append("o motorista não foi encaminhado a um humano")
    return "; ".join(problems) or None


def h1():
    done = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", "."],
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=300,
    )
    tail = done.stderr.strip().splitlines()[-1] if done.stderr.strip() else ""
    return None if done.returncode == 0 else f"testes automáticos falharam: {tail}"


@dataclass(frozen=True)
class SystemCase:
    id: str
    title: str
    expectation: str
    run: Callable[[], str | None]


SYSTEM_CASES = (
    SystemCase("E1", "/resumo em conversa nova", "Mostra 'Ainda não há dados nesta conversa.'", e1),
    SystemCase(
        "E2", "/resumo depois de um turno", "Mostra os campos (ausentes aparecem como ausente).", e2
    ),
    SystemCase("E3", "/novo", "Recomeça e o registro fica vazio.", e3),
    SystemCase("E4", "/sair", "Volta ao menu.", e4),
    SystemCase("E5", "Linha em branco", "É ignorada, sem resposta.", e5),
    SystemCase("E6", "Opção inválida no menu", "Avisa e volta a perguntar.", e6),
    SystemCase("E7", "Ctrl+C e Ctrl+D", "Encerra com 'Até logo!', sem traceback.", e7),
    SystemCase(
        "E8", "Pergunta ao fechar o caso", "'s' mantém aberta e dá a dica; 'n' volta ao menu.", e8
    ),
    SystemCase("E9", "Sem cores em pipe / NO_COLOR", "Nenhum código ANSI na saída.", e9),
    SystemCase(
        "E10", "Largura do terminal (50 colunas)", "Nenhuma linha passa de 50 colunas.", e10
    ),
    SystemCase("E11", "Indicador de espera", "'IA está respondendo…' aparece e é apagado.", e11),
    SystemCase("F1", "Sem chave de API", "Mensagem clara e código de saída 2.", f1),
    SystemCase(
        "F2", "Chave inválida", "Mensagem de falha, sem traceback e sem a chave na tela.", f2
    ),
    SystemCase("F3", "Sem rede", "Mensagem de falha, sem travar.", f3),
    SystemCase("F4", "Timeout curto", "Mensagem de falha rápida.", f4),
    SystemCase("F5", "Configuração inválida", "'Configuração inválida' e código 1.", f5),
    SystemCase("F6", "Raciocínio ligado", "A conversa funciona (mais lenta).", f6),
    SystemCase(
        "G1", "Demo dos 4 perfis", "4 registros, sem '(s/n)', motorista para um humano.", g1
    ),
    SystemCase("H1", "Testes automáticos", "Todos passam.", h1),
)
