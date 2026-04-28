from __future__ import annotations

from .calc import OfficialRunnerError

__all__ = [
    "OfficialRunnerError",
    "ETTNotManiaError",
    "ETTParseError",
    "ETTUnsupportedKeyError",
    "analyze_ett_chart",
    "analyze_ett_zip",
]


def __getattr__(name: str):
    if name in {"ETTNotManiaError", "ETTParseError", "ETTUnsupportedKeyError", "analyze_ett_chart", "analyze_ett_zip", "format_ett_result_text"}:
        from .ett import (  # imported lazily to keep estimator imports lightweight
            ETTNotManiaError,
            ETTParseError,
            ETTUnsupportedKeyError,
            analyze_ett_chart,
            analyze_ett_zip,
            format_ett_result_text,
        )

        globals().update(
            {
                "ETTNotManiaError": ETTNotManiaError,
                "ETTParseError": ETTParseError,
                "ETTUnsupportedKeyError": ETTUnsupportedKeyError,
                "analyze_ett_chart": analyze_ett_chart,
                "analyze_ett_zip": analyze_ett_zip,
                "format_ett_result_text": format_ett_result_text,
            }
        )
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
