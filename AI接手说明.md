# PitchPrism · 当前交接

独立新项目，GameBuddy 原仓库未修改。默认入口：`python3 -m product.football.server --port 4180`。

见 [README](README.md)、[迁移记录](docs/football/MIGRATION.md)、[验收](docs/football/VALIDATION.md) 和 [Azure 配置](infra/azure/README.md)。

已实现合成足球数据、足球统计、英文观赛界面、复用播放器与双时间轴、球迷/分析师及球队/球员偏好、战术事件图、Foundry REST 工具循环适配、本地解释、MP4 渲染、Pages 物化演示及 Azure Bicep。

Azure CLI 已安装。首次登录识别账号，但当时没有订阅；用户随后选择免费试用，身份与银行卡步骤由其本人完成。尚无实际模型成功或 Azure 部署证据。不能把适配器测试、Bicep 编译或 Pages LOCAL 演示说成微软云成功接入。

原 GameBuddy 说明保存在 README-GAMEBUDDY.md、GAMEBUDDY-HANDOFF.md。篮球材料保留为复用和回归来源，不由足球 HTTP 服务公开。
