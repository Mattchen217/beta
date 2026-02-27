const SETTINGS_KEY = "hetai_settings_v1";

export function defaultSettings() {
  return {
    bio: {
      nickname: "Michael",
      role: "创业者 / 产品设计",
      goal: "打造有长期记忆的 AI 系统",
      comm_pref: "简洁直接",
      banned_words: "过度营销、夸张承诺",
    },
    style: { tone: "balanced" }, // concise | balanced | detailed | friend | consultant
    memory: {
      auto_save: true,
      cross_session: true,
      recent_first: true,
      high_conf_only: true,
    },
    labs: {
      showTiming: true,
      showCitations: true,
    },
  };
}

export function loadSettings() {
  try {
    const raw = localStorage.getItem(SETTINGS_KEY);
    if (!raw) return defaultSettings();
    const parsed = JSON.parse(raw);
    return parsed || defaultSettings();
  } catch {
    return defaultSettings();
  }
}

export function saveSettings(s) {
  localStorage.setItem(SETTINGS_KEY, JSON.stringify(s));
}

export const store = {
  state: {
    tab: "chat", // chat | home | settings

    // message area
    chatView: "list", // list | conv
    activeConvId: "agent",
    conversations: [],
    convCache: {},

    // agent query history (Q/A cards)
    agentTurns: [], // {id, q, a, cited_memories?, timing_ms?}

    // settings
    settings: loadSettings(),
  },
  listeners: new Set(),
  set(patch) {
    this.state = { ...this.state, ...patch };
    this.listeners.forEach((fn) => fn(this.state));
  },
  subscribe(fn) {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  },
};

export function updateSettings(next) {
  saveSettings(next);
  store.set({ settings: next });
}
