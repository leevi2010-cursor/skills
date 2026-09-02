#!/usr/bin/env python3
"""Validate a furniture-showroom consultation video script candidate."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


REQUIRED_HEADINGS = [
    "## 状态",
    "## 已审核选题",
    "## 输入与缺失信息",
    "## 核心命题",
    "## 制作难度判断",
    "## 逐镜脚本",
    "## 拍摄前检查",
    "## 禁用表达",
    "## 测试记录",
]

REQUIRED_LABELS = [
    "脚本状态",
    "选题审核",
    "审核人",
    "审核日期",
    "主要目标事件",
    "拍摄授权",
    "发布授权",
    "广告投放授权",
    "素材权利状态",
    "承接入口",
    "承接人",
    "单一行动指令",
    "建议拍摄等级",
    "最重动作",
    "重家具处理",
    "所需人员与设备",
    "营业与安全条件",
    "选择理由",
    "唯一主要测试变量",
    "当前结果",
]

REQUIRED_TABLE_COLUMNS = [
    "时间",
    "说服任务",
    "画面与动作",
    "口播/同期声",
    "屏幕文字",
    "证明点",
    "实现方式",
    "制作等级",
    "替代方案",
]

ACTION_KEYWORDS = {
    "私信": "私信",
    "评论": "评论",
    "关注": "关注",
    "预约": "预约",
    "到店": "到店",
    "扫码": "扫码",
    "点击": "点击",
    "电话": "电话",
    "拨打": "电话",
    "填写": "表单",
    "留资": "表单",
}

BANNED_CLAIMS = [
    "保证不会买错",
    "一定不会买错",
    "保证有效",
    "一定有效",
    "百分之百转化",
    "100%转化",
    "45秒是最佳",
    "45 秒是最佳",
    "任何旧家具都能救",
    "永远不会出错",
]

HEAVY_MOVE_PATTERNS = [
    "搬动沙发",
    "更换沙发",
    "替换沙发",
    "搬动餐桌",
    "更换餐桌",
    "替换餐桌",
    "搬动柜体",
    "更换柜体",
    "替换柜体",
    "搬动大茶几",
    "更换大茶几",
    "替换大茶几",
]

EMPTY_VALUES = {"", "-", "—", "无", "不适用", "待确认", "[...]", "[待确认]"}


def section(text: str, heading: str) -> str:
    start = text.find(heading)
    if start < 0:
        return ""
    start += len(heading)
    match = re.search(r"^##\s+", text[start:], flags=re.MULTILINE)
    end = start + match.start() if match else len(text)
    return text[start:end]


def field_value(text: str, label: str) -> str | None:
    pattern = rf"^\s*-\s*(?:\*\*)?{re.escape(label)}(?:\*\*)?\s*[：:]\s*(.+?)\s*$"
    match = re.search(pattern, text, flags=re.MULTILINE)
    return match.group(1).strip() if match else None


def table_cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def is_separator_row(cells: list[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells)


def validate(path: Path) -> tuple[list[str], list[str], dict[str, object]]:
    errors: list[str] = []
    warnings: list[str] = []
    text = path.read_text(encoding="utf-8")

    if not re.search(r"^#\s+\S+", text, flags=re.MULTILINE):
        errors.append("缺少一级标题")

    for heading in REQUIRED_HEADINGS:
        if heading not in text:
            errors.append(f"缺少标题：{heading}")

    for label in REQUIRED_LABELS:
        if field_value(text, label) is None:
            errors.append(f"缺少字段：{label}")

    if (field_value(text, "脚本状态") or "") != "候选":
        errors.append("脚本状态必须写为“候选”")
    if "已通过" not in (field_value(text, "选题审核") or ""):
        errors.append("选题审核必须明确写为“已通过”")
    if (field_value(text, "主要目标事件") or "") != "咨询":
        errors.append("主要目标事件必须写为“咨询”")

    reviewer = field_value(text, "审核人") or ""
    if reviewer in EMPTY_VALUES or "待确认" in reviewer:
        errors.append("审核人必须是可识别的人或明确身份")

    cta = field_value(text, "单一行动指令") or ""
    if cta in EMPTY_VALUES or "待确认" in cta:
        errors.append("单一行动指令不能为空或待确认")
    action_types = sorted({kind for word, kind in ACTION_KEYWORDS.items() if word in cta})
    if len(action_types) == 0:
        errors.append("单一行动指令中没有识别到咨询动作")
    elif len(action_types) > 1:
        errors.append(f"单一行动指令包含多个动作：{', '.join(action_types)}")

    test_variable = field_value(text, "唯一主要测试变量") or ""
    if test_variable in EMPTY_VALUES or "待确认" in test_variable:
        errors.append("唯一主要测试变量不能为空或待确认")

    overall_effort = field_value(text, "建议拍摄等级") or ""
    if not re.fullmatch(r"L[0-3]", overall_effort):
        errors.append("建议拍摄等级必须是 L0、L1、L2 或 L3")

    script_section = section(text, "## 逐镜脚本")
    table_lines = [line for line in script_section.splitlines() if line.strip().startswith("|")]
    data_rows: list[dict[str, str]] = []
    if len(table_lines) < 3:
        errors.append("逐镜脚本必须包含表头、分隔行和镜头行")
    else:
        headers = table_cells(table_lines[0])
        if headers != REQUIRED_TABLE_COLUMNS:
            errors.append("逐镜脚本表头与工作单不一致")
        else:
            for line in table_lines[1:]:
                cells = table_cells(line)
                if is_separator_row(cells):
                    continue
                if len(cells) != len(headers):
                    errors.append(f"逐镜表列数不一致：{line.strip()}")
                    continue
                data_rows.append(dict(zip(headers, cells)))

    if data_rows and not 4 <= len(data_rows) <= 10:
        warnings.append(f"逐镜表当前有 {len(data_rows)} 个镜头；通常建议 4–10 个有效镜头")

    for index, row in enumerate(data_rows, start=1):
        effort = row.get("制作等级", "")
        if not re.fullmatch(r"L[0-3]", effort):
            errors.append(f"第 {index} 个镜头的制作等级无效：{effort or '空'}")
        alternative = row.get("替代方案", "").strip()
        if effort in {"L2", "L3"}:
            if alternative in EMPTY_VALUES:
                errors.append(f"第 {index} 个 L2/L3 镜头缺少 L0/L1 替代方案")
            elif not re.search(r"L[01]", alternative):
                warnings.append(f"第 {index} 个 L2/L3 镜头的替代方案没有明确标记 L0 或 L1")

        visual = row.get("画面与动作", "")
        if effort in {"L0", "L1"} and "不搬动" not in visual and "无需搬动" not in visual:
            for pattern in HEAVY_MOVE_PATTERNS:
                if pattern in visual:
                    errors.append(f"第 {index} 个镜头写有“{pattern}”，但制作等级是 {effort}")

    if data_rows:
        effort_order = {"L0": 0, "L1": 1, "L2": 2, "L3": 3}
        valid_row_efforts = [row["制作等级"] for row in data_rows if row.get("制作等级") in effort_order]
        if valid_row_efforts:
            highest_effort = max(valid_row_efforts, key=effort_order.__getitem__)
            if overall_effort in effort_order and effort_order[overall_effort] != effort_order[highest_effort]:
                errors.append(f"建议拍摄等级为 {overall_effort}，但逐镜表最高等级为 {highest_effort}")

        action_rows = [row for row in data_rows if "行动" in row.get("说服任务", "")]
        if len(action_rows) != 1:
            errors.append(f"逐镜表必须且只能有一个行动镜头；当前为 {len(action_rows)} 个")
        else:
            action_copy = action_rows[0].get("口播/同期声", "") + " " + action_rows[0].get("屏幕文字", "")
            row_action_types = sorted({kind for word, kind in ACTION_KEYWORDS.items() if word in action_copy})
            if row_action_types != action_types:
                errors.append("行动镜头与“单一行动指令”使用的动作不一致")

    claim_scan = text
    prohibited = section(text, "## 禁用表达")
    if prohibited:
        claim_scan = claim_scan.replace("## 禁用表达" + prohibited, "")
    for phrase in BANNED_CLAIMS:
        if phrase in claim_scan:
            errors.append(f"正文出现禁用承诺：{phrase}")

    status_fields = {
        label: field_value(text, label)
        for label in ["脚本状态", "选题审核", "拍摄授权", "发布授权", "广告投放授权", "素材权利状态"]
    }
    summary: dict[str, object] = {
        "file": str(path),
        "shots": len(data_rows),
        "overall_effort": overall_effort or None,
        "cta_action_types": action_types,
        "status_fields": status_fields,
    }
    return errors, warnings, summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("script", type=Path, help="Markdown script candidate")
    args = parser.parse_args()

    path = args.script.expanduser().resolve()
    if not path.is_file():
        print(json.dumps({"status": "error", "errors": [f"文件不存在：{path}"]}, ensure_ascii=False, indent=2))
        return 2

    try:
        errors, warnings, summary = validate(path)
    except (OSError, UnicodeError) as exc:
        print(json.dumps({"status": "error", "errors": [str(exc)]}, ensure_ascii=False, indent=2))
        return 2

    payload = {
        "status": "valid" if not errors else "invalid",
        **summary,
        "warnings": warnings,
        "errors": errors,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
