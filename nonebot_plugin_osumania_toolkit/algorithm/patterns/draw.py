from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from .service import PatternAnalysisResult


_TEMPLATE_NAME = "pattern.html"
_PATTERN_RENDER_LOCK = asyncio.Lock()
_FUTURE_NOT_READY_TEXT = "Future object is not initialized"


def _get_template_to_pic():
    from nonebot import require

    require("nonebot_plugin_htmlkit")
    from nonebot_plugin_htmlkit import template_to_pic  # type: ignore[import-not-found]

    return template_to_pic


def _template_dir_from_file() -> Path:
    return Path(__file__).resolve().parents[2] / "templates"


def _format_meta_title(meta_data: Any) -> str:
    if isinstance(meta_data, dict):
        required = {"Creator", "Artist", "Title", "Version"}
        if required.issubset(meta_data.keys()):
            return f"{meta_data['Artist']} - {meta_data['Title']} [{meta_data['Version']}] // {meta_data['Creator']}"
    return "*Failed to parse meta data*"


def _mode_tag_class(tag: str) -> str:
    normalized = tag if tag in {"RC", "LN", "HB", "Mix"} else "Mix"
    return f"mode-{normalized.lower()}"


def _specific_types_text(specific_types: list[tuple[str, float]]) -> str:
    if not specific_types:
        return "-"
    top = sorted(specific_types, key=lambda x: x[1], reverse=True)[:2]
    return ", ".join(f"{name} ({ratio * 100:.1f}%)" for name, ratio in top)


def _build_cluster_rows(result: PatternAnalysisResult, rate: float, max_rows: int = 6) -> list[dict[str, Any]]:
    report = result.report
    source_clusters = list(report.ImportantClusters) or list(report.Clusters)
    clusters = source_clusters[:max_rows]
    rows: list[dict[str, str]] = []

    if clusters:
        max_amount = max(float(c.Amount or 0.0) for c in clusters)
        if max_amount <= 0.0:
            max_amount = 1.0

        duration = float(report.Duration or 0.0)
        if duration <= 0.0:
            duration = 1.0

        for cluster in clusters:
            amount = float(cluster.Amount or 0.0)
            width = max(8.0, amount / max_amount * 100.0)
            amount_ratio = max(0.0, amount / duration * 100.0)
            rows.append(
                {
                    "label": cluster.Format(rate),
                    "width": f"{width:.1f}%",
                    "amount_text": f"{amount_ratio:.2f}%",
                    "subtype": _specific_types_text(list(cluster.SpecificTypes or [])),
                    "is_empty": False,
                }
            )

    while len(rows) < max_rows:
        rows.append(
            {
                "label": "-",
                "width": "0%",
                "amount_text": "-",
                "subtype": "No data",
                "is_empty": True,
            }
        )

    return rows


def build_pattern_card_data(meta_data: Any, result: PatternAnalysisResult, rate: float = 1.0) -> dict[str, Any]:
    report = result.report
    mode_tag = report.ModeTag if report.ModeTag in {"RC", "LN", "HB", "Mix"} else "Mix"

    metrics = [
        {"label": "Keys", "value": f"{result.keys}K"},
        {"label": "Rate", "value": f"{rate:.2f}x"},
        {"label": "LN", "value": f"{report.LNPercent * 100:.1f}%"},
    ]

    return {
        "status_text": "Pattern Analysis",
        "meta_title": _format_meta_title(meta_data),
        "category": report.Category or "Unknown",
        "mode_tag": mode_tag,
        "mode_tag_class": _mode_tag_class(mode_tag),
        "metrics": metrics,
        "clusters": _build_cluster_rows(result, rate=rate),
    }


async def _render_pattern_card_once(template_dir: Path, data: dict[str, Any]) -> bytes:
    template_to_pic = _get_template_to_pic()
    return await template_to_pic(
        template_path=template_dir,
        template_name=_TEMPLATE_NAME,
        templates=data,
        max_width=475,
        device_height=520,
        allow_refit=False,
    )


async def render_pattern_card(data: dict[str, Any], template_dir: Path | None = None) -> bytes:
    target_dir = template_dir or _template_dir_from_file()

    async with _PATTERN_RENDER_LOCK:
        last_future_error: Exception | None = None

        for attempt in range(3):
            try:
                return await _render_pattern_card_once(target_dir, data)
            except Exception as exc:
                if _FUTURE_NOT_READY_TEXT not in str(exc):
                    raise
                last_future_error = exc
                await asyncio.sleep(0.05 * (attempt + 1))

        try:
            return await _render_pattern_card_once(target_dir, data)
        except Exception as exc:
            if _FUTURE_NOT_READY_TEXT in str(exc) and last_future_error is not None:
                raise RuntimeError("htmlkit renderer is not ready, please retry later.") from last_future_error
            raise
