# 目标 skill 文件地图与改写规则

改写任何一个目标 skill 前，先在这里确认「这个文件是干什么的、能不能改、改它有什么连锁影响」。

## 6 个目标 skill 与各自的领域边界

| skill | 职责 | 不该越界到 |
|---|---|---|
| combat-design | 战斗机制、技能、怪物/BOSS、伤害模型、战斗平衡 | 纯数值调优→numerical；纯架构→system |
| gameplay-design | 核心循环、关卡、副本、活动、奖励、交互、难度曲线 | 系统架构→system；数值公式→numerical |
| numerical-planning | 属性定义、成长曲线、公式、经济、平衡、配表 | 战斗机制→combat；系统架构→system |
| system-design | 模块划分、UI流程、系统间依赖、配表字段定义 | 战斗→combat；数值→numerical；玩法→gameplay |
| executive-planning | 排期、资源、里程碑、风险、商业化、埋点 | 具体玩法→gameplay；数值公式→numerical |
| qa-review | 跨模块一致性、配表校验、模板合规、边界检查 | 具体设计→对应领域 skill |
| table-config | 把数值设计落成 gamedata 配表变更提案（预览xlsx+可粘贴tsv+校验）| 数值公式设计→numerical；文档产出→docx |

**进化时务必守住这些边界**：一条经验若属于 A 的职责，就写进 A，不要顺手塞进正在看的 B。

## 每个 skill 内部的文件结构

```
<skill>/
├── SKILL.md                    # 角色 / 知识来源策略 / 核心职责 / 执行流程 / 输出契约 / 约束
├── assets/output-template.md   # 产出物的固定模板(章节 + 表头)
├── references/*.md             # 深度领域知识(如 combat 的 damage-formulas.md / buff-system.md)，按需加载
├── tests/trigger-cases.json    # 触发测试用例(input → expectedSkill)
└── workflows/*.yaml            # 编排流程定义
```

## 各类文件的改写规则

### SKILL.md 正文（最常改）
- **可改**：执行流程步骤、核心职责、输出契约章节清单、约束条款、知识来源策略。
- **改动影响**：直接改变 skill 每次运行的行为。
- **原则**：改流程要解释 why；新增约束优先用「解释理由」而非堆 MUST；能精简就精简。

### SKILL.md frontmatter 的 `description`（谨慎改）
- **影响触发**：这是 skill 何时被调用的主要依据。改它可能让 skill 过度触发或触发不足。
- **规则**：只在反思发现「该触发时没触发 / 不该触发时触发」的真实证据时才改；改完**必须**同步检查并更新 `tests/trigger-cases.json`，把新情形补进去。

### frontmatter 的 `version`（每次实质改动都 bump）
- 有实质行为变化 → 升 minor（1.0.0 → 1.1.0）；仅措辞微调 → 升 patch（1.0.0 → 1.0.1）。

### assets/output-template.md（模板摩擦时改）
- **何时改**：某章节反复空着（该删或该改说明）、或反复临时新增同类章节（该固化进模板）、或表头字段不够用。
- **注意**：模板是产出物骨架，改动会影响所有未来产出的结构；保持字段占位符 `{...}` 风格一致。

### references/*.md（沉淀深度知识时改/加）
- **何时用**：一条经验是「较长、领域纵深、并非每次都要」的知识（如一套新的伤害公式变体、一类 buff 规则）。放进 references，并在 SKILL.md 的「资源加载规则」里加一句何时读它。
- **好处**：SKILL.md 保持精简，深度知识按需加载。

### tests/trigger-cases.json（触发相关改动时同步改）
- 格式：`[{"input": "...", "expectedSkill": "<skill>", "keywords": [...]}]`
- 改 description / 边界时，把新覆盖或新排除的情形补成用例。

### workflows/*.yaml（一般不动）
- 属于编排层。除非经验明确指向流程编排问题，否则不在常规进化范围内；要改先向用户说明。

## 双镜像同步

- 权威副本 = `.claude/skills/<skill>/`；镜像 = `.agents/skills/<skill>/`。
- 只编辑权威副本，然后：
  ```bash
  python .claude/skills/skill-evolution/scripts/sync_mirrors.py --apply <skill>
  # 校验全部：
  python .claude/skills/skill-evolution/scripts/sync_mirrors.py --check-all
  ```
- 进化状态文件（`ledgers/`、`CHANGELOG.md`）只在本元 skill 下保留一份，**不**同步、**不**进目标 skill。

## 自动反思接线（已启用）

已在 `.claude/settings.json` 配置 Stop hook，命令为
`python scripts/reflect_stop_hook.py`（exec 形式，直接调用 python.exe，避免 shell 引号问题）。

工作方式：
- Stop 时读取 stdin 的 `transcript_path`，结构化解析 JSONL，**只统计真实的 Skill 工具调用**
  （`tool_use` 且 `name=="Skill"`，`input.skill` 为某策划 skill），忽略散文里出现的名字。
- 命中且「该次调用之后尚未复盘」时，用 `systemMessage` 提醒用户；否则静默。
- 任何异常静默退出、退出码 0，绝不打断会话。是提醒、不 block、不改文件。

维护提示：
- python 路径写的是本机绝对路径；换机器需在 settings.json 里更新。
- 若改动某策划 skill 的名字，记得同步更新 `reflect_stop_hook.py` 里的 `PLANNING_SKILLS`。
- 临时关闭在 `/hooks` 里禁用；新建 settings.json 后若 hook 未生效，打开一次 `/hooks` 或重启以重载配置。
