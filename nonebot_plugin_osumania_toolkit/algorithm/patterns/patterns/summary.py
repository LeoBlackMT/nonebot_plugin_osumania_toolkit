# -*- coding: utf-8 -*-
"""
对应 prelude/src/Calculator/Patterns/Summary.fs
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from ..calculator.difficulty import Difficulty
from .density import Density, process_chart
from .find_patterns import find
from .clustering import Cluster, calculate_clustered_patterns, find_percentile
from .primitives import sv_time
from .categorise import categorise_chart


@dataclass
class PatternReport:
    Clusters: List[Cluster]
    Category: str
    SVAmount: float

    Density10: Density
    Density25: Density
    Density50: Density
    Density75: Density
    Density90: Density

    Duration: float

    @property
    def ImportantClusters(self):
        if len(self.Clusters) == 0:
            return []
        importance = self.Clusters[0].Importance
        out = []
        for c in self.Clusters:
            if c.Importance / importance > 0.5:
                out.append(c)
            else:
                break
        return out


def from_chart(difficulty_info: Difficulty, chart) -> PatternReport:
    density = process_chart(chart)
    patterns = find(density, difficulty_info, chart)

    clusters = [c for c in calculate_clustered_patterns(patterns) if c.BPM > 25]
    clusters.sort(key=lambda x: x.Amount, reverse=True)

    def can_be_pruned(cluster: Cluster) -> bool:
        for other in clusters:
            if other.Pattern == cluster.Pattern and other.Amount * 0.5 > cluster.Amount and other.BPM > cluster.BPM:
                return True
        return False

    filtered = [c for c in clusters if not can_be_pruned(c)]

    # 每类最多 3 个，然后按 Importance 排序
    by_stream = [c for c in filtered if c.Pattern.value == "Stream"][:3]
    by_chord = [c for c in filtered if c.Pattern.value == "Chordstream"][:3]
    by_jacks = [c for c in filtered if c.Pattern.value == "Jacks"][:3]
    pruned_clusters = by_stream + by_chord + by_jacks
    pruned_clusters.sort(key=lambda x: x.Importance, reverse=True)

    sv_amount = sv_time(chart)
    sorted_densities = sorted(density)

    return PatternReport(
        Clusters=pruned_clusters,
        SVAmount=sv_amount,
        Category=categorise_chart(chart.Keys, pruned_clusters, sv_amount),
        Density10=find_percentile(0.1, sorted_densities),
        Density25=find_percentile(0.25, sorted_densities),
        Density50=find_percentile(0.5, sorted_densities),
        Density75=find_percentile(0.75, sorted_densities),
        Density90=find_percentile(0.9, sorted_densities),
        Duration=(chart.LastNote - chart.FirstNote),
    )