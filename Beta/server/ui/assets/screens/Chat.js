import { esc, uid, fmtTiming } from "../ui.js";
import { chat, listConversations, getConversation } from "../api.js";
import { store } from "../store.js";

import { TopBar } from "../components/TopBar.js";
import { ConversationList } from "../components/ConversationList.js";
import { ConversationView } from "../components/ConversationView.js";
import { AgentPanel } from "../components/AgentPanel.js";

export function ChatScreen(state){
  if(state.chatView === "list"){
    return `
      <div class="screen">
        ${TopBar({ title: "消息" })}
        ${ConversationList({ conversations: state.conversations || [], agentPreviewText: lastAgentPreview(state) })}
      </div>
    `;
  }

  // conv view
  if(state.activeConvId === "agent"){
    const showCitations = !!(state.settings?.labs?.showCitations);
    const timingPill = state.agentTurns?.[0]?.timing_ms ? fmtTiming(state.agentTurns[0].timing_ms) : "⏱ --";
    return `
      <div class="screen">
        ${TopBar({ title: "我和我的AI", back: true })}
        ${AgentPanel({
          turns: state.agentTurns || [],
          loading: !!state.loading,
          timingPill,
          placeholder: "输入你想查询的记忆 / 事实（避免闲聊）…",
          showCitations,
        })}
      </div>
    `;
  }

  const conv = state.convCache?.[state.activeConvId];
  return `
    <div class="screen">
      ${TopBar({ title: conv?.title || "对话", back: true })}
      ${conv ? ConversationView(conv) : `<div class="emptyHint">Loading…</div>`}
    </div>
  `;
}

export async function initChatData(){
  try{
    const list = await listConversations();
    store.set({ conversations: list.conversations || [] });
  }catch(e){
    // ignore
  }
}

export function bindChat(state){
  if(state.chatView === "list"){
    document.querySelectorAll(".convItem").forEach(el=>{
      el.onclick = async ()=>{
        const convId = el.getAttribute("data-conv");
        store.set({ chatView: "conv", activeConvId: convId });
        if(convId !== "agent" && !store.state.convCache[convId]){
          try{
            const data = await getConversation(convId);
            store.set({ convCache: { ...store.state.convCache, [convId]: data } });
            // scroll
            setTimeout(()=>{
              const chatEl = document.getElementById("chat");
              if(chatEl) chatEl.scrollTop = chatEl.scrollHeight;
            },0);
          }catch(e){
            // ignore
          }
        }
      };
    });
    return;
  }

  // back
  document.getElementById("backBtn")?.addEventListener("click", ()=>{
    store.set({ chatView: "list" });
  });

  // agent bindings
  if(state.activeConvId === "agent"){
    const btn = document.getElementById("agentSend");
    const input = document.getElementById("agentQ");
    const send = async ()=>{
      const q = (input?.value || "").trim();
      if(!q || store.state.loading) return;
      store.set({ loading: true });
      if(input) input.value = "";
      try{
        const data = await chat({ question: q, mode: 1 });

        const cited = (data.cited_memories || []).map((m, i)=>({
          idx: i+1,
          conv_id: m.conv_id,
          conv_title: m.conv_title,
          time_range: m.time_range,
          score: m.score,
          confidence: m.confidence,
          msg_ids: m.msg_ids,
          snippet: m.snippet,
        }));

        const turn = {
          id: uid(),
          q,
          a: data.answer || "",
          cited_memories: cited,
          timing_ms: data.timing_ms,
        };

        store.set({
          loading: false,
          agentTurns: [turn, ...(store.state.agentTurns||[])],
        });
      }catch(e){
        const turn = { id: uid(), q, a: "请求失败：" + (e?.message||e), cited_memories: [] };
        store.set({ loading:false, agentTurns: [turn, ...(store.state.agentTurns||[])] });
      }
    };
    if(btn) btn.onclick = send;
    if(input) input.onkeydown = (e)=>{ if(e.key==="Enter") send(); };
  }
}

function lastAgentPreview(state){
  const t = (state.agentTurns||[])[0];
  if(!t) return "点击开始查询";
  return `Q: ${t.q}`;
}
