import {
  analysisFor,
  escapeHTML as esc,
  pitchSVG,
  sceneGraphics,
} from "./tactical-model.js?v=english-v1";

export function createTacticalStudio({ stage, onSeek, onClose }) {
  const dialog = document.createElement("dialog");
  dialog.className = "tactical-studio";
  dialog.setAttribute("aria-label", "Tactical Studio");
  dialog.innerHTML = `<div class="studio-shell">
    <header class="studio-header"><div class="studio-brand"><span class="studio-mark">P</span><div><small>PITCHPRISM / TACTICAL STUDIO</small><h1>See the game. Read the moment.</h1></div></div><div class="studio-header-actions"><span class="studio-editorial">● REVIEWED FRAME</span><button class="studio-close" aria-label="Close Tactical Studio">×</button></div></header>
    <nav class="studio-scenes" aria-label="Choose a reviewed moment"></nav>
    <div class="studio-grid"><section class="studio-main">
      <div class="studio-view-heading"><span><i></i> 01 / BROADCAST VIEW</span><span class="studio-source-time"></span></div>
      <div class="studio-camera"><video muted playsinline preload="metadata" aria-label="Reviewed source still"></video><svg class="studio-camera-art" viewBox="0 0 1280 720" aria-label="Reviewed foot anchors and editorial options"></svg><div class="studio-frame-status" role="status">Loading the reviewed source frame…</div><span class="studio-camera-caption">Source still · reviewed anchors</span></div>
      <div class="studio-analysis"><div class="studio-analysis-heading"><span class="studio-tag"></span><span class="studio-counter"></span></div><h2></h2><p class="studio-summary"></p><div class="studio-step-copy" aria-live="polite"><b></b><p></p></div></div>
    </section><aside class="studio-board"><div class="studio-view-heading"><span><i></i> 02 / TACTICAL VIEW</span><span>Schematic</span></div><div class="studio-pitch"></div><div class="studio-key"><span><i class="key-city"></i>Manchester City</span><span><i class="key-new"></i>Newcastle</span><span><i class="key-option"></i>Passing options</span><span><i class="key-defense"></i>Opponents</span></div><p>Pitch positions are editorial schematics, not calibrated tracking.</p></aside></div>
    <footer class="studio-footer"><div class="studio-step-nav" role="group" aria-label="Tactical reading steps"></div><div class="studio-tools"><button class="studio-sequence" aria-pressed="false">▷ Play readings</button><label><input type="checkbox" data-layer="routes" checked>Routes</label><label><input type="checkbox" data-layer="zones" checked>Focus area</label><label><input type="checkbox" data-layer="labels" checked>Labels</label></div><p class="studio-limitation"></p></footer>
  </div>`;
  stage.append(dialog);
  const $ = (s) => dialog.querySelector(s),
    preview = $("video");
  preview.src = new URL("./media/source.mp4", import.meta.url).href;
  let match = null,
    scene = null,
    step = 0,
    timer = null,
    returnFocus = null;
  const layers = { routes: true, zones: true, labels: true };
  function stop() {
    clearInterval(timer);
    timer = null;
    $(".studio-sequence").setAttribute("aria-pressed", "false");
    $(".studio-sequence").textContent = "▷ Play readings";
  }
  function paint() {
    if (!scene) return;
    const plan = analysisFor(scene),
      reading = plan.steps[step];
    $(".studio-camera-art").innerHTML = sceneGraphics(scene, {
      camera: true,
      step,
      ...layers,
      prefix: "camera",
    });
    $(".studio-pitch").innerHTML = pitchSVG(scene, {
      step,
      ...layers,
      prefix: "studio-board",
    });
    $(".studio-counter").textContent =
      `${String(step + 1).padStart(2, "0")} / 03`;
    $(".studio-step-copy b").textContent = reading.title;
    $(".studio-step-copy p").textContent = reading.text;
    dialog
      .querySelectorAll("[data-step]")
      .forEach((button) =>
        button.setAttribute(
          "aria-pressed",
          String(Number(button.dataset.step) === step),
        ),
      );
  }
  function checkFrame() {
    const ready =
      scene &&
      preview.readyState >= 2 &&
      Math.abs(preview.currentTime - scene.second) < 0.08;
    $(".studio-camera").classList.toggle("is-ready", !!ready);
    $(".studio-frame-status").hidden = !!ready;
  }
  function locate() {
    if (scene && preview.readyState >= 1) {
      preview.pause();
      preview.currentTime = scene.second;
      checkFrame();
    }
  }
  preview.addEventListener("loadedmetadata", locate);
  preview.addEventListener("seeked", checkFrame);
  preview.addEventListener("loadeddata", checkFrame);
  preview.addEventListener("error", () => {
    $(".studio-frame-status").hidden = false;
    $(".studio-frame-status").textContent =
      "Source frame unavailable. Check the media files.";
    $(".studio-camera").classList.remove("is-ready");
  });
  function select(next, { seek = false, initialStep = 0 } = {}) {
    stop();
    scene = next;
    step = initialStep;
    if (seek) onSeek(scene.second, step);
    const plan = analysisFor(scene);
    $(".studio-camera").classList.remove("is-ready");
    $(".studio-frame-status").hidden = false;
    $(".studio-frame-status").textContent =
      "Loading the reviewed source frame…";
    $(".studio-source-time").textContent =
      `${scene.clock} · SOURCE ${scene.second.toFixed(2)}s`;
    $(".studio-tag").textContent = plan.tag;
    $(".studio-analysis h2").textContent = plan.title;
    $(".studio-summary").textContent = plan.summary;
    $(".studio-limitation").textContent = plan.limitation;
    $(".studio-step-nav").innerHTML = plan.steps
      .map(
        (s, i) =>
          `<button data-step="${i}" aria-pressed="${i === 0}"><span>${String(i + 1).padStart(2, "0")}</span>${esc(s.title)}</button>`,
      )
      .join("");
    dialog.querySelectorAll("[data-step]").forEach(
      (button) =>
        (button.onclick = () => {
          stop();
          step = Number(button.dataset.step);
          onSeek(scene.second, step);
          paint();
        }),
    );
    dialog
      .querySelectorAll("[data-scene]")
      .forEach((button) =>
        button.setAttribute(
          "aria-pressed",
          String(button.dataset.scene === scene.id),
        ),
      );
    locate();
    paint();
  }
  $(".studio-close").onclick = () => dialog.close();
  dialog.addEventListener("close", () => {
    stop();
    preview.pause();
    returnFocus?.focus();
    onClose?.();
  });
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  });
  document.addEventListener("visibilitychange", onVisibility);
  function onVisibility() {
    if (document.hidden) stop();
  }
  $(".studio-sequence").onclick = () => {
    if (timer) {
      stop();
      return;
    }
    step = 0;
    onSeek(scene.second, step);
    paint();
    $(".studio-sequence").setAttribute("aria-pressed", "true");
    $(".studio-sequence").textContent = "Ⅱ Pause readings";
    timer = setInterval(() => {
      if (step >= 2) {
        stop();
        return;
      }
      step++;
      onSeek(scene.second, step);
      paint();
    }, match.production.readingStepSeconds * 1000);
  };
  dialog.querySelectorAll("[data-layer]").forEach(
    (input) =>
      (input.onchange = () => {
        layers[input.dataset.layer] = input.checked;
        paint();
      }),
  );
  return {
    open(data, state, review) {
      match = data;
      returnFocus = document.activeElement;
      $(".studio-scenes").innerHTML = match.scenes
        .map(
          (s, i) =>
            `<button data-scene="${s.id}" aria-pressed="false"><span>0${i + 1}</span><b>${esc(analysisFor(s).title)}</b><time>${s.clock}</time><small>Jump to freeze ↗</small></button>`,
        )
        .join("");
      dialog.querySelectorAll("[data-scene]").forEach(
        (button) =>
          (button.onclick = () =>
            select(
              match.scenes.find((s) => s.id === button.dataset.scene),
              { seek: true },
            )),
      );
      const first = state?.scene || match.scenes[0];
      select(first, {
        seek: !state?.scene,
        initialStep: review?.scene === first.id ? review.step : 0,
      });
      dialog.showModal();
      $(".studio-close").focus();
    },
    get isOpen() {
      return dialog.open;
    },
    close() {
      dialog.close();
    },
    destroy() {
      stop();
      document.removeEventListener("visibilitychange", onVisibility);
      preview.removeAttribute("src");
      preview.load();
      dialog.remove();
    },
  };
}
