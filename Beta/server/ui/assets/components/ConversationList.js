import { esc, safeSliceTime } from "../ui.js";

function initialsFromTitle(title){
  const t = (title||"").trim();
  if(!t) return "?";
  const ch = t[0];
  return (ch+"").toUpperCase();
}

function avatarHTML(conv){
  const n = (conv.participants||[]).length;
  if(conv.conv_id === "agent"){
    return `<img class="convAvatarImg" src="/assets/avatars/agent.png" alt="AI" />`;
  }
  if(n > 2){
    return `<img class="convAvatarImg" src="/assets/avatars/group.png" alt="Group" />`;
  }
  const ini = initialsFromTitle(conv.title);
  return `<div class="convAvatarText">${esc(ini)}</div>`;
}

export function ConversationList({ conversations, agentPreviewText }){
  const items = [
    {
      conv_id: "agent",
      title: "我和我的AI",
      participants: ["me","agent"],
      last_text: agentPreviewText || "点击开始查询",
      last_ts: "",
      pinned: true,
    },
    ...conversations,
  ];

  return `
    <div class="convList" id="convList">
      ${items.map(c=>`
        <div class="convItem ${c.pinned?"pinned":""}" data-conv="${esc(c.conv_id)}">
          <div class="convIco">${avatarHTML(c)}</div>
          <div class="convMain">
            <div class="convTop">
              <div class="convTitle">${esc(c.title||"")}${c.pinned?" <span class=\"pin\">置顶</span>":""}</div>
              <div class="convTime">${esc(safeSliceTime(c.last_ts||""))}</div>
            </div>
            <div class="convSub">${esc(c.last_text||"")}</div>
          </div>
        </div>
      `).join("")}
    </div>
  `;
}
