import { getConfig, subscribe, updateConfig } from "./shared/config/config.js";
import { createStageLayout } from "./shared/stage/layout.js";
import { GlassManager } from "./shared/glass/glass-manager.js";
import {
  paintAmbienceSource,
  stopAmbienceSource,
} from "./shared/glass/ambience-source.js";
import { createPlayerControls } from "./shared/media/player-controls.js?v=broadcast-v1";
import { createDrawer } from "./shared/navigation/drawer.js?v=broadcast-v1";
import { createContentPanel } from "./shared/content/content-panel.js?v=broadcast-v1";
import { createInspector } from "./shared/dev/inspector.js?v=broadcast-v1";
import { mountFootballBuddy } from "./football-buddy.js?v=broadcast-v1";
import { createTacticalStudio } from "./tactical-studio.js?v=broadcast-v1";
import {
  outputToSourceTime,
  readPreferences,
  savePreferences,
} from "./shared/adapters/catalog.js";
import { createFootballPitch } from "./football-pitch.js?v=broadcast-v1";
import {
  presentationTimeForSource,
  reviewAt,
} from "./shared/adapters/editorial-timeline.js";
import { roleName } from "./tactical-model.js?v=broadcast-v1";
import { englishInspector } from "./english-inspector.js?v=broadcast-v1";
import { api } from "./transport.js?v=broadcast-v1";

const $ = (selector) => document.querySelector(selector),
  $$ = (selector) => [...document.querySelectorAll(selector)];
const stage = $("#stage"),
  video = $("#match-video");
const esc = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const clock = (value) =>
  `${Math.floor(value / 60)}:${String(Math.floor(value % 60)).padStart(2, "0")}`;
const storage = {
  getItem: () => localStorage.getItem("pitchprism.preferences.v2"),
  setItem: (_key, value) =>
    localStorage.setItem("pitchprism.preferences.v2", value),
};
let preferences = readPreferences(storage),
  match,
  storyMap,
  state,
  currentStory,
  health,
  variant = "enhanced",
  activeMenu = null;
let layout,
  glass,
  inspector,
  noticeTimer,
  idleTimer,
  refreshId = 0,
  explainId = 0,
  lastSecond = -1,
  openKind = null,
  explaining = false;
const buddy = mountFootballBuddy($("#game-buddy-slot"));
const studio = createTacticalStudio({
  stage,
  onSeek: (second, step) => seek(second, step),
  onClose: () => {
    activeMenu = null;
    buddy.play("idle");
    showControls();
  },
});
function openStudio() {
  if (!match) return;
  video.pause();
  content.close();
  $("#settings").hidden = true;
  activeMenu = "studio";
  buddy.play("review");
  studio.open(
    match,
    state,
    variant === "enhanced" ? reviewAt(match, video.currentTime) : null,
  );
  showControls();
}
function notice(message) {
  $("#notice").textContent = String(message);
  $("#notice").hidden = false;
  clearTimeout(noticeTimer);
  noticeTimer = setTimeout(() => ($("#notice").hidden = true), 4200);
}
function showControls() {
  stage.classList.remove("controls-hidden");
  clearTimeout(idleTimer);
  idleTimer = setTimeout(() => {
    if (
      !activeMenu &&
      !studio.isOpen &&
      !content.isOpen &&
      !inspector.isOpen &&
      !video.paused &&
      !stage.querySelector(":focus-visible")
    )
      stage.classList.add("controls-hidden");
  }, getConfig().motion.controlsIdle);
}
const content = createContentPanel({
  locale: "en",
  onSeek: (second, options) => {
    if (options?.playbackRate) video.playbackRate = options.playbackRate;
    seek(second);
    content.close();
  },
  onStory: (_story, next) => {
    switchVideo(next);
    content.close();
  },
  onClose: () => {
    openKind = null;
    activeMenu = null;
  },
});
stage.append(content.element);
const pitch = createFootballPitch({
  onInspect: openStudio,
  onMode: setMode,
  onSelect: (id) => {
    preferences.player = id;
    $("#follow-player").value = id;
    save();
    syncPitch();
  },
  onTheme: (preset) => {
    pitch.setTheme(preset);
    updateConfig({ courtTheme: { preset } });
  },
});
$("#court-foreground").append(pitch.element);
const controls = createPlayerControls({
  video,
  stage,
  locale: "en",
  onError: notice,
  onMenuChange: (value) => {
    activeMenu = value;
    showControls();
  },
});
$("#controls-host").append(controls.element);
const drawer = createDrawer({
  locale: "en",
  onAction: (kind) =>
    kind === "settings" ? toggleSettings() : openContent(kind),
});
$("#drawer-host").append(drawer.element);
drawer.element.dataset.component = "dock";
layout = createStageLayout({
  stage,
  video,
  surface: $("#video-surface"),
  panel: $("#court-shell"),
  controls: $("#controls-host"),
  config: getConfig,
  onFrame: (rect) => {
    $("#top-tabs").style.right =
      (stage.clientWidth < 700
        ? 12
        : rect.panel.x < stage.clientWidth
          ? stage.clientWidth - rect.panel.x + 20
          : 30) + "px";
    if (stage.clientWidth < 700) {
      const width = stage.clientWidth - 24,
        height = stage.clientHeight;
      Object.assign($("#controls-host").style, {
        left: "12px",
        width: width + "px",
        top: height - 104 + "px",
      });
      if (rect.open > 0.001) {
        const videoHeight = Math.min((width * 9) / 16, height * 0.25),
          panelTop = 76 + videoHeight;
        Object.assign($("#video-surface").style, {
          left: "12px",
          top: "64px",
          width: width + "px",
          height: videoHeight + "px",
        });
        Object.assign($("#court-shell").style, {
          left: "12px",
          top: panelTop + "px",
          width: width + "px",
          height: Math.max(200, height - panelTop - 120) + "px",
        });
      }
    }
    pitch.setView(rect.half);
    $("#court-shell").dataset.component =
      rect.half < 0.5 ? "fullCourt" : "halfCourt";
    const heading = $("#moment-heading");
    heading.style.left = rect.video.x + 32 + "px";
    heading.style.top = rect.video.y + 35 + "px";
  },
});
function setMode(mode) {
  layout.to(mode);
  $$("[data-mode]").forEach((button) => {
    button.classList.toggle("selected", button.dataset.mode === mode);
    button.setAttribute("aria-pressed", String(button.dataset.mode === mode));
  });
  $("#right-edge").setAttribute("aria-expanded", String(mode !== "immersive"));
  glass?.apply();
  showControls();
}
function sourceTime() {
  return Math.min(
    match?.durationSeconds ?? Infinity,
    variant === "enhanced"
      ? outputToSourceTime(storyMap, video.currentTime)
      : video.currentTime,
  );
}
function syncPitch() {
  if (!state) return;
  pitch.update(
    state,
    sourceTime(),
    preferences.player === "all" ? null : preferences.player,
    variant === "enhanced" ? reviewAt(match, video.currentTime)?.step : 2,
  );
}
function save() {
  try {
    savePreferences(preferences, storage);
  } catch {
    notice(
      "Local storage is unavailable. Preferences apply to this visit only.",
    );
  }
}
function updatePreferences() {
  preferences = {
    player: $("#follow-player").value,
    familiarity: $("#familiarity").value,
    purpose: $("#watch-purpose").value,
  };
  save();
  syncPitch();
  explain(false);
}
for (const id of ["follow-player", "familiarity", "watch-purpose"])
  $("#" + id).addEventListener("change", updatePreferences);
const audience = () =>
  preferences.familiarity === "familiar" || preferences.purpose === "analyze"
    ? "analyst"
    : "casual";
function storyDescriptor() {
  return {
    id: match.id,
    sample: "football",
    title: match.title,
    durationSeconds: match.durationSeconds,
    chapters: match.chapters.map((chapter) => ({
      ...chapter,
      title: chapter.title.replace(/^\d+\s*\/\s*/, ""),
    })),
    evidence: [],
  };
}
function panelBody(html, title, eyebrow) {
  content.element.querySelector(".content-sheet-title").textContent = title;
  content.element.querySelector(".content-eyebrow").textContent = eyebrow;
  content.element.querySelector(".content-sheet-body").innerHTML = html;
}
function paintInsights() {
  if (!state || !currentStory) return;
  const source = state.scene
    ? `Freeze ${state.scene.clock} / source ${state.scene.second.toFixed(2)}s`
    : "Match excerpt / visual observation";
  panelBody(
    `<div class="content-badge">${currentStory.provider === "azure-foundry" ? "AZURE FOUNDRY" : "LOCAL EDITORIAL"} · ${esc(source)}</div><h3 class="football-story-title">${esc(currentStory.headline)}</h3><p class="football-story-copy">${esc(currentStory.explanation)}</p><div class="football-metric-grid"><div class="football-metric"><small>Visible scoreboard</small><strong>0 – 0</strong><small>Manchester City / Newcastle</small></div><div class="football-metric"><small>Source time</small><strong>${state.sourceSecond.toFixed(1)} <small>s</small></strong><small>Source and enhanced video aligned</small></div><div class="football-metric"><small>Official xG</small><strong>—</strong><small>Not supplied</small></div><div class="football-metric"><small>Full-match pass accuracy</small><strong>—</strong><small>Unavailable from this excerpt</small></div></div><button class="football-explain" id="explain-moment" ${explaining ? "disabled" : ""}>✦ ${explaining ? "Reading evidence…" : "Explain this moment"}</button><p class="football-source-note">${health.foundryConfigured ? "Foundry is configured. Only successful model responses are labelled as cloud insights." : "Local editorial insight · Azure Foundry is not configured."}</p><details><summary>Inspect the evidence behind this insight</summary><pre class="football-source">${esc(
      JSON.stringify(
        state.events.filter((e) => currentStory.evidenceIds.includes(e.id)),
        null,
        2,
      ),
    )}</pre></details><p class="football-source-note">Role highlights refer to manually reviewed stills. Pitch positions and dashed options are editorial schematics, not tracking or completed-pass data.</p>`,
    "Match insights",
    "PITCHPRISM / MATCH INTELLIGENCE",
  );
  $("#explain-moment").onclick = () => explain(true);
}
function openContent(kind) {
  if (!match) return;
  $("#settings").hidden = true;
  openKind = kind;
  activeMenu = "content";
  drawer.setOpen(true);
  content.open("moments", storyDescriptor(), [], {
    preferences,
    events: match.observations.map((o) => ({
      time: o.second,
      text: o.text,
      sourceLabel: "Reviewed source frame · not an official event record",
      evidenceIds: [o.id],
      playerIds: ["carrier", "right", "runner"],
    })),
    media: { variant, width: video.videoWidth, height: video.videoHeight },
  });
  if (kind === "moments") {
    content.element
      .querySelectorAll(".content-sheet-body > .content-note")
      .forEach((note) => note.remove());
    const note = document.createElement("p");
    note.className = "content-note";
    note.textContent =
      "Chapters use source time and seek to the corresponding moment in the enhanced video. Each reviewed freeze has three readings; dashed arrows show options.";
    content.element.querySelector(".content-sheet-body").append(note);
    return;
  }
  if (kind === "data") {
    paintInsights();
    return;
  }
  if (kind === "library") {
    panelBody(
      '<p class="content-lead">One excerpt. One source clock.</p><div class="football-actions"><button id="choose-source">Watch source</button><button id="choose-enhanced">Watch enhanced</button><button id="restart-highlight">Play from start</button></div><p class="football-source-note">The enhanced movie includes three tactical sequences, option arrows, role highlights, pitch transitions and half-speed replay. Chapters use source time; the player shows enhanced time.</p>',
      "Media library",
      "MEDIA LIBRARY",
    );
    $("#choose-source").onclick = () => {
      switchVideo("source");
      content.close();
    };
    $("#choose-enhanced").onclick = () => {
      switchVideo("enhanced");
      content.close();
    };
    $("#restart-highlight").onclick = () => {
      video.currentTime = 0;
      content.close();
      video.play().catch(notice);
    };
    return;
  }
  panelBody(
    `<p class="content-lead">PitchPrism · Turn the match into a visual story.</p><p class="football-source-note">Reviewed enhanced movie: 118.4 seconds, 1080p / 25fps. Three reviewed freezes each contain three readings. Role highlights, dashed options, pitch diagrams and half-speed replay are burned into the video.</p><p class="football-source-note">This 66.6-second Manchester City × Newcastle excerpt is bound to the source SHA-256. Foot anchors are manually reviewed; pitch positions and arrows are editorial. Official events, xG, full-match statistics and unverified identities remain unavailable.</p><p class="football-source-note">The public demo uses local editorial insights. Azure Foundry results require server configuration and a successful model call. See LICENSE and THIRD_PARTY_NOTICES for code licensing, media rights and attribution.</p>`,
    "About PitchPrism",
    "PITCHPRISM / ABOUT",
  );
}
async function explain(cloud) {
  if (!state || explaining) return;
  const sequence = ++explainId,
    second = state.sourceSecond;
  if (cloud) {
    video.pause();
    explaining = true;
    if (openKind === "data") paintInsights();
  }
  try {
    const result = await api("/api/clip/explain", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        second,
        mode: audience(),
        team: "all",
        player: preferences.player,
        provider: cloud && health.foundryConfigured ? "azure-foundry" : "local",
      }),
    });
    if (sequence === explainId && Math.abs(sourceTime() - second) < 0.6) {
      currentStory = result;
      if (openKind === "data") paintInsights();
    }
  } catch (error) {
    notice(error.message);
  } finally {
    explaining = false;
    if (openKind === "data") paintInsights();
  }
}
async function refresh(force = false) {
  if (!match) return;
  const second = sourceTime();
  if (!force && Math.abs(second - lastSecond) < 0.4) return;
  lastSecond = second;
  const id = ++refreshId;
  try {
    const result = await api("/api/clip/snapshot?t=" + second);
    if (id !== refreshId) return;
    state = result;
    syncPitch();
    if (!explaining) explain(false);
  } catch (error) {
    notice(error.message);
  }
}
function seek(second, step = 0) {
  video.pause();
  video.currentTime =
    variant === "enhanced"
      ? presentationTimeForSource(storyMap, second, step)
      : second;
  refresh(true);
  showControls();
}
function switchVideo(next) {
  if (next === variant) return;
  const second = sourceTime();
  variant = next;
  $("#analysis-toggle").checked = next === "enhanced";
  video.pause();
  video.addEventListener(
    "loadedmetadata",
    () => {
      video.currentTime =
        next === "enhanced"
          ? presentationTimeForSource(storyMap, second)
          : second;
      refresh(true);
    },
    { once: true },
  );
  video.src = new URL(`./media/${next}.mp4?v=broadcast-v1`, import.meta.url).href;
  video.load();
  $("#media-version").textContent =
    next === "enhanced" ? "Switch to source ›" : "Switch to enhanced ›";
}
function toggleSettings() {
  content.close();
  const open = $("#settings").hidden;
  $("#settings").hidden = !open;
  activeMenu = open ? "settings" : null;
  drawer.setOpen(true);
  showControls();
}
$("#media-version").onclick = (e) => {
  e.preventDefault();
  switchVideo(variant === "enhanced" ? "source" : "enhanced");
};
$("#left-edge").onpointerenter = () => drawer.setOpen(true);
$("#left-edge").onclick = () => drawer.setOpen(true);
drawer.element.onpointerleave = () => {
  if (!content.isOpen && $("#settings").hidden) drawer.setOpen(false);
};
$("#right-edge").onclick = () => setMode("halfCourt");
$("#court-close").onclick = () => setMode("immersive");
$$("[data-mode]").forEach(
  (button) => (button.onclick = () => setMode(button.dataset.mode)),
);
$("#open-insights").onclick = () => openContent("data");
$("#open-tactics").onclick = openStudio;
$$("[data-content]").forEach(
  (button) => (button.onclick = () => openContent(button.dataset.content)),
);
$("#analysis-toggle").onchange = (e) =>
  switchVideo(e.target.checked ? "enhanced" : "source");
inspector = createInspector({ translate: englishInspector });
stage.append(inspector.element);
$("#style-inspector").hidden = false;
$("#style-inspector").onclick = () => {
  $("#settings").hidden = true;
  inspector.open();
};
glass = new GlassManager(stage, getConfig, {
  enabled: new URLSearchParams(location.search).get("glass") === "liquid",
});
glass.start();
subscribe(() => {
  layout.draw();
  glass.apply();
  pitch.setStyle(getConfig().halfCourt);
});
stage.onpointermove = showControls;
stage.onfocusin = showControls;
stage.addEventListener("keydown", (event) => {
  if (studio.isOpen) return;
  if (event.key === "Escape") {
    if (inspector.isOpen) {
      inspector.close();
      return;
    }
    if (content.isOpen) {
      content.close();
      return;
    }
    $("#settings").hidden = true;
    activeMenu = null;
    drawer.setOpen(false);
    setMode("immersive");
  }
  if (event.target.matches("input,select,textarea,button")) return;
  if (event.code === "Space") {
    event.preventDefault();
    video.paused ? video.play().catch(notice) : video.pause();
  }
  if (event.key.toLowerCase() === "f") {
    document.fullscreenElement
      ? document.exitFullscreen()
      : stage.requestFullscreen();
  }
});
window.addEventListener("broadcast-layout-request", (e) =>
  setMode(e.detail.layout),
);
window.addEventListener("broadcast-config-select", (e) => {
  if (["fullCourt", "halfCourt"].includes(e.detail.component))
    setMode(e.detail.component);
});
window.addEventListener("broadcast-inspector-state", (e) => {
  activeMenu = e.detail.open ? "inspector" : null;
  showControls();
});
video.addEventListener("play", () => buddy.play("running"));
video.addEventListener("pause", () => buddy.play("idle"));
video.addEventListener("timeupdate", () => refresh());
for (const event of ["seeked", "loadeddata", "pause", "ended"])
  video.addEventListener(event, () => {
    refresh(true);
    showControls();
  });
video.addEventListener("loadeddata", () => ($("#load-error").hidden = true));
video.addEventListener("error", () => {
  $("#load-error").hidden = false;
  showControls();
});
$("#retry-media").onclick = () => video.load();
video.addEventListener("loadedmetadata", () => {
  $("#media-info").textContent =
    `${variant === "enhanced" ? "Enhanced" : "Source"} · ${video.videoWidth} × ${video.videoHeight} · ${video.duration.toFixed(2)}s`;
  layout.draw();
});
function paint() {
  if (glass.enabled) paintAmbienceSource($("#ambience"), video, stage);
  video.requestVideoFrameCallback?.(paint);
}
video.requestVideoFrameCallback?.(paint);
window.broadcastUI = {
  setMode,
  video,
  layout,
  openContent,
  getConfig,
  updateConfig,
  showControls,
  glass: () => glass,
};
window.broadcastDiagnostics = () => ({
  mode: layout.mode,
  layout: layout.rects,
  glass: glass.status(),
  media: {
    variant,
    time: video.currentTime,
    sourceTime: sourceTime(),
    duration: video.duration,
  },
  reuse: [
    "StageLayout",
    "GlassManager",
    "PlayerControls",
    "Drawer",
    "ContentPanel",
    "Inspector",
    "CourtPanel",
    "sourceOutputMapping",
  ],
  extensions: ["FootballBuddy", "TacticalStudio"],
});
async function init() {
  [match, health] = await Promise.all([api("/api/clip"), api("/api/health")]);
  storyMap = { ...match, enhancedAvailable: true };
  pitch.setStory(match);
  $("#follow-player").replaceChildren(new Option("All roles", "all"));
  for (const p of match.roster)
    $("#follow-player").add(new Option(roleName(p), p.id));
  if (!match.roster.some((p) => p.id === preferences.player))
    preferences.player = "all";
  $("#follow-player").value = preferences.player;
  $("#familiarity").value = preferences.familiarity;
  $("#watch-purpose").value = preferences.purpose;
  $("#preference-status").textContent =
    "Follow a visible role in the reviewed still. Unverified players are not assigned names.";
  $("#moment-kicker").textContent = "PitchPrism · Your football companion";
  $("#moment-title").textContent = "Read every attack";
  $("#moment-subtitle").textContent =
    "Immersive viewing · Tactical detail · Evidence-backed insights";
  $("#moment-heading").hidden = true;
  pitch.setStyle(getConfig().halfCourt);
  video.addEventListener(
    "loadedmetadata",
    () => {
      video.currentTime = 1.4;
      refresh(true);
    },
    { once: true },
  );
  video.src = new URL(
    "./media/enhanced.mp4?v=broadcast-v1",
    import.meta.url,
  ).href;
  video.load();
  const mode = new URLSearchParams(location.search).get("mode");
  if (["halfCourt", "fullCourt"].includes(mode)) setMode(mode);
  showControls();
}
init().catch((error) => notice(error.message));
window.addEventListener("pagehide", (event) => {
  if (event.persisted) return;
  buddy.destroy();
  studio.destroy();
  layout.destroy();
  pitch.destroy();
  controls.destroy();
  glass.destroy();
  inspector.destroy();
  stopAmbienceSource($("#ambience"));
});
