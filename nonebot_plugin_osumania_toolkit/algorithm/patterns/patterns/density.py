# -*- coding: utf-8 -*-
"""
对应 prelude/src/Calculator/Patterns/Density.fs
"""

from __future__ import annotations

from typing import List

from ..chart import Chart, NoteType


Density = float  # float32</rate> -> Python float


DENSITY_SENSITIVITY = 0.9


def _note(delta_time_ms: float, d: Density) -> Density:
    next_d = 1000.0 / delta_time_ms if delta_time_ms > 0 else float("inf")
    return d * DENSITY_SENSITIVITY + next_d * (1.0 - DENSITY_SENSITIVITY)


def process_chart(chart: Chart) -> List[Density]:
    column_densities = [0.0 for _ in range(chart.Keys)]
    column_sinces = [float("-inf") for _ in range(chart.Keys)]

    out: List[Density] = []

    for item in chart.Notes:
        t = item.Time
        row = item.Data
        for k in range(chart.Keys):
            if row[k] in (NoteType.NORMAL, NoteType.HOLDHEAD):
                delta = t - column_sinces[k]
                # F# 里如果 column_sinces 是 -infinity，会得到 0 density（因为 1000/inf = 0）
                if column_sinces[k] == float("-inf"):
                    delta = float("inf")
                column_densities[k] = _note(delta, column_densities[k])
                column_sinces[k] = t

        out.append(max(column_densities))

    return out