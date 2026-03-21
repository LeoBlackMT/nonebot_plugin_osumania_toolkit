# -*- coding: utf-8 -*-
"""
移植：prelude/src/Calculator/Patterns/Patterns.fs
ref: 9786913f5e52e6ef0fb51fdacc8c7c61f42728d0

注意：
- PatternRecogniser: (RowInfo list) -> int
- 这里的 RowInfo / Direction 来自 patterns/primitives.py
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, List, Optional, Tuple

from .primitives import RowInfo, Direction


# -----------------------------
# CorePattern（对应 F# discriminated union）
# -----------------------------

class CorePattern(Enum):
    Stream = "Stream"
    Chordstream = "Chordstream"
    Jacks = "Jacks"

    @property
    def DensityToBPM(self) -> float:
        # F#：beat/minute 的单位在 Python 不保留，直接用数值
        if self == CorePattern.Stream:
            return 52.5
        if self == CorePattern.Chordstream:
            return 35.0
        if self == CorePattern.Jacks:
            return 17.5
        raise ValueError

    @property
    def RatingMultiplier(self) -> float:
        if self == CorePattern.Stream:
            return 1.0 / 3.0
        if self == CorePattern.Chordstream:
            return 0.5
        if self == CorePattern.Jacks:
            return 1.0
        raise ValueError

    @property
    def AccuracyBreakpoints(self) -> Tuple[float, float, float]:
        if self == CorePattern.Stream:
            return (0.97, 0.935, 0.90)
        if self == CorePattern.Chordstream:
            return (0.98, 0.95, 0.91)
        if self == CorePattern.Jacks:
            return (0.99, 0.96, 0.93)
        raise ValueError


PatternRecogniser = Callable[[List[RowInfo]], int]


# -----------------------------
# Core recognisers（module Core）
# -----------------------------

def CORE_STREAM(xs: List[RowInfo]) -> int:
    # | {Notes=1;Jacks=0;RawNotes=x}::{Notes=1;Jacks=0}::{Notes=1;Jacks=0}::{Notes=1;Jacks=0}::{Notes=1;Jacks=0;RawNotes=y}::_ when x[0]<>y[0] -> 5
    if len(xs) < 5:
        return 0
    a, b, c, d, e = xs[0], xs[1], xs[2], xs[3], xs[4]
    if (
        a.Notes == 1 and a.Jacks == 0 and
        b.Notes == 1 and b.Jacks == 0 and
        c.Notes == 1 and c.Jacks == 0 and
        d.Notes == 1 and d.Jacks == 0 and
        e.Notes == 1 and e.Jacks == 0
    ):
        # RawNotes 是 int list，F# 里 x.[0]
        if a.RawNotes[0] != e.RawNotes[0]:
            return 5
    return 0


def CORE_JACKS(xs: List[RowInfo]) -> int:
    # | {Jacks=x;MsPerBeat=mspb}::_ when x>1 && mspb<2000 -> 1
    if len(xs) < 1:
        return 0
    x0 = xs[0]
    if x0.Jacks > 1 and x0.MsPerBeat < 2000.0:
        return 1
    return 0


def CORE_CHORDSTREAM(xs: List[RowInfo]) -> int:
    # | {Notes=a;Jacks=0}::{Notes=b;Jacks=0}::{Notes=c;Jacks=0}::{Notes=d;Jacks=0}::_ when a>1 && (b>1||c>1||d>1) -> 4
    if len(xs) < 4:
        return 0
    a, b, c, d = xs[0], xs[1], xs[2], xs[3]
    if a.Notes > 1 and a.Jacks == 0 and b.Jacks == 0 and c.Jacks == 0 and d.Jacks == 0:
        if (b.Notes > 1) or (c.Notes > 1) or (d.Notes > 1):
            return 4
    return 0


# -----------------------------
# module Jacks
# -----------------------------

def JACKS_CHORDJACKS(xs: List[RowInfo]) -> int:
    # | {Notes=a}::{Notes=b;Jacks=j}::_ when a>2 && b>1 && j>=1 && (b<a || j<b) -> 2
    if len(xs) < 2:
        return 0
    a, b = xs[0], xs[1]
    if a.Notes > 2 and b.Notes > 1 and b.Jacks >= 1 and ((b.Notes < a.Notes) or (b.Jacks < b.Notes)):
        return 2
    return 0


def JACKS_MINIJACKS(xs: List[RowInfo]) -> int:
    # | {Jacks=x}::{Jacks=0}::_ when x>0 -> 2
    if len(xs) < 2:
        return 0
    a, b = xs[0], xs[1]
    if a.Jacks > 0 and b.Jacks == 0:
        return 2
    return 0


def JACKS_LONGJACKS(xs: List[RowInfo]) -> int:
    # | {Jacks=a;RawNotes=ra}::{Jacks=b;RawNotes=rb}::{Jacks=c;RawNotes=rc}::{Jacks=d;RawNotes=rd}::{Jacks=e;RawNotes=re}::_ when a>0&&b>0&&c>0&&d>0&&e>0 ->
    #     if exists x in ra where x in rb && x in rc && x in rd && x in re then 5 else 0
    if len(xs) < 5:
        return 0
    a, b, c, d, e = xs[0], xs[1], xs[2], xs[3], xs[4]
    if a.Jacks > 0 and b.Jacks > 0 and c.Jacks > 0 and d.Jacks > 0 and e.Jacks > 0:
        ra, rb, rc, rd, re = a.RawNotes, b.RawNotes, c.RawNotes, d.RawNotes, e.RawNotes
        for x in ra:
            if (x in rb) and (x in rc) and (x in rd) and (x in re):
                return 5
        return 0
    return 0


# -----------------------------
# module Jacks_4K
# -----------------------------

def JACKS_4K_QUADSTREAM(xs: List[RowInfo]) -> int:
    # | {Notes=4}::_::{Jacks=0}::{Jacks=0}::_ -> 4
    if len(xs) < 4:
        return 0
    a, _, c, d = xs[0], xs[1], xs[2], xs[3]
    if a.Notes == 4 and c.Jacks == 0 and d.Jacks == 0:
        return 4
    return 0


def JACKS_4K_GLUTS(xs: List[RowInfo]) -> int:
    # | {RawNotes=ra}::{Jacks=1;RawNotes=rb}::{Jacks=1;RawNotes=rc}::_ ->
    #     if exists x in ra where x in rb && x in rc then 0 else 3
    if len(xs) < 3:
        return 0
    a, b, c = xs[0], xs[1], xs[2]
    ra, rb, rc = a.RawNotes, b.RawNotes, c.RawNotes
    if b.Jacks == 1 and c.Jacks == 1:
        for x in ra:
            if (x in rb) and (x in rc):
                return 0
        return 3
    return 0


# -----------------------------
# module Chordstream_4K
# -----------------------------

def CHORDSTREAM_4K_HANDSTREAM(xs: List[RowInfo]) -> int:
    # | {Notes=3;Jacks=0}::{Jacks=0}::{Jacks=0}::{Jacks=0}::_ -> 4
    if len(xs) < 4:
        return 0
    a, b, c, d = xs[0], xs[1], xs[2], xs[3]
    if a.Notes == 3 and a.Jacks == 0 and b.Jacks == 0 and c.Jacks == 0 and d.Jacks == 0:
        return 4
    return 0


def CHORDSTREAM_4K_JUMPSTREAM(xs: List[RowInfo]) -> int:
    # | {Notes=2;Jacks=0}::{Notes=1;Jacks=0}::{Notes=a;Jacks=0}::{Notes=b;Jacks=0}::_ when a<3 && b<3 -> 4
    if len(xs) < 4:
        return 0
    a, b, c, d = xs[0], xs[1], xs[2], xs[3]
    if a.Notes == 2 and a.Jacks == 0 and b.Notes == 1 and b.Jacks == 0 and c.Jacks == 0 and d.Jacks == 0:
        if c.Notes < 3 and d.Notes < 3:
            return 4
    return 0


def CHORDSTREAM_4K_DOUBLE_JUMPSTREAM(xs: List[RowInfo]) -> int:
    # | {Notes=1;Jacks=0}::{Notes=2;Jacks=0}::{Notes=2;Jacks=0}::{Notes=1;Jacks=0}::_ -> 4
    if len(xs) < 4:
        return 0
    a, b, c, d = xs[0], xs[1], xs[2], xs[3]
    if (
        a.Notes == 1 and a.Jacks == 0 and
        b.Notes == 2 and b.Jacks == 0 and
        c.Notes == 2 and c.Jacks == 0 and
        d.Notes == 1 and d.Jacks == 0
    ):
        return 4
    return 0


def CHORDSTREAM_4K_TRIPLE_JUMPSTREAM(xs: List[RowInfo]) -> int:
    # | {Notes=1;Jacks=0}::{Notes=2;Jacks=0}::{Notes=2;Jacks=0}::{Notes=2;Jacks=0}::{Notes=1;Jacks=0}::_ -> 4
    if len(xs) < 5:
        return 0
    a, b, c, d, e = xs[0], xs[1], xs[2], xs[3], xs[4]
    if (
        a.Notes == 1 and a.Jacks == 0 and
        b.Notes == 2 and b.Jacks == 0 and
        c.Notes == 2 and c.Jacks == 0 and
        d.Notes == 2 and d.Jacks == 0 and
        e.Notes == 1 and e.Jacks == 0
    ):
        return 4
    return 0


def CHORDSTREAM_4K_JUMPTRILL(xs: List[RowInfo]) -> int:
    # | {Notes=2}::{Notes=2;Roll=true}::{Notes=2;Roll=true}::{Notes=2;Roll=true}::_ -> 4
    if len(xs) < 4:
        return 0
    a, b, c, d = xs[0], xs[1], xs[2], xs[3]
    if a.Notes == 2 and b.Notes == 2 and c.Notes == 2 and d.Notes == 2 and b.Roll and c.Roll and d.Roll:
        return 4
    return 0


def CHORDSTREAM_4K_SPLITTRILL(xs: List[RowInfo]) -> int:
    # | {Notes=2}::{Notes=2;Jacks=0;Roll=false}::{Notes=2;Jacks=0;Roll=false}::_ -> 3
    if len(xs) < 3:
        return 0
    a, b, c = xs[0], xs[1], xs[2]
    if a.Notes == 2 and b.Notes == 2 and c.Notes == 2 and b.Jacks == 0 and c.Jacks == 0 and (not b.Roll) and (not c.Roll):
        return 3
    return 0


# -----------------------------
# module Stream_4K
# -----------------------------

def STREAM_4K_ROLL(xs: List[RowInfo]) -> int:
    # | {Notes=1;Direction=Left}::{Notes=1;Direction=Left}::{Notes=1;Direction=Left}::_ -> 3
    # | {Notes=1;Direction=Right}::{Notes=1;Direction=Right}::{Notes=1;Direction=Right}::_ -> 3
    if len(xs) < 3:
        return 0
    a, b, c = xs[0], xs[1], xs[2]
    if a.Notes == 1 and b.Notes == 1 and c.Notes == 1:
        if a.Direction == Direction.Left and b.Direction == Direction.Left and c.Direction == Direction.Left:
            return 3
        if a.Direction == Direction.Right and b.Direction == Direction.Right and c.Direction == Direction.Right:
            return 3
    return 0


def STREAM_4K_TRILL(xs: List[RowInfo]) -> int:
    # | {RawNotes=a}::{RawNotes=b;Jacks=0}::{RawNotes=c;Jacks=0}::{RawNotes=d;Jacks=0}::_ when a=c && b=d -> 4
    if len(xs) < 4:
        return 0
    a, b, c, d = xs[0], xs[1], xs[2], xs[3]
    if b.Jacks == 0 and c.Jacks == 0 and d.Jacks == 0:
        if a.RawNotes == c.RawNotes and b.RawNotes == d.RawNotes:
            return 4
    return 0


def STREAM_4K_MINITRILL(xs: List[RowInfo]) -> int:
    # | {RawNotes=a}::{RawNotes=b;Jacks=0}::{RawNotes=c;Jacks=0}::{RawNotes=d}::_ when a=c && b<>d -> 4
    if len(xs) < 4:
        return 0
    a, b, c, d = xs[0], xs[1], xs[2], xs[3]
    if b.Jacks == 0 and c.Jacks == 0:
        if a.RawNotes == c.RawNotes and b.RawNotes != d.RawNotes:
            return 4
    return 0


# -----------------------------
# module Chordstream_7K
# -----------------------------

def CHORDSTREAM_7K_DOUBLE_STREAMS(xs: List[RowInfo]) -> int:
    # | {Notes=2}::{Notes=2;Jacks=0;Roll=false}::_ -> 2
    if len(xs) < 2:
        return 0
    a, b = xs[0], xs[1]
    if a.Notes == 2 and b.Notes == 2 and b.Jacks == 0 and (not b.Roll):
        return 2
    return 0


def CHORDSTREAM_7K_DENSE_CHORDSTREAM(xs: List[RowInfo]) -> int:
    # | {Notes=x}::{Notes=y;Jacks=0}::_ when x>1 && y>1 -> 2
    if len(xs) < 2:
        return 0
    a, b = xs[0], xs[1]
    if a.Notes > 1 and b.Notes > 1 and b.Jacks == 0:
        return 2
    return 0


def CHORDSTREAM_7K_LIGHT_CHORDSTREAM(xs: List[RowInfo]) -> int:
    # | {Notes=x}::{Notes=y;Jacks=0}::_ when x>1 && y=1 -> 2
    if len(xs) < 2:
        return 0
    a, b = xs[0], xs[1]
    if a.Notes > 1 and b.Notes == 1 and b.Jacks == 0:
        return 2
    return 0


def CHORDSTREAM_7K_CHORD_ROLL(xs: List[RowInfo]) -> int:
    # | {Notes=x}::{Notes=y;Direction=Left;Roll=true}::{Notes=z;Direction=Left;Roll=true}::_ when x>1 && y>1 && z>1 -> 3
    # | {Notes=x}::{Notes=y;Direction=Right;Roll=true}::{Notes=z;Direction=Right;Roll=true}::_ when x>1 && y>1 && z>1 -> 3
    if len(xs) < 3:
        return 0
    a, b, c = xs[0], xs[1], xs[2]
    if a.Notes > 1 and b.Notes > 1 and c.Notes > 1 and b.Roll and c.Roll:
        if b.Direction == Direction.Left and c.Direction == Direction.Left:
            return 3
        if b.Direction == Direction.Right and c.Direction == Direction.Right:
            return 3
    return 0


def CHORDSTREAM_7K_BRACKETS(xs: List[RowInfo]) -> int:
    # | {Notes=x}::{Notes=y;Roll=false;Jacks=0}::{Notes=z;Roll=false;Jacks=0}::_ when x>2 && y>2 && z>2 && x+y+z>9 -> 3
    if len(xs) < 3:
        return 0
    a, b, c = xs[0], xs[1], xs[2]
    if a.Notes > 2 and b.Notes > 2 and c.Notes > 2 and (not b.Roll) and (not c.Roll) and b.Jacks == 0 and c.Jacks == 0:
        if (a.Notes + b.Notes + c.Notes) > 9:
            return 3
    return 0


# -----------------------------
# module Chordstream_Other（与 7K 很像，但不含 BRACKETS）
# -----------------------------

def CHORDSTREAM_OTHER_DOUBLE_STREAMS(xs: List[RowInfo]) -> int:
    # 同 7K DOUBLE_STREAMS
    return CHORDSTREAM_7K_DOUBLE_STREAMS(xs)


def CHORDSTREAM_OTHER_DENSE_CHORDSTREAM(xs: List[RowInfo]) -> int:
    return CHORDSTREAM_7K_DENSE_CHORDSTREAM(xs)


def CHORDSTREAM_OTHER_LIGHT_CHORDSTREAM(xs: List[RowInfo]) -> int:
    return CHORDSTREAM_7K_LIGHT_CHORDSTREAM(xs)


def CHORDSTREAM_OTHER_CHORD_ROLL(xs: List[RowInfo]) -> int:
    return CHORDSTREAM_7K_CHORD_ROLL(xs)


# -----------------------------
# SpecificPatterns record（对应 F# type SpecificPatterns with 3 static members）
# -----------------------------

@dataclass
class SpecificPatterns:
    Stream: List[Tuple[str, PatternRecogniser]]
    Chordstream: List[Tuple[str, PatternRecogniser]]
    Jack: List[Tuple[str, PatternRecogniser]]


def SPECIFIC_4K() -> SpecificPatterns:
    return SpecificPatterns(
        Stream=[
            ("Rolls", STREAM_4K_ROLL),
            ("Trills", STREAM_4K_TRILL),
            ("Minitrills", STREAM_4K_MINITRILL),
        ],
        Chordstream=[
            ("Handstream", CHORDSTREAM_4K_HANDSTREAM),
            ("Split Trill", CHORDSTREAM_4K_SPLITTRILL),
            ("Jumptrill", CHORDSTREAM_4K_JUMPTRILL),
            # F# 里注释掉了 Triple/Double Jumpstream
            # ("Triple Jumpstream", CHORDSTREAM_4K_TRIPLE_JUMPSTREAM),
            # ("Double Jumpstream", CHORDSTREAM_4K_DOUBLE_JUMPSTREAM),
            ("Jumpstream", CHORDSTREAM_4K_JUMPSTREAM),
        ],
        Jack=[
            ("Longjacks", JACKS_LONGJACKS),
            ("Quadstream", JACKS_4K_QUADSTREAM),
            ("Gluts", JACKS_4K_GLUTS),
            ("Chordjacks", JACKS_CHORDJACKS),
            ("Minijacks", JACKS_MINIJACKS),
        ],
    )


def SPECIFIC_7K() -> SpecificPatterns:
    return SpecificPatterns(
        Stream=[],
        Chordstream=[
            ("Brackets", CHORDSTREAM_7K_BRACKETS),
            # F# 注释：("Chord Rolls", Chordstream_7K.CHORD_ROLL)
            ("Double Stream", CHORDSTREAM_7K_DOUBLE_STREAMS),
            ("Dense Chordstream", CHORDSTREAM_7K_DENSE_CHORDSTREAM),
            ("Light Chordstream", CHORDSTREAM_7K_LIGHT_CHORDSTREAM),
        ],
        Jack=[
            ("Longjacks", JACKS_LONGJACKS),
            ("Chordjacks", JACKS_CHORDJACKS),
            ("Minijacks", JACKS_MINIJACKS),
        ],
    )


def SPECIFIC_OTHER() -> SpecificPatterns:
    return SpecificPatterns(
        Stream=[],
        Chordstream=[
            ("Chord Rolls", CHORDSTREAM_OTHER_CHORD_ROLL),
            ("Double Stream", CHORDSTREAM_OTHER_DOUBLE_STREAMS),
            ("Dense Chordstream", CHORDSTREAM_OTHER_DENSE_CHORDSTREAM),
            ("Light Chordstream", CHORDSTREAM_OTHER_LIGHT_CHORDSTREAM),
        ],
        Jack=[
            ("Longjacks", JACKS_LONGJACKS),
            ("Chordjacks", JACKS_CHORDJACKS),
            ("Minijacks", JACKS_MINIJACKS),
        ],
    )