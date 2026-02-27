// API layer (keep thin, no UI logic)

export async function chat({ question, mode = 1 }) {
  const res = await fetch("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, mode }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function listConversations() {
  const res = await fetch("/api/conversations");
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function getConversation(conv_id) {
  const res = await fetch(`/api/conversations/${encodeURIComponent(conv_id)}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}
