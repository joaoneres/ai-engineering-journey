import {
  PRIORITIES,
  PRIORITY_LABELS,
  STATUSES,
  STATUS_LABELS,
  type Pickup,
  type Priority,
  type Status,
} from "./pickups.ts";

export function renderPage(pickups: readonly Pickup[], message?: PageMessage): string {
  return `<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>FilaFácil Logística</title>
  <style>
    body { margin: 0; font: 16px/1.45 system-ui, sans-serif; color: #1c2430; background: #f4f6f8; }
    main { max-width: 920px; margin: 0 auto; padding: 32px 20px 64px; }
    h1 { margin: 0 0 4px; font-size: 1.6rem; }
    h2 { margin: 28px 0 12px; font-size: 1.15rem; }
    p.lead { margin: 0; color: #526072; }
    form.card, .banner { background: #fff; border: 1px solid #d8dee6; border-radius: 8px; padding: 16px; }
    .grid { display: grid; gap: 12px; grid-template-columns: 1fr 1fr; }
    label { display: flex; flex-direction: column; gap: 4px; font-size: 0.92rem; }
    input, select, button { font: inherit; }
    input, select { padding: 8px; border: 1px solid #c5ced8; border-radius: 6px; background: #fff; }
    button { padding: 8px 14px; border: 0; border-radius: 6px; background: #0f6b4c; color: #fff; cursor: pointer; }
    table { width: 100%; border-collapse: collapse; background: #fff; }
    th, td { padding: 8px 10px; border-bottom: 1px solid #e4e9ee; text-align: left; vertical-align: middle; }
    th { font-size: 0.82rem; color: #526072; }
    td form { display: flex; gap: 8px; align-items: center; }
    .error { background: #fff1f0; border-color: #e7b2ad; }
    .notice { background: #eef8f3; border-color: #b7dccb; }
    .empty { color: #526072; }
    @media (max-width: 700px) { .grid { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <main>
    <h1>FilaFácil Logística</h1>
    <p class="lead">Coletas do time técnico. Cada gravação atualiza o arquivo no object storage.</p>
    ${banner(message)}
    <h2>Cadastrar coleta</h2>
    <form class="card" method="post" action="/pickups">
      <div class="grid">
        <label>Nome do cliente <input name="customer_name" required maxlength="100"></label>
        <label>Endereço <input name="address" required maxlength="200"></label>
        <label>Quantidade de pacotes <input name="package_count" required inputmode="numeric"></label>
        <label>Prioridade <select name="priority">${options(PRIORITIES, PRIORITY_LABELS, "medium")}</select></label>
      </div>
      <p><button type="submit">Cadastrar</button></p>
    </form>
    <h2>Coletas</h2>
    ${table(pickups)}
  </main>
</body>
</html>`;
}

export interface PageMessage {
  kind: "error" | "notice";
  text: string;
}

function banner(message: PageMessage | undefined): string {
  if (message === undefined) {
    return "";
  }
  return `<p class="banner ${message.kind}">${escapeHtml(message.text)}</p>`;
}

function table(pickups: readonly Pickup[]): string {
  if (pickups.length === 0) {
    return `<p class="empty">Nenhuma coleta cadastrada.</p>`;
  }
  const rows = pickups
    .map(
      (pickup) => `<tr>
        <td>${pickup.id}</td>
        <td>${escapeHtml(pickup.customer_name)}</td>
        <td>${escapeHtml(pickup.address)}</td>
        <td>${pickup.package_count}</td>
        <td>${escapeHtml(PRIORITY_LABELS[pickup.priority])}</td>
        <td>${escapeHtml(STATUS_LABELS[pickup.status])}</td>
        <td>
          <form method="post" action="/status">
            <input type="hidden" name="id" value="${pickup.id}">
            <select name="status">${options(STATUSES, STATUS_LABELS, pickup.status)}</select>
            <button type="submit">Atualizar</button>
          </form>
        </td>
      </tr>`,
    )
    .join("");
  return `<table>
    <thead><tr><th>ID</th><th>Cliente</th><th>Endereço</th><th>Pacotes</th><th>Prioridade</th><th>Status</th><th>Novo status</th></tr></thead>
    <tbody>${rows}</tbody>
  </table>`;
}

function options<T extends Priority | Status>(
  values: readonly T[],
  labels: Record<T, string>,
  selected: T,
): string {
  return values
    .map(
      (value) =>
        `<option value="${value}"${value === selected ? " selected" : ""}>${escapeHtml(labels[value])}</option>`,
    )
    .join("");
}

export function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}
