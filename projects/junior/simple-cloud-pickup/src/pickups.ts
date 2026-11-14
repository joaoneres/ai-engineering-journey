export const PRIORITIES = ["low", "medium", "high"] as const;
export const STATUSES = ["pending", "in_transit", "completed"] as const;
export const INITIAL_STATUS = "pending";

export const PRIORITY_LABELS: Record<Priority, string> = {
  low: "Baixa",
  medium: "Média",
  high: "Alta",
};

export const STATUS_LABELS: Record<Status, string> = {
  pending: "Pendente",
  in_transit: "Em rota",
  completed: "Concluída",
};

export type Priority = (typeof PRIORITIES)[number];
export type Status = (typeof STATUSES)[number];

export interface Pickup {
  id: number;
  customer_name: string;
  address: string;
  package_count: number;
  priority: Priority;
  status: Status;
}

export interface NewPickup {
  customer_name: string;
  address: string;
  package_count: string;
  priority: string;
}

export class InputError extends Error {}

export class StoreError extends Error {}

export function registerPickup(pickups: readonly Pickup[], input: NewPickup): Pickup[] {
  const customerName = requiredText(input.customer_name, "Informe o nome do cliente.");
  const address = requiredText(input.address, "Informe o endereço.");
  const packageCount = requiredPackageCount(input.package_count);
  const priority = requiredChoice(input.priority, PRIORITIES, "Prioridade inválida.");
  const pickup: Pickup = {
    id: nextId(pickups),
    customer_name: customerName,
    address,
    package_count: packageCount,
    priority,
    status: INITIAL_STATUS,
  };
  return sortById([...pickups, pickup]);
}

export function updateStatus(
  pickups: readonly Pickup[],
  id: number,
  status: string,
): Pickup[] {
  const nextStatus = requiredChoice(status, STATUSES, "Status inválido.");
  const current = pickups.find((pickup) => pickup.id === id);
  if (current === undefined) {
    throw new InputError(`Coleta #${id} não encontrada.`);
  }
  if (current.status === nextStatus) {
    throw new InputError("O status informado já é o atual.");
  }
  return sortById(
    pickups.map((pickup) => (pickup.id === id ? { ...pickup, status: nextStatus } : pickup)),
  );
}

export function parsePickups(raw: string): Pickup[] {
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    throw new StoreError("O arquivo de coletas no storage está inválido. Nada foi alterado.");
  }
  if (!Array.isArray(parsed)) {
    throw new StoreError("O arquivo de coletas no storage está inválido. Nada foi alterado.");
  }
  const pickups = parsed.map(parsePickup);
  const ids = new Set(pickups.map((pickup) => pickup.id));
  if (ids.size !== pickups.length) {
    throw new StoreError("O arquivo de coletas no storage está inválido. Nada foi alterado.");
  }
  return sortById(pickups);
}

export function serializePickups(pickups: readonly Pickup[]): string {
  return JSON.stringify(sortById(pickups), null, 2);
}

function parsePickup(value: unknown): Pickup {
  if (typeof value !== "object" || value === null) {
    throw new StoreError("O arquivo de coletas no storage está inválido. Nada foi alterado.");
  }
  const record = value as Record<string, unknown>;
  if (!isWholeNumber(record.id) || record.id < 1) {
    throw new StoreError("O arquivo de coletas no storage está inválido. Nada foi alterado.");
  }
  if (typeof record.customer_name !== "string" || record.customer_name.trim() === "") {
    throw new StoreError("O arquivo de coletas no storage está inválido. Nada foi alterado.");
  }
  if (typeof record.address !== "string" || record.address.trim() === "") {
    throw new StoreError("O arquivo de coletas no storage está inválido. Nada foi alterado.");
  }
  if (!isWholeNumber(record.package_count) || record.package_count < 1) {
    throw new StoreError("O arquivo de coletas no storage está inválido. Nada foi alterado.");
  }
  if (!isChoice(record.priority, PRIORITIES) || !isChoice(record.status, STATUSES)) {
    throw new StoreError("O arquivo de coletas no storage está inválido. Nada foi alterado.");
  }
  return {
    id: record.id,
    customer_name: record.customer_name,
    address: record.address,
    package_count: record.package_count,
    priority: record.priority,
    status: record.status,
  };
}

function nextId(pickups: readonly Pickup[]): number {
  return pickups.reduce((highest, pickup) => Math.max(highest, pickup.id), 0) + 1;
}

function sortById(pickups: readonly Pickup[]): Pickup[] {
  return [...pickups].sort((left, right) => left.id - right.id);
}

function requiredText(value: string, message: string): string {
  const text = value.trim();
  if (text === "") {
    throw new InputError(message);
  }
  return text;
}

function requiredPackageCount(value: string): number {
  if (!/^[1-9]\d*$/.test(value.trim())) {
    throw new InputError("A quantidade de pacotes deve ser um número inteiro maior que zero.");
  }
  return Number(value.trim());
}

function requiredChoice<T extends string>(
  value: string,
  allowed: readonly T[],
  message: string,
): T {
  if (!isChoice(value, allowed)) {
    throw new InputError(message);
  }
  return value;
}

function isChoice<T extends string>(value: unknown, allowed: readonly T[]): value is T {
  return typeof value === "string" && allowed.includes(value as T);
}

function isWholeNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isInteger(value);
}
