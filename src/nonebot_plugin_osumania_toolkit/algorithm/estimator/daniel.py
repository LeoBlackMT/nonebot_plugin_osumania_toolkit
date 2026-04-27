from __future__ import annotations

from typing import Any

from .exceptions import UnsupportedKeyError
from .rc import estimate_daniel_dan
from .sunny import estimate_sunny_result


def estimate_daniel_result(
    source: Any,
    speed_rate: float = 1.0,
    od_flag: Any = None,
    cvt_flag: Any = None,
    *,
    sunny_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if sunny_result is None:
        sunny_result = estimate_sunny_result(source, speed_rate, od_flag, cvt_flag)

    column_count = int(sunny_result.get("columnCount", 0) or 0)
    if column_count != 4:
        return sunny_result

    daniel = estimate_daniel_dan(float(sunny_result.get("star", 0.0)))
    numeric = daniel["numeric"]
    est_diff = daniel["label"]
    hint = "N/A" if numeric is None else None

    return {
        **sunny_result,
        "numericDifficulty": round(float(numeric), 2) if numeric is not None else None,
        "numericDifficultyHint": hint,
        "estDiff": est_diff,
        "rawNumericDifficulty": round(float(numeric), 4) if numeric is not None else None,
    }
