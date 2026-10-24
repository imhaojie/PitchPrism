const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const clip = JSON.parse(
  fs.readFileSync(path.join(__dirname, "../football/data/clip.json"), "utf8"),
);
const model = import("../football/watch/tactical-model.js");

test("every tactical reading refers only to roles and routes in its reviewed still", async () => {
  const { analysisFor } = await model;
  for (const scene of clip.scenes) {
    const reading = analysisFor(scene);
    const roles = new Set(scene.players.map((p) => p.id));
    assert.equal(reading.steps.length, 3);
    for (const step of reading.steps) {
      for (const id of step.focus)
        assert.ok(roles.has(id), `${scene.id}: unknown role ${id}`);
      for (const index of step.routes) {
        const route = scene.routes[index];
        assert.ok(route, `${scene.id}: unknown route ${index}`);
        assert.ok(roles.has(route.a) && roles.has(route.b));
      }
    }
  }
});

test("camera overlays retain reviewed pixel anchors instead of using editorial board coordinates", async () => {
  const { sceneGraphics } = await model;
  for (const scene of clip.scenes) {
    const camera = sceneGraphics(scene, { camera: true });
    for (const player of scene.players) {
      assert.ok(
        camera.includes(
          `transform="translate(${player.foot[0]} ${player.foot[1]})"`,
        ),
      );
    }
    assert.ok(!camera.includes("NaN"));
    assert.ok(!camera.includes("undefined"));
  }
});

test("layers can be removed independently without dropping the reviewed players", async () => {
  const { sceneGraphics, pitchSVG, analysisFor } = await model;
  const scene = clip.scenes[2];
  const graphics = sceneGraphics(scene, {
    routes: false,
    zones: false,
    labels: false,
  });
  assert.ok(!graphics.includes('class="tactic-route'));
  assert.ok(!graphics.includes('class="tactic-defense'));
  assert.ok(!graphics.includes('class="tactic-label'));
  assert.ok(graphics.includes('data-role="carrier"'));
  assert.ok(pitchSVG(null).includes("非实时追踪"));
  assert.equal(analysisFor(null), null);
});

const story = JSON.parse(
  fs.readFileSync(
    path.join(__dirname, "../football/data/tactical-story.json"),
    "utf8",
  ),
);
const timing = import("../watch/adapters/editorial-timeline.js");
const mapping = import("../watch/adapters/catalog.js");

test("web reading focus and option arrows match the English burned-in editorial script", async () => {
  const { analysisFor, sceneGraphics } = await model;
  for (const scene of clip.scenes) {
    const web = analysisFor(scene);
    story.scenes[scene.id].steps.forEach((step, i) => {
      assert.deepEqual(web.steps[i].focus, step.focus);
      assert.deepEqual(web.steps[i].routes, step.routes);
      const graphics = sceneGraphics(scene, { step: i });
      assert.ok(!graphics.includes("tactic-defense"));
      assert.ok(!graphics.includes("is-relation"));
      assert.ok(
        !graphics.includes(">BALL<") &&
          !graphics.includes(">PRESS<") &&
          !graphics.includes(">RUN<"),
      );
    });
  }
});

test("all six chapter seeks and nine reading steps map to the reviewed movie, without future evidence", async () => {
  const { presentationTimeForSource, reviewAt } = await timing;
  const { outputToSourceTime } = await mapping;
  const match = { ...clip, enhancedAvailable: true };
  const expected = [2.8, 11.2, 36.4, 42.6, 54.2, 86.4];
  clip.chapters.forEach((chapter, i) => {
    const output = presentationTimeForSource(match, chapter.start);
    assert.ok(Math.abs(output - expected[i]) < 0.00001);
    assert.ok(
      Math.abs(outputToSourceTime(match, output) - chapter.start) < 0.00001,
    );
  });
  for (const freeze of clip.production.timeline.filter(
    (s) => s.kind === "freeze",
  )) {
    for (let step = 0; step < 3; step++) {
      const output = presentationTimeForSource(match, freeze.sourceStart, step);
      assert.deepEqual(reviewAt(match, output), { scene: freeze.scene, step });
      assert.equal(outputToSourceTime(match, output), freeze.sourceStart);
    }
    assert.equal(reviewAt(match, freeze.outputStart - 0.04), null);
    assert.equal(reviewAt(match, freeze.outputEnd), null);
    assert.deepEqual(reviewAt(match, freeze.outputStart + 4.1), {
      scene: freeze.scene,
      step: 1,
    });
  }
  assert.equal(outputToSourceTime(match, 109.6), 56.8);
  assert.ok(Math.abs(outputToSourceTime(match, 112.4) - 58.2) < 0.00001);
  assert.equal(outputToSourceTime(match, 118.4), 66.56);
});

test("every rendered role label stays in frame and avoids every other label in all nine readings", async () => {
  const { sceneGraphics } = await model;
  for (const scene of clip.scenes)
    for (const camera of [true, false])
      for (let step = 0; step < 3; step++) {
        const svg = sceneGraphics(scene, { camera, step });
        const boxes = [];
        for (const group of svg.matchAll(
          /<g transform="translate\(([\d.]+) ([\d.]+)\)"[^>]*>([\s\S]*?)<\/g>/g,
        )) {
          const rect = group[3].match(
            /<rect ([^>]*class="tactic-label-bg"[^>]*)>/,
          );
          if (!rect) continue;
          const attrs = Object.fromEntries(
            [...rect[1].matchAll(/(\w+)="([^"]+)"/g)].map((m) => [m[1], m[2]]),
          );
          boxes.push({
            x: Number(group[1]) + Number(attrs.x),
            y: Number(group[2]) + Number(attrs.y),
            w: Number(attrs.width),
            h: Number(attrs.height),
          });
        }
        const [w, h] = camera ? [1280, 720] : [68, 105];
        for (let i = 0; i < boxes.length; i++) {
          const a = boxes[i];
          assert.ok(
            a.x >= 0 && a.y >= 0 && a.x + a.w <= w && a.y + a.h <= h,
            `${scene.id}/${step}: clipped label`,
          );
          for (const b of boxes.slice(i + 1))
            assert.ok(
              !(
                a.x < b.x + b.w &&
                a.x + a.w > b.x &&
                a.y < b.y + b.h &&
                a.y + a.h > b.y
              ),
              `${scene.id}/${step}: overlapping labels`,
            );
        }
        assert.ok(boxes.length > 0);
      }
});
