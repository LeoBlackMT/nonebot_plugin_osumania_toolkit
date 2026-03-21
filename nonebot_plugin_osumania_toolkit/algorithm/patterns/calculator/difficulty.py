# -*- coding: utf-8 -*-
"""
对应 prelude/src/Calculator/Difficulty.fs
这里只实现 Pattern 识别需要的字段：NoteDifficulty / Strains / Variety / Overall
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable, List

from ..time_types import Rate
from ..chart import NoteRow, TimeArray
from .notes import NoteDifficulty, calculate_note_ratings
from .variety import calculate_variety
from .strain import RowStrain, calculate_finger_strains


@dataclass
class Difficulty:
    NoteDifficulty: List[List[NoteDifficulty]]
    Strains: List[RowStrain]
    Variety: List[float]
    Overall: float


CURVE_POWER = 0.6
CURVE_SCALE = 0.4056
MOST_IMPORTANT_NOTES = 2500.0

def WEIGHTING_CURVE(x: float) -> float:
    return 0.002 + x ** 4.0


def weighted_overall_difficulty(data: Iterable[float]) -> float:
    data_array = sorted(list(data))
    length = float(len(data_array))
    weight = 0.0
    total = 0.0

    for i, v in enumerate(data_array):
        x = ((float(i) + MOST_IMPORTANT_NOTES - length) / MOST_IMPORTANT_NOTES)
        x = max(x, 0.0)
        w = WEIGHTING_CURVE(x)
        weight += w
        total += v * w

    if weight == 0.0:
        return 0.0
    return (total / weight) ** CURVE_POWER * CURVE_SCALE


def calculate(rate: Rate, notes: TimeArray[NoteRow]) -> Difficulty:
    note_data = calculate_note_ratings(rate, notes)
    variety = calculate_variety(rate, notes, note_data)
    physical_data = calculate_finger_strains(rate, notes, note_data)

    # F#：physical = weighted_overall_difficulty (physical_data |> Seq.map _.StrainV1Notes |> concat |> filter >0)
    all_strains = []
    for rs in physical_data:
        for x in rs.StrainV1Notes:
            if x > 0.0:
                all_strains.append(x)

    physical = weighted_overall_difficulty(all_strains)
    if not (physical == physical and abs(physical) != float("inf")):
        physical = 0.0

    return Difficulty(
        NoteDifficulty=note_data,
        Strains=physical_data,
        Variety=variety,
        Overall=float(physical),
    )