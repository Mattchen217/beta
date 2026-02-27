function uid(){
  return Date.now().toString(36) + Math.random().toString(36).slice(2);
}

(function () {
  // ---------- utils ----------
  function esc(s = "") {
    return (s + "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }
  function fmtTiming(timing) {
    if (!timing) return "--";
    if (timing.total !== undefined) return `⏱ ${Math.round(timing.total)}ms`;
    const keys = Object.keys(timing);
    if (keys.length === 0) return "--";
    return "⏱ " + keys.sort().map(k => `${k}:${Math.round(timing[k])}ms`).join(" · ");
  }

async function chatApi({ question, mode = 1 }) {
  const res = await fetch("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, mode }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
} // ✅ 1) 这里补上 chatApi 的闭合大括号
  
async function listConversationsApi() {
  const res = await fetch("/api/conversations");
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

async function getConversationApi(conv_id) {
  const res = await fetch(`/api/conversations/${encodeURIComponent(conv_id)}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

  // ---------- simple store ----------
  const store = {
    state: { tab: "home", showTiming: true, showCitations: true, timingPill: "--", loading: false, conversations: [], chatView: "list", activeConvId: "agent", agentMessages: [], convCache: {} },
    listeners: new Set(),
    set(patch) {
      this.state = Object.assign({}, this.state, patch);
      this.listeners.forEach((fn) => fn(this.state));
    },
    subscribe(fn) {
      this.listeners.add(fn);
      return () => this.listeners.delete(fn);
    },
  };

  // ---------- components ----------
  function TabBar(active){
  const mk = (key, ico, text) => `
    <div class="tab ${active===key?"active":""}" data-tab="${key}">
      <div class="ico">${ico}</div>
      <div>${text}</div>
    </div>
  `;
  return `
    <div class="tabbar" id="tabbar">
      ${mk("chat","💬","聊天")}
      ${mk("home","🧠","主页")}
      ${mk("settings","⚙️","设置")}
    </div>
  `;
}

function HomeScreen(state){
  const msgCount = (state.agentMessages||[]).filter(m => m.role==="assistant").length;
  const memoryCount = 1915;
  const tempMemory = 320;
  const aiFit = 60;

  return `
      <div class="homeCard">
        <div class="profileTop">
          <div class="avatarWrap">
            <img class="avatar" src="/assets/avatar.jpg" alt="avatar"/>
            <div class="avatarPlus">+</div>
          </div>
          <div class="profileName">小西瓜🍉</div>
        </div>

        <div class="gridStats">
          <div class="stat">
            <div class="num">${memoryCount}</div>
            <div class="lbl">记忆</div>
          </div>
          <div class="stat">
            <div class="num">${msgCount}</div>
            <div class="lbl">消息</div>
          </div>
          <div class="stat">
            <div class="num">${tempMemory}</div>
            <div class="lbl">临时记忆</div>
          </div>
        </div>

        <div class="progress">
          <div class="progressRow">
            <div style="font-weight:900;">AI 适配度</div>
            <div style="font-weight:900;">${aiFit}%</div>
          </div>
          <div class="bar"><div style="width:${aiFit}%;"></div></div>
          <div style="margin-top:10px;color:var(--muted);font-size:12px;">
            * Beta：适配度/统计为占位，后续可接真实指标。
          </div>
        </div>
      </div>
  `;
}

function SettingsScreen(state){
  const on1 = state && state.showTiming ? "on" : "";
  const on2 = state && state.showCitations ? "on" : "";
  return `
      <div class="settingCard">
        <div class="settingRow">
          <div>
            <div style="font-weight:800;">显示耗时</div>
            <div style="font-size:12px;color:var(--muted);margin-top:2px;">在回答气泡下显示推理耗时 badge</div>
          </div>
          <div class="toggle ${on1}" id="toggleTiming"></div>
        </div>

        <div class="settingRow">
          <div>
            <div style="font-weight:800;">显示引用</div>
            <div style="font-size:12px;color:var(--muted);margin-top:2px;">显示“引用了哪些记忆”，点击可展开</div>
          </div>
          <div class="toggle ${on2}" id="toggleCitations"></div>
        </div>

        <div class="settingRow">
          <div>
            <div style="font-weight:800;">提示</div>
            <div style="font-size:12px;color:var(--muted);margin-top:2px;">目前是 Beta UI：数据统计仍为占位，后续可接你的真实指标接口。</div>
          </div>
          <div style="color:var(--muted);font-size:12px;">v0</div>
        </div>
      </div>
  `;
}
  function ChatHeader({ timingPill = "--" }) {
    return `
      <div class="header">
        <div class="title">HetaiAI Beta</div>
        <div class="badge">${esc(timingPill)}</div>
      </div>
    `;
  }

  function MessageBubble(m) {
    const cls = m.role === "user" ? "out" : "in";
    const bubbleCls = m.role === "user" ? "bubble out" : "bubble in";

    const meta = (store.state.showTiming && m.role === "assistant" && m.timing_ms)
        ? `<div class="metaLine">${esc(fmtTiming(m.timing_ms))}</div>`
        : "";const citeCount = (m.cited_memories || []).length;
    const cite =
      (store.state.showCitations && m.role === "assistant" && citeCount > 0)
        ? `<div class="metaLine">
             <a href="javascript:void(0)" class="citeLink" data-mid="${esc(m._id)}">引用记忆：${citeCount}（点开）</a>
           </div>`
        : "";

    return `
      <div class="msgRow ${cls}">
        <div class="${bubbleCls}">
          ${esc(m.text || "")}
          ${meta}
          ${cite}
        </div>
      </div>
    `;
  }

  function ChatList(messages) {
    return `
      <div class="chat" id="chat">
        ${messages.map(MessageBubble).join("")}
      </div>
    `;
  }

  function Composer({ loading }) {
    return `
      <div class="composer">
        <input class="input" id="q" placeholder="聊天…" />
        <button class="sendBtn" id="sendBtn" ${loading ? "disabled" : ""}>Send</button>
      </div>
    `;
  }


  // ---------- Conversations ----------
  function ConvAvatar(participants){
    const n = (participants||[]).length;
    return n>2 ? "👥" : "👤";
  }

  function ConversationListScreen(state){
    const items = [];
    // 1) Agent chat pinned on top
    items.push({
      conv_id: "agent",
      title: "我和我的AI",
      participants: ["me","agent"],
      is_group: false,
      last_text: (state.agentMessages.slice(-1)[0]?.text) || "点击开始对话",
      last_ts: ""
    });

    const convs = (state.conversations||[]);
    for(const c of convs){
      items.push(c);
    }

    return `
      <div class="convList" id="convList">
        ${items.map(c => `
          <div class="convItem" data-conv="${esc(c.conv_id)}">
            <div class="convIco">${ConvAvatar(c.participants)}</div>
            <div class="convMain">
              <div class="convTop">
                <div class="convTitle">${esc(c.title || "")}</div>
                <div class="convTime">${esc((c.last_ts||"").slice(5,16).replace("T"," "))}</div>
              </div>
              <div class="convSub">${esc(c.last_text || "")}</div>
            </div>
          </div>
        `).join("")}
      </div>
    `;
  }

  function ChatTopBar({ title, subtitle, showBack }){
    return `
      <div class="chatTopBar">
        <div class="left">
          ${showBack ? `<div class="backBtn" id="backBtn">‹</div>` : ``}
          <div class="twrap">
            <div class="t1">${esc(title||"")}</div>
            <div class="t2">${esc(subtitle||"")}</div>
          </div>
        </div>
        <div class="rightPill">${esc(store.state.showTiming ? store.state.timingPill : "--")}</div>
      </div>
    `;
  }

  function SampleMessageBubble(m, conv){
    const sender = m.sender || "unknown";
    const isMe = sender === "me";
    const cls = isMe ? "out" : "in";
    const bubbleCls = isMe ? "bubble out" : "bubble in";
    const isGroup = (conv?.participants||[]).length > 2;
    const nameLine = (!isMe && isGroup) ? `<div class="nameLine">${esc(sender)}</div>` : "";
    const timeLine = m.ts ? `<div class="metaLine">${esc(m.ts.slice(5,16).replace("T"," "))}</div>` : "";
    const atts = (m.attachments||[]).map(a => `<div class="attLine">📎 ${esc(a.name||"attachment")}</div>`).join("");
    return `
      <div class="msgRow ${cls}">
        <div class="${bubbleCls}">
          ${nameLine}
          ${esc(m.text || "")}
          ${atts}
          ${timeLine}
        </div>
      </div>
    `;
  }

  function SampleChatList(conv){
    const msgs = conv?.messages || [];
    return `
      <div class="chat" id="chat">
        ${msgs.map(m => SampleMessageBubble(m, conv)).join("")}
      </div>
    `;
  }

  // 记忆 Drawer（底部抽屉）
  function MemoryDrawer({ open, memories }) {
    const display = open ? "block" : "none";
    const cards = (memories || []).map(m => `
      <div class="memCard">
        <div class="memTitle">[${esc(m.idx)}] ${esc(m.conv_title || "(无标题)")}</div>
        <div class="memSub">
          conv_id=${esc(m.conv_id || "")} · ${esc(m.time_range || "")}
          · score=${Number(m.score || 0).toFixed(3)} · conf=${esc(m.confidence || "")}
        </div>
        <div class="memSub">msg_ids: ${esc((m.msg_ids || []).join(", "))}</div>
        <div class="memSnippet">${esc(m.snippet || "")}</div>
      </div>
    `).join("");

    return `
      <div class="drawerMask" id="drawerMask" style="display:${display}">
        <div class="drawer">
          <div class="drawerHeader">
            <div class="drawerTitle">引用的记忆</div>
            <button class="drawerClose" id="drawerClose">关闭</button>
          </div>
          <div class="drawerBody">
            ${cards || `<div class="memEmpty">（无）</div>`}
          </div>
        </div>
      </div>
    `;
  }

  // ---------- render ----------
  let drawerOpen = false;
  let drawerMemories = [];
  function openDrawer(memories){
    drawerMemories = memories || [];
    drawerOpen = true;
    render(store.state);
  }
  function closeDrawer(){
    drawerOpen = false;
    drawerMemories = [];
    render(store.state);
  }

  async function send(){
    // only allow sending in agent conversation
    if(store.state.tab !== "chat") return;
    if(store.state.chatView !== "conv") return;
    if(store.state.activeConvId !== "agent") return;

    const input = document.getElementById("q");
    if (!input) return;

    const question = (input.value || "").trim();
    if (!question || store.state.loading) return;

    input.value = "";
    input.focus();

    const userMsg = { _id: uid(), role: "user", text: question };
    store.set({ agentMessages: [...(store.state.agentMessages||[]), userMsg], loading: true });

    const t0 = performance.now();
    try{
      const data = await chatApi({ question, mode: 1 });
      const t1 = performance.now();

      const timing = (data && data.timing_ms) ? data.timing_ms : {};
      if (timing.total == null) timing.total = Math.round(t1 - t0);

      const pill = fmtTiming(timing);

      const botMsg = {
        _id: uid(),
        role: "assistant",
        text: data.answer || "（空）",
        cited_memories: data.cited_memories || [],
        timing_ms: timing
      };

      store.set({
        agentMessages: [...(store.state.agentMessages||[]), botMsg],
        loading: false,
        timingPill: pill,
      });
    }catch(err){
      store.set({ loading: false });
      const botMsg = { _id: uid(), role: "assistant", text: "（请求失败）"+String(err) };
      store.set({ agentMessages: [...(store.state.agentMessages||[]), botMsg] });
    }
  }


  
  function render(state) {
    const app = document.getElementById("app");
    if (!app) return;

    let screen = "";
    let header = "";

    if (state.tab === "chat") {
      if (state.chatView === "list") {
        header = `
          <div class="header">
            <div class="title">消息</div>
            <div class="pill">${state.showTiming ? state.timingPill : "--"}</div>
          </div>
        `;
        screen = `<div class="screen">${ConversationListScreen(state)}</div>`;
      } else {
        const isAgent = state.activeConvId === "agent";
        const conv = isAgent ? null : state.convCache[state.activeConvId];

        const title = isAgent ? "我和我的AI" : (conv?.title || "");
        const subtitle = isAgent ? "对话中" : ((conv?.participants || []).join(" · "));

        header = ChatTopBar({ title, subtitle, showBack: true });

        const body = isAgent
          ? `${ChatList(state.agentMessages || [])}${Composer({ loading: state.loading })}`
          : `${SampleChatList(conv)}`;

        screen = `
          <div class="screen">
            ${body}
          </div>
          ${isAgent ? MemoryDrawer({ open: drawerOpen, memories: drawerMemories }) : ""}
        `;
      }
    } else if (state.tab === "home") {
      header = `
        <div class="header">
          <div class="title">我的AI</div>
          <div class="pill">${state.showTiming ? state.timingPill : "--"}</div>
        </div>
      `;
      screen = `<div class="screen">${HomeScreen(state)}</div>`;
    } else if (state.tab === "settings") {
      header = `
        <div class="header">
          <div class="title">设置</div>
          <div class="pill">${state.showTiming ? state.timingPill : "--"}</div>
        </div>
      `;
      screen = `<div class="screen">${SettingsScreen(state)}</div>`;
    } else {
      state.tab = "chat";
      state.chatView = "list";
      header = `
        <div class="header">
          <div class="title">消息</div>
          <div class="pill">${state.showTiming ? state.timingPill : "--"}</div>
        </div>
      `;
      screen = `<div class="screen">${ConversationListScreen(state)}</div>`;
    }

    app.innerHTML = `
      <div class="appShell">
        ${header}
        ${screen}
        ${TabBar(state.tab)}
      </div>
    `;

    // --- tab switch ---
    document.querySelectorAll(".tab").forEach((el) => {
      el.onclick = () => {
        const t = el.getAttribute("data-tab");
        if (!t) return;
        if (t === "chat") {
          store.set({ tab: "chat", chatView: "list" });
        } else {
          store.set({ tab: t });
        }
      };
    });

    // --- settings toggles ---
    const t1 = document.getElementById("toggleTiming");
    if (t1) t1.onclick = () => store.set({ showTiming: !state.showTiming });
    const t2 = document.getElementById("toggleCitations");
    if (t2) t2.onclick = () => store.set({ showCitations: !state.showCitations });

    // --- chat: list interactions ---
    const listEl = document.getElementById("convList");
    if (listEl) {
      listEl.querySelectorAll(".convItem").forEach((el) => {
        el.onclick = async () => {
          const cid = el.getAttribute("data-conv");
          if (!cid) return;

          if (cid === "agent") {
            store.set({ chatView: "conv", activeConvId: "agent" });
            return;
          }

          if (!store.state.convCache[cid]) {
            try {
              const conv = await getConversationApi(cid);
              store.set({ convCache: Object.assign({}, store.state.convCache, { [cid]: conv }) });
            } catch (e) {
              return;
            }
          }
          store.set({ chatView: "conv", activeConvId: cid });
        };
      });
    }

    // --- chat: back button ---
    const backBtn = document.getElementById("backBtn");
    if (backBtn) backBtn.onclick = () => store.set({ chatView: "list" });

    // --- agent chat bindings ---
    if (state.tab === "chat" && state.chatView === "conv" && state.activeConvId === "agent") {
      const chatEl = document.getElementById("chat");
      if (chatEl) chatEl.scrollTop = chatEl.scrollHeight;

      const btn = document.getElementById("sendBtn");
      const input = document.getElementById("q");

      if (btn) btn.onclick = () => send();
      if (input) input.onkeydown = (e) => { if (e.key === "Enter") send(); };

      const closeBtn = document.getElementById("drawerClose");
      const mask = document.getElementById("drawerMask");
      if (closeBtn) closeBtn.onclick = closeDrawer;
      if (mask) mask.onclick = (e) => { if (e.target && e.target.id === "drawerMask") closeDrawer(); };

      document.querySelectorAll(".citeLink").forEach((a) => {
        a.addEventListener("click", () => {
          if (!state.showCitations) return;
          const mid = a.getAttribute("data-mid");
          const msg = (state.agentMessages || []).find((x) => x._id === mid);
          if (!msg || !msg.cited_memories) return;
          openDrawer(msg.cited_memories);
        });
      });
    } else if (state.tab === "chat" && state.chatView === "conv") {
      const chatEl = document.getElementById("chat");
      if (chatEl) chatEl.scrollTop = chatEl.scrollHeight;
    }
  }
// ---------- init ----------
  store.subscribe(render);
  render(store.state);

  // load sample conversations for Message list
  (async () => {
    try{
      const data = await listConversationsApi();
      const convs = (data && data.conversations) ? data.conversations : [];
      store.set({ conversations: convs });
    }catch(e){
      // ignore
    }
  })();


  // crash to screen (防白屏)
  window.addEventListener("error", (e) => {
    document.getElementById("app").innerHTML =
      `<div style="padding:18px;color:#b00020">
        <b>UI Error</b><pre style="white-space:pre-wrap">${esc(e?.error?.stack || e.message || e)}</pre>
       </div>`;
  });
  window.addEventListener("unhandledrejection", (e) => {
    document.getElementById("app").innerHTML =
      `<div style="padding:18px;color:#b00020">
        <b>Promise Error</b><pre style="white-space:pre-wrap">${esc(e?.reason?.stack || e.reason || e)}</pre>
       </div>`;
  });
})();