# -*- coding: utf-8 -*-
"""
对应 prelude/src/Calculator/Strain.fs
目前 PatternReport 只用到 calculate_finger_strains 的 StrainV1Notes
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import List, Tuple

from ..time_types import Rate, Time, GameplayTime
from ..chart import NoteType, NoteRow, TimeArray
from .notes import NoteDifficulty


@dataclass
class RowStrain:
    NotesV1: List[float]
    StrainV1Notes: List[float]


STRAIN_SCALE = 0.01626
STRAIN_TIME_CAP = 200.0  # ms/rate


def strain_func(half_life: float):
    # DECAY_RATE = log 0.5 / half_life
    decay_rate = math.log(0.5) / half_life

    def f(value: float, input_v: float, delta: GameplayTime) -> float:
        dcap = min(STRAIN_TIME_CAP, delta)
        decay = math.exp(decay_rate * dcap)
        time_cap_decay = math.exp(decay_rate * (delta - STRAIN_TIME_CAP)) if delta > STRAIN_TIME_CAP else 1.0
        a = value * time_cap_decay
        b = input_v * input_v * STRAIN_SCALE
        return b - (b - a) * decay

    return f


strain_burst = strain_func(1575.0)
# strain_stamina = strain_func(60000.0)  # PatternReport 目前不需要


def calculate_finger_strains(rate: Rate, notes: TimeArray[NoteRow], note_difficulty: List[List[NoteDifficulty]]) -> List[RowStrain]:
    keys = len(notes[0].Data)
    last_note_in_column: List[Time] = [0.0 for _ in range(keys)]
    strain_v1: List[float] = [0.0 for _ in range(keys)]

    out: List[RowStrain] = []

    for i in range(len(notes)):
        offset = notes[i].Time
        nr = notes[i].Data

        notes_v1 = [0.0 for _ in range(keys)]
        row_strain_v1 = [0.0 for _ in range(keys)]

        for k in range(keys):
            if nr[k] in (NoteType.NORMAL, NoteType.HOLDHEAD):
                notes_v1[k] = note_difficulty[i][k].Total
                delta = (offset - last_note_in_column[k]) / rate
                strain_v1[k] = strain_burst(strain_v1[k], notes_v1[k], delta)
                row_strain_v1[k] = strain_v1[k]
                last_note_in_column[k] = offset

        out.append(RowStrain(NotesV1=notes_v1, StrainV1Notes=row_strain_v1))

    return out