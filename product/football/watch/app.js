import { getConfig, subscribe, updateConfig } from "./shared/config/config.js";
import { createStageLayout } from "./shared/stage/layout.js";
import { GlassManager } from "./shared/glass/glass-manager.js";
import {
  paintAmbienceSource,
  stopAmbienceSource,
} from "./shared/glass/ambience-source.js";
import { createPlayerControls } from "./shared/media/player-controls.js";
import { createDrawer } from "./shared/navigation/drawer.js";
import { createContentPanel } from "./shared/content/content-panel.js";
import { createInspector } from "./shared/dev/inspector.js";
import { mountFootballBuddy } from "./football-buddy.js";
import { createTacticalStudio } from "./tactical-studio.js";
import {
  outputToSourceTime,
  readPreferences,
  savePreferences,
} from "./shared/adapters/catalog.js";
import { createFootballPitch } from "./football-pitch.js";
import {
  presentationTimeForSource,
  reviewAt,
} from "./shared/adapters/editorial-timeline.js";
import { api } from "./transport.js";

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
  onError: notice,
  onMenuChange: (value) => {
    activeMenu = value;
    showControls();
  },
});
$("#controls-host").append(controls.element);
const drawer = createDrawer({
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
    notice("本机存储不可用，偏好仅用于当前页面。");
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
    ? `定格 ${state.scene.clock} / 原片 ${state.scene.second.toFixed(2)}s`
    : "播放片段 / 画面观察";
  panelBody(
    `<div class="content-badge">${currentStory.provider === "azure-foundry" ? "AZURE FOUNDRY" : "LOCAL EDITORIAL"} · ${esc(source)}</div><h3 class="football-story-title">${esc(currentStory.headline)}</h3><p class="football-story-copy">${esc(currentStory.explanation)}</p><div class="football-metric-grid"><div class="football-metric"><small>画面记分牌</small><strong>0 – 0</strong><small>Manchester City / Newcastle</small></div><div class="football-metric"><small>原片时间</small><strong>${state.sourceSecond.toFixed(1)} <small>s</small></strong><small>原片与增强片同步</small></div><div class="football-metric"><small>官方 xG</small><strong>—</strong><small>未提供，保留缺失</small></div><div class="football-metric"><small>全场传球成功率</small><strong>—</strong><small>片段不足以计算</small></div></div><button class="football-explain" id="explain-moment" ${explaining ? "disabled" : ""}>✦ ${explaining ? "正在读取证据…" : "解读这一刻"}</button><p class="football-source-note">${health.foundryConfigured ? "Foundry 已配置；实际调用成功后才标记为云模型解读。" : "本地编辑解读 · Azure Foundry 尚未配置。"}</p><details><summary>查看本条解读的画面证据</summary><pre class="football-source">${esc(
      JSON.stringify(
        state.events.filter((e) => currentStory.evidenceIds.includes(e.id)),
        null,
        2,
      ),
    )}</pre></details><p class="football-source-note">人物光圈对应人工审核的定格帧。战术板与虚线是编辑示意，不是自动追踪或实际传球数据。</p>`,
    "这一刻的解读",
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
      sourceLabel: "已审核原片画面 · 非官方事件记录",
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
      "章节标注原片时间；跳转会定位增强片中的对应时刻。审核定格包含三步解析，虚线表示可选线路。";
    content.element.querySelector(".content-sheet-body").append(note);
    return;
  }
  if (kind === "data") {
    paintInsights();
    return;
  }
  if (kind === "library") {
    panelBody(
      '<p class="content-lead">同一素材，同一原始时间。</p><div class="football-actions"><button id="choose-source">观看原片</button><button id="choose-enhanced">观看增强片</button><button id="restart-highlight">从头播放</button></div><p class="football-source-note">增强片包含三组分步解析、选项箭头、角色高亮、战术板转场与半速回放。章节按原片时刻定位，播放器显示增强片时间。</p>',
      "片段与版本",
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
    `<p class="content-lead">PitchPrism · 让比赛成为可读的视觉故事。</p><p class="football-source-note">复核版增强视频：118.4 秒，1080p / 25fps。三个审核定格各含三步解析；人物高亮、虚线选项、战术板与半速回看都已烧录进视频。</p><p class="football-source-note">当前素材为曼城对纽卡斯尔 66.6 秒片段，观察记录绑定原文件 SHA-256。足部锚点为人工审核，俯视站位与箭头为编辑示意。官方事件、xG、整场统计与未核验身份保持缺失。</p><p class="football-source-note">公开演示使用本地编辑解读。Azure Foundry 需服务端配置并成功调用后才标记为云模型结果。代码许可、素材权利和第三方归属见项目的 LICENSE 与 THIRD_PARTY_NOTICES。</p>`,
    "关于 PitchPrism",
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
  video.src = new URL(`./media/${next}.mp4?v=1.0.0`, import.meta.url).href;
  video.load();
  $("#media-version").textContent =
    next === "enhanced" ? "切换原片 ›" : "切换增强片 ›";
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
inspector = createInspector();
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
    `${variant === "enhanced" ? "增强片" : "原片"} · ${video.videoWidth} × ${video.videoHeight} · ${video.duration.toFixed(2)}s`;
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
  $("#follow-player").replaceChildren(new Option("全队", "all"));
  for (const p of match.roster)
    $("#follow-player").add(new Option(p.name, p.id));
  if (!match.roster.some((p) => p.id === preferences.player))
    preferences.player = "all";
  $("#follow-player").value = preferences.player;
  $("#familiarity").value = preferences.familiarity;
  $("#watch-purpose").value = preferences.purpose;
  $("#preference-status").textContent =
    "关注定格中的角色；未核验的球员不补姓名。";
  $("#moment-kicker").textContent = "PitchPrism · 足球观赛伙伴";
  $("#moment-title").textContent = "看懂每一次进攻";
  $("#moment-subtitle").textContent = "沉浸观看 · 战术展开 · 证据解读";
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
  video.src = new URL("./media/enhanced.mp4?v=1.0.0", import.meta.url).href;
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
