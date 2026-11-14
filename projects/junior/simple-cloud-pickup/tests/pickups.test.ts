import assert from "node:assert/strict";
import test from "node:test";

import { handleRequest, type Env } from "../src/index.ts";
import {
  InputError,
  StoreError,
  parsePickups,
  registerPickup,
  serializePickups,
  updateStatus,
  type Pickup,
} from "../src/pickups.ts";
import { escapeHtml } from "../src/page.ts";

const base: Pickup = {
  id: 1,
  customer_name: "Maria Souza",
  address: "Rua das Flores, 123",
  package_count: 3,
  priority: "high",
  status: "pending",
};

test("register keeps the first id at 1 and the status pending", () => {
  const saved = registerPickup([], {
    customer_name: "  Maria Souza  ",
    address: " Rua das Flores, 123 ",
    package_count: "3",
    priority: "high",
  });
  assert.deepEqual(saved, [base]);
});

test("register assigns the next id from the highest existing one", () => {
  const saved = registerPickup([base], {
    customer_name: "João Lima",
    address: "Av. Brasil, 45",
    package_count: "10",
    priority: "low",
  });
  assert.equal(saved[1]?.id, 2);
  assert.equal(saved[1]?.status, "pending");
});

test("register rejects blank text, a non-positive package count, and an unknown priority", () => {
  const input = {
    customer_name: "Maria Souza",
    address: "Rua das Flores, 123",
    package_count: "3",
    priority: "high",
  };
  assert.throws(() => registerPickup([], { ...input, customer_name: "   " }), InputError);
  assert.throws(() => registerPickup([], { ...input, address: "" }), InputError);
  assert.throws(() => registerPickup([], { ...input, package_count: "0" }), InputError);
  assert.throws(() => registerPickup([], { ...input, package_count: "2.5" }), InputError);
  assert.throws(() => registerPickup([], { ...input, package_count: "01" }), InputError);
  assert.throws(() => registerPickup([], { ...input, priority: "urgent" }), InputError);
});

test("update changes only the status of the requested pickup", () => {
  const saved = updateStatus([base], 1, "in_transit");
  assert.equal(saved[0]?.status, "in_transit");
  assert.equal(base.status, "pending");
});

test("update rejects an unknown id and a status that is already current", () => {
  assert.throws(() => updateStatus([base], 9, "completed"), /não encontrada/);
  assert.throws(() => updateStatus([base], 1, "pending"), /já é o atual/);
  assert.throws(() => updateStatus([base], 1, "delivered"), /inválido/);
});

test("parse rejects a file that is not a list of complete pickups", () => {
  assert.throws(() => parsePickups("{"), StoreError);
  assert.throws(() => parsePickups("{}"), StoreError);
  assert.throws(() => parsePickups(JSON.stringify([{ ...base, id: 0 }])), StoreError);
  assert.throws(() => parsePickups(JSON.stringify([base, { ...base }])), StoreError);
});

test("serialize round-trips and orders by id", () => {
  const second = { ...base, id: 2, customer_name: "João Lima" };
  const raw = serializePickups([second, base]);
  assert.deepEqual(parsePickups(raw).map((pickup) => pickup.id), [1, 2]);
});

test("the page escapes text that a pickup could carry into HTML", () => {
  assert.equal(escapeHtml(`<script>"&`), "&lt;script&gt;&quot;&amp;");
});

test("the worker stores a pickup and then updates it", async () => {
  const bucket = new MemoryBucket();
  const env = environment(bucket);

  const created = await handleRequest(post("/pickups", validForm()), env);
  assert.equal(created.status, 303);
  assert.equal(created.headers.get("Location"), "/?notice=created");

  const page = await handleRequest(new Request("http://example.test/"), env);
  const body = await page.text();
  assert.equal(page.status, 200);
  assert.match(body, /Maria Souza/);
  assert.match(body, /Pendente/);

  const updated = await handleRequest(post("/status", { id: "1", status: "completed" }), env);
  assert.equal(updated.status, 303);

  const stored = parsePickups(bucket.objects.get("pickups.json") ?? "");
  assert.equal(stored[0]?.status, "completed");
});

test("an invalid registration does not write the file", async () => {
  const bucket = new MemoryBucket();
  const response = await handleRequest(
    post("/pickups", { ...validForm(), customer_name: " " }),
    environment(bucket),
  );
  assert.equal(response.status, 400);
  assert.equal(bucket.objects.size, 0);
  assert.match(await response.text(), /Informe o nome do cliente/);
});

test("a broken stored file is left untouched", async () => {
  const bucket = new MemoryBucket();
  bucket.objects.set("pickups.json", "{");
  const response = await handleRequest(post("/pickups", validForm()), environment(bucket));
  assert.equal(response.status, 500);
  assert.equal(bucket.objects.get("pickups.json"), "{");
});

test("names are escaped when the page is rendered", async () => {
  const bucket = new MemoryBucket();
  await handleRequest(
    post("/pickups", { ...validForm(), customer_name: `<script>` }),
    environment(bucket),
  );
  const page = await handleRequest(new Request("http://example.test/"), environment(bucket));
  const body = await page.text();
  assert.match(body, /&lt;script&gt;/);
  assert.doesNotMatch(body, /<script>/);
});

test("unknown paths respond as not found", async () => {
  const response = await handleRequest(
    new Request("http://example.test/admin"),
    environment(new MemoryBucket()),
  );
  assert.equal(response.status, 404);
});

function validForm(): Record<string, string> {
  return {
    customer_name: "Maria Souza",
    address: "Rua das Flores, 123",
    package_count: "3",
    priority: "high",
  };
}

function post(path: string, fields: Record<string, string>): Request {
  return new Request(`http://example.test${path}`, {
    method: "POST",
    headers: { "content-type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams(fields),
  });
}

function environment(bucket: MemoryBucket): Env {
  return { PICKUPS: bucket, OBJECT_KEY: "pickups.json" } as unknown as Env;
}

class MemoryBucket {
  objects = new Map<string, string>();

  async get(key: string): Promise<{ text: () => Promise<string> } | null> {
    const body = this.objects.get(key);
    if (body === undefined) {
      return null;
    }
    return { text: async () => body };
  }

  async put(key: string, value: string): Promise<void> {
    this.objects.set(key, value);
  }
}
