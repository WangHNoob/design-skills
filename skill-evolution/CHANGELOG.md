# 策划 skill 进化 CHANGELOG

> 由 skill-evolution 元 skill 在「固化」阶段追加。每条固化改动一记，只增不删。
> 格式：日期 · skill · 版本 · 改了什么 · 依据账本哪些条目。

## 2026-07-03 · 事实库迁到项目根目录 facts/（去 agent 依赖）
- **背景**：用户指出事实库放 `.claude/` 下会绑定 Claude Code 私有目录、造成 agent 依赖。改为放**项目根 `facts/`，各 agent 共享同一份**，谁都不依赖谁的私有目录，还能复用。
- **改动**：① `.claude/facts` → 根 `facts/`，删除 `.agents/facts` 镜像（不再镜像，单一共享一份）；② 所有活跃引用 `.claude/facts` → `facts/`：session-retrospect SKILL、reflect_stop_hook.py 注入指令、7 个业务 skill 的"开工前先扫"引导、根 facts/INDEX.md 自身标题；③ `sync_mirrors.py` 移除上一步刚加的 `sync_facts()` 及调用（根目录共享无需镜像），docstring 相应更新。
- **依据**：用户"facts 放根目录、不管用什么 agent 都不影响、还能复用"。
- **验证**：两脚本 py_compile OK；sync --apply-all → 7 skill [OK]、exit 0（facts 不再出现在同步输出，符合预期）；全仓 `.claude/facts` 活跃引用清零（仅本 CHANGELOG 历史留痕）；.agents 侧 7 skill 均为 `facts/INDEX.md`、无 .claude/facts 残留、无 .agents/facts 目录。

## 2026-07-03 · 新增 session-retrospect + 会话复盘引擎 + 独立事实库
- **背景**：用户要"引擎自动转、不靠人自觉"。会话内已有大量高质量信号（用户纠正/需求对齐/口径约定）藏在 transcript，本会白白流失。决定：Stop hook 自动起一个复盘 subagent 捞回来。
- **① 改造 `skill-evolution/scripts/reflect_stop_hook.py`**：注入指令从"自己反思"→"**起一个会话复盘 subagent**，读一遍 transcript 做两件产出：①skill 缺陷反思(→ledgers/，达阈值走固化闸门) ②关键事实抽取(→.claude/facts/)"。"已复盘"判据扩为 skill-evolution/session-retrospect 调用 或 写过 ledgers/、facts/。粗筛仍是"真调用过业务 skill"(纯闲聊不触发)。py_compile OK。
- **② 新增 skill `session-retrospect`(v1.0.0，meta-skill，仅 .claude、不纳管、不镜像 skill 本体)**：复盘 subagent 操作手册。含两件产出方法 + **防膨胀四机制**（高阈值抽取、写入即去重覆盖、软上限 20 条+淘汰归档、分层读取）。固化仍复用 skill-evolution 闸门。
- **③ 建独立事实库 `.claude/facts/`**：INDEX.md 常驻索引 + 一事一文(frontmatter: type/status/source/updated) + archive/。种子为 2 条真实事实(kb 只读边界、用户偏好)，非造假。
- **④ 7 个业务 skill**：执行流程开头加"开工前先扫 .claude/facts/INDEX.md，相关才展开读"——即"让 agent 注意读取"的落点。
- **⑤ `sync_mirrors.py`**：新增 `sync_facts()`，--check-all/--apply-all 时把 .claude/facts 单向同步到 .agents/facts(复盘只写权威侧，靠 sync 推镜像，防两侧分叉)。Codex 侧可读。
- **依据**：本次对话用户明确要 A(hook 起 subagent 反思) + 新增自动事实抽取 skill；拍板"独立事实库 + 合成一个复盘 subagent + 上限 20 条 + facts 也镜像到 .agents"。C(KB 校验硬门槛)本次不做。
- **验证**：两个脚本 py_compile OK；sync --apply-all → 7 skill + facts 全 [OK]、exit 0；.agents/facts 镜像已建。

## 2026-07-03 · 全部 6 个策划 skill · 模板轻量化 + executive 重定位
- **背景**：用户评估后判断原模板"太复杂、不像策划日常真用的"。分析确认三处错配：①用"新游戏立项级教科书全案"套"一期活动/迭代需求"；②executive 把商业化/埋点/风险矩阵/里程碑排期（制作人/PM 文档）塞进执行策划 skill；③模板是"几十行嵌套表格问卷"而非"最小骨架按需生长"。
- **改动**：
  - **system / combat / gameplay / numerical / qa-review**：`assets/output-template.md` 从立项级完整模板（6–8 段嵌套大表）重写为**一页纸轻量需求版**（背景目标 / 规则流程 / 界面交互 / 配表需求 / 边界异常 / 引用来源，按需生长）。配表一律"只列清单+关键口径，落表移交 table-config"。
  - **qa-review**：原模板是"完整策划案"（`{system_design}`/`{combat_design}`… 汇总各路产出，属旧多智能体主策 Agent 设计）→ 重写为**单文档 QA 审阅报告**（结论 / 问题清单 / 配表校验 / 引用来源）。
  - **executive-planning 重定位**：从"制作人/PM 全案"改为**执行策划的「上线执行清单」**（本期改动 / 配表交付项 / 依赖阻塞 / 埋点需求 / 上线自测检查项）。同步改 SKILL.md 的 description、角色、职责、流程、约束。
- **一次性决定**：先建了 5 个 `output-template-full.md` 保留完整版，用户明确"完整版不需要留"→ 已全部删除，只保留轻量版。
- **依据**：本次对话用户直接指令。落地走 skill-evolution 闸门：先出 diff（system-design 作样板）经用户认可，再执行全部；用户追加"旧的遗留可以去除了""完整版不需要留"。
- **镜像**：sync_mirrors.py --apply-all → 全部 7 个 skill `[OK]`。
- **未动**：table-config 的 `proposal-template.md` 本就是精简变更提案，符合方向，保持不变。

## 2026-07-02 · skill-evolution（自身）· 1.0.0 → 1.1.0
- **改动**：把进化的触发主动权从「用户提关键词」转为「agent 自主判断」。① `description` 重写为常驻自觉职责——任务收尾/出现修正·补缺·新知识等信号时 agent 主动反思，不依赖用户；② 模式 A「何时进入」把自主判断提到第一位，用户话术降为触发之一；③ 模式 B 改为 agent 主动发起固化并出 diff（发起自主，写入仍留 diff 确认）；④ Stop hook 从「给用户的 systemMessage 提醒」改为「注入 agent 的 additionalContext 指令：立即自动反思」，并把「已反思」判据扩为 skill-evolution 调用 **或** 对 ledgers/ 的写入，避免重复触发。
- **保留边界**：GATE-2（固化写入前必给 diff、经用户本轮确认）不变——反思零风险全自动，改 skill 文件仍有一次人工闸门，防漂移可回滚。
- **依据**：本次对话用户明确要求「进化主动权交给 agent、不靠用户记住关键词」；并选定「反思全自动、固化仍留 diff 确认」。
- **修复**：hook 预筛字符串 `"name":"Skill"` 收紧为对空格容忍（`"name"`+`"Skill"` 同现），兼容紧凑/带空格两种 transcript 写法。
- **验证**：py_compile OK；4 情形测试通过（用过策划 skill→注入反思指令；已反思(skill 调用/ledger 写入)→静默；未真实调用→静默）。frontmatter YAML 合法、version=1.1.0。
- **镜像**：本 skill 不在受管镜像清单内（仅 `.claude`），无需 sync。

## 2026-07-02 · table-config（新建 + 纳管）· 1.0.0
- **新建** table-config skill：把数值设计落成「配表变更提案」（预览xlsx + 可粘贴tsv + 主键/外键校验），只读知识库、不改原始表。
- **纳入 skill-evolution 管理**：加入 `MANAGED_SKILLS` / `managed_skills` / skill-anatomy 表；已镜像到 `.agents`，7 个 skill 全部 parity `[OK]`。
- **方案B（去本地依赖）**：knowledge-hub 新增只读 MCP 工具 `kb_get_table_raw`（返回忠实原始网格：列ID行+全表头+列序+空列，array-of-arrays）；table_tool.py 增加 `--grid-json` 通道，可纯 MCP 取模板、不依赖本地 gamedata。本地 `--table` 作回退。
- **依据**：本次对话用户批准的两件事（方案B + table-config 纳管镜像）。
- **待生效**：`kb_get_table_raw` 需远程 MCP（81.70.215.87）重新部署 + 发布新 release 才可调用；未部署前 table-config 自动回退本地通道。

## 2026-07-02 · numerical-planning · 1.1.0 → 1.2.0
- **改动**：删除臆造工具 `table_create`/`table_write` 与 `mode=TABLE` 分支、以及 workspace 副本遗留说明；明确「本 skill 只做数值设计，配表落地移交 table-config」，并说明数值设计文档即 table-config 的输入。
- **依据**：新建 table-config skill 后，numerical 里指向不存在写表工具的 TABLE 模式已过时；本次对话用户批准的跟进项 1。
- **镜像**：sync_mirrors.py --apply numerical-planning → [OK]。

## 2026-07-02 · combat/gameplay/numerical/system/executive/qa-review（全部 6 个）· 1.0.0 → 1.1.0
- **改动**：产出形式从「以文本形式倒进对话、系统自动保存」改为「用 docx skill 生成 .docx 到 ./output/，对话只回 文件路径 + 6–10 行摘要 + 待决策点」，并加 docx 失败时降级写 .md 的分支。
- **同时铲除多智能体管道遗留**：删除 `workspace_read`/`workspace_list` 读前置任务、`output.md`/`references.json` 作为任务间接口、以及「系统会自动保存」的失效假设；「读前置」改为「用 Read 读对话中提供的或 ./output/ 下的参考文档」。qa-review 的审阅对象从「workspace 所有 output.md」改为「对话/./output/ 下的设计文档」；引用来源从 references.json 改为文档内「引用来源」小节。
- **修掉臆造工具**：`docx_from_markdown`（不存在）→ 改为「用 docx skill」。
- **依据**：本次对话用户直接反馈——(1)「使用策划 skill 后应借助 docx skill 生成文档，对话不适合长篇」；(2)「workspace_read 那些是旧多智能体设计，现在纯用 Claude Code/Codex，不需要」。属直接横切指令，未走账本，来源以本条为准。
- **镜像**：sync_mirrors.py --apply-all → 全部 [OK]。

<!-- 示例：
## 2026-07-02 · combat-design · 1.0.0 → 1.1.0
- **改动**: references/damage-formulas.md 明确项目默认减伤形式为 `ATK*(1-DEF/(DEF+K))`；SKILL.md 输出契约补充默认口径说明。
- **依据**: ledgers/combat-design.md「[2026-07-02] 项目伤害公式统一…」
- **镜像**: sync_mirrors.py --apply combat-design → [OK]
-->
