"""镜像同步工具：以 .claude/skills 为权威副本，将某个 skill 同步到 .agents/skills。

用法:
    python sync_mirrors.py --check   <skill>        # 对比两套镜像，不改动，列出差异
    python sync_mirrors.py --apply   <skill>        # 以 .claude 为准覆盖 .agents，然后校验
    python sync_mirrors.py --check-all              # 对比全部 skill
    python sync_mirrors.py --apply-all              # 同步全部 skill

约定:
    - .claude/skills/<skill> 是「权威副本」(canonical)，改动先落在这里。
    - .agents/skills/<skill> 是镜像，由本脚本保持与权威副本逐字节一致。
    - 事实库 facts/ 在项目根目录，各 agent 共享同一份、不镜像（本脚本不管它）。
    - 退出码 0 = 一致 / 同步成功；非 0 = 存在差异或出错(便于 CI / 钩子判断)。
"""

from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from pathlib import Path

# 被管理的 6 个策划 skill。--check-all / --apply-all 只作用于它们，
# 不碰元 skill 自身(含 ledgers/CHANGELOG 状态)或其它无关 skill(如 docx)。
MANAGED_SKILLS: tuple[str, ...] = (
    "combat-design",
    "gameplay-design",
    "numerical-planning",
    "system-design",
    "executive-planning",
    "qa-review",
    "table-config",
)


def project_root() -> Path:
    """<root>/.claude/skills/skill-evolution/scripts/sync_mirrors.py -> <root>"""
    return Path(__file__).resolve().parents[4]


def skill_dirs(root: Path, mirror: str) -> Path:
    return root / mirror / "skills"


def list_skills(claude_skills: Path) -> list[str]:
    """--all 只返回被管理的 7 个 skill 中实际存在的那些。"""
    if not claude_skills.is_dir():
        return []
    return [s for s in MANAGED_SKILLS if (claude_skills / s).is_dir()]


def diff_report(a: Path, b: Path) -> list[str]:
    """返回 a 与 b 目录树的差异描述列表；空列表表示逐文件一致。"""
    problems: list[str] = []

    if not a.is_dir():
        return [f"权威副本不存在: {a}"]

    def walk(cmp: filecmp.dircmp, rel: str) -> None:
        for name in cmp.left_only:
            problems.append(f"仅存在于权威副本(.claude): {rel}{name}")
        for name in cmp.right_only:
            problems.append(f"仅存在于镜像(.agents): {rel}{name}")
        for name in cmp.diff_files:
            problems.append(f"内容不一致: {rel}{name}")
        for name in cmp.funny_files:
            problems.append(f"无法比较: {rel}{name}")
        for sub, subcmp in cmp.subdirs.items():
            walk(subcmp, f"{rel}{sub}/")

    if not b.is_dir():
        return [f"镜像不存在: {b}(需 --apply 创建)"]

    walk(filecmp.dircmp(str(a), str(b)), "")
    return problems


def apply_sync(a: Path, b: Path) -> list[str]:
    """以 a 覆盖 b，使 b 与 a 逐字节一致；返回同步后仍存在的差异(应为空)。"""
    if not a.is_dir():
        return [f"权威副本不存在，无法同步: {a}"]
    if b.exists():
        shutil.rmtree(b)
    shutil.copytree(a, b)
    return diff_report(a, b)


def main() -> int:
    parser = argparse.ArgumentParser(description="策划 skill 双镜像同步 (.claude 权威 -> .agents 镜像)")
    parser.add_argument("skill", nargs="?", help="skill 名称，如 combat-design")
    parser.add_argument("--check", action="store_true", help="仅对比差异，不改动")
    parser.add_argument("--apply", action="store_true", help="以 .claude 为准同步到 .agents")
    parser.add_argument("--check-all", action="store_true", help="对比全部 skill")
    parser.add_argument("--apply-all", action="store_true", help="同步全部 skill")
    parser.add_argument("--claude-root", default=None, help="覆盖 .claude 根目录")
    parser.add_argument("--agents-root", default=None, help="覆盖 .agents 根目录")
    args = parser.parse_args()

    root = project_root()
    claude_skills = Path(args.claude_root) if args.claude_root else skill_dirs(root, ".claude")
    agents_skills = Path(args.agents_root) if args.agents_root else skill_dirs(root, ".agents")

    if args.check_all or args.apply_all:
        targets = list_skills(claude_skills)
    elif args.skill:
        targets = [args.skill]
    else:
        parser.error("需要指定 <skill> 或使用 --check-all / --apply-all")
        return 2

    do_apply = args.apply or args.apply_all
    exit_code = 0

    for skill in targets:
        a = claude_skills / skill
        b = agents_skills / skill
        if do_apply:
            remaining = apply_sync(a, b)
            if remaining:
                exit_code = 1
                print(f"[FAIL] {skill}: 同步后仍有差异")
                for p in remaining:
                    print(f"       - {p}")
            else:
                print(f"[OK]   {skill}: 已同步，两套镜像一致")
        else:
            problems = diff_report(a, b)
            if problems:
                exit_code = 1
                print(f"[DIFF] {skill}: {len(problems)} 处差异")
                for p in problems:
                    print(f"       - {p}")
            else:
                print(f"[OK]   {skill}: 两套镜像一致")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
