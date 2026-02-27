import { esc } from "../ui.js";
import { updateSettings, defaultSettings } from "../store.js";

export function SettingsScreen(state){
  const s = state.settings || defaultSettings();
  const on = (v)=> v?"on":"";
  const rc = (v)=> (s.style.tone===v?"checked":"");

  return `
    <div class="screen settingStack">
      <div class="settingCard">
        <div class="cardTitle">👤 我的画像（Bio）</div>
        <div class="formRow"><div class="formLbl">昵称</div>
          <input class="input" id="bio_nickname" value="${esc(s.bio.nickname||"")}" />
        </div>
        <div class="formRow"><div class="formLbl">身份/角色</div>
          <input class="input" id="bio_role" value="${esc(s.bio.role||"")}" />
        </div>
        <div class="formRow"><div class="formLbl">长期目标</div>
          <input class="input" id="bio_goal" value="${esc(s.bio.goal||"")}" />
        </div>
        <div class="formRow"><div class="formLbl">沟通偏好</div>
          <input class="input" id="bio_comm" value="${esc(s.bio.comm_pref||"")}" />
        </div>
        <div class="formRow"><div class="formLbl">禁用词/不喜欢</div>
          <input class="input" id="bio_banned" value="${esc(s.bio.banned_words||"")}" />
        </div>
      </div>

      <div class="settingCard">
        <div class="cardTitle">🎭 回答风格</div>
        <label class="radioRow"><input type="radio" name="tone" value="concise" ${rc("concise")}/> <div class="radioText"><b>简洁优先</b></div></label>
        <label class="radioRow"><input type="radio" name="tone" value="balanced" ${rc("balanced")}/> <div class="radioText"><b>平衡</b></div></label>
        <label class="radioRow"><input type="radio" name="tone" value="detailed" ${rc("detailed")}/> <div class="radioText"><b>详细解释</b></div></label>
        <label class="radioRow"><input type="radio" name="tone" value="consultant" ${rc("consultant")}/> <div class="radioText"><b>专业顾问</b></div></label>
      </div>

      <div class="settingCard">
        <div class="cardTitle">🧠 记忆策略</div>
        <div class="settingRow"><div>自动记录重要信息</div><div class="toggle ${on(s.memory.auto_save)}" id="mem_auto"></div></div>
        <div class="settingRow"><div>跨会话召回</div><div class="toggle ${on(s.memory.cross_session)}" id="mem_cross"></div></div>
        <div class="settingRow"><div>优先引用最近记忆</div><div class="toggle ${on(s.memory.recent_first)}" id="mem_recent"></div></div>
        <div class="settingRow"><div>高置信度才引用</div><div class="toggle ${on(s.memory.high_conf_only)}" id="mem_conf"></div></div>
      </div>

      <div class="settingCard">
        <button class="primaryBtn" id="saveSettingsBtn">保存设置</button>
        <button class="ghostBtn" id="resetSettingsBtn">恢复默认</button>
        <div class="formHint" id="saveHint" style="display:none;margin-top:8px;">✅ 已保存</div>
      </div>
    </div>
  `;
}

export function bindSettings(state){
  const s = JSON.parse(JSON.stringify(state.settings || defaultSettings()));
  const commit = () => updateSettings(s);

  const bindToggle=(id, fn)=>{ const el=document.getElementById(id); if(el) el.onclick=fn; };
  bindToggle("mem_auto", ()=>{ s.memory.auto_save=!s.memory.auto_save; commit(); });
  bindToggle("mem_cross", ()=>{ s.memory.cross_session=!s.memory.cross_session; commit(); });
  bindToggle("mem_recent", ()=>{ s.memory.recent_first=!s.memory.recent_first; commit(); });
  bindToggle("mem_conf", ()=>{ s.memory.high_conf_only=!s.memory.high_conf_only; commit(); });

  document.querySelectorAll('input[name="tone"]').forEach(r=>{
    r.onchange=()=>{ s.style.tone=r.value; commit(); };
  });

  const hint = document.getElementById("saveHint");
  const flash = () => { if(!hint) return; hint.style.display="block"; setTimeout(()=>hint.style.display="none", 1200); };

  document.getElementById("saveSettingsBtn")?.addEventListener("click", ()=>{
    s.bio.nickname = document.getElementById("bio_nickname")?.value || "";
    s.bio.role = document.getElementById("bio_role")?.value || "";
    s.bio.goal = document.getElementById("bio_goal")?.value || "";
    s.bio.comm_pref = document.getElementById("bio_comm")?.value || "";
    s.bio.banned_words = document.getElementById("bio_banned")?.value || "";
    commit();
    flash();
  });

  document.getElementById("resetSettingsBtn")?.addEventListener("click", ()=>{
    const d = defaultSettings();
    updateSettings(d);
    flash();
  });
}
