# 策划 Skill 包（Game-Design Skills）

一套面向**游戏策划工作流**的 Claude Code / Codex 技能包。不自研重 agent，而是把领域能力拆成 **Skill（技能包）**，挂到**现成 agent** 上，配合**只读知识库 MCP**，稳定产出**高质量策划文档**与**精准配表方案**。

> 本仓库 = `.claude/skills/`，**只包含 skill 本身**。运行还依赖仓库外的几样配套（知识库 MCP、事实库、安装脚本），见文末「外部配套」。

---

## 设计理念

| 层 | 角色 | 归属 |
|---|---|---|
| **编排层** | 现成 agent（Claude Code / Codex）负责对话、调度 skill、调用 MCP | 外部 |
| **能力层** | 本仓库的 skill：领域方法 + 固定模板 + 确定性脚本，按需加载 | **本仓库** |
| **知识层** | knowledge-hub MCP：只读、带可信度与证据，权威源在上游 SVN | 外部 |
| **记忆层** | `facts/` 事实库：跨会话的对齐结论/口径/约束/偏好，各 agent 共享 | 外部（项目根） |

三层解耦、即插即用；agent 可随模型迭代升级，能力沉淀在 skill 与知识库里。

---

## Skill 清单

### 业务策划 skill（7 个，一领域一 skill，别越界）

| Skill | 版本 | 职责 |
|---|---|---|
| `combat-design` | 1.1.0 | 战斗机制 / 技能 / 怪物 BOSS / 伤害模型 / 战斗平衡 |
| `gameplay-design` | 1.1.0 | 核心循环 / 关卡副本 / 活动 / 奖励 / 交互 / 难度曲线 |
| `numerical-planning` | 1.2.0 | 属性 / 成长曲线 / 公式 / 经济 / 平衡（**只设计不落表**） |
| `system-design` | 1.1.0 | 模块划分 / UI 流程 / 系统依赖 / 配表结构 |
| `executive-planning` | 1.1.0 | 一期上线执行清单：改动 / 配表交付 / 依赖阻塞 / 埋点 / 自测 |
| `qa-review` | 1.1.0 | 跨模块一致性 / 配表校验 / 模板合规 / 边界检查 |
| `table-config` | 1.0.0 | 把已定数值落成 gamedata **配表变更提案**（预览 xlsx + 可粘贴 TSV + 校验） |

> 产出默认走**轻量需求版**模板（一页纸、按需生长）。`numerical-planning` 的数值设计文档 = `table-config` 的输入。

### 元 skill（3 个，管 skill 自己、不做策划设计）

| Skill | 版本 | 职责 |
|---|---|---|
| `skill-evolution` | 1.1.0 | Skill 自进化：从真实使用中反思→固化。反思零风险自动，**改 skill 文件必过 diff 人工闸门** |
| `session-retrospect` | 1.0.0 | 会话复盘方法论：Stop hook 触发的复盘 subagent 依此工作，读一遍 transcript → ①skill 缺陷反思 ②关键事实抽取 |
| `onboarding-calibration` | 1.0.0 | 入职校准：策划开工前，把各 skill 的产出模板从占位货校准成本团队要用的样子 |

### 外部引入（vendored）

| Skill | 来源 | 说明 |
|---|---|---|
| `docx` | `anthropics/skills` | 生成 Word 文档（含 `LICENSE.txt`） |
| `xlsx` | `anthropics/skills` | 生成 Excel 表格 |

> 版本与来源哈希记录在父目录 `skills-lock.json`。

---

## 自进化 + 会话复盘回路（引擎自动转，不靠人自觉）

```
开工前读 facts/  →  用策划 skill 干活  →  任务收尾
                                            │
                          Stop hook 粗筛（真用过 skill？已复盘？）
                                            │ 命中
                              主 agent 起「会话复盘 subagent」读一遍 transcript
                                    ├─ ① skill 缺陷反思 → ledgers/（达阈值→出 diff）
                                    └─ ② 关键事实       → facts/（去重覆盖·上限 20）
                                            │
                              ③ 固化：先给用户看 diff、批准后才写 skill 文件
                                    → 同步镜像、记 CHANGELOG
```

- **反思 / 抽事实 / 发起固化**都自动，不必等用户提出。
- **唯一人工闸门**：写入 skill 文件前，用户对本轮 diff 确认一次。
- 触发靠 `skill-evolution/scripts/reflect_stop_hook.py`（Stop hook）。

---

## 目录约定

```
.claude/skills/            ← 本仓库（权威副本 canonical）
├── <skill>/
│   ├── SKILL.md           必需：frontmatter(name/description/version) + 方法正文
│   ├── assets/            输出模板等（如 output-template.md）
│   ├── references/        按需加载的参考文档
│   ├── scripts/           确定性脚本（如 table_tool.py）
│   ├── ledgers/           经验账本（skill-evolution，只追加）
│   └── CHANGELOG.md       固化留痕
└── .gitignore
```

- **本仓库是权威副本**；父目录 `.agents/skills/` 是**镜像**（给 Codex 侧），由 `skill-evolution/scripts/sync_mirrors.py` 生成、逐字节一致——**镜像在仓库外、不入本仓库版本控制，不要手改**。
- 元 skill（skill-evolution / session-retrospect / onboarding-calibration）只在本仓库，**不镜像、不纳入受管清单**。

---

## 安全红线

- **只读上游**：绝不改原始 gamedata / 知识库；产物只进项目 `./output/`。
- **配表是提案不是成品表**：`table-config` 出可粘贴提案，策划审一眼、粘一下、提交 SVN。
- **不臆造**：知识 / 数值 / 道具 ID 无来源一律标「待人工确认」。
- **凭证隔离**：知识库 token 只走环境变量 `KB_MCP_TOKEN`，绝不写进产出或配置正文。
- **先审后成**：正式产物前先出草稿获批。
- **失败显性**：工具失败 / 校验不过 / 步骤跳过，如实说明。

---

## 修改本仓库的正确姿势

1. **改 skill 内容**（表述 / 模板 / 流程 / 触发词 / references）→ 走 `skill-evolution` 固化流程：出 before/after diff → 用户确认 → 写入 → `python skill-evolution/scripts/sync_mirrors.py --apply <skill>` → 记 CHANGELOG。
2. **别手改 `.agents/skills` 镜像**，一律靠 sync 脚本从本仓库推。
3. **校准产出模板** → 用 `onboarding-calibration`（它只碰 `output-template.md`，写入仍交 `skill-evolution` 闸门）。

---

## 外部配套（不在本仓库，在本仓库父目录下）

| 配套 | 作用 |
|---|---|
| `knowledge-hub` MCP | 只读知识库（streamable http），提供页面 / 表结构 / 真实数据 / 校验 |
| `facts/`（项目根） | 跨会话事实库，各 agent 共享一份、不镜像 |
| `.agents/skills/` | 本仓库的 Codex 侧镜像（sync 生成） |
| `install.bat` / `INSTALL.md` | 一键安装：连 MCP + 装 skill + 装依赖 |
| `workflow.html` | 工作流可视化说明 |

---

## 快速上手

1. 装好外部配套（见 `INSTALL.md`），让 agent 能连 knowledge-hub MCP。
2. 在 Claude Code / Codex 里，按任务领域触发对应 skill（如"设计一期活动" → `gameplay-design`）。
3. agent 会：查库取事实 → 出草稿给你审 → 生成 `./output/` 产物 → 校验 → 回报路径+摘要。
4. 用得越多，`skill-evolution` + `session-retrospect` 会自动把经验沉淀回 skill 与 `facts/`。
