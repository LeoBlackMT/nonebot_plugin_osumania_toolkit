# -*- coding: utf-8 -*-
"""
对应 prelude/src/Calculator/Patterns/Primitives.fs
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple

from ..chart import Chart, NoteType
from .density import Density
from ..calculator.difficulty import Difficulty


class Direction(Enum):
    None_ = "None"
    Left = "Left"
    Right = "Right"
    Outwards = "Outwards"
    Inwards = "Inwards"


@dataclass
class RowInfo:
    Index: int
    Time: float
    MsPerBeat: float
    Notes: int
    Jacks: int
    Direction: Direction
    Roll: bool
    Density: Density
    Variety: float
    Strains: List[float]
    RawNotes: List[int]


def detect_direction(previous_row: List[int], current_row: List[int]) -> Tuple[Direction, bool]:
    assert len(previous_row) > 0
    assert len(current_row) > 0

    pleftmost = previous_row[0]
    prightmost = previous_row[-1]
    cleftmost = current_row[0]
    crightmost = current_row[-1]

    leftmost_change = cleftmost - pleftmost
    rightmost_change = crightmost - prightmost

    if leftmost_change > 0:
        if rightmost_change > 0:
            direction = Direction.Right
        else:
            direction = Direction.Inwards
    elif leftmost_change < 0:
        if rightmost_change < 0:
            direction = Direction.Left
        else:
            direction = Direction.Outwards
    else:
        if rightmost_change < 0:
            direction = Direction.Inwards
        elif rightmost_change > 0:
            direction = Direction.Outwards
        else:
            direction = Direction.None_

    is_roll = (pleftmost > crightmost) or (prightmost < cleftmost)
    return direction, is_roll


def calculate_primitives(density_arr: List[Density], difficulty_info: Difficulty, chart: Chart) -> List[RowInfo]:
    first_note = chart.Notes[0].Time
    first_row = chart.Notes[0].Data

    previous_row = [k for k in range(chart.Keys) if first_row[k] in (NoteType.NORMAL, NoteType.HOLDHEAD)]
    if len(previous_row) == 0:
        # F# 会 Logging.Error 然后返回 []
        return []

    previous_time = first_note
    index = 0

    out: List[RowInfo] = []

    # 从第二行开始
    for item in chart.Notes[1:]:
        t = item.Time
        row = item.Data
        index += 1

        current_row = [k for k in range(chart.Keys) if row[k] in (NoteType.NORMAL, NoteType.HOLDHEAD)]
        if len(current_row) == 0:
            continue

        direction, is_roll = detect_direction(previous_row, current_row)
        # Jacks = current_row.Length - (Array.except previous_row current_row).Length
        # 即：当前行里有多少列也在上一行里（交集大小）
        except_count = len([x for x in current_row if x not in previous_row])
        jacks = len(current_row) - except_count

        out.append(
            RowInfo(
                Index=index,
                Time=(t - first_note),
                MsPerBeat=(t - previous_time) * 4.0,   # *4 => 1/4 间隔
                Notes=len(current_row),
                Jacks=jacks,
                Direction=direction,
                Roll=is_roll,
                Density=density_arr[index],
                Variety=difficulty_info.Variety[index],
                Strains=difficulty_info.Strains[index].StrainV1Notes,
                RawNotes=current_row,
            )
        )

        previous_row = current_row
        previous_time = t

    return out


def ln_percent(chart: Chart) -> float:
    notes = 0
    lnotes = 0
    for item in chart.Notes:
        nr = item.Data
        for n in nr:
            if n == NoteType.NORMAL:
                notes += 1
            elif n == NoteType.HOLDHEAD:
                notes += 1
                lnotes += 1
    return (float(lnotes) / float(notes)) if notes > 0 else 0.0


def sv_time(chart: Chart) -> float:
    # 对应 Metrics.sv_time：统计 SV != 1 的时间段
    if len(chart.SV) == 0:
        return 0.0
    total = 0.0
    time = chart.FirstNote
    vel = 1.0
    for sv in chart.SV:
        if (not (vel == vel)) or abs(vel - 1.0) > 0.01:
            total += (sv.Time - time)
        vel = sv.Data
        time = sv.Time
    if (not (vel == vel)) or abs(vel - 1.0) > 0.01:
        total += (chart.LastNote - time)
    return total