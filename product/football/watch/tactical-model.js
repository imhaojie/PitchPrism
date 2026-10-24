// Editorial reading of the three reviewed stills. Never tracking or completed-pass data.
export const escapeHTML = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const plans = {
  build: {
    title: "带球推进，读出接应层次",
    tag: "BUILD-UP / 推进观察",
    summary:
      "先找持球人，再比较内侧接应与远侧宽度。画面呈现的是当下站位；线路表达可供观察的选择。",
    steps: [
      {
        title: "锁定持球人与近侧对手",
        text: "持球角色向中线附近推进。先比较他与前方最近纽卡球员的位置，再观察球是否继续向前。",
        focus: ["carrier", "press"],
        routes: [],
      },
      {
        title: "寻找前方接应",
        text: "前方的 LINK 角色提供一个可观察的连接点。青色虚线连接两人的示意位置，不代表传球已经发生或线路畅通。",
        focus: ["carrier", "support"],
        routes: [0],
      },
      {
        title: "把远侧宽度纳入视野",
        text: "远侧 WIDE 角色靠近边线。比较持球、接应、远侧三个位置和不同方向；虚线为独立选项，不是连续传球记录。后续是否采用这一选择要回到原片确认。",
        focus: ["carrier", "support", "wide"],
        routes: [0, 1],
      },
    ],
    limitation: "此帧不能证明对手已被吸引、传球一定成功或进攻即将形成机会。",
  },
  combine: {
    title: "由边入内，观察前方接应",
    tag: "INFIELD / 内侧连接",
    summary:
      "球已来到内侧。将持球、前方跑位与球门前的防守角色一起阅读，比只盯住球更容易理解这一帧。",
    steps: [
      {
        title: "先确认球所在的位置",
        text: "持球角色出现在内侧。比较持球人与后方 LINK 接应的位置；这一步不画传球线。",
        focus: ["support", "carrier"],
        routes: [],
      },
      {
        title: "看向禁区弧附近的队友",
        text: "SUPPORT 角色位于更接近禁区弧的位置。青色虚线提示一个值得关注的接应方向；它不是预测路线，也没有测量传球难度。",
        focus: ["carrier", "runner"],
        routes: [0],
      },
      {
        title: "同时阅读球门前的防守",
        text: "纽卡球员位于球与球门之间。逐个高亮防守角色，比较其与接应者的位置；无法据此确认越位或防守意图。",
        focus: ["carrier", "runner", "cover", "line", "deep"],
        routes: [0],
      },
    ],
    limitation:
      "没有官方事件、校准坐标或连续追踪，不能给出精确距离、越位结论或球员身份。",
  },
  release: {
    title: "中央受限，把视线转向右侧",
    tag: "RIGHT OPTION / 右侧观察",
    summary:
      "中央持球人与附近对手形成第一关注点；右侧队友是第二关注点。分步高亮让两处位置之间的关系更清楚。",
    steps: [
      {
        title: "从中央的持球点开始",
        text: "纽卡球员靠近中央持球角色。金色光圈突出当前关注区域，仅用于阅读画面，不表示计算出的施压强度。",
        focus: ["carrier", "press"],
        routes: [],
      },
      {
        title: "找到右侧可见队友",
        text: "RIGHT 角色位于右侧、靠近禁区边缘。箭头提示从中央看向右侧的选择，不表示这条路线已开放或一定会被采用。",
        focus: ["carrier", "right"],
        routes: [0],
      },
      {
        title: "把右侧接应与对手一起看",
        text: "右侧附近仍有防守角色。将 RIGHT、邻近对手与中央持球人一起比较，然后回到视频查看接下来的动作。",
        focus: ["carrier", "right", "cover", "line"],
        routes: [0],
      },
    ],
    limitation:
      "箭头是定格时刻的选项示意；不预测后续传球，也不推断进球、xG 或整场表现。",
  },
};
export const analysisFor = (scene) => plans[scene?.id] || null;
export const roleName = (p) =>
  ({
    carrier: "持球",
    press: "近侧对手",
    support: "接应",
    wide: "远侧宽度",
    inside: "内侧",
    cover: "防守",
    screen: "防守",
    runner: "前方接应",
    left: "边路",
    right: "右侧接应",
    line: "防守",
    deep: "防守",
  })[p.id] || "可见角色";
export function sceneGraphics(
  scene,
  {
    camera = false,
    step = 2,
    routes = true,
    zones = true,
    labels = true,
    focus = null,
    prefix = "tactic",
  } = {},
) {
  const plan = analysisFor(scene);
  if (!scene || !plan) return "";
  const reading = plan.steps[step],
    project = (p) =>
      camera ? p.foot : [p.board[1] * 0.68, (100 - p.board[0]) * 1.05];
  const scale = camera ? 17 : 1;
  const players = Object.fromEntries(scene.players.map((p) => [p.id, p]));
  const node = (tag, attrs, body = "") =>
    `<${tag} ${Object.entries(attrs)
      .map(([k, v]) => `${k}="${escapeHTML(v)}"`)
      .join(" ")}>${body}</${tag}>`;
  let result = `<defs><marker id="${prefix}-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M1 1 9 5 1 9" fill="none" stroke="#8efbea" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></marker><radialGradient id="${prefix}-zone"><stop stop-color="#ffc66d" stop-opacity=".32"/><stop offset="1" stop-color="#ffc66d" stop-opacity="0"/></radialGradient></defs>`;
  const carrier = players.carrier;
  if (zones) {
    const [x, y] = project(carrier);
    result += node("ellipse", {
      cx: x,
      cy: y,
      rx: 7 * scale,
      ry: (camera ? 3 : 7) * scale,
      fill: `url(#${prefix}-zone)`,
      class: "tactic-zone",
    });
  }
  if (routes)
    scene.routes.forEach((route, i) => {
      const a = players[route.a],
        b = players[route.b];
      if (route.kind !== "option" || !a || !b) return;
      const visible = reading.routes.includes(i),
        [x1, y1] = project(a),
        [x2, y2] = project(b);
      const length = Math.hypot(x2 - x1, y2 - y1),
        offset = 2.9 * scale;
      const dx = (x2 - x1) / length,
        dy = (y2 - y1) / length;
      const d = `M${x1 + dx * offset},${y1 + dy * offset}Q${(x1 + x2) / 2 - dy * 2 * scale},${(y1 + y2) / 2 + dx * 2 * scale} ${x2 - dx * offset},${y2 - dy * offset}`;
      result += node("path", {
        d,
        class: `tactic-route ${route.kind === "option" ? "is-option" : "is-relation"}${visible ? " is-active" : ""}`,
        "stroke-width": (visible ? 0.6 : 0.3) * scale,
        "marker-end": route.kind === "option" ? `url(#${prefix}-arrow)` : "",
        opacity: visible ? 1 : 0.13,
        "stroke-dasharray":
          route.kind === "option" ? `${1.8 * scale} ${1.3 * scale}` : "none",
      });
    });
  const labelBoxes = [];
  const overlaps = (a, b) =>
    a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y;
  for (const p of scene.players) {
    const [x, y] = project(p),
      active = focus ? p.id === focus : reading.focus.includes(p.id),
      r = (camera ? 1.3 : 1.8) * scale;
    let inner = "";
    if (active)
      inner += node("ellipse", {
        cx: 0,
        cy: 0,
        rx: r * 1.9,
        ry: camera ? r * 0.58 : r * 1.9,
        class: "tactic-halo",
        "stroke-width": 0.22 * scale,
      });
    inner += node("ellipse", {
      cx: 0,
      cy: 0,
      rx: r,
      ry: camera ? r * 0.37 : r,
      class: `tactic-dot ${p.team === "MCI" ? "is-city" : "is-newcastle"}`,
      "stroke-width": 0.24 * scale,
    });
    if (!camera)
      inner += node(
        "text",
        { x: 0, y: 0.65, "text-anchor": "middle", class: "tactic-token" },
        p.id === "carrier" ? "●" : p.team === "MCI" ? "◆" : "",
      );
    if (labels && active) {
      const label =
          { carrier: "CARRIER", press: "OPPONENT", runner: "SUPPORT" }[p.id] ||
          p.label ||
          "DEF",
        width = Math.max(7, label.length * 1.35) * scale;
      // Place labels in image/pitch space, avoiding other labels before markers.
      // The same deterministic search works on dense camera and board clusters.
      const anchors = scene.players.map((player) => {
        const [px, py] = project(player);
        return {
          x: px - 2.2 * scale,
          y: py - (camera ? 0.7 : 2.2) * scale,
          w: 4.4 * scale,
          h: (camera ? 1.4 : 4.4) * scale,
        };
      });
      const offsets = [];
      for (const dy of [-6, -10, 4, -14, 8, 12])
        for (const dx of [0, 8, -8, 16, -16, 24, -24]) offsets.push([dx, dy]);
      const candidates = offsets.map(([dx, dy]) => ({
        lx: dx * scale - width / 2,
        ly: dy * scale,
        x: x + dx * scale - width / 2 - 0.7 * scale,
        y: y + (dy - 2.7) * scale,
        w: width + 1.4 * scale,
        h: 3.8 * scale,
        distance: Math.hypot(dx, dy + 6),
      }));
      const bounds = camera ? [1280, 720] : [68, 105];
      const cost = (box) =>
        labelBoxes.filter((other) => overlaps(box, other)).length * 10000 +
        (box.x < 0 ||
        box.x + box.w > bounds[0] ||
        box.y < 0 ||
        box.y + box.h > bounds[1]
          ? 100000
          : 0) +
        anchors.filter((other) => overlaps(box, other)).length * 5 +
        box.distance;
      const box = candidates.reduce((best, next) =>
        cost(next) < cost(best) ? next : best,
      );
      const { lx, ly } = box;
      labelBoxes.push(box);
      inner += node("rect", {
        x: lx - 0.7 * scale,
        y: ly - 2.7 * scale,
        width: width + 1.4 * scale,
        height: 3.8 * scale,
        rx: 0.8 * scale,
        class: "tactic-label-bg",
      });
      inner += node(
        "text",
        {
          x: lx + width / 2,
          y: ly,
          "text-anchor": "middle",
          class: "tactic-label",
          "font-size": 2.25 * scale,
        },
        label,
      );
    }
    result += node(
      "g",
      {
        transform: `translate(${x} ${y})`,
        opacity: active ? 1 : 0.38,
        class: `tactic-person${active ? " is-active" : ""}`,
        "data-role": p.id,
      },
      inner,
    );
  }
  return result;
}
export function pitchSVG(scene, options = {}) {
  const prefix = options.prefix || "board";
  return `<svg class="prism-pitch" viewBox="-3 -6 74 117" role="img" aria-label="已审核定格的足球站位示意，非实时追踪">
  <defs><pattern id="${prefix}-grass" width="68" height="10.5" patternUnits="userSpaceOnUse"><rect width="68" height="10.5" fill="#123b35"/><rect width="68" height="5.25" fill="#18433b"/></pattern><linearGradient id="${prefix}-light" x2="1" y2="1"><stop stop-color="#8cf7e9" stop-opacity=".13"/><stop offset="1" stop-color="#08272d" stop-opacity=".12"/></linearGradient></defs>
  <rect x="-3" y="-6" width="74" height="117" rx="3" fill="#082c2d"/><rect width="68" height="105" fill="url(#${prefix}-grass)"/><rect width="68" height="105" fill="url(#${prefix}-light)"/>
  <g class="prism-pitch-lines"><rect width="68" height="105"/><path d="M0 52.5H68M13.84 0V16.5H54.16V0M24.84 0V5.5H43.16V0M13.84 105V88.5H54.16V105M24.84 105V99.5H43.16V105M30.34 0V-2H37.66V0M30.34 105V107H37.66V105"/><circle cx="34" cy="52.5" r="9.15"/><circle cx="34" cy="11" r=".5"/><circle cx="34" cy="94" r=".5"/><path d="M26.687512 16.5A9.15 9.15 0 0 0 41.312488 16.5M26.687512 88.5A9.15 9.15 0 0 1 41.312488 88.5"/><circle cx="34" cy="52.5" r=".35"/><path d="M0 1A1 1 0 0 0 1 0M67 0A1 1 0 0 0 68 1M68 104A1 1 0 0 0 67 105M1 105A1 1 0 0 0 0 104"/></g>
  <text x="34" y="-3.4" text-anchor="middle" class="pitch-end-label">ATTACK ↑</text><text x="34" y="110" text-anchor="middle" class="pitch-end-label">PITCHPRISM / EDITORIAL VIEW</text>
  <g class="tactic-art">${sceneGraphics(scene, { ...options, prefix })}</g></svg>`;
}
