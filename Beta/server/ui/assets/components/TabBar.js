export function TabBar(active){
  const mk = (key, icoSrc, text) => `
    <div class="tab ${active===key?"active":""}" data-tab="${key}">
      <div class="ico"><img class="tabIcoImg" src="${icoSrc}" alt=""/></div>
      <div>${text}</div>
    </div>
  `;
  return `
    <div class="tabbar" id="tabbar">
      ${mk("chat","/assets/icons/chat.png","聊天")}
      ${mk("home","/assets/icons/home.png","主页")}
      ${mk("settings","/assets/icons/settings.png","我的")}
    </div>
  `;
}
