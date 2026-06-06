import { defineConfig } from "wxt";

export default defineConfig({
  modules: ["@wxt-dev/module-react"],
  manifest: {
    name: "Ботяра",
    description:
      "AI-powered meeting assistant — records meetings, extracts tasks and decisions",
    permissions: [
      "tabCapture",
      "offscreen",
      "sidePanel",
      "storage",
      "activeTab",
      "alarms",
      "tabs",
    ],
    host_permissions: [
      "http://localhost/*",
      "http://localhost:8080/*",
      "https://42team.ru/*",
    ],
    side_panel: {
      default_path: "sidepanel.html",
    },
    action: {
      default_popup: "popup.html",
      default_icon: {
        "16": "icon/16.png",
        "32": "icon/32.png",
        "48": "icon/48.png",
        "128": "icon/128.png",
      },
    },
  },
});
