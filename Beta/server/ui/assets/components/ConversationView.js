import { esc, safeSliceTime } from "../ui.js";

function MsgBubble(m, isGroup){
  const sender = m.sender || "unknown";
  const isMe = sender === "me";
  const cls = isMe ? "out" : "in";
  const nameLine = (!isMe && isGroup) ? `<div class="nameLine">${esc(sender)}</div>` : "";
  const atts = (m.attachments||[]).map(a=>`<div class="attLine"><img class="attIco" src="/assets/icons/file.png" alt=""/> ${esc(a.name||"attachment")}</div>`).join("");
  const timeLine = m.ts ? `<div class="metaLine">${esc(safeSliceTime(m.ts))}</div>` : "";
  return `
    <div class="msgRow ${cls}">
      <div class="bubble ${cls}">
        ${nameLine}
        ${esc(m.text||"")}
        ${atts}
        ${timeLine}
      </div>
    </div>
  `;
}

export function ConversationView(conv){
  const isGroup = (conv?.participants||[]).length > 2;
  const msgs = conv?.messages || [];
  return `
    <div class="chat" id="chat">
      ${msgs.map(m=>MsgBubble(m, isGroup)).join("")}
    </div>
  `;
}
