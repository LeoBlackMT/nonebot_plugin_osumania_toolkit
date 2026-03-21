# -*- coding: utf-8 -*-
"""
对应 prelude/src/Calculator/Patterns/FindPatterns.fs
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from ..chart import Chart
from ..calculator.difficulty import Difficulty
from .density import Density
from .primitives import RowInfo, calculate_primitives
from .patterns_def import (
    CorePattern,
    SpecificPatterns,
    CORE_STREAM,
    CORE_CHORDSTREAM,
    CORE_JACKS,
    SPECIFIC_4K,
    SPECIFIC_7K,
    SPECIFIC_OTHER,
)


@dataclass
class FoundPattern:
    Pattern: CorePattern
    SpecificType: Optional[str]
    Mixed: bool
    Start: float
    End: float
    MsPerBeat: float
    Strains: List[float]
    Density: float


PATTERN_STABILITY_THRESHOLD = 5.0


def _pick_specific(specific_list, remaining: List[RowInfo]):
    # F#：tryPick 找到第一个返回非 0 的 recogniser
    for name, p in specific_list:
        n = p(remaining)
        if n != 0:
            return n, name
    return None


def matches(specific_patterns: SpecificPatterns, last_note: float, primitives: List[RowInfo]) -> List[FoundPattern]:
    remaining = primitives[:]
    results: List[FoundPattern] = []

    while len(remaining) > 0:
        # Stream
        n = CORE_STREAM(remaining)
        if n != 0:
            picked = _pick_specific(specific_patterns.Stream, remaining)
            if picked is None:
                n2, specific_type = n, None
            else:
                m, st = picked
                n2, specific_type = max(n, m), st

            d = remaining[:n2]
            mean_mspb = sum(x.MsPerBeat for x in d) / len(d)

            mixed = not all(abs(x.MsPerBeat - mean_mspb) < PATTERN_STABILITY_THRESHOLD for x in d)
            start = remaining[0].Time
            end = remaining[n2].Time if n2 < len(remaining) else last_note

            results.append(
                FoundPattern(
                    Pattern=CorePattern.Stream,
                    SpecificType=specific_type,
                    Mixed=mixed,
                    Start=start,
                    End=end,
                    MsPerBeat=mean_mspb,
                    Strains=remaining[0].Strains,
                    Density=sum(x.Density for x in d) / len(d),
                )
            )

        # Chordstream
        n = CORE_CHORDSTREAM(remaining)
        if n != 0:
            picked = _pick_specific(specific_patterns.Chordstream, remaining)
            if picked is None:
                n2, specific_type = n, None
            else:
                m, st = picked
                n2, specific_type = max(n, m), st

            d = remaining[:n2]
            mean_mspb = sum(x.MsPerBeat for x in d) / len(d)

            mixed = not all(abs(x.MsPerBeat - mean_mspb) < PATTERN_STABILITY_THRESHOLD for x in d)
            start = remaining[0].Time
            end = remaining[n2].Time if n2 < len(remaining) else last_note

            results.append(
                FoundPattern(
                    Pattern=CorePattern.Chordstream,
                    SpecificType=specific_type,
                    Mixed=mixed,
                    Start=start,
                    End=end,
                    MsPerBeat=mean_mspb,
                    Strains=remaining[0].Strains,
                    Density=sum(x.Density for x in d) / len(d),
                )
            )

        # Jacks
        n = CORE_JACKS(remaining)
        if n != 0:
            picked = _pick_specific(specific_patterns.Jack, remaining)
            if picked is None:
                n2, specific_type = n, None
            else:
                m, st = picked
                n2, specific_type = max(n, m), st

            d = remaining[:n2]
            mean_mspb = sum(x.MsPerBeat for x in d) / len(d)

            mixed = not all(abs(x.MsPerBeat - mean_mspb) < PATTERN_STABILITY_THRESHOLD for x in d)
            start = remaining[0].Time
            # F# 的 Jacks End 有特殊 max(...) 逻辑
            end_candidate = remaining[n2].Time if n2 < len(remaining) else last_note
            end = max(remaining[0].Time + remaining[0].MsPerBeat * 0.5, end_candidate)

            results.append(
                FoundPattern(
                    Pattern=CorePattern.Jacks,
                    SpecificType=specific_type,
                    Mixed=mixed,
                    Start=start,
                    End=end,
                    MsPerBeat=mean_mspb,
                    Strains=remaining[0].Strains,
                    Density=sum(x.Density for x in d) / len(d),
                )
            )

        remaining = remaining[1:]

    return results


def find(density: List[Density], difficulty_info: Difficulty, chart: Chart) -> List[FoundPattern]:
    primitives = calculate_primitives(density, difficulty_info, chart)

    if chart.Keys == 4:
        keymode_patterns = SPECIFIC_4K()
    elif chart.Keys == 7:
        keymode_patterns = SPECIFIC_7K()
    else:
        keymode_patterns = SPECIFIC_OTHER()

    return matches(keymode_patterns, chart.LastNote - chart.FirstNote, primitives)