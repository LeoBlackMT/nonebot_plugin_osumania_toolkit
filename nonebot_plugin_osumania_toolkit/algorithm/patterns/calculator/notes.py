# -*- coding: utf-8 -*-
"""
对应 prelude/src/Calculator/Notes.fs
负责为每个音符计算：
- J (jack) 同列间隔换算到 BPM（带 cutoff）
- SL / SR (stream-left/right) 同手其他列的 stream 值（带 compensation + cutoff curve）
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import List

from ..time_types import Rate, Time, GameplayTime
from ..chart import NoteType, NoteRow, TimeArray
from .layout import keys_on_left_hand


@dataclass
class NoteDifficulty:
    J: float = 0.0
    SL: float = 0.0
    SR: float = 0.0

    @property
    def Total(self) -> float:
        return total(self)


JACK_CURVE_CUTOFF = 230.0

def ms_to_jack_bpm(delta: GameplayTime) -> float:
    # 15000 / delta, 再 min cutoff
    if delta <= 0:
        return JACK_CURVE_CUTOFF
    return min(15000.0 / delta, JACK_CURVE_CUTOFF)


STREAM_CURVE_CUTOFF = 10.0
STREAM_CURVE_CUTOFF_2 = 10.0

def ms_to_stream_bpm(delta: GameplayTime) -> float:
    # 300/(0.02*delta) - 300/(0.02*delta)^cutoff/cutoff_2 |> max 0
    if delta <= 0:
        return 0.0
    x = 0.02 * delta
    # 这里完全照 F# 的式子
    v = 300.0 / x - 300.0 / (x ** STREAM_CURVE_CUTOFF) / STREAM_CURVE_CUTOFF_2
    return max(v, 0.0)


def jack_compensation(jack_delta: GameplayTime, stream_delta: GameplayTime) -> float:
    # ratio = jack_delta/stream_delta
    # log2(ratio) |> max 0 |> sqrt |> min 1
    if stream_delta <= 0:
        return 0.0
    ratio = jack_delta / stream_delta
    if ratio <= 0:
        return 0.0
    v = math.log(ratio, 2.0)
    v = max(v, 0.0)
    v = math.sqrt(v)
    return min(v, 1.0)


OHTNERF = 3.0
STREAM_SCALE = 6.0
STREAM_POW = 0.5

def total(note: NoteDifficulty) -> float:
    # ((STREAM_SCALE*SL^STREAM_POW)^OHTNERF + (STREAM_SCALE*SR^STREAM_POW)^OHTNERF + (J)^OHTNERF)^(1/OHTNERF)
    a = (STREAM_SCALE * (note.SL ** STREAM_POW)) ** OHTNERF
    b = (STREAM_SCALE * (note.SR ** STREAM_POW)) ** OHTNERF
    c = (note.J) ** OHTNERF
    return (a + b + c) ** (1.0 / OHTNERF)


def calculate_note_ratings(rate: Rate, notes: TimeArray[NoteRow]) -> List[List[NoteDifficulty]]:
    keys = len(notes[0].Data)
    data: List[List[NoteDifficulty]] = [[NoteDifficulty() for _ in range(keys)] for _ in range(len(notes))]
    hand_split = keys_on_left_hand(keys)

    # F#：last_note_in_column 初始 = first_time - 1000000ms
    first_time = notes[0].Time
    last_note_in_column: List[Time] = [first_time - 1000000.0 for _ in range(keys)]

    def note_difficulty(i: int, k: int, time: Time) -> None:
        # jack
        delta = (time - last_note_in_column[k]) / rate
        data[i][k].J = ms_to_jack_bpm(delta)
        jack_delta = delta

        # 同手范围
        if k < hand_split:
            hand_lo, hand_hi = 0, hand_split - 1
        else:
            hand_lo, hand_hi = hand_split, keys - 1

        sl = 0.0
        sr = 0.0
        for hand_k in range(hand_lo, hand_hi + 1):
            if hand_k == k:
                continue
            trill_delta = (time - last_note_in_column[hand_k]) / rate
            trill_v = ms_to_stream_bpm(trill_delta) * jack_compensation(jack_delta, trill_delta)
            if hand_k < k:
                sl = max(sl, trill_v)
            else:
                sr = max(sr, trill_v)

        data[i][k].SL = sl
        data[i][k].SR = sr

    for i in range(len(notes)):
        time = notes[i].Time
        nr = notes[i].Data

        # 先计算
        for k in range(keys):
            if nr[k] in (NoteType.NORMAL, NoteType.HOLDHEAD):
                note_difficulty(i, k, time)

        # 再更新 last_note
        for k in range(keys):
            if nr[k] in (NoteType.NORMAL, NoteType.HOLDHEAD):
                last_note_in_column[k] = time

    return data