import { store } from "./store.js";

import { TabBar } from "./components/TabBar.js";
import { ChatScreen, bindChat, initChatData } from "./screens/Chat.js";
import { HomeScreen } from "./screens/Home.js";
import { SettingsScreen, bindSettings } from "./screens/Settings.js";

function render(state){
  const app = document.getElementById("app");
  if(!app) return;

  let body = "";
  if(state.tab === "chat") body = ChatScreen(state);
  if(state.tab === "home") body = HomeScreen(state);
  if(state.tab === "settings") body = SettingsScreen(state);

  app.innerHTML = `
    <div class="appShell">
      ${body}
      ${TabBar(state.tab)}
    </div>
  `;

  // tab click
  document.querySelectorAll(".tab").forEach(t=>{
    t.onclick = ()=>{
      const key = t.getAttribute("data-tab");
      store.set({ tab: key });
    };
  });

  // screen binds
  if(state.tab === "chat") bindChat(state);
  if(state.tab === "settings") bindSettings(state);
}

store.subscribe(render);

// bootstrap
render(store.state);
initChatData();
