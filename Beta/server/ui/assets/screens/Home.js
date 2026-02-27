import { esc } from "../ui.js";

export function HomeScreen(){
  return `
    <div class="screen">
      <div class="homeCard">
        <div class="profileTop">
          <div class="avatarWrap">
            <img class="avatar" src="/assets/avatar.jpg" />
            <div class="avatarPlus">+</div>
          </div>
          <div class="profileName">小西瓜 🍉</div>
        </div>

        <div class="progress">
          <div class="progressRow">
            <div style="font-weight:800;">AI 适配度</div>
            <div style="font-weight:900;">60%</div>
          </div>
          <div class="bar"><div style="width:60%"></div></div>
          <div style="font-size:12px;color:var(--muted);margin-top:8px;">
            * Beta：适配度统计为占位，后续可接真实指标。
          </div>
        </div>
      </div>
    </div>
  `;
}
