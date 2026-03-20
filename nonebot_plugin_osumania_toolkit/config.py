from pydantic import BaseModel


class Config(BaseModel):
    """Plugin Config Here"""

    # 缓存文件最大保留时间（小时），默认 24 小时
    omtk_cache_max_age: int = 24
    
    # 允许的最大谱面文件大小（MB），默认 50 MB
    max_file_size_mb: int = 50
    
    # .mc 转 .osu 的默认 OverallDifficulty 和 HPDrainRate
    default_convert_od: int = 8
    default_convert_hp: int = 8
    
    # 作弊分析基础阈值
    # 统计按压时长分布时，最大统计窗口（毫秒）
    bin_max_time: int = 500
    # 直方图桶宽（毫秒），越小越敏感但也更容易噪声抖动
    bin_width: int = 1
    # 轨道分布相似度过高时判作弊阈值
    sim_right_cheat_threshold: float = 0.99
    # 轨道分布相似度过高时判可疑阈值
    sim_right_sus_threshold: float = 0.985
    # 轨道分布相似度过低时判作弊阈值（过低可能是非自然映射/生成）
    sim_left_cheat_threshold: float = 0.4
    # 轨道分布相似度过低时判可疑阈值
    sim_left_sus_threshold: float = 0.55
    # 单个时间点尖峰占所在区间总量的比例阈值
    abnormal_peak_threshold: float = 0.33
    # 低于该采样率时，弱化部分时域尖峰检测，减少误判
    low_sample_rate_threshold: float = 165

    # 高级 delta_t 分析阈值（用于识别人类化脚本）
    # 多押强判：最小样本数
    delta_chord_hard_min_count: int = 30
    # 多押强判：近同步比例阈值（span <= 1.2ms 的占比）
    delta_chord_hard_ratio: float = 0.93
    # 多押强判：P95 跨度上限（毫秒）
    delta_chord_hard_p95: float = 1.8
    # 多押软判：最小样本数
    delta_chord_soft_min_count: int = 15
    # 多押软判：近同步比例阈值
    delta_chord_soft_ratio: float = 0.78
    # 多押软判：P90 跨度上限（毫秒）
    delta_chord_soft_p90: float = 2.2
    # 局部密度统计半径（毫秒），用于区分高密/低密段
    delta_dense_radius_ms: int = 200
    # 高密段强判：MAD 上限
    delta_dense_hard_mad: float = 2.2
    # 高密段强判：高密MAD/低密MAD 比值上限
    delta_dense_hard_ratio: float = 0.72
    # 高密段软判：MAD 上限
    delta_dense_soft_mad: float = 3.0
    # 高密段软判：高密MAD/低密MAD 比值上限
    delta_dense_soft_ratio: float = 0.8
    # 长空段画像：未匹配按键比例阈值
    delta_gap_unmatched_ratio: float = 0.42
    # 长空段画像：空段按键占比阈值
    delta_gap_press_ratio: float = 0.18
    # 多特征风险分融合：达到该分值直接判作弊
    delta_risk_cheat_score: int = 4
    # 多特征风险分融合：达到该分值判可疑
    delta_risk_sus_score: int = 2
