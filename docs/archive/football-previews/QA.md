> Historical preview. Use [current validation](../../football/VALIDATION.md) for the released product.

# Browser QA inventory

Claims: actual playable synthetic footage; source/output time mapping; no future evidence in live insights; canonical numeric facts; audience/team/player personalization; readable desktop/mobile layout; separate local/cloud status.

| Control / state | Functional check | Visual evidence |
|---|---|---|
| Play/pause, seek | Time advances, stops and follows source mapping | Match room |
| Speed menu | Select 0.5×, restore 1×; menu closes | Player controls |
| Mute/volume | Toggle both ways; volume updates | Player controls |
| Fullscreen | Enter/exit, controls remain accessible | Full stage |
| Source/enhanced | Same original moment before/after; restore | Both media variants |
| Tactical/match | Canvas draws pitch and paths, toggle back | Tactical screenshot |
| Fan/analyst | Different copy and distance label; restore | Both audience states |
| Team/player | Highlight/filter; switch all and back | Focused player screenshot |
| Chapters | Exact switch/shot/goal source boundaries; rewind removes goal | Score/facts/evidence |
| Source events | Cited IDs and synthetic provenance; close/Escape | Source dialog |
| Explain | LOCAL result stays LOCAL; no fake request trace | Provider note |
| Recap | Explicit full-excerpt scope; close | Recap dialog |
| About / transparency | Accurate provenance, scope and model status | Dialogs |
| Preference reload | Audience/player restored | Persisted state |
| Mobile | No horizontal overflow; player controls reachable | 390 × 844 screenshot |

Exploratory cases: a selected player without events; conflicting team/player selection; rapid chapter changes; source rewind during explanation; initial tactical canvas resize; corrupted local preferences. Cloud failure tests remain protocol tests until live access exists.
