// Preserve GameBuddy's glass shell and continuous full/half view transition.
import { createCourtPanel } from "./shared/court/court-panel.js";
import {
  analysisFor,
  pitchSVG,
  roleName,
} from "./tactical-model.js?v=english-v1";

export function createFootballPitch({ onMode, onSelect, onTheme, onInspect }) {
  const original = createCourtPanel({ onMode, onSelect, onTheme });
  const element = original.element;
  element.classList.add("prism-court");
  const $ = (s) => element.querySelector(s);
  $(".court-drawing").innerHTML = pitchSVG(null, { prefix: "sidebar" });
  $(".court-theme-choice").hidden = true;
  $(".court-theme-choice").remove();
  $(".court-segments").setAttribute("aria-label", "Pitch view");
  $("[data-court-mode=fullCourt]").textContent = "Full pitch";
  $("[data-court-mode=halfCourt]").textContent = "Half pitch";
  $(".court-legend").setAttribute("aria-label", "Tactical legend");
  $(".court-header").insertAdjacentHTML(
    "afterend",
    '<div class="pitch-editorial-tag"><i></i> TACTICAL SNAPSHOT <span>Editorial view</span></div>',
  );
  $(".court-legend").innerHTML =
    '<span><i class="dark-team"></i>Man City</span><span><i class="white-team"></i>Newcastle</span><span><i class="route-swatch"></i>Options</span><span><i class="held-swatch"></i>Reviewed anchors</span>';
  $(".court-legend").insertAdjacentHTML(
    "beforebegin",
    '<div class="football-snapshot-note"></div><button class="pitch-reading"><small>READ THE GAME</small><strong>Waiting for the first reviewed moment</strong><span>Open Tactical Studio ↗</span></button>',
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
    $(".court-team-badge").title = "PitchPrism";
    $(".court-team-logo").alt = "";
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
      ? `Freeze ${scene.clock} · source ${scene.second.toFixed(2)}s · not live tracking`
      : "First reviewed moment at source 8s · explore below";
    $(".pitch-reading strong").textContent =
      analysisFor(scene)?.title || "Read the carrier, support and space";
    const svg = $(".prism-pitch");
    svg.setAttribute("viewBox", `-3 -6 74 ${117 - half * 52.5}`);
    for (const marker of element.querySelectorAll(".tactic-person")) {
      const id = marker.dataset.role;
      if (!match.roster.some((p) => p.id === id)) continue;
      marker.setAttribute("role", "button");
      marker.setAttribute("tabindex", "0");
      marker.setAttribute("aria-label", "Follow " + roleName({ id }));
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
