// Original vector companion for PitchPrism; no basketball atlas or external asset.
export function mountFootballBuddy(container) {
  const host = document.createElement("div");
  host.className = "football-buddy";
  host.dataset.action = "idle";
  host.innerHTML = `<svg viewBox="0 0 160 170" aria-hidden="true">
    <defs>
      <radialGradient id="buddy-shell" cx="32%" cy="24%" r="80%"><stop stop-color="#fff"/><stop offset=".55" stop-color="#e2f4f1"/><stop offset="1" stop-color="#7baeb6"/></radialGradient>
      <linearGradient id="buddy-boot" x2="0" y2="1"><stop stop-color="#80f7db"/><stop offset="1" stop-color="#138c94"/></linearGradient>
      <clipPath id="buddy-clip"><circle cx="80" cy="75" r="47"/></clipPath>
    </defs>
    <ellipse class="buddy-shadow" cx="80" cy="146" rx="37" ry="7" fill="#031e2d" opacity=".5"/>
    <g class="buddy-body">
      <path d="M38 84Q17 87 19 105M122 84Q143 81 140 63" fill="none" stroke="#9fffe7" stroke-width="8" stroke-linecap="round"/>
      <path d="M58 116 54 133M100 116 106 133" stroke="#99bac8" stroke-width="8" stroke-linecap="round"/>
      <path d="M54 129q-22-3-21 10 9 8 32 2l-1-10M106 129q22-3 21 10-9 8-32 2l1-10" fill="url(#buddy-boot)" stroke="#b9fff1" stroke-width="2"/>
      <circle cx="80" cy="75" r="49" fill="#b3fff0" opacity=".12"/>
      <circle cx="80" cy="75" r="47" fill="url(#buddy-shell)" stroke="#e2fff9" stroke-width="2"/>
      <g clip-path="url(#buddy-clip)" fill="#203c50" stroke="#6f97a3" stroke-width="1.2">
        <path d="m70 29 23-2 11 20-21 14-24-14zM32 53l21-10 8 22-14 19-20-9zM116 49l17 12 1 23-20 1-9-22zM49 103l21-5 13 17-13 17-23-7zM99 103l20-9 13 15-9 20-24 3z"/>
        <path d="m83 61-2 15M47 84l14 13M114 85l-14 18M83 115l16 17M61 47 53 43M104 47l12 2" fill="none"/>
      </g>
      <path d="M48 76q32-14 64 0v19q-31 14-64 0z" fill="#102e40" stroke="#81d7d2" stroke-width="1.5"/>
      <g class="buddy-eyes" fill="#a6ffdc"><rect x="59" y="78" width="9" height="14" rx="4.5"/><rect x="91" y="78" width="9" height="14" rx="4.5"/></g>
      <path d="M74 96q6 5 12-1" fill="none" stroke="#c1ffec" stroke-width="2" stroke-linecap="round"/>
      <path d="M46 53q3-13 17-17" fill="none" stroke="#fff" stroke-width="4" stroke-linecap="round" opacity=".8"/>
      <path class="buddy-spark" d="m133 25 2 7 7 2-7 2-2 7-2-7-7-2 7-2z" fill="#b8ffe4"/>
    </g>
  </svg><span class="buddy-name">PRISM <i>●</i></span>`;
  container.replaceChildren(host);
  return {
    play(action) {
      host.dataset.action = action;
    },
    destroy() {
      host.remove();
    },
  };
}
