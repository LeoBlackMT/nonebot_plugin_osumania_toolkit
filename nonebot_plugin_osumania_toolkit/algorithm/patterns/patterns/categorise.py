# -*- coding: utf-8 -*-
"""
对应 prelude/src/Calculator/Patterns/Categorise.fs
"""

from __future__ import annotations

from typing import List

from .clustering import Cluster
from .patterns_def import CorePattern


SV_AMOUNT_THRESHOLD = 2000.0  # ms


def categorise_chart(keys: int, ordered_clusters: List[Cluster], sv_amount: float) -> str:
    if len(ordered_clusters) == 0:
        return "SV" if sv_amount >= SV_AMOUNT_THRESHOLD else "Uncategorised"

    # important_clusters：Importance / first > 0.5
    first_imp = ordered_clusters[0].Importance
    important = []
    for c in ordered_clusters:
        if c.Importance / first_imp > 0.5:
            important.append(c)
        else:
            break

    cluster_1 = important[0]
    cluster_2 = important[1] if len(important) > 1 else None

    is_hybrid = False
    if cluster_2 is not None:
        if cluster_2.Pattern == CorePattern.Jacks and cluster_1.Pattern in (CorePattern.Stream, CorePattern.Chordstream):
            is_hybrid = True
        if cluster_2.Pattern in (CorePattern.Stream, CorePattern.Chordstream) and cluster_1.Pattern == CorePattern.Jacks:
            is_hybrid = True

    is_tech = cluster_1.Mixed
    is_sv = sv_amount >= SV_AMOUNT_THRESHOLD

    if len(cluster_1.SpecificTypes) > 0 and cluster_1.SpecificTypes[0][1] > 0.4:
        name = cluster_1.SpecificTypes[0][0]
    elif len(cluster_1.SpecificTypes) >= 2 and cluster_1.SpecificTypes[0][0] == "Jumpstream" and cluster_1.SpecificTypes[1][0] == "Handstream":
        a1 = cluster_1.SpecificTypes[0][1]
        a2 = cluster_1.SpecificTypes[1][1]
        name = "Jumpstream/Handstream" if (a2 / a1) > 0.4 else cluster_1.Pattern.value
    else:
        name = cluster_1.Pattern.value

    return f"{name}{' Hybrid' if is_hybrid else ''}{' Tech' if is_tech else ''}{' + SV' if is_sv else ''}"