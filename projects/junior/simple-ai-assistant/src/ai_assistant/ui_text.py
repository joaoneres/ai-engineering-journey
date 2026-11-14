"""Every text shown to the user, in Brazilian Portuguese, in one place.

The rest of the project is in English. Only what a person reads on the screen lives here (plus the
Portuguese examples inside the prompt library, which the model imitates).
"""

from ai_assistant.library import Profile
from ai_assistant.memory import ConversationState

PROFILE_LABELS = {
    "customer": "Cliente",
    "operator": "Operador",
    "partner": "Parceiro",
    "driver": "Motorista",
}
INTENT_LABELS = {
    "delivery": "Entrega",
    "occurrence": "Ocorrência",
    "proof": "Comprovante",
    "address": "Endereço",
    "human_escalation": "Atendimento humano",
    "unclear": "Pouco claro",
}
NEXT_ACTION_LABELS = {
    "ask_missing_information": "Pedir as informações que faltam",
    "provide_information": "Informar o usuário",
    "hand_off_to_team": "Repassar à equipe",
    "escalate_to_human": "Encaminhar para atendimento humano",
    "close": "Encerrar",
}
ORIGIN_LABELS = {
    "informed": "informado",
    "inferred": "inferido",
    "absent": "ausente",
    "base": "base",
}
PRIORITY_LABELS = {"low": "Baixa", "medium": "Média", "high": "Alta"}
FIELD_LABELS = {
    "code": "Código",
    "customer_name": "Nome do cliente",
    "description": "Descrição",
    "location": "Local",
    "time": "Horário",
    "status": "Status",
    "moment": "Momento",
    "problem": "Problema",
    "reported_address": "Endereço informado",
}

MENU_TITLE = "=== FilaFácil · Assistente com IA ==="
MENU_QUESTION = "Quem é você?"
MENU_EXIT = "Sair"
MENU_PROMPT = "Escolha uma opção: "
INVALID_OPTION = "Opção inválida. Tente novamente."
DEMO_BANNER = "Modo demonstração: respostas gravadas, sem chamar nenhum modelo."
PRIVACY_NOTICE = (
    "Aviso: use somente dados fictícios. "
    "Tudo o que você digitar é enviado a um serviço externo de IA."
)
CHAT_HEADER = "--- Conversa: {profile} ---  (/resumo  /novo  /sair)"
USER_PROMPT = "Você: "
ASSISTANT_PREFIX = "IA:   "
NEW_CONVERSATION = "Nova conversa iniciada."
BACK_TO_MENU = "Voltando ao menu."
GOODBYE = "Até logo!"
CONCLUDED = "Conversa concluída."
ESCALATED = "Este caso foi encaminhado para um atendente humano."
FAILED = "Não consegui concluir com segurança; encaminhei para um atendente."
MISSING_KEY = (
    "A chave do DeepSeek não está configurada.\n"
    "Copie o arquivo .env.example para .env e preencha DEEPSEEK_API_KEY,\n"
    "ou rode com --demo para ver os 4 cenários sem chave."
)
LOAD_ERROR = "Não foi possível carregar a biblioteca do assistente: {detail}"
SETTINGS_ERROR = "Configuração inválida: {detail}"
UNEXPECTED_ERROR = "Ocorreu um erro inesperado ({kind}). A conversa foi encerrada."
SUMMARY_TITLE = "===== Registro estruturado ====="
SUMMARY_EMPTY = "Ainda não há dados nesta conversa."
ABSENT = "ausente"
FINAL_ACTIONS = ("hand_off_to_team", "escalate_to_human", "close")


def _origin(origin: str) -> str:
    return ORIGIN_LABELS.get(origin, origin)


def _field_lines(state: ConversationState, profile: Profile) -> list[str]:
    known = dict(state.fields)
    names = list(profile.required_fields) + [n for n in known if n not in profile.required_fields]
    lines = []
    for name in names:
        label = FIELD_LABELS.get(name, name)
        item = known.get(name)
        if item is not None and item.present:
            lines.append(f"  - {label}: {item.value} ({_origin(item.origin)})")
        else:
            lines.append(f"  - {label}: {ABSENT}")
    return lines


def _record_lines(record: dict) -> list[str]:
    lines = []
    for name, item in record.items():
        value = item["value"] if item["value"] is not None else ABSENT
        lines.append(f"  - {FIELD_LABELS.get(name, name)}: {value} ({_origin(item['origin'])})")
    return lines


def format_summary(state: ConversationState, profile: Profile) -> str:
    """The structured record of the conversation so far, in Portuguese."""
    if not state.fields and not state.extras:
        return SUMMARY_EMPTY
    extras = dict(state.extras)
    lines = [SUMMARY_TITLE, f"Perfil: {PROFILE_LABELS[profile.id]}"]
    if state.intent:
        lines.append(f"Intenção: {INTENT_LABELS.get(state.intent, state.intent)}")
    lines += ["Campos:", *_field_lines(state, profile)]
    if "summary" in extras:
        lines.append(f"Resumo: {extras['summary']}")
    if "internal_note" in extras:
        note = extras["internal_note"]
        if note["priority"] is None:
            lines.append("Nota interna: prioridade não definida")
        else:
            priority = PRIORITY_LABELS.get(note["priority"], note["priority"])
            lines.append(
                f"Nota interna: prioridade {priority} ({_origin(note['priority_origin'])})"
            )
        lines.append(f"  {note['text']}")
    if "record" in extras:
        lines += ["Registro padronizado:", *_record_lines(extras["record"])]
    if state.last_next_action:
        label = NEXT_ACTION_LABELS.get(state.last_next_action, state.last_next_action)
        lines.append(f"Próxima ação: {label}")
    return "\n".join(lines)
