import { NextResponse } from "next/server";

const backendUrl = process.env.EDIFLOW_BACKEND_URL ?? "http://127.0.0.1:8080";

export async function POST(request: Request) {
  const body = await request.text();
  const timestamp = Math.floor(Date.now() / 1000).toString();
  const secret = process.env.EDIFLOW_WEBHOOK_SECRET;
  const apiKey = process.env.EDIFLOW_API_KEY;

  if (!secret || !apiKey) {
    return NextResponse.json(
      { detail: "Rescue proxy is not configured" },
      { status: 503 }
    );
  }

  const signature = await hmacSha256(secret, `${timestamp}.${body}`);
  const response = await fetch(`${backendUrl}/api/v1/trigger-rescue`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": apiKey,
      "X-Webhook-Timestamp": timestamp,
      "X-Webhook-Signature": signature,
      "Idempotency-Key": `client-${crypto.randomUUID()}`
    },
    body
  });

  return NextResponse.json(await response.json(), { status: response.status });
}

async function hmacSha256(secret: string, value: string) {
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const digest = await crypto.subtle.sign(
    "HMAC",
    key,
    new TextEncoder().encode(value)
  );
  return Array.from(new Uint8Array(digest))
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}
