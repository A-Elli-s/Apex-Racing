
const INBOX_ID = "12519a16-1c2d-4dca-a79f-d14d24c5f582";
const encoder = new TextEncoder();

function decodeBase64(value) {
  const normalized = value.replace(/-/g, "+").replace(/_/g, "/");
  const bytes = atob(normalized);
  return Uint8Array.from(bytes, c => c.charCodeAt(0));
}

async function verifyWebhook(body, request, secret) {
  const id = request.headers.get("svix-id");
  const timestamp = request.headers.get("svix-timestamp");
  const signatures = request.headers.get("svix-signature");

  if (!id || !timestamp || !signatures || !secret?.startsWith("whsec_")) {
    return false;
  }

  if (!/^\d+$/.test(timestamp) ||
      Math.abs(Date.now() / 1000 - Number(timestamp)) > 300) {
    return false;
  }

  const key = await crypto.subtle.importKey(
    "raw",
    decodeBase64(secret.slice(6)),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );

  const signedContent = `${id}.${timestamp}.${body}`;
  const expected = new Uint8Array(
    await crypto.subtle.sign("HMAC", key, encoder.encode(signedContent))
  );

  for (const entry of signatures.split(" ")) {
    const [version, encoded] = entry.split(",");
    if (version !== "v1" || !encoded) continue;

    let actual;
    try {
      actual = decodeBase64(encoded);
    } catch {
      continue;
    }

    if (actual.length !== expected.length) continue;

    let difference = 0;
    for (let i = 0; i < expected.length; i++) {
      difference |= expected[i] ^ actual[i];
    }

    if (difference === 0) return true;
  }

  return false;
}

function clean(value) {
  return String(value ?? "")
    .replace(/[\u0000-\u001f\u007f]/g, " ")
    .slice(0, 500);
}

export async function onRequestGet() {
  return new Response("Apex mail webhook endpoint", { status: 200 });
}

export async function onRequestPost({ request, env }) {
  if (!env.RESEND_API_KEY ||
      !env.RESEND_WEBHOOK_SECRET ||
      !env.FORWARD_TO_EMAIL) {
    return new Response("Not configured", { status: 503 });
  }

  const body = await request.text();

  if (!(await verifyWebhook(body, request, env.RESEND_WEBHOOK_SECRET))) {
    return new Response("Invalid signature", { status: 401 });
  }

  let event;
  try {
    event = JSON.parse(body);
  } catch {
    return new Response("Invalid JSON", { status: 400 });
  }

  if (event.type !== "inbox.email.received") {
    return new Response("Ignored", { status: 200 });
  }

  const data = event.data || {};
  const inboxId = data.inbox_id;
  const threadId = data.thread_id;
  const emailId = data.email_id;

  if (inboxId !== INBOX_ID || !threadId || !emailId) {
    return new Response("Ignored", { status: 200 });
  }

  const authorization = {
    Authorization: `Bearer ${env.RESEND_API_KEY}`
  };

  const messageUrl =
    `https://api.resend.com/inboxes/${encodeURIComponent(inboxId)}` +
    `/threads/${encodeURIComponent(threadId)}` +
    `/emails/${encodeURIComponent(emailId)}`;

  const result = await fetch(messageUrl, {
    headers: authorization
  });

  if (!result.ok) {
    console.error("Inbox retrieval failed", result.status);
    return new Response("Retrieval failed", { status: 502 });
  }

  const response = await result.json();
  const mail = response.data || response;

  const sender = clean(mail.from);
  const subject = clean(mail.subject || "(No subject)");
  const message = String(
    mail.text ||
    mail.html?.replace(/<[^>]*>/g, " ") ||
    "(No text content)"
  ).slice(0, 20000);

  const attachmentNotice =
    Array.isArray(mail.attachments) && mail.attachments.length
      ? "\n\nAttachments are available in the Resend inbox."
      : "";

  const notification = {
    from: "Apex Racing World <contact@apexracingworld.com>",
    to: [env.FORWARD_TO_EMAIL],
    subject: `[Apex Contact] ${subject}`,
    text:
      `New business email\n\n` +
      `From: ${sender}\n` +
      `Subject: ${subject}\n\n` +
      message +
      attachmentNotice +
      `\n\nReply to the original sender through your Resend inbox.`
  };

  const forwarded = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      ...authorization,
      "Content-Type": "application/json",
      "Idempotency-Key": `apex-forward-${emailId}`
    },
    body: JSON.stringify(notification)
  });

  if (!forwarded.ok) {
    console.error("Forwarding failed", forwarded.status);
    return new Response("Forwarding failed", { status: 502 });
  }

  return new Response("Forwarded", { status: 200 });
}
