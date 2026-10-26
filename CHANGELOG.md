# Changelog

## 1.1.0 — 2026-10-26

The demo movie is replaced by the broadcast-package render; timing is unchanged, so every chapter and reading jump still applies.

**Tactical accuracy**
- Reviewed every reading against the footage. Scene 1's "link" arrow ran through the Newcastle presser (0.4 m off the lane) and is now a covered lane; scene 2's runner is level with the ball and central, not ahead or nearer the box. The movie and the web Tactical Studio are corrected together.
- Measure each reviewed still on the ground plane (`data/tactical-geometry.json`, `tactical_geometry.py`) from visible Law 1 markings, checked against the penalty arc. Graphics and the web board use these positions; reviewed `editorialBoard` values are kept alongside.
- Add covered lanes, carry arrows, free-space, pressure and goal-side zones. Every option, lane, carry and zone is refused at render time and in offline tests if the measured positions contradict it.
- Add two verified live captions: Newcastle defending in numbers, and the contest by the corner.

**Visuals**
- Perspective 3D tactical view (`pitch3d.py`): each freeze rises from a touchline angle to an overhead board, then swings behind the attack where anonymous team-coloured figures stand with shadows and light columns. No likeness, number or identity.
- Broadcast identity: deep violet ink, a cyan/green/magenta spectrum accent, bundled Barlow Condensed italic display type (OFL), slanted spectrum lower thirds, spotlight and push-in on stills, notched option arrows and collision-free role chips audited on every frame.
- New brand mark (`watch/mark.svg`): a prism on the centre spot splits the halfway line into three rays.
- New cold open and full-time card, joined to the match by a three-blade spectrum stinger.

Observations and reviewed foot anchors are unchanged; only `production.version` in `clip.json` changes.

## 1.0.1 — 2026-10-24

- Make the complete viewing interface English, including tactical readings, chapters, preferences, accessibility labels and the appearance editor.
- Reuse the reviewed English movie text for all nine interactive reading steps.
- Fit the full English navigation on narrow phones.
- Version static state and frontend module URLs so returning visitors refresh the released movie and matching timeline together.

## 1.0.0 — 2026-10-24

- Publish the reviewed 118.4-second, 1080p/25fps tactical movie with English text, option arrows, role highlights, nine reading steps and half-speed replay.
- Synchronize six chapters, three tactical freezes, source/enhanced switching and interactive reading steps with the published movie.
- Add an interactive Tactical Studio, independently switchable visual layers and an animated football companion.
- Align pitch geometry, role labels and option semantics across the web player and MP4.
- Verify release media hashes and player timing during static export; retain reviewed source/evidence provenance separately from presentation metadata.
- Add release documentation, contribution guidance, security policy and issue/PR templates.

The public demo uses local editorial explanations. Live Azure inference and deployment are not certified by this release.
