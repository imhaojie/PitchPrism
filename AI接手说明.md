# PitchPrism 当前维护说明

2026-10-24。先读 [README](README.md)、[架构](docs/football/ARCHITECTURE.md)、[媒体流程](docs/football/MEDIA.md) 和 [来源归属](docs/football/MIGRATION.md)。默认入口为 `python -m product.football.server --port 4180`；活动目录为 `product/football/`。

## 当前媒体与时钟

当前正式版本为 v1.0.0。网页使用复核版 118.4 秒、1920×1080、25fps 增强视频，SHA-256 为 `986f282682283a789c40150832840db910dd1ce16e0017318558fda021f5e0ed`。这是已交付的 `build/tactical-v4/PitchPrism-Enhanced-Reviewed.mp4` 的原字节副本，没有重新编码。媒体通过 GitHub Release 分发，不入 Git。

原片 66.6 秒，MCI 0–0 NEW，无进球。原始输入与无损重封装文件是不同哈希；见 `data/source-lock.json`。人工审核的观察、足部锚点和示意站位保持不变。`data/clip.json` 的 production 已更新为复核版时间轴；release manifest 分开记录原渲染输入的数据哈希和当前网页数据哈希。

三个定格在增强时间 10.8–24.0、53.8–67.0、86.0–99.2 秒，分别对应原片 8、37.8、56.8 秒。每个定格的三步解析在本地偏移 0、4.1、8.2 秒切换。章节和步骤跳转通过 `product/watch/adapters/editorial-timeline.js`；跳转含 0.4 秒稳定显示偏移。切换原片与增强片保留原片时刻。

## 产品与发布

足球伙伴为 `football-buddy.js` 的 SVG/CSS 动画。战术演播室支持三个定格、三步解析和图层开关；角色及线路与烧录英文稿 `data/tactical-story.json` 一致，测试校验这一约束。不画防守连接线或历史传球关系线；虚线仅为选项。名义球场按 105×68m 与 IFAB Law 1 几何推导，非校准追踪。

媒体下载和静态导出同时检查三个资产的哈希、数据绑定和时间轴。正式发布流程见媒体文档。完整门禁、浏览器和媒体解码是不同验收层；记录见 [当前验收](docs/football/VALIDATION.md)。历史文档归档，README 面向当前产品。

`data/match.json` 是独立合成测试，禁止与真实视频混用。缺少官方事件、xG、全场统计及可靠身份时保持缺失；不得从未来观察支持当前解读。

Azure Foundry 适配器和 Bicep 已实现，但真实部署和模型调用仍未核验。免费试用要求、禁止付费升级及禁止 AWS 资源变更的约束继续有效。GitHub Pages 为 LOCAL EDITORIAL，不冒充云输出。比赛资格、素材授权与受支持视频平台 URL 仍是独立提交事项；不因发布版本而自动完成。
