from __future__ import annotations

import asyncio
import os
import shutil
import time
from pathlib import Path
from typing import Any

from nonebot import require

require("nonebot_plugin_htmlkit")
from nonebot_plugin_htmlkit import template_to_pic  # type: ignore[import-not-found]

from ...file.osu_file_parser import osu_file
from ..convert import convert_mc_to_osu
from ..mapview import (
    STAR_BG_STOPS,
    STAR_TEXT_STOPS,
    _color_for,
    _mode_tag_class,
    _pick_readable_text_color,
)
from ..patterns import analyze_pattern_file
from ..utils import extract_zip_file, is_mc_file, resolve_meta_data
from .calc import OfficialRunnerError, compute_difficulties

DEFAULT_SCORE_GOAL = 0.93
MAX_SKILL_VALUE = 41.0
OVERALL_MAX = 41.0
OVERALL_TO_STAR_MAX = 10.0
SKILLSET_ORDER = [
    "Stream",
    "Jumpstream",
    "Handstream",
    "Stamina",
    "JackSpeed",
    "Chordjack",
    "Technical",
]


class ETTParseError(Exception):
    pass


class ETTNotManiaError(Exception):
    pass


class ETTUnsupportedKeyError(Exception):
    pass


async def render_ett_card(template_dir: Path, data: dict) -> bytes:
    image_bytes = await template_to_pic(
        template_path=template_dir,
        template_name="ett.html",
        templates=data,
        max_width=475,
        device_height=520,
        allow_refit=False,
    )
    return image_bytes


def _render_meta_title(meta_data: Any) -> str:
    if isinstance(meta_data, dict):
        need = {"Creator", "Artist", "Title", "Version"}
        if need.issubset(meta_data.keys()):
            return f"{meta_data['Artist']} - {meta_data['Title']} [{meta_data['Version']}] // {meta_data['Creator']}"
    return "*Failed to parse meta data*"


def _resolve_keycount(parsed_count: int) -> int:
    if parsed_count in (4, 6, 7):
        return parsed_count
    raise ETTUnsupportedKeyError(
        f"该谱面 key 数为 {parsed_count}，ETT 仅支持 4/6/7 键谱面。"
    )


def _format_rate(rate: float) -> str:
    return f"{rate:.2f}".rstrip("0").rstrip(".")


def _build_skill_rows(values: dict[str, float]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for name in SKILLSET_ORDER:
        value = float(values.get(name, 0.0))
        clamped = max(0.0, min(value, MAX_SKILL_VALUE))
        width = (clamped / MAX_SKILL_VALUE) * 100.0
        label_pos = max(14.0, min(width, 98.0))
        rows.append(
            {
                "label": name,
                "value_text": f"{value:.2f}",
                "width": f"{width:.2f}%",
                "label_pos": f"{label_pos:.2f}%",
            }
        )
    return rows


def _overall_to_star_value(overall: float) -> float:
    normalized = max(0.0, min(overall, OVERALL_MAX)) / OVERALL_MAX
    return normalized * OVERALL_TO_STAR_MAX


def _compute_values(
    chart: osu_file,
    speed_rate: float,
    keycount: int,
    score_goal: float,
) -> dict[str, float]:
    values = compute_difficulties(
        chart,
        music_rate=speed_rate,
        keycount=keycount,
        score_goal=score_goal,
    )
    return {k: float(v) for k, v in values.items()}


async def analyze_ett_chart(
    chart_file: Path,
    file_name: str,
    speed_rate: float,
    cvt_flag: list[str],
    mod_display: str,
    cache_dir: Path,
    score_goal: float = DEFAULT_SCORE_GOAL,
) -> dict[str, Any]:
    target_file = chart_file
    target_name = file_name

    if is_mc_file(str(target_file)):
        osu_file_path = convert_mc_to_osu(str(target_file), str(cache_dir))
        target_file = Path(osu_file_path)
        target_name = os.path.basename(osu_file_path)

    chart = osu_file(str(target_file))
    chart.process()

    if chart.status == "NotMania":
        raise ETTNotManiaError()
    if chart.status != "OK":
        raise ETTParseError()

    _ = cvt_flag
    _ = mod_display
    ln_ratio = chart.LN_ratio
    keycount = _resolve_keycount(chart.column_count)

    loop = asyncio.get_running_loop()
    values = await loop.run_in_executor(
        None,
        _compute_values,
        chart,
        speed_rate,
        keycount,
        score_goal,
    )
    pattern_result = await analyze_pattern_file(str(target_file), rate=speed_rate)

    meta_data = resolve_meta_data(target_file, target_name)

    meta_lines = [
        f"LN%: {ln_ratio:.2%}",
        f"Rate: x{_format_rate(speed_rate)}",
        f"Keys: {keycount}K",
    ]

    overall = float(values.get("Overall", 0.0))
    star_value = _overall_to_star_value(overall)
    overall_bg = _color_for(star_value, STAR_BG_STOPS, "#6d7894")
    overall_text_pref = _color_for(star_value, STAR_TEXT_STOPS, "#f6fbff")
    overall_text = _pick_readable_text_color(star_value, overall_bg, overall_text_pref)

    return {
        "file_name": target_name,
        "template": {
            "status_text": _render_meta_title(meta_data),
            "mode_tag": pattern_result.report.ModeTag,
            "mode_tag_class": _mode_tag_class(pattern_result.report.ModeTag),
            "overall_value": f"{overall:.2f}",
            "overall_bg_color": overall_bg,
            "overall_text_color": overall_text,
            "ett_meta_lines": meta_lines,
            "skillsets": _build_skill_rows(values),
        },
    }


async def analyze_ett_zip(
    zip_file: Path,
    speed_rate: float,
    cvt_flag: list[str],
    mod_display: str,
    cache_dir: Path,
    score_goal: float = DEFAULT_SCORE_GOAL,
) -> tuple[list[dict[str, Any]], list[str]]:
    temp_dir = cache_dir / f"ett_batch_{int(time.time())}_{os.getpid()}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []
    errors: list[str] = []

    try:
        chart_files = extract_zip_file(zip_file, temp_dir)
        for chart_file in chart_files:
            try:
                row = await analyze_ett_chart(
                    chart_file,
                    chart_file.name,
                    speed_rate,
                    cvt_flag,
                    mod_display,
                    temp_dir,
                    score_goal,
                )
                results.append(row)
            except ETTParseError:
                errors.append(f"{chart_file.name}: 谱面解析失败")
            except ETTNotManiaError:
                errors.append(f"{chart_file.name}: 该谱面不是 mania 模式")
            except ETTUnsupportedKeyError as e:
                errors.append(f"{chart_file.name}: {e}")
            except OfficialRunnerError as e:
                errors.append(f"{chart_file.name}: ETT 计算失败 - {e}")
            except Exception as e:
                errors.append(f"{chart_file.name}: 分析失败 - {e}")

        return results, errors
    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
