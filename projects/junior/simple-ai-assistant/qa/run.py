"""Runs the executable test map against the real model and writes a report.

    python -m qa.run                  # every case, 3 runs of each conversation
    python -m qa.run --only A1,D1     # some cases
    python -m qa.run --runs 5         # more runs per conversation (more intermittence coverage)

It needs DEEPSEEK_API_KEY (environment or .env) and costs a few cents. It is not part of the unit
tests, which stay offline.
"""

import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from qa.cases import CONVERSATION_CASES
from qa.harness import SETTINGS, CaseResult, run_all
from qa.system_cases import SYSTEM_CASES

DEFAULT_REPORT = Path(__file__).parent / "report.md"
GROUPS = {
    "A": "Perfil 1: Cliente",
    "B": "Perfil 2: Operador",
    "C": "Perfil 3: Parceiro",
    "D": "Perfil 4: Motorista",
    "E": "Interface e comandos",
    "F": "Falhas do sistema",
    "G": "Demo",
    "H": "Testes automáticos",
}


def run_system(cases):
    def one(case):
        try:
            return case, case.run()
        except Exception as error:  # a crashing case is a failed case, not a crashed report
            return case, f"exceção: {type(error).__name__}: {error}"

    with ThreadPoolExecutor(max_workers=4) as pool:
        return list(pool.map(one, cases))


def _sample(result: CaseResult, index: int = 0) -> str:
    run = result.samples[index]
    lines = []
    for turn in run.turns:
        speech = turn.speech or "(sem resposta: caso escalado por falha)"
        lines.append(f"- **Você:** {turn.message}")
        lines.append(f"  **IA** `{turn.result.next_action}`: {speech}")
    return "\n".join(lines)


def build_report(conversations, systems, runs, seconds, history="") -> str:
    ok_conv = sum(r.ok for r in conversations)
    ok_sys = sum(problem is None for _, problem in systems)
    total_cases = len(conversations) + len(systems)
    executions = sum(r.runs for r in conversations)
    passed_runs = sum(r.passed for r in conversations)
    calls = sum(r.calls for r in conversations)
    lines = [
        "# Relatório de testes: simple-ai-assistant",
        "",
        f"Gerado em {datetime.now():%d/%m/%Y %H:%M} com o modelo real `{SETTINGS.model}` "
        f"(raciocínio {'ligado' if SETTINGS.thinking else 'desligado'}), dados fictícios.",
        "",
        "## Resumo",
        "",
        "| Item | Resultado |",
        "|---|---|",
        f"| Casos aprovados | **{ok_conv + ok_sys} de {total_cases}** |",
        f"| Casos de conversa | {ok_conv} de {len(conversations)} (cada um rodado {runs}x; "
        "todas as execuções precisam passar) |",
        f"| Execuções de conversa aprovadas | {passed_runs} de {executions} |",
        f"| Casos de interface, falhas, demo e testes automáticos | {ok_sys} de {len(systems)} |",
        f"| Chamadas ao modelo nas conversas | {calls} |",
        f"| Tempo da rodada | {seconds:.0f} s |",
        "",
        "Um caso de conversa só é aprovado se **todas** as execuções passarem: isso é o que mede a "
        "intermitência. As verificações olham regras (o que deve e o que nunca deve acontecer), "
        "não o texto exato, porque o modelo escreve de um jeito diferente a cada vez.",
        "",
    ]
    for letter, title in GROUPS.items():
        conv = [r for r in conversations if r.case.id.startswith(letter)]
        sys_rows = [(c, p) for c, p in systems if c.id.startswith(letter)]
        if not conv and not sys_rows:
            continue
        lines += [f"## {title}", "", "| ID | Caso | Esperado | Resultado |", "|---|---|---|---|"]
        for r in conv:
            mark = "✅" if r.ok else "❌"
            note = f" _({r.case.note})_" if r.case.note else ""
            lines.append(
                f"| {r.case.id} | {r.case.title} | {r.case.expectation}{note} "
                f"| {mark} {r.passed}/{r.runs} |"
            )
        for c, problem in sys_rows:
            mark = "✅" if problem is None else f"❌ {problem}"
            lines.append(f"| {c.id} | {c.title} | {c.expectation} | {mark} |")
        lines.append("")
    failed = [r for r in conversations if not r.ok]
    failed_sys = [(c, p) for c, p in systems if p is not None]
    if failed or failed_sys:
        lines += ["## Falhas", ""]
        for r in failed:
            lines.append(f"### {r.case.id}: {r.case.title} ({r.passed}/{r.runs})")
            for index, problems in enumerate(r.failures):
                if problems:
                    lines.append(f"- Execução {index + 1}: " + "; ".join(problems))
            lines += [
                "",
                "Exemplo de execução:",
                "",
                _sample(r, next(i for i, p in enumerate(r.failures) if p)),
                "",
            ]
        for c, problem in failed_sys:
            lines += [f"### {c.id}: {c.title}", f"- {problem}", ""]
    if history:
        lines += [history, ""]
    lines += ["## Transcrições (execução 1 de cada caso de conversa)", ""]
    for r in conversations:
        lines += [f"### {r.case.id}: {r.case.title}", "", _sample(r), ""]
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="qa.run")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--only", default="")
    parser.add_argument("--skip-system", action="store_true")
    parser.add_argument("--out", type=Path, default=DEFAULT_REPORT)
    parser.add_argument(
        "--history", type=Path, default=None, help="markdown to include as a section"
    )
    args = parser.parse_args(argv)
    if not SETTINGS.api_key:
        print("DEEPSEEK_API_KEY não configurada (.env ou ambiente).")
        return 2
    wanted = {item.strip() for item in args.only.split(",") if item.strip()}
    conv_cases = [c for c in CONVERSATION_CASES if not wanted or c.id in wanted]
    sys_cases = (
        [] if args.skip_system else [c for c in SYSTEM_CASES if not wanted or c.id in wanted]
    )

    started = time.time()
    conversations = run_all(conv_cases, args.runs)
    systems = run_system(sys_cases)
    seconds = time.time() - started

    history = args.history.read_text(encoding="utf-8") if args.history else ""
    args.out.write_text(
        build_report(conversations, systems, args.runs, seconds, history), encoding="utf-8"
    )

    bad = [r for r in conversations if not r.ok]
    bad_sys = [(c, p) for c, p in systems if p is not None]
    print(
        f"Conversas: {len(conversations) - len(bad)}/{len(conversations)} casos ok | "
        f"Sistema: {len(systems) - len(bad_sys)}/{len(systems)} ok | {seconds:.0f}s | "
        f"relatório: {args.out}"
    )
    for r in bad:
        print(f"\n❌ {r.case.id} {r.case.title} ({r.passed}/{r.runs})")
        for index, problems in enumerate(r.failures):
            if problems:
                print(f"   run {index + 1}: " + " | ".join(problems))
    for c, problem in bad_sys:
        print(f"\n❌ {c.id} {c.title}: {problem}")
    return 0 if not bad and not bad_sys else 1


if __name__ == "__main__":
    sys.exit(main())
