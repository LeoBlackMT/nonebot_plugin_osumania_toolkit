# -*- coding: utf-8 -*-
"""
对应 prelude/src/Calculator/Variety.fs
"""

from __future__ import annotations

from typing import Dict, List
import math

from ..time_types import Rate
from ..chart import NoteType, NoteRow, TimeArray
from .notes import NoteDifficulty


VARIETY_WINDOW = 750.0  # ms/rate


def _round_fsharp(x: float) -> float:
    """
    F# 的 round：银行家舍入（MidpointToEven）。
    Python 的 round 也是 bankers rounding（对 .5），行为基本一致。
    """
    return float(round(x))


def calculate_variety(rate: Rate, notes: TimeArray[NoteRow], note_difficulties: List[List[NoteDifficulty]]) -> List[float]:
    keys = len(notes[0].Data)

    buckets: Dict[float, int] = {}
    front = 0
    back = 0

    out: List[float] = []

    for i in range(len(notes)):
        now = notes[i].Time

        # front 推进：< now + window*rate
        while front < len(notes) and notes[front].Time < now + VARIETY_WINDOW * rate:
            fnr = notes[front].Data
            for k in range(keys):
                if fnr[k] in (NoteType.NORMAL, NoteType.HOLDHEAD):
                    strain = _round_fsharp(note_difficulties[front][k].Total / 5.0)
                    buckets[strain] = buckets.get(strain, 0) + 1
            front += 1

        # back 推进：< now - window*rate
        while back < i and notes[back].Time < now - VARIETY_WINDOW * rate:
            bnr = notes[back].Data
            for k in range(keys):
                if bnr[k] in (NoteType.NORMAL, NoteType.HOLDHEAD):
                    strain = _round_fsharp(note_difficulties[back][k].Total / 5.0)
                    buckets[strain] = buckets.get(strain, 0) - 1
                    if buckets[strain] == 0:
                        del buckets[strain]
            back += 1

        out.append(float(len(buckets)))

    return out