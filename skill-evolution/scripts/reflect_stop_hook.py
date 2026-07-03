"""Stop hook：任务结束时做「廉价粗筛」，判断本轮是否真正调用过策划 skill 且尚未复盘；
命中则通过 additionalContext 注入指令，让主 agent 起一个**会话复盘 subagent**——
一个 subagent、读一遍 transcript、两件产出：①skill 缺陷反思(→ledgers/、必要时走
skill-evolution 固化闸门) ②关键事实抽取(→facts/，带防膨胀规则)。

设计分工：**hook 只做粗门**(用没用过业务 skill / 是否已复盘，省得每次唤醒)，
**细判交给 subagent**(真正理解本轮返修、按 session-retrospect 方法论沉淀)——
以此避开脆弱的关键词匹配。

判定基于 transcript(JSONL)里真实的 Skill 工具调用(tool_use，name=="Skill"，
input.skill 为某策划 skill)——而不是「提到了 skill 名字」的散文文本，避免把
讨论/参数里出现的名字误判为真正使用。

行为：
- 只有出现真实的策划 skill 调用时才触发(纯闲聊/查询不复盘)。
- 若最近一次策划 skill 调用之后已复盘(调用过 skill-evolution/session-retrospect，
  或写过 ledgers/、facts/)，则不再触发，避免空转/重复；再次用策划 skill 后重新触发。
- 任何异常都静默退出(不输出、退出码 0)，绝不打断会话。

输入：Stop hook 的 stdin JSON，至少包含 transcript_path(Claude Code 传入的是原生
系统路径，如 Windows 的 C:\\...\\xxx.jsonl)。
输出：命中时打印 {"hookSpecificOutput":{...additionalContext}, "systemMessage": "..."}；否则不输出。
"""

from __future__ import annotations

import json
import sys
from typing import Iterator

PLANNING_SKILLS: frozenset[str] = frozenset(
    {
        "combat-design",
        "gameplay-design",
        "numerical-planning",
        "system-design",
        "executive-planning",
        "qa-review",
    }
)
META_SKILL = "skill-evolution"


def read_payload() -> dict:
    try:
        raw = sys.stdin.read()
    except OSError:
        return {}
    try:
        return json.loads(raw) if raw.strip() else {}
    except ValueError:
        return {}


def _skill_names_in(obj: object) -> Iterator[str]:
    """遍历一条 transcript 记录，产出其中所有 Skill 工具调用的 input.skill 值。"""
    stack: list[object] = [obj]
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            if cur.get("type") == "tool_use" and cur.get("name") == "Skill":
                inp = cur.get("input")
                if isinstance(inp, dict):
                    name = inp.get("skill")
                    if isinstance(name, str):
                        yield name
            stack.extend(cur.values())
        elif isinstance(cur, list):
            stack.extend(cur)


def _wrote_retro_artifact_in(obj: object) -> bool:
    """这条记录里是否有对 ledgers/ 或 facts/ 的写入(Edit/Write)——复盘已落地的旁证信号。

    复盘 subagent 有两件产出：反思落进 ledgers/，事实落进 facts/。命中任一即视为已复盘。
    """
    stack: list[object] = [obj]
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            if cur.get("type") == "tool_use" and cur.get("name") in ("Edit", "Write"):
                inp = cur.get("input")
                if isinstance(inp, dict):
                    path = inp.get("file_path") or inp.get("path") or ""
                    norm = path.replace("\\", "/") if isinstance(path, str) else ""
                    if "ledgers/" in norm or "/facts/" in norm or norm.endswith("facts/INDEX.md"):
                        return True
            stack.extend(cur.values())
        elif isinstance(cur, list):
            stack.extend(cur)
    return False


def last_launch_index(lines: list[str], targets: frozenset[str]) -> int:
    """返回最后一条真实调用了 targets 中某 skill 的行号；未命中返回 -1。

    以 '"name":"Skill"' 作快速预筛，再做结构化 JSON 校验，兼顾性能与准确。
    skill 名兼容插件命名空间(如 'plugin:name')，按冒号后的基础名匹配。
    """
    hit = -1
    for i, line in enumerate(lines):
        # 快速预筛：容忍 "name":"Skill" 与 "name": "Skill" 两种写法（有无空格）。
        if '"Skill"' not in line or '"name"' not in line:
            continue
        stripped = line.strip()
        if not stripped:
            continue
        try:
            record = json.loads(stripped)
        except ValueError:
            continue
        for name in _skill_names_in(record):
            if name.split(":")[-1] in targets:
                hit = i
                break
    return hit


def main() -> int:
    # 强制 UTF-8 输出，避免在中文 Windows 代码页下 print 表情/中文时崩溃。
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except (AttributeError, ValueError):
        pass

    payload = read_payload()
    transcript_path = payload.get("transcript_path")
    if not transcript_path:
        return 0

    try:
        with open(transcript_path, "r", encoding="utf-8", errors="ignore") as fh:
            lines = fh.readlines()
    except OSError:
        return 0

    planning_idx = last_launch_index(lines, PLANNING_SKILLS)
    if planning_idx < 0:
        return 0  # 本轮没真正调用过策划 skill → 不触发

    # 复盘已发生的判据：调用过 skill-evolution / session-retrospect，或对 ledgers/、facts/ 有过写入。
    reflection_idx = last_launch_index(
        lines, frozenset({META_SKILL, "session-retrospect"})
    )
    artifact_idx = -1
    for i, line in enumerate(lines):
        if "ledgers" not in line and "facts" not in line:
            continue
        stripped = line.strip()
        if not stripped:
            continue
        try:
            record = json.loads(stripped)
        except ValueError:
            continue
        if _wrote_retro_artifact_in(record):
            artifact_idx = i
    if max(reflection_idx, artifact_idx) > planning_idx:
        return 0  # 最近一次策划 skill 之后已复盘 → 不重复触发，避免空转/打扰

    # 给 agent 注入「起一个会话复盘 subagent」的指令（不是给用户的提醒）。
    # 一个 subagent、读一遍 transcript、两件产出：①skill 缺陷反思 ②关键事实。
    directive = (
        "本轮任务中真实调用过策划 skill。现在请**启动一个会话复盘 subagent**"
        "（用 Agent 工具，subagent_type 默认即可），让它读本轮交互，按 session-retrospect skill "
        "的方法完成两件产出，产出后把要点回报给你：\n"
        "① **skill 缺陷反思** → 把可复用经验（用户纠正 / 反复追问 / 流程缺口 / 新领域知识或配表约定）"
        "只追加进对应 ledgers/<skill>.md；某账本待固化条目达阈值（≥3 或强信号反复）时，"
        "主动整理 diff 走 skill-evolution 固化闸门请用户确认（仅『写入 skill 文件』需用户确认，反思/发起固化不必等用户提出）。\n"
        "② **关键事实抽取** → 把跨会话仍有用、且不能从代码/git/KB 推导的事实（需求对齐结论、口径约定、项目约束、用户偏好），"
        "按 session-retrospect 的防膨胀规则写入 facts/（写入即去重覆盖、不追加堆积；软上限 20 条，超限先合并压缩）。\n"
        "本轮无可沉淀的部分，如实说明、不硬凑。"
    )
    out = {
        "hookSpecificOutput": {
            "hookEventName": "Stop",
            "additionalContext": directive,
        },
        "systemMessage": "🔄 会话复盘：任务用到策划 skill，正在起复盘 subagent 反思 skill 缺陷 + 抽取关键事实（账本/facts 只追加，不改 skill）。",
    }
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
