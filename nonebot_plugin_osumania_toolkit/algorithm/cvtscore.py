from __future__ import annotations

import asyncio
import os
import re
from pathlib import Path
from typing import Any, Optional

from .match import match_notes_and_presses
from .score import get_score_result
from .utils import parse_bid_or_url
from ..file.mr_file_parser import mr_file
from ..file.osr_file_parser import osr_file
from ..file.osu_file_parser import osu_file
from ..file.ruleset_file_parser import load_ruleset_json, ruleset_file


_SCOREV2_MOD_BIT = 536870912
_MR_RANK_TO_MALODY = {
    0: "A",
    1: "B",
    2: "C",
    3: "D",
    4: "E",
}

_NUMBER_RE = re.compile(r"^[+-]?\d+(?:\.\d+)?$")
_PREFIX_NUMBER_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)(?:=)?([+-]?\d+(?:\.\d+)?)$")
_CMD_PREFIX_RE = re.compile(r"^/?(?:cvtscore|转换)(?:\s+|$)", re.IGNORECASE)
_FUTURE_NOT_READY_TEXT = "Future object is not initialized"
_CVTSCORE_RENDER_LOCK = asyncio.Lock()
_CVTSCORE_TEMPLATE_NAME = "cvtscore.html"


def first_file_segment(message: Any):
    for seg in message:
        if getattr(seg, "type", None) == "file":
            return seg
    return None


def all_cleanup_targets(state: dict[str, Any]) -> tuple[Path | str | None, ...]:
    return (
        state.get("replay_path"),
        state.get("downloaded_chart_path"),
        state.get("converted_chart_path"),
    )


async def cleanup_cvtscore_state(state: dict[str, Any]) -> None:
    from ..file.file import cleanup_paths

    asyncio.create_task(cleanup_paths(*all_cleanup_targets(state)))


async def load_replay_from_file_seg(bot: Any, file_seg: Any, state: dict[str, Any], cache_dir: Path) -> str | None:
    from ..file.file import download_file, get_file_url, safe_filename

    file_info = await get_file_url(bot, file_seg)
    if not file_info:
        return "无法获取文件信息。请确保机器人有权限访问该文件。"

    file_name, file_url = file_info
    file_name = os.path.basename(file_name)
    lower_name = file_name.lower()

    if not (lower_name.endswith(".osr") or lower_name.endswith(".mr")):
        return "请发送 .osr 或 .mr 回放文件。"

    replay_path = cache_dir / safe_filename(file_name)
    success = await download_file(file_url, replay_path)
    if not success:
        return "回放文件下载失败，请稍后重试。"

    # 即使后续解析失败，也保留路径用于统一清理。
    state["replay_path"] = replay_path

    if lower_name.endswith(".osr"):
        replay_obj = osr_file(replay_path)
        replay_obj.process()
        err = validate_replay_status("osr", osr_obj=replay_obj)
        if err:
            return err

        state["replay_kind"] = "osr"
        state["mr_obj"] = None
        state["osr_obj"] = replay_obj
        state["replay_path"] = replay_path
        state["replay_name"] = file_name
        return None

    mr_obj = mr_file(replay_path)
    err = validate_replay_status("mr", mr_obj=mr_obj)
    if err:
        return err

    from .convert import convert_mr_to_osr

    replay_obj = convert_mr_to_osr(mr_obj)
    if replay_obj.status in {"NotMania", "tooFewKeys"}:
        return "该 mr 回放有效轨道数量不足或并非 Mania 数据，无法计算。"

    state["replay_kind"] = "mr"
    state["mr_obj"] = mr_obj
    state["osr_obj"] = replay_obj
    state["replay_path"] = replay_path
    state["replay_name"] = file_name
    return None


async def load_chart_from_file_seg(bot: Any, file_seg: Any, state: dict[str, Any], cache_dir: Path) -> str | None:
    from ..file.file import download_file, get_file_url, safe_filename

    file_info = await get_file_url(bot, file_seg)
    if not file_info:
        return "无法获取文件信息。请确保机器人有权限访问该文件。"

    file_name, file_url = file_info
    file_name = os.path.basename(file_name)
    lower_name = file_name.lower()

    if not (lower_name.endswith(".osu") or lower_name.endswith(".mc")):
        return "请发送 .osu 或 .mc 谱面文件。"

    downloaded_path = cache_dir / safe_filename(file_name)
    success = await download_file(file_url, downloaded_path)
    if not success:
        return "谱面文件下载失败，请稍后重试。"

    # 即使后续解析失败，也保留路径用于统一清理。
    state["downloaded_chart_path"] = downloaded_path

    chart_path = downloaded_path
    converted_path: Path | None = None

    if lower_name.endswith(".mc"):
        from .utils import is_mc_file
        from .convert import convert_mc_to_osu

        if not is_mc_file(str(downloaded_path)):
            return "无效的 .mc 文件，或不是支持的 key 模式谱面。"
        try:
            converted_path = Path(convert_mc_to_osu(str(downloaded_path), str(cache_dir)))
        except Exception as exc:
            return f".mc 转换失败: {exc}"
        chart_path = converted_path
        file_name = converted_path.name

    osu_obj = osu_file(str(chart_path))
    osu_obj.process()
    err = validate_chart_status(osu_obj)
    if err:
        return err

    state["downloaded_chart_path"] = downloaded_path
    state["converted_chart_path"] = converted_path
    state["chart_path"] = chart_path
    state["chart_name"] = file_name
    state["osu_obj"] = osu_obj
    return None


async def load_chart_from_bid(state: dict[str, Any], cache_dir: Path) -> str | None:
    from ..file.file import download_file_by_id

    bid = state.get("bid")
    if bid is None:
        return "未提供 bid。"

    try:
        osu_path, osu_name = await download_file_by_id(cache_dir, int(bid))
    except Exception as exc:
        return f"通过 bid 下载谱面失败: {exc}"

    osu_obj = osu_file(str(osu_path))
    osu_obj.process()
    err = validate_chart_status(osu_obj)
    if err:
        return err

    state["downloaded_chart_path"] = osu_path
    state["converted_chart_path"] = None
    state["chart_path"] = osu_path
    state["chart_name"] = osu_name
    state["osu_obj"] = osu_obj
    return None


async def prepare_cvtscore_state(state: dict[str, Any], cache_dir: Path) -> tuple[bool, str]:
    if state.get("osr_obj") is None:
        state["stage"] = "need_replay"
        return False, "请发送回放文件（.osr 或 .mr）。可以同时补充 bid/ruleset 参数，输入 0 取消。"

    if state.get("osu_obj") is None:
        if state.get("bid") is not None and not state.get("bid_loaded"):
            state["bid_loaded"] = True
            bid_err = await load_chart_from_bid(state, cache_dir)
            if bid_err:
                state["bid_load_error"] = bid_err
                state["osu_obj"] = None

        if state.get("osu_obj") is None:
            state["stage"] = "need_chart"
            bid_err = state.get("bid_load_error")
            if bid_err:
                return (
                    False,
                    f"{bid_err}\n请重新输入 b<bid>（或 mania 链接），或发送 .osu/.mc 谱面文件。谱面不可跳过。输入 0 取消。",
                )
            return False, "请发送谱面文件（.osu/.mc），或输入 b<bid>（或 mania 链接）。谱面不可跳过，输入 0 取消。"

    if not state.get("target_spec"):
        state["stage"] = "need_ruleset"
        return False, "请输入目标 ruleset。\n" + get_ruleset_quick_help_text() + "\n你也可以附带 -sv2 / -nosv2。"

    state["stage"] = "ready"
    return True, ""


async def run_cvtscore_conversion(state: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    target_spec = str(state.get("target_spec") or "").strip()
    target_rs, target_info, target_err = resolve_target_ruleset(target_spec)
    if target_err:
        return None, target_err

    replay_kind = str(state.get("replay_kind") or "").lower()
    osr_obj = state.get("osr_obj")
    mr_obj = state.get("mr_obj")
    osu_obj = state.get("osu_obj")
    force_sv2 = state.get("force_sv2")

    source_rs, source_info, source_err = detect_source_ruleset(
        replay_kind=replay_kind,
        osu_obj=osu_obj,
        osr_obj=osr_obj,
        mr_obj=mr_obj,
        force_sv2=force_sv2,
    )
    if source_err:
        return None, source_err

    result, cvt_err = compute_cvtscore(
        osu_obj=osu_obj,
        osr_obj=osr_obj,
        source_ruleset=source_rs,
        target_ruleset=target_rs,
    )
    if cvt_err:
        return None, cvt_err

    message = format_cvtscore_message(
        source_info=source_info,
        target_info=target_info,
        source_ruleset=source_rs,
        target_ruleset=target_rs,
        source_score=result["source_score"],
        target_score=result["target_score"],
    )

    card_data: dict[str, Any] | None = None
    try:
        card_data = build_cvtscore_card_data(
            source_info=source_info,
            target_info=target_info,
            source_ruleset=source_rs,
            target_ruleset=target_rs,
            source_score=result["source_score"],
            target_score=result["target_score"],
        )
    except Exception:
        # Keep text output available even when card data building fails.
        card_data = None

    return {
        "text": message,
        "card_data": card_data,
    }, None


def update_cvtscore_state_from_text_input(text: str, state: dict[str, Any]) -> list[str]:
    bid, force_sv2, spec, errors = parse_cvtscore_cmd(text)
    if force_sv2 is not None:
        state["force_sv2"] = force_sv2
    if bid is not None:
        state["bid"] = bid
        state["bid_loaded"] = False
        state["bid_load_error"] = None
    if spec:
        state["target_spec"] = spec
    return errors


def _rulesets_root() -> Path:
    return Path(__file__).resolve().parents[1] / "rulesets"


def _templates_dir() -> Path:
    return _rulesets_root() / "templates"


def _card_templates_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "templates"


def _get_template_to_pic():
    from nonebot import require

    require("nonebot_plugin_htmlkit")
    from nonebot_plugin_htmlkit import template_to_pic  # type: ignore[import-not-found]

    return template_to_pic


def _is_number_token(text: str) -> bool:
    return bool(_NUMBER_RE.fullmatch(text.strip()))


def _to_float(text: str) -> Optional[float]:
    try:
        return float(text)
    except Exception:
        return None


def parse_cvtscore_cmd(cmd_text: str) -> tuple[int | None, Optional[bool], str | None, list[str]]:
    """解析 /cvtscore 首轮命令。"""
    text = (cmd_text or "").strip()

    # 支持大小写不敏感命令前缀，并兼容无参数写法（如 /CVTSCORE）。
    text = _CMD_PREFIX_RE.sub("", text, count=1).strip()

    if not text:
        return None, None, None, []

    bid: int | None = None
    force_sv2: Optional[bool] = None
    errors: list[str] = []
    ruleset_tokens: list[str] = []

    parts = [p for p in re.split(r"\s+", text) if p]
    for part in parts:
        low = part.lower()

        if low in {"-sv2", "sv2", "+sv2"}:
            if force_sv2 is False:
                errors.append("sv2 参数冲突：已指定关闭 sv2，又收到开启 sv2。")
            force_sv2 = True
            continue

        if low in {"-nosv2", "nosv2", "sv1", "-sv1"}:
            if force_sv2 is True:
                errors.append("sv2 参数冲突：已指定开启 sv2，又收到关闭 sv2。")
            force_sv2 = False
            continue

        parsed_bid, bid_err = parse_bid_or_url(part)
        if bid_err is not None:
            errors.append(bid_err)
            continue
        if parsed_bid is not None:
            bid = parsed_bid
            continue

        ruleset_tokens.append(part)

    ruleset_spec = " ".join(ruleset_tokens).strip() or None
    return bid, force_sv2, ruleset_spec, errors


def _build_ruleset_catalog() -> dict[str, Any]:
    root = _rulesets_root()
    template_dir = _templates_dir()

    templates: dict[str, str] = {}
    concrete: dict[tuple[str, str], Path] = {}
    flat_concrete: dict[str, list[tuple[str, str, Path]]] = {}

    if template_dir.exists():
        for file_path in sorted(template_dir.glob("*.ruleset")):
            name = file_path.stem
            templates[name.lower()] = name

    if root.exists():
        for group_dir in sorted(root.iterdir()):
            if not group_dir.is_dir():
                continue
            if group_dir.name.lower() == "templates":
                continue

            group = group_dir.name
            for file_path in sorted(group_dir.glob("*.ruleset")):
                name = file_path.stem
                key = (group.lower(), name.lower())
                concrete[key] = file_path
                flat_concrete.setdefault(name.lower(), []).append((group, name, file_path))

    return {
        "templates": templates,
        "concrete": concrete,
        "flat_concrete": flat_concrete,
    }


def _extract_template_diff(tokens: list[str], template_meta: dict[str, Any]) -> tuple[Optional[float], Optional[str]]:
    arg_name = str(template_meta.get("ArgumentName", "diff") or "diff").strip().lower()
    aliases: set[str] = {"diff", arg_name}

    raw_aliases = template_meta.get("Aliases")
    if isinstance(raw_aliases, list):
        for alias in raw_aliases:
            if isinstance(alias, str) and alias.strip():
                aliases.add(alias.strip().lower())

    numeric_tokens: list[float] = []

    i = 0
    while i < len(tokens):
        token = tokens[i].strip()
        low = token.lower()

        if low in aliases:
            if i + 1 >= len(tokens):
                return None, f"模板参数 {token} 缺少数值。"
            value = _to_float(tokens[i + 1])
            if value is None:
                return None, f"模板参数 {token} 后面的值不是数字：{tokens[i + 1]}"
            return value, None

        m = _PREFIX_NUMBER_RE.fullmatch(token)
        if m:
            prefix = m.group(1).lower()
            value = _to_float(m.group(2))
            if prefix in aliases and value is not None:
                return value, None

        for alias in sorted(aliases, key=len, reverse=True):
            if not low.startswith(alias):
                continue
            suffix = token[len(alias) :]
            if not suffix:
                continue
            if suffix.startswith("="):
                suffix = suffix[1:]
            value = _to_float(suffix)
            if value is None:
                return None, f"模板参数格式无效：{token}"
            return value, None

        if _is_number_token(token):
            number = _to_float(token)
            if number is not None:
                numeric_tokens.append(number)

        i += 1

    if len(numeric_tokens) == 1:
        return numeric_tokens[0], None

    if len(numeric_tokens) > 1:
        return None, "检测到多个可能的模板参数，请使用 diff<num> 或别名<num> 明确指定。"

    return None, None


def get_ruleset_quick_help_text() -> str:
    return (
        "ruleset 输入示例:\n"
        "1. 模板优先: sc diff4 或 wife3 j7\n"
        "2. 具体规则: Quaver/chill\n"
        "3. 模板显式写法: template/sc diff4\n"
        "你可以使用/omtk cvtscore查看详细用法。"
    )


def resolve_target_ruleset(spec_text: str) -> tuple[Optional[ruleset_file], Optional[dict[str, Any]], Optional[str]]:
    spec = (spec_text or "").strip()
    if not spec:
        return None, None, "目标 ruleset 不能为空。"

    catalog = _build_ruleset_catalog()
    templates: dict[str, str] = catalog["templates"]
    concrete: dict[tuple[str, str], Path] = catalog["concrete"]
    flat_concrete: dict[str, list[tuple[str, str, Path]]] = catalog["flat_concrete"]

    parts = [p for p in re.split(r"\s+", spec) if p]
    head = parts[0]
    rest = parts[1:]

    selected_template: str | None = None
    selected_concrete: tuple[str, str, Path] | None = None

    if "/" in head:
        group_raw, name_raw = head.split("/", 1)
        group = group_raw.strip()
        name = name_raw.strip()
        if not group or not name:
            return None, None, "ruleset 写法不完整，请使用 Group/Name 形式。"

        if group.lower() == "template":
            key = name.lower()
            if key not in templates:
                return None, None, f"未找到模板 ruleset: {name}"
            selected_template = templates[key]
        else:
            key = (group.lower(), name.lower())
            path = concrete.get(key)
            if path is None:
                return None, None, f"未找到具体 ruleset: {group}/{name}"
            selected_concrete = (group, name, path)

    else:
        head_low = head.lower()

        if head_low in templates:
            selected_template = templates[head_low]
        elif head_low in flat_concrete:
            matched = flat_concrete[head_low]
            if len(matched) > 1:
                candidates = ", ".join(f"{g}/{n}" for g, n, _ in matched)
                return None, None, f"规则名 {head} 存在歧义，请使用 Group/Name。可选: {candidates}"
            selected_concrete = matched[0]
        elif len(parts) >= 2:
            # 兼容不带斜杠写法：Quaver chill
            key = (head_low, parts[1].lower())
            path = concrete.get(key)
            if path is not None:
                selected_concrete = (head, parts[1], path)
                rest = parts[2:]
            else:
                return None, None, f"未识别的 ruleset: {spec}"
        else:
            return None, None, f"未识别的 ruleset: {spec}"

    if selected_template is not None:
        template_path = _templates_dir() / f"{selected_template}.ruleset"
        if not template_path.exists():
            return None, None, f"模板文件不存在: {selected_template}.ruleset"

        try:
            data = load_ruleset_json(template_path)
        except Exception as exc:
            return None, None, f"读取模板失败: {exc}"

        template_meta = data.get("Template") if isinstance(data, dict) else None
        if not isinstance(template_meta, dict):
            return None, None, f"模板 {selected_template} 缺少 Template 元信息。"

        diff_value, diff_err = _extract_template_diff(rest, template_meta)
        if diff_err:
            return None, None, diff_err

        source: tuple[Any, ...]
        if diff_value is None:
            source = ("template", selected_template)
        else:
            source = ("template", selected_template, diff_value)

        rs = ruleset_file(source)
        if rs.status != "OK":
            reason = rs.errors[0] if rs.errors else f"状态={rs.status}"
            return None, None, f"模板 ruleset 构建失败: {reason}"

        info = {
            "type": "template",
            "display": f"template/{selected_template} (diff={rs.template_context.get('diff_text') or rs.template_context.get('diff')})",
            "template": selected_template,
            "diff": rs.template_context.get("diff"),
            "diff_text": rs.template_context.get("diff_text"),
            "path": rs.template_context.get("template_path", str(template_path)),
        }
        return rs, info, None

    assert selected_concrete is not None
    group, name, path = selected_concrete
    rs = ruleset_file(path)
    if rs.status != "OK":
        reason = rs.errors[0] if rs.errors else f"状态={rs.status}"
        return None, None, f"规则文件加载失败: {group}/{name} ({reason})"

    info = {
        "type": "concrete",
        "display": f"{group}/{name}",
        "group": group,
        "name": name,
        "path": str(path),
    }
    return rs, info, None


def detect_source_ruleset(
    *,
    replay_kind: str,
    osu_obj: osu_file,
    osr_obj: osr_file,
    mr_obj: Optional[mr_file],
    force_sv2: Optional[bool],
) -> tuple[Optional[ruleset_file], Optional[dict[str, Any]], Optional[str]]:
    replay_kind_lower = replay_kind.lower()

    if replay_kind_lower == "osr":
        od_value = float(getattr(osu_obj, "od", 8.0) or 8.0)

        mod_value = int(getattr(osr_obj, "mod", 0) or 0)
        mods = getattr(osr_obj, "mods", [])
        has_sv2_mod = bool(mod_value & _SCOREV2_MOD_BIT)
        if not has_sv2_mod and isinstance(mods, list):
            has_sv2_mod = any(str(m).lower() == "scorev2" for m in mods)

        if force_sv2 is True:
            use_sv2 = True
            reason = "用户强制启用 sv2"
        elif force_sv2 is False:
            use_sv2 = False
            reason = "用户强制关闭 sv2"
        else:
            use_sv2 = has_sv2_mod
            reason = "自动检测到 ScoreV2 模组" if has_sv2_mod else "自动检测为非 ScoreV2"

        template_name = "osu-sv2" if use_sv2 else "osu"
        rs = ruleset_file(("template", template_name, od_value))
        if rs.status != "OK":
            reason_text = rs.errors[0] if rs.errors else f"状态={rs.status}"
            return None, None, f"源 ruleset 构建失败: {reason_text}"

        info = {
            "display": f"template/{template_name} (od={rs.template_context.get('diff_text') or od_value})",
            "type": "template",
            "template": template_name,
            "od": od_value,
            "reason": reason,
            "replay_kind": "osr",
        }
        return rs, info, None

    if replay_kind_lower == "mr":
        if mr_obj is None:
            return None, None, "mr 回放对象为空，无法识别源规则。"

        rank = int(getattr(mr_obj, "rank", -1))
        malody_level = _MR_RANK_TO_MALODY.get(rank)
        if malody_level is None:
            return None, None, f"无法识别 mr rank={rank}，仅支持 0~4。"

        ruleset_path = _rulesets_root() / "Malody" / f"{malody_level}.ruleset"
        rs = ruleset_file(ruleset_path)
        if rs.status != "OK":
            reason_text = rs.errors[0] if rs.errors else f"状态={rs.status}"
            return None, None, f"源 ruleset 加载失败: {reason_text}"

        reason = f"mr rank={rank} -> Malody/{malody_level}.ruleset"
        if force_sv2 is not None:
            reason += "；sv2 选项对 mr 回放无效，已忽略"

        info = {
            "display": f"Malody/{malody_level}",
            "type": "concrete",
            "group": "Malody",
            "name": malody_level,
            "reason": reason,
            "replay_kind": "mr",
        }
        return rs, info, None

    return None, None, f"不支持的回放类型: {replay_kind}"


def compute_cvtscore(
    *,
    osu_obj: osu_file,
    osr_obj: osr_file,
    source_ruleset: ruleset_file,
    target_ruleset: ruleset_file,
) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    source_match = match_notes_and_presses(osu_obj, osr_obj, source_ruleset, use_chart_time=True)
    if source_match.get("status") != "OK":
        return None, f"源规则匹配失败: {source_match.get('error') or source_match.get('status')}"

    source_score = get_score_result(source_ruleset, source_match)
    if source_score.get("status") != "OK":
        return None, f"源规则计分失败: {source_score.get('error') or source_score.get('status')}"

    source_score = _align_source_score_with_osr_header(
        score=source_score,
        source_ruleset=source_ruleset,
        osr_obj=osr_obj,
    )

    target_match = match_notes_and_presses(osu_obj, osr_obj, target_ruleset, use_chart_time=True)
    if target_match.get("status") != "OK":
        return None, f"目标规则匹配失败: {target_match.get('error') or target_match.get('status')}"

    target_score = get_score_result(target_ruleset, target_match)
    if target_score.get("status") != "OK":
        return None, f"目标规则计分失败: {target_score.get('error') or target_score.get('status')}"

    return {
        "source_match": source_match,
        "source_score": source_score,
        "target_match": target_match,
        "target_score": target_score,
    }, None


def _normalize_judgement_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", str(name or "")).upper()


def _counts_from_osr_for_ruleset(source_ruleset: ruleset_file, osr_obj: osr_file) -> Optional[list[int]]:
    judge = getattr(osr_obj, "judge", None)
    if not isinstance(judge, dict):
        return None

    judgements = source_ruleset.raw_data.get("Judgements", []) if isinstance(source_ruleset.raw_data, dict) else []
    if not isinstance(judgements, list) or not judgements:
        return None

    out: list[int] = []
    for item in judgements:
        name = str(item.get("Name", "")) if isinstance(item, dict) else ""
        key = _normalize_judgement_name(name)

        value = 0
        if "300G" in key or "MARV" in key or "GEKI" in key:
            value = int(judge.get("320", 0) or 0)
        elif "MISS" in key or key == "0":
            value = int(judge.get("0", 0) or 0)
        elif "300" in key:
            value = int(judge.get("300", 0) or 0)
        elif "200" in key or "KATU" in key:
            value = int(judge.get("200", 0) or 0)
        elif "100" in key:
            value = int(judge.get("100", 0) or 0)
        elif "50" in key:
            value = int(judge.get("50", 0) or 0)
        out.append(max(0, value))

    return out


def _accuracy_from_counts(source_ruleset: ruleset_file, counts: list[int], fallback: float) -> tuple[float, float, float]:
    raw = source_ruleset.raw_data if isinstance(source_ruleset.raw_data, dict) else {}
    acc = raw.get("Accuracy") if isinstance(raw.get("Accuracy"), dict) else {}
    points = acc.get("PointsPerJudgement") if isinstance(acc.get("PointsPerJudgement"), list) else None
    if not isinstance(points, list) or len(points) != len(counts):
        return fallback, 0.0, 0.0

    total_objects = float(sum(int(c) for c in counts))
    if total_objects <= 0:
        return 1.0, 0.0, 0.0

    weights = [float(v) for v in points]
    points_sum = sum(float(c) * w for c, w in zip(counts, weights))
    max_weight = max(weights) if weights else 1.0
    max_points = total_objects * max_weight
    if max_points <= 0:
        return fallback, points_sum, max_points
    return points_sum / max_points, points_sum, max_points


def _align_source_score_with_osr_header(
    *,
    score: dict[str, Any],
    source_ruleset: ruleset_file,
    osr_obj: osr_file,
) -> dict[str, Any]:
    if not isinstance(score, dict):
        return score
    if score.get("status") != "OK":
        return score

    template = str((getattr(source_ruleset, "template_context", {}) or {}).get("template", "")).lower()
    if template not in {"osu", "osu-sv2"}:
        return score

    counts = _counts_from_osr_for_ruleset(source_ruleset, osr_obj)
    if not counts:
        return score

    merged = dict(score)
    merged["judgement_counts"] = counts

    fallback_acc = float(score.get("accuracy_fraction", 0.0) or 0.0)
    acc_frac, points_sum, max_points = _accuracy_from_counts(source_ruleset, counts, fallback_acc)
    merged["accuracy_fraction"] = float(acc_frac)
    if max_points > 0:
        merged["points_sum"] = float(points_sum)
        merged["max_points"] = float(max_points)

    combo = dict(score.get("combo", {}) if isinstance(score.get("combo"), dict) else {})
    best_combo = int(getattr(osr_obj, "max_combo", combo.get("best_combo", 0)) or 0)
    combo_breaks = int(getattr(osr_obj, "judge", {}).get("0", combo.get("combo_breaks", 0)) or 0)
    combo["best_combo"] = max(0, best_combo)
    combo["combo_breaks"] = max(0, combo_breaks)
    merged["combo"] = combo

    return merged


def _decimal_places_from_ruleset(rs: ruleset_file) -> int:
    fmt = rs.raw_data.get("Formatting") if isinstance(rs.raw_data, dict) else None
    if not isinstance(fmt, dict):
        return 2

    value = str(fmt.get("DecimalPlaces", "TWO")).upper()
    if value == "THREE":
        return 3
    if value == "FOUR":
        return 4
    return 2


def _format_accuracy_percent(score: dict[str, Any], rs: ruleset_file) -> str:
    frac = float(score.get("accuracy_fraction", 0.0) or 0.0)
    dp = _decimal_places_from_ruleset(rs)
    return f"{frac * 100:.{dp}f}%"


def _format_judgement_counts(score: dict[str, Any], rs: ruleset_file) -> str:
    counts = score.get("judgement_counts", [])
    judgements = rs.raw_data.get("Judgements", []) if isinstance(rs.raw_data, dict) else []

    if not isinstance(counts, list) or not isinstance(judgements, list):
        return "无"

    lines: list[str] = []
    for idx, judgement in enumerate(judgements):
        name = f"J{idx}"
        if isinstance(judgement, dict):
            name = str(judgement.get("Name", name))
        value = 0
        if idx < len(counts):
            try:
                value = int(counts[idx])
            except Exception:
                value = 0
        lines.append(f"{name}:{value}")
    return " | ".join(lines) if lines else "无"


def _format_lamp(score: dict[str, Any]) -> str:
    lamp = score.get("lamp")
    if isinstance(lamp, str):
        lamp_name = lamp.strip()
        if lamp_name:
            return lamp_name

    lamps = score.get("lamps")
    if not isinstance(lamps, dict):
        return "None"

    passed = [name for name, ok in lamps.items() if bool(ok)]
    return passed[0] if passed else "None"


def _format_grade(score: dict[str, Any]) -> str:
    grade = score.get("grade")
    if not isinstance(grade, dict):
        return "None"
    name = str(grade.get("name", "")).strip()
    return name if name else "None"


def _visible_warnings(score: dict[str, Any]) -> list[str]:
    raw = score.get("warnings")
    if not isinstance(raw, list):
        return []

    severe_flags = ("[severe]", "[critical]", "[fatal]", "严重", "错误", "error", "critical", "fatal")
    visible: list[str] = []
    for item in raw:
        text = str(item).strip()
        if not text:
            continue
        low = text.lower()
        if any(flag in low for flag in severe_flags):
            visible.append(text)
    return visible


def _format_score_block(title: str, score: dict[str, Any], rs: ruleset_file) -> str:
    combo = score.get("combo", {}) if isinstance(score.get("combo"), dict) else {}
    best_combo = int(combo.get("best_combo", 0) or 0)
    combo_breaks = int(combo.get("combo_breaks", 0) or 0)
    grade_text = _format_grade(score)
    lamp_text = _format_lamp(score)

    grade_and_lamp = grade_text
    if lamp_text not in {"", "None", "NONE", "无"}:
        grade_and_lamp = f"{grade_text} | {lamp_text}"

    lines = [
        f"[{title}]",
        grade_and_lamp,
        f"准确度: {_format_accuracy_percent(score, rs)}",
        f"判定: {_format_judgement_counts(score, rs)}",
        f"最大连击: {best_combo} ({combo_breaks}X)",
    ]

    warnings = _visible_warnings(score)
    if warnings:
        lines.append("警告: " + "；".join(warnings[:3]))

    return "\n".join(lines)


def format_cvtscore_message(
    *,
    source_info: dict[str, Any],
    target_info: dict[str, Any],
    source_ruleset: ruleset_file,
    target_ruleset: ruleset_file,
    source_score: dict[str, Any],
    target_score: dict[str, Any],
) -> str:
    source_display = str(source_info.get("display", "未知"))
    target_display = str(target_info.get("display", "未知"))

    head = [
        "转换完成。",
        f"源规则: {source_display}",
        f"目标规则: {target_display}",
    ]
    body = [
        _format_score_block("源规则成绩", source_score, source_ruleset),
        "\n",
        _format_score_block("转换后成绩", target_score, target_ruleset),
    ]

    return "\n".join(head + [""] + body)


def _normalize_argb_color(color: Any) -> tuple[int, int, int, int] | None:
    if not isinstance(color, list) or len(color) != 4:
        return None

    channels: list[int] = []
    for value in color:
        if not isinstance(value, int):
            return None
        channels.append(min(255, max(0, value)))

    return channels[0], channels[1], channels[2], channels[3]


def _rgba_css_from_argb(
    color: Any,
    *,
    alpha_scale: float,
    alpha_floor: float,
    fallback: str,
) -> str:
    argb = _normalize_argb_color(color)
    if argb is None:
        return fallback

    a, r, g, b = argb
    alpha = min(1.0, max(alpha_floor, (a / 255.0) * alpha_scale))
    return f"rgba({r}, {g}, {b}, {alpha:.3f})"


def _srgb_to_linear(channel: int) -> float:
    value = channel / 255.0
    if value <= 0.04045:
        return value / 12.92
    return ((value + 0.055) / 1.055) ** 2.4


def _relative_luminance_from_argb(color: Any) -> float | None:
    argb = _normalize_argb_color(color)
    if argb is None:
        return None

    _, r, g, b = argb
    return 0.2126 * _srgb_to_linear(r) + 0.7152 * _srgb_to_linear(g) + 0.0722 * _srgb_to_linear(b)


def _text_color_for_argb(color: Any) -> str:
    lum = _relative_luminance_from_argb(color)
    if lum is None:
        return "#f5f7ff"
    return "#0f1424" if lum >= 0.62 else "#f5f7ff"


def _find_named_color(items: Any, name: str) -> Any:
    if not isinstance(items, list):
        return None

    target = str(name or "").strip().lower()
    if not target:
        return None

    for item in items:
        if not isinstance(item, dict):
            continue
        item_name = str(item.get("Name", "")).strip().lower()
        if item_name == target:
            return item.get("Color")
    return None


def _build_judgement_rows(score: dict[str, Any], rs: ruleset_file) -> list[dict[str, Any]]:
    counts = score.get("judgement_counts", [])
    if not isinstance(counts, list):
        counts = []

    judgements = rs.raw_data.get("Judgements", []) if isinstance(rs.raw_data, dict) else []
    if not isinstance(judgements, list):
        return []

    rows: list[dict[str, Any]] = []
    for idx, judgement in enumerate(judgements):
        if not isinstance(judgement, dict):
            continue

        name = str(judgement.get("Name", f"J{idx}"))
        count = 0
        if idx < len(counts):
            try:
                count = int(counts[idx])
            except Exception:
                count = 0

        color = judgement.get("Color")
        rows.append(
            {
                "name": name,
                "count": str(max(0, count)),
                "bg": _rgba_css_from_argb(
                    color,
                    alpha_scale=0.35,
                    alpha_floor=0.16,
                    fallback="rgba(255, 255, 255, 0.14)",
                ),
                "border": _rgba_css_from_argb(
                    color,
                    alpha_scale=0.9,
                    alpha_floor=0.34,
                    fallback="rgba(255, 255, 255, 0.30)",
                ),
                "text": _text_color_for_argb(color),
                "swatch": _rgba_css_from_argb(
                    color,
                    alpha_scale=1.0,
                    alpha_floor=0.7,
                    fallback="rgba(255, 255, 255, 0.85)",
                ),
            }
        )

    return rows


def _format_combo_text(score: dict[str, Any]) -> str:
    combo = score.get("combo", {}) if isinstance(score.get("combo"), dict) else {}
    best_combo = int(combo.get("best_combo", 0) or 0)
    combo_breaks = int(combo.get("combo_breaks", 0) or 0)
    return f"{best_combo} ({combo_breaks}X)"


def _is_visible_badge_value(value: str) -> bool:
    normalized = str(value or "").strip().lower()
    return normalized not in {"", "none", "无"}


def _build_judgement_bar_rows(score: dict[str, Any], rs: ruleset_file) -> list[dict[str, Any]]:
    counts = score.get("judgement_counts", [])
    if not isinstance(counts, list):
        counts = []

    judgements = rs.raw_data.get("Judgements", []) if isinstance(rs.raw_data, dict) else []
    if not isinstance(judgements, list):
        return []

    normalized: list[tuple[str, int, Any]] = []
    max_count = 0

    for idx, judgement in enumerate(judgements):
        if not isinstance(judgement, dict):
            continue

        name = str(judgement.get("Name", f"J{idx}"))
        count = 0
        if idx < len(counts):
            try:
                count = max(0, int(counts[idx]))
            except Exception:
                count = 0

        max_count = max(max_count, count)
        normalized.append((name, count, judgement.get("Color")))

    if max_count <= 0:
        max_count = 1

    rows: list[dict[str, Any]] = []
    for name, count, color in normalized:
        width = 0.0 if count <= 0 else min(100.0, max(6.0, count / max_count * 100.0))
        rows.append(
            {
                "name": name,
                "count": str(count),
                "width": f"{width:.1f}%",
                "track": _rgba_css_from_argb(
                    color,
                    alpha_scale=0.26,
                    alpha_floor=0.12,
                    fallback="rgba(75, 90, 128, 0.34)",
                ),
                "fill": _rgba_css_from_argb(
                    color,
                    alpha_scale=1.0,
                    alpha_floor=0.62,
                    fallback="rgba(85, 200, 255, 0.82)",
                ),
                "count_bg": _rgba_css_from_argb(
                    color,
                    alpha_scale=0.34,
                    alpha_floor=0.16,
                    fallback="rgba(255, 255, 255, 0.14)",
                ),
                "count_border": _rgba_css_from_argb(
                    color,
                    alpha_scale=0.9,
                    alpha_floor=0.34,
                    fallback="rgba(255, 255, 255, 0.30)",
                ),
                "count_text": _text_color_for_argb(color),
            }
        )

    return rows


def _resolve_cvtscore_card_height(use_bar_chart: bool, row_count: int) -> int:
    safe_rows = max(1, int(row_count))
    if use_bar_chart:
        return int(min(580, max(460, 380 + safe_rows * 20)))
    return int(min(600, max(470, 400 + safe_rows * 14)))


def _build_score_section(
    title: str,
    score: dict[str, Any],
    rs: ruleset_file,
    *,
    prefer_bar_chart: bool,
) -> dict[str, Any]:
    grade_name = _format_grade(score)
    lamp_name = _format_lamp(score)

    grades = rs.raw_data.get("Grades", []) if isinstance(rs.raw_data, dict) else []
    lamps = rs.raw_data.get("Lamps", []) if isinstance(rs.raw_data, dict) else []

    grade_color = _find_named_color(grades, grade_name)
    lamp_color = _find_named_color(lamps, lamp_name)

    warnings = _visible_warnings(score)
    chip_rows = _build_judgement_rows(score, rs)
    bar_rows = _build_judgement_bar_rows(score, rs)

    # 估算条形图高度，超出可用空间时回退到原 chip 形式。
    estimated_bar_height = len(bar_rows) * 30
    use_bar_chart = bool(prefer_bar_chart and bar_rows and estimated_bar_height <= 250)
    card_height = _resolve_cvtscore_card_height(
        use_bar_chart=use_bar_chart,
        row_count=len(bar_rows) if use_bar_chart else len(chip_rows),
    )

    show_grade = _is_visible_badge_value(grade_name)
    show_lamp = _is_visible_badge_value(lamp_name)

    return {
        "title": title,
        "grade": grade_name if show_grade else "",
        "grade_bg": _rgba_css_from_argb(
            grade_color,
            alpha_scale=0.36,
            alpha_floor=0.16,
            fallback="rgba(255, 255, 255, 0.14)",
        ),
        "grade_border": _rgba_css_from_argb(
            grade_color,
            alpha_scale=0.9,
            alpha_floor=0.34,
            fallback="rgba(255, 255, 255, 0.30)",
        ),
        "grade_text": _text_color_for_argb(grade_color),
        "show_grade": show_grade,
        "lamp": lamp_name if show_lamp else "",
        "lamp_bg": _rgba_css_from_argb(
            lamp_color,
            alpha_scale=0.36,
            alpha_floor=0.16,
            fallback="rgba(135, 155, 190, 0.18)",
        ),
        "lamp_border": _rgba_css_from_argb(
            lamp_color,
            alpha_scale=0.9,
            alpha_floor=0.34,
            fallback="rgba(135, 155, 190, 0.35)",
        ),
        "lamp_text": _text_color_for_argb(lamp_color),
        "show_lamp": show_lamp,
        "accuracy": _format_accuracy_percent(score, rs),
        "combo": _format_combo_text(score),
        "judgements": chip_rows,
        "judgement_bars": bar_rows,
        "use_bar_chart": use_bar_chart,
        "card_height": card_height,
        "warnings_text": "；".join(warnings[:2]),
    }


def build_cvtscore_card_data(
    *,
    source_info: dict[str, Any],
    target_info: dict[str, Any],
    source_ruleset: ruleset_file,
    target_ruleset: ruleset_file,
    source_score: dict[str, Any],
    target_score: dict[str, Any],
) -> dict[str, Any]:
    target_section = _build_score_section(
        "Converted Score",
        target_score,
        target_ruleset,
        prefer_bar_chart=True,
    )

    return {
        "status_text": "Conversion Complete",
        "source_display": str(source_info.get("display", "Unknown")),
        "target_display": str(target_info.get("display", "Unknown")),
        "target": target_section,
        "card_height": int(target_section.get("card_height", 500)),
    }


async def _render_cvtscore_card_once(template_dir: Path, data: dict[str, Any]) -> bytes:
    # try:
    #     card_height = int(data.get("card_height", 400))
    # except Exception:
    #     card_height = 400
    # card_height = min(620, max(450, card_height))
    card_height = 400

    template_to_pic = _get_template_to_pic()
    return await template_to_pic(
        template_path=template_dir,
        template_name=_CVTSCORE_TEMPLATE_NAME,
        templates=data,
        max_width=475,
        device_height=card_height,
        allow_refit=False,
    )


async def render_cvtscore_card(data: dict[str, Any], template_dir: Path | None = None) -> bytes:
    target_dir = template_dir or _card_templates_dir()

    async with _CVTSCORE_RENDER_LOCK:
        last_future_error: Exception | None = None

        for attempt in range(3):
            try:
                return await _render_cvtscore_card_once(target_dir, data)
            except Exception as exc:
                if _FUTURE_NOT_READY_TEXT not in str(exc):
                    raise
                last_future_error = exc
                await asyncio.sleep(0.05 * (attempt + 1))

        try:
            return await _render_cvtscore_card_once(target_dir, data)
        except Exception as exc:
            if _FUTURE_NOT_READY_TEXT in str(exc) and last_future_error is not None:
                raise RuntimeError("htmlkit renderer is not ready, please retry later.") from last_future_error
            raise


def validate_replay_status(
    replay_kind: str,
    osr_obj: Optional[osr_file] = None,
    mr_obj: Optional[mr_file] = None,
) -> Optional[str]:
    if replay_kind.lower() == "osr":
        if osr_obj is None:
            return "osr 回放对象为空。"
        status = str(getattr(osr_obj, "status", ""))
        if status == "NotMania":
            return "该回放不是 Mania 模式。"
        if status == "tooFewKeys":
            return "有效轨道数量过少，无法计算。"
        if status != "OK":
            return f"回放状态异常: {status}"
        return None

    if replay_kind.lower() == "mr":
        if mr_obj is None:
            return "mr 回放对象为空。"
        status = str(getattr(mr_obj, "status", ""))
        if status != "OK":
            return f"mr 回放状态异常: {status}"
        return None

    return f"不支持的回放类型: {replay_kind}"


def validate_chart_status(osu_obj: osu_file) -> Optional[str]:
    status = str(getattr(osu_obj, "status", ""))
    if status == "NotMania":
        return "该谱面不是 Mania 模式。"
    if status != "OK":
        return f"谱面状态异常: {status}"
    return None
