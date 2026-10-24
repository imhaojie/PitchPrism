// Preserve GameBuddy's glass shell and continuous full/half view transition.
import { createCourtPanel } from "./shared/court/court-panel.js";
import { analysisFor, pitchSVG } from "./tactical-model.js";

export function createFootballPitch({ onMode, onSelect, onTheme, onInspect }) {
  const original = createCourtPanel({ onMode, onSelect, onTheme });
  const element = original.element;
  element.classList.add("prism-court");
  const $ = (s) => element.querySelector(s);
  $(".court-drawing").innerHTML = pitchSVG(null, { prefix: "sidebar" });
  $(".court-theme-choice").hidden = true;
  $(".court-header").insertAdjacentHTML(
    "afterend",
    '<div class="pitch-editorial-tag"><i></i> TACTICAL SNAPSHOT <span>编辑示意</span></div>',
  );
  $(".court-legend").innerHTML =
    '<span><i class="dark-team"></i>曼城</span><span><i class="white-team"></i>纽卡</span><span><i class="route-swatch"></i>选项示意</span><span><i class="held-swatch"></i>人工审核</span>';
  $(".court-legend").insertAdjacentHTML(
    "beforebegin",
    '<div class="football-snapshot-note"></div><button class="pitch-reading"><small>READ THE GAME / 阅读这一帧</small><strong>等待首个战术定格</strong><span>打开战术演播室 ↗</span></button>',
  );
  $(".pitch-reading").onclick = () => onInspect?.();
  let half = 0,
    match = null,
    lastKey = "",
    activeScene = null;
  function setTheme(value) {
    const team = value === "rockets" ? "NEW" : "MCI";
    $(".court-city").textContent = "MATCH INTELLIGENCE";
    $(".court-team-name").textContent = "CITY × NEWCASTLE";
    $(".court-team-logo").hidden = true;
    $(".court-team-short").hidden = false;
    $(".court-team-short").textContent = "PP";
    $(".court-team-badge").classList.remove("has-logo");
    element.dataset.footballTeam = team;
  }
  function fit() {
    const zone = $(".court-view-zone"),
      height = 117 - half * 52.5;
    const w = Math.max(
      0,
      Math.min(zone.clientWidth - 2, ((zone.clientHeight - 2) * 74) / height),
    );
    if (w <= 0) return;
    $(".court-floor-frame").style.width = w + "px";
    $(".prism-pitch").style.height = (w * height) / 74 + "px";
    element.querySelectorAll(".court-baseline").forEach((e) => {
      e.style.display = "none";
    });
  }
  function tabStops() {
    for (const marker of element.querySelectorAll(
      ".tactic-person[role=button]",
    )) {
      const player = activeScene?.players.find(
        (p) => p.id === marker.dataset.role,
      );
      marker.setAttribute(
        "tabindex",
        player && (100 - player.board[0]) * 1.05 <= 111 - half * 52.5
          ? "0"
          : "-1",
      );
    }
  }
  function setView(value) {
    half = value;
    original.setView(value);
    $(".prism-pitch").setAttribute("viewBox", `-3 -6 74 ${117 - half * 52.5}`);
    tabStops();
    fit();
  }
  function update(state, time, focus, step = 2) {
    if (!match || !state) return;
    const scene = state.scene,
      key = (scene?.id || "empty") + "|" + (focus || "all") + "|" + step;
    if (key === lastKey) return;
    lastKey = key;
    activeScene = scene;
    element.dataset.hasData = "true";
    $(".court-drawing").innerHTML = pitchSVG(scene, {
      focus,
      step: step ?? 2,
      prefix: "sidebar",
    });
    $(".football-snapshot-note").textContent = scene
      ? `定格 ${scene.clock} · 原片 ${scene.second.toFixed(2)}s · 非实时追踪`
      : "原片 8 秒：首个审核定格 · 点击下方查看";
    $(".pitch-reading strong").textContent =
      analysisFor(scene)?.title || "从持球、接应到空间";
    const svg = $(".prism-pitch");
    svg.setAttribute("viewBox", `-3 -6 74 ${117 - half * 52.5}`);
    for (const marker of element.querySelectorAll(".tactic-person")) {
      const id = marker.dataset.role;
      if (!match.roster.some((p) => p.id === id)) continue;
      marker.setAttribute("role", "button");
      marker.setAttribute("tabindex", "0");
      marker.setAttribute(
        "aria-label",
        "关注" + match.roster.find((p) => p.id === id).name,
      );
      marker.setAttribute("aria-pressed", String(id === focus));
      const choose = () => onSelect(focus === id ? "all" : id);
      marker.onclick = choose;
      marker.onkeydown = (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          choose();
        }
      };
    }
    tabStops();
    fit();
  }
  const observer = new ResizeObserver(fit);
  observer.observe($(".court-view-zone"));
  setTheme("mavericks");
  return {
    ...original,
    setView,
    update,
    setTheme,
    setStory(value) {
      match = value;
      lastKey = "";
    },
    setStyle(next) {
      original.setStyle({
        ...next,
        woodColor: "#123b35",
        paintColor: "#082c2d",
        lineColor: "#bcebdd",
      });
      fit();
    },
    destroy() {
      observer.disconnect();
      original.destroy();
    },
  };
}
