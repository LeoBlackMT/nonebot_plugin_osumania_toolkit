from __future__ import annotations

import asyncio
from typing import Optional

from .osu_parser import parse_osu_mania
from .calculator.difficulty import calculate as calc_difficulty
from .patterns.summary import PatternReport, from_chart


class PatternParseError(Exception):
    pass


class PatternNotManiaError(Exception):
    pass


def _format_specific_types(specific_types: list[tuple[str, float]]) -> str:
    if not specific_types:
        return ""
    parts = []
    for name, ratio in specific_types[:3]:
        parts.append(f"{ratio * 100:.0f}% {name}")
    return ", ".join(parts)


def format_pattern_result_text(meta_data, report: PatternReport, rate: float = 1.0) -> str:
    lines = []

    if isinstance(meta_data, dict):
        creator = meta_data.get("Creator", "Unknown")
        artist = meta_data.get("Artist", "Unknown")
        title = meta_data.get("Title", "Unknown")
        version = meta_data.get("Version", "Unknown")
        lines.append(f"{creator} // {artist} - {title} [{version}]")
    else:
        lines.append("谱面信息解析失败")

    lines.append(f"键型分类: {report.Category}")

    if not report.Clusters:
        lines.append("未识别到有效键型聚类。")
    else:
        lines.append("键型聚类:")
        for c in report.Clusters:
            row = f"- {c.Format(rate)} | Rating={c.Rating:.3f} | Amount={c.Amount/1000.0:.2f}s"
            st = _format_specific_types(c.SpecificTypes)
            if st:
                row += f" | {st}"
            lines.append(row)

    return "\n".join(lines)


def _analyze_pattern_file_sync(file_path: str, rate: float) -> PatternReport:
    chart = parse_osu_mania(file_path)
    diff = calc_difficulty(rate, chart.Notes)
    return from_chart(diff, chart)


async def analyze_pattern_file(file_path: str, rate: float = 1.0) -> PatternReport:
    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(None, _analyze_pattern_file_sync, file_path, rate)
    except PatternNotManiaError:
        raise
    except ValueError as e:
        if "not mania" in str(e).lower():
            raise PatternNotManiaError() from e
        raise PatternParseError(str(e)) from e
    except Exception as e:
        raise PatternParseError(str(e)) from e
