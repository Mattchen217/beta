import { esc } from "../ui.js";

export function TopBar({ title, right = "", back = false }){
  return `
    <div class="topbar">
      <div class="topbarLeft">
        ${back ? `<button class="backBtn" id="backBtn">‹</button>` : ``}
        <div class="topbarTitle">${esc(title||"")}</div>
      </div>
      <div class="topbarRight">${esc(right||"")}</div>
    </div>
  `;
}
