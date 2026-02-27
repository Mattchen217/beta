import { esc, fmtTiming } from "../ui.js";

function MemoryCard(mem){
  const srcIco = `<img class="memSrcIco" src="/assets/icons/chat.png" alt="src" />`;
  return `
    <div class="memCard">
      <div class="memTitle">${srcIco}<span>[${esc(mem.idx)}] ${esc(mem.conv_title || "(无标题)")}</span></div>
      <div class="memMeta">conv_id=${esc(mem.conv_id||"")} · ${esc(mem.time_range||"")} · score=${Number(mem.score||0).toFixed(3)} · conf=${esc(mem.confidence||"")}</div>
      <div class="memMeta">msg_ids: ${esc((mem.msg_ids||[]).join(", "))}</div>
      <div class="memSnippet">${esc(mem.snippet||"")}</div>
    </div>
  `;
}

function TurnCard(t, showCitations){
  const cited = t.cited_memories || [];
  const citeBlock = (!showCitations || cited.length===0) ? "" : `
    <details class="memDetails">
      <summary>引用的记忆（${cited.length}）</summary>
      <div class="memWrap">${cited.map(MemoryCard).join("")}</div>
    </details>
  `;

  return `
    <div class="turnCard">
      <div class="qLine"><span class="qBadge">Q</span><div class="qText">${esc(t.q||"")}</div></div>
      <div class="aLine">${esc(t.a||"")}</div>
      ${citeBlock}
    </div>
  `;
}

export function AgentPanel({ turns, loading, timingPill, placeholder, showCitations }){
  return `
    <div class="agentScreen">
      <div class="agentHeader">
        <img class="agentAvatar" src="/assets/avatars/agent.png" alt="AI" />
        <div>
          <div class="agentTitle">HetaiAI Beta</div>
          <div class="agentSubTitle">Personal Memory Agent</div>
        </div>
      </div>

      <div class="agentInputCard">
        <div class="agentInputRow">
          <input class="agentInput" id="agentQ" placeholder="${esc(placeholder)}" />
          <button class="agentSend" id="agentSend" ${loading?"disabled":""}>Send</button>
        </div>
        <div class="agentPills">
          <span class="pill">Mode: Self</span>
          <span class="pill">${esc(timingPill || "⏱ --")}</span>
        </div>
        <div class="agentHint">建议输入：你想查询的事实 / 记忆，例如“客户A的报价是多少？”“上次彩排什么时候？”</div>
      </div>

      <div class="agentTurns">
        ${turns.length===0 ? `
          <div class="emptyState">
            <img class="agentHero" src="/assets/illustrations/agent_hero.png" alt="" />
            <div class="emptyHint">还没有查询记录。试试输入一个你想查的记忆 / 事实。</div>
          </div>
        ` : turns.map(t=>TurnCard(t, showCitations)).join("")}
      </div>
    </div>
  `;
}
