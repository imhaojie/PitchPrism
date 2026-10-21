# PitchPrism · 当前交接

2026-10-21。独立项目，原 GameBuddy 仓库未修改。用户要求恢复完整原版视觉，并指定 `/Users/jack/work/BroadcastCode/match.mp4` 为实际测试素材。默认入口 `python3 -m product.football.server --port 4180`。

当前前端真正导入 GameBuddy 的三态布局、玻璃材质、播放器、抽屉、内容面板、Inspector、CourtPanel、小伙伴动画和时间映射。足球适配只替换几何/数据/必要文案与样式。实际特效库为 Python/OpenCV/Pillow/FFmpeg，不是 Remotion。

源片66.6秒，曼城对纽卡斯尔，画面0–0，无进球。人工逐段审核，三个定格8.0、37.8、56.8秒，SHA绑定在 `product/football/data/clip.json`。全源片保留，新增原版开场、光圈/箭头、战术板形变、半速回放、片尾，输出97.2秒1080p/25fps。原片/增强片全解码通过；556项行为测试及完整门禁通过。浏览器完成真实播放、切换、回看、偏好、全屏、三态等验收。

`data/match.json` 为独立合成数据测试，不与真实视频混用。没有官方xG、全场统计或可靠球员身份时保留缺失。战术板是编辑示意，非自动追踪。LOCAL解读是审核观察的本地模板，不冒充模型输出。

Azure CLI 已安装，首次登录当时无订阅。用户选择免费试用；尚无已确认可用订阅，无实际Foundry调用或Azure部署。不得升级付费。原REST工具循环增加真实片段context，继续使用相同读证据/验证/预算逻辑。

冻结媒体从 `football-match-v2` release 获取，以 `data/media-lock.json` 核验；源码Git不含MP4。复现渲染须提供与源SHA一致的原始match.mp4，重新封装的source.mp4哈希不同，不能当原输入。

入口和交付见 [README](README.md)、[源片分析](docs/football/SOURCE-ANALYSIS.md)、[复用说明](docs/football/MIGRATION.md)、[验收](docs/football/VALIDATION.md)。旧football-demo-v1为被用户否定的历史合成版本，不再作为当前成果。赛制新作品/旧获奖项目复用资格、广播素材许可、视频平台URL和实际微软云验收仍未完成。
