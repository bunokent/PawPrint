// Minimal PayMongo API stub for Playwright E2E (no real network calls).
// Implements just enough of the REST API for the GCash checkout flow:
//   POST /v1/checkout_sessions -> fake checkout session with a checkout_url
//   GET  /health                -> 200 (used by playwright webServer)
//   GET  /last                  -> last created checkout session id (test introspection)
// Any other /v1/* POST gets a generic 200 payload so drivers never hang.

import { createServer } from "node:http";

const PORT = Number(process.env.STUB_PAYMONGO_PORT ?? 9100);
const HOST = "127.0.0.1";

let lastSession = null;

function readBody(req) {
  return new Promise((resolve) => {
    let data = "";
    req.on("data", (c) => (data += c));
    req.on("end", () => resolve(data));
  });
}

const server = createServer(async (req, res) => {
  const url = new URL(req.url ?? "/", `http://${HOST}:${PORT}`);
  const json = (code, body) => {
    res.writeHead(code, { "Content-Type": "application/json" });
    res.end(JSON.stringify(body));
  };

  if (req.method === "GET" && url.pathname === "/health") return json(200, { status: "ok" });
  if (req.method === "GET" && url.pathname === "/last") return json(200, lastSession ?? {});

  if (req.method === "POST" && url.pathname === "/v1/checkout_sessions") {
    await readBody(req);
    const id = `cs_test_${Math.random().toString(36).slice(2, 14)}`;
    lastSession = { id, checkout_url: `https://checkout.paymongo.test/c/${id}` };
    return json(200, {
      data: {
        id,
        type: "checkout_session",
        attributes: {
          id,
          status: "active",
          checkout_url: lastSession.checkout_url,
          payment_method_types: ["gcash"],
          payments: [],
        },
      },
    });
  }

  if (req.method === "POST" && url.pathname.startsWith("/v1/")) {
    await readBody(req);
    const id = `pi_test_${Math.random().toString(36).slice(2, 14)}`;
    return json(200, { data: { id, type: "payment_intent", attributes: { id, status: "awaiting_payment_method" } } });
  }

  return json(404, { errors: [{ code: "not_found", detail: url.pathname }] });
});

server.listen(PORT, HOST, () => {
  console.log(`stub-paymongo listening on http://${HOST}:${PORT}`);
});
