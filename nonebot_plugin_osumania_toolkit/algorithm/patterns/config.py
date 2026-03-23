# -*- coding: utf-8 -*-
"""
集中配置：用于快速调参。

说明：
1. 本文件仅放“经常需要手动微调”的常量，尽量避免把业务流程代码塞进来。
2. 改完后直接重新运行 main.py 即可生效（无需改其它模块）。
3. 这里的默认值尽量保持现有行为，只在你明确想调时再改。
"""

from __future__ import annotations


# -----------------------------
# 运行入口相关
# -----------------------------

# main.py 写入 output 时使用的默认 rate。
DEFAULT_RATE = 1.0

# 通过 bid 下载 .osu 的超时时间（秒）。
# 网络慢时可适当调大。
BID_DOWNLOAD_TIMEOUT_SECONDS = 20


# -----------------------------
# RatingMultiplier（倍率）
# -----------------------------

# CorePattern 级别倍率。
# 键名必须与 CorePattern.value 一致。
CORE_RATING_MULTIPLIER: dict[str, float] = {
    "Stream": 1.0 / 3.0,
    "Chordstream": 0.65,
    "Jacks": 0.9,
    "Coordination": 0.75,
    "Density": 0.9,
    "Wildcard": 1.0,
}

# 子类倍率覆盖。若子类不在该表中，会回退到对应 CorePattern 的倍率。
SUBTYPE_RATING_MULTIPLIER: dict[str, float] = {
    # Coordination
    "Column Lock": 1.5,
    "Release": 0.73,
    "Shield": 0.8,

    # Density
    "JS Density": 1.0,
    "HS Density": 1.0,
    "DS Density": 1.0,
    "LCS Density": 1.0,
    "DCS Density": 1.0,
    "Inverse": 1.5,

    # Wildcard
    "Jacky WC": 0.55,
    "Speedy WC": 0.8,
}


# -----------------------------
# 聚类/分类相关阈值
# -----------------------------

# assign_clusters 时，非 Mixed 模式按 ms/beat 聚类的距离阈值。
# 值越大：不同节奏更容易合并到同一 BPM 簇。
BPM_CLUSTER_THRESHOLD = 5.0

# Mixed 判定阈值：同一段内各点 ms/beat 相对均值的允许偏差。
# 偏差超过该阈值则更容易被判定为 Mixed。
PATTERN_STABILITY_THRESHOLD = 5.0

# “重要簇”筛选阈值：Importance / 第一簇 Importance > 该值。
# 值越低：参与分类判断的重要簇越多。
IMPORTANT_CLUSTER_RATIO = 0.5

# Category 里 Jumpstream/Handstream 混合命名阈值。
# 当第二名占比 / 第一名占比 > 该值时，名称显示为 Jumpstream/Handstream。
CATEGORY_JS_HS_SECONDARY_RATIO = 0.4

# SV 分类阈值（ms）。
SV_AMOUNT_THRESHOLD = 2000.0

# Cluster.Format 显示子类名称的最低占比。
# 设为 0.0 表示只要有子类统计就显示第一名子类名；
# 例如设为 0.4 表示第一名子类至少 40% 才显示，否则显示 CorePattern 名称。
CLUSTER_SPECIFIC_NAME_MIN_RATIO = 0.0

# 同一窗口内是否保留同一大类的多个子类标签。
# True：同窗内多个 recogniser 同时命中时全部保留（用于观察“吞标签”现象）。
# False：保持旧行为，只保留顺序上的第一个命中标签。
ENABLE_MULTI_LABEL_SAME_WINDOW = True

# 三大新增类（Coordination / Density / Wildcard）内部子类匹配顺序。
# 仅影响“同一大类内部”优先级，不影响大类之间（Stream/Chordstream/Jacks 等）。
# 可以直接改列表顺序来调试“先命中谁”。
COORDINATION_SPECIFIC_ORDER: list[str] = [
    "Column Lock",
    "Shield",
    "Release",
]

DENSITY_SPECIFIC_ORDER: list[str] = [
    "Inverse",
    "JS Density",
    "HS Density",
    "DS Density",
    "DCS Density",
    "LCS Density",
]

WILDCARD_SPECIFIC_ORDER: list[str] = [
    "Speedy WC",
    "Jacky WC",
]


# -----------------------------
# 识别器相关（可用于微调判定松紧）
# -----------------------------

# Column Lock 中 jack 速度下限。
JACKY_MIN_BPM = 90.0

# Shield 的最大时间间隔上限（按 beat 比例）。
SHIELD_MAX_BEAT_RATIO = 0.25

# Inverse 判定：尾到头间隔一致性容忍（毫秒）。
INVERSE_GAP_TOLERANCE_MS = 30.0

# Inverse 判定：窗口内 LN Body 最少覆盖列数。
INVERSE_MIN_FILLED_LANES = 3

# Release：从窗口前多少行里找单尾（len(LNTails)==1）。
RELEASE_SCAN_ROWS = 4

# Release：至少需要多少个单尾点才能继续判定。
RELEASE_MIN_TAIL_ROWS = 4

# Release：用于判定 roll 的最小点数（给 STREAM_4K_ROLL 的长度）。
RELEASE_ROLL_POINTS = 2

# Release：达到该点数时返回更长匹配长度（更稳定的 Release 段）。
RELEASE_FULL_MATCH_ROWS = 5

# Jacky WC：LN 上下文检测窗口。
JACKY_CONTEXT_WINDOW = 6

# Jacky WC 放宽分支：当有连续 jack 且速度足够快时可判定。
JACKY_FALLBACK_MAX_MSPB = 185.0
