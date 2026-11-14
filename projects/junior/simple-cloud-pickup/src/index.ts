import { InputError, StoreError, registerPickup, updateStatus } from "./pickups.ts";
import { renderPage, type PageMessage } from "./page.ts";
import { loadPickups, savePickups } from "./store.ts";

export interface Env {
  PICKUPS: R2Bucket;
  OBJECT_KEY: string;
}

const NOTICES: Record<string, string> = {
  created: "Coleta cadastrada.",
  updated: "Status atualizado.",
};

export default {
  fetch(request: Request, env: Env): Promise<Response> {
    return handleRequest(request, env);
  },
};

export async function handleRequest(request: Request, env: Env): Promise<Response> {
  const url = new URL(request.url);
  try {
    if (request.method === "GET" && url.pathname === "/") {
      const pickups = await loadPickups(env.PICKUPS, env.OBJECT_KEY);
      return html(renderPage(pickups, noticeFrom(url)));
    }
    if (request.method === "POST" && url.pathname === "/pickups") {
      return await createPickup(request, env);
    }
    if (request.method === "POST" && url.pathname === "/status") {
      return await changeStatus(request, env);
    }
    return text("Não encontrado", 404);
  } catch (error) {
    if (error instanceof StoreError) {
      return html(renderPage([], { kind: "error", text: error.message }), 500);
    }
    return html(
      renderPage([], { kind: "error", text: "Não foi possível concluir a operação." }),
      500,
    );
  }
}

async function createPickup(request: Request, env: Env): Promise<Response> {
  const pickups = await loadPickups(env.PICKUPS, env.OBJECT_KEY);
  const form = await request.formData();
  try {
    const next = registerPickup(pickups, {
      customer_name: field(form, "customer_name"),
      address: field(form, "address"),
      package_count: field(form, "package_count"),
      priority: field(form, "priority"),
    });
    await savePickups(env.PICKUPS, env.OBJECT_KEY, next);
  } catch (error) {
    if (error instanceof InputError) {
      return html(renderPage(pickups, { kind: "error", text: error.message }), 400);
    }
    throw error;
  }
  return redirect("/?notice=created");
}

async function changeStatus(request: Request, env: Env): Promise<Response> {
  const pickups = await loadPickups(env.PICKUPS, env.OBJECT_KEY);
  const form = await request.formData();
  const id = Number(field(form, "id"));
  try {
    const next = updateStatus(pickups, id, field(form, "status"));
    await savePickups(env.PICKUPS, env.OBJECT_KEY, next);
  } catch (error) {
    if (error instanceof InputError) {
      return html(renderPage(pickups, { kind: "error", text: error.message }), 400);
    }
    throw error;
  }
  return redirect("/?notice=updated");
}

function noticeFrom(url: URL): PageMessage | undefined {
  const code = url.searchParams.get("notice");
  if (code === null || NOTICES[code] === undefined) {
    return undefined;
  }
  return { kind: "notice", text: NOTICES[code] };
}

function field(form: FormData, name: string): string {
  const value = form.get(name);
  return typeof value === "string" ? value : "";
}

function html(body: string, status = 200): Response {
  return new Response(body, {
    status,
    headers: { "content-type": "text/html; charset=utf-8" },
  });
}

function text(body: string, status: number): Response {
  return new Response(body, {
    status,
    headers: { "content-type": "text/plain; charset=utf-8" },
  });
}

function redirect(location: string): Response {
  return new Response(null, { status: 303, headers: { Location: location } });
}
