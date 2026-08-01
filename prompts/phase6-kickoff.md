# Codex 首条提示词：Phase 6 交接恢复

这是 C5 麦克纳姆守门员项目的 Phase 6 新任务。请先完成一次只读恢复与重新定向，
不要直接实现算法。

1. 若当前工作区只有 U 盘 handoff 包，先读包根目录 `README-FIRST.md`，校验
   `manifests/files.sha256`，按说明从 GitHub 指定分支或离线 Git bundle 重建仓库，
   再覆盖 `workspace-overlay/`；不要把 overlay 中的模型、视频、商家资料提交 Git。
2. 读取仓库 `AGENTS.md`、`README.md`、`tasks/current.md`、
   `docs/handoff-phase6.md`、`docs/goalkeeper-behavior.md`、
   `docs/ball-follow-control.md`、`docs/host-link.md` 和 `docs/unresolved.md`。
3. 用有界查询核对分支、提交、工作区状态、外部资产、默认 RKNN 模型和本机工具；
   不递归输出大目录。
4. 第一轮只回复紧凑的中文恢复报告：当前基线、已通过的实物能力、仍未闭环的验收、
   Phase 6 首个纵向目标、缺少的场地/标定输入和建议下一步。等待用户确认后再 plan。

安全边界：第一轮不修改项目文件，不连接或部署香橙派，不运行 CubeMX/Keil 构建，不烧录，不
ARM，不发送非零运动指令，不驱动电机。后续默认只做 dry-run；烧录和实车运动必须
由用户再次明确授权。不要读取或导入旧聊天、Codex session/rollout JSONL，也不要
假定交接文档中的 Orange Pi IP 和运行状态仍然有效。
