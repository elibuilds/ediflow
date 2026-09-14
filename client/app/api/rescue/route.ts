import { NextResponse } from "next/server";

const backendUrl = process.env.EDIFLOW_BACKEND_URL ?? "http://127.0.0.1:8080";

export async function POST(request: Request) {
  const body = await request.text();
  const authorization = request.headers.get("authorization");
  if (!authorization) {
    return NextResponse.json(
      { detail: "Store login required" },
      { status: 401 }
    );
  }

  const response = await fetch(`${backendUrl}/api/v1/trigger-rescue`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: authorization,
      "Idempotency-Key": `client-${crypto.randomUUID()}`
    },
    body
  });

  return NextResponse.json(await response.json(), { status: response.status });
}
