# GameBuddy reuse and football adaptation

Independent repository from upstream snapshot `17d74fd2a5df64a240198a7305312174de7684b0`. The original GameBuddy checkout remains unchanged.

The initial synthetic dashboard was superseded after user feedback. The current frontend directly imports the **original** StageLayout, GlassManager, PlayerControls, Drawer, ContentPanel, Inspector, GameBuddyAmbient, CourtPanel, timeline mapping and preference persistence. `football-pitch.js` wraps CourtPanel and substitutes football geometry/data. `style.css` contains limited source-specific/readability/responsive corrections; the original player materials and interaction system remain in charge.

`gamebuddy_fx.py` imports the original `broadcast_fx.legacy` and `broadcast_fx.tactics`: Layers, render_intro, render_outro, draw_caption, draw_marker, draw_path and easing. Reviewed football foot anchors and editorial board positions replace basketball-specific scene inputs. Branding copy is an optional extension whose original defaults remain unchanged. The upstream assets use Python/OpenCV/Pillow/FFmpeg, not Remotion.

Active entry: `product/football/`. Original modules under `product/watch/` and `product/broadcast-fx/`. The real source is hash-bound by `data/clip.json`; synthetic analytics remain in `data/match.json` for regression and a separate potential rules-compliant event scenario. They are never merged.

| Original role | Football path |
|---|---|
| Bedrock / AgentCore | Shared bounded tool loop + Azure Foundry v1 transport and real-clip context |
| Lambda / worker | Single Python container app and fixed pre-rendered scene |
| S3 / CloudFront | Pages for static LOCAL demo; Azure Container Apps template for server |
| SageMaker model training | No retraining; canonical observation tools |

The active app requires no AWS service. Azure credentials/subscription remain unavailable; no live Microsoft inference is claimed. Generated media stays outside source control and is downloaded with frozen hashes. See [source analysis](SOURCE-ANALYSIS.md) and [validation](VALIDATION.md).
