export function uid() {
  return (
    Date.now().toString(36) +
    Math.random().toString(36).slice(2)
  );
}

export function esc(s = "") {
  return (s + "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

export function fmtTiming(timing) {
  if (!timing) return "--";
  if (timing.total !== undefined) return `⏱ Total ${Math.round(timing.total)}ms`;
  const keys = Object.keys(timing);
  if (keys.length === 0) return "--";
  return (
    "⏱ " +
    keys
      .sort()
      .map((k) => `${k}:${Math.round(timing[k])}ms`)
      .join(" · ")
  );
}

export function safeSliceTime(ts = "") {
  // 2026-02-16T10:01:12 -> 02-16 10:01
  if (!ts || ts.length < 16) return "";
  return ts.slice(5, 16).replace("T", " ");
}
