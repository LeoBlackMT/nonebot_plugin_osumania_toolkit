import numpy as np
import asyncio
import traceback
import bisect

from scipy.fft import fft, fftfreq
from scipy.signal import find_peaks
from nonebot import get_plugin_config
from ..algorithm.utils import match_notes_and_presses

from collections import Counter
from ..file.osr_file_parser import osr_file
from ..file.osu_file_parser import osu_file
from ..config import Config

config = get_plugin_config(Config)

async def run_analyze_cheating(osr_obj: osr_file, osu_obj: osu_file=None):
    loop = asyncio.get_running_loop()
    def wrapped():
        try:
            return analyze_cheating(osr_obj, osu_obj)
        except Exception as e:
            traceback.print_exc()
            raise
    result = await loop.run_in_executor(None, wrapped)
    return result

def analyze_time_domain(data: dict) -> dict:
    '''
    时域分析作弊特征
    参数:
        data: osr_file.get_data 返回的字典
    返回字典:
        cheat: 是否作弊
        suspicious: 是否可疑
        reason: 原因描述
    '''
    pressset = data["pressset"]
    sample_rate = data["fft_analysis"]["peak_frequency"] if (data["fft_analysis"] != None and data["fft_analysis"]["peak_frequency"] != 0) else data["sample_rate"]
    # 检查是否由 .mr 文件转换
    mr_flag = True if data["player_name"] == "ConvertedFromMalody" else False
    
    max_time = config.bin_max_time # 直方图最大时间(ms)
    SHORT_BAND = (0, 25) # 短按区间 [0,25) ms
    LONG_BAND = (100, max_time) # 长按区间 [100,500) ms
    
    abnormal_peak = False # 异常尖峰标记
    reasons = [] #原因列表

    # 过滤样本数过少的轨道
    non_empty = [p for p in pressset if len(p) > 5]
    if len(non_empty) < 2:
        return {"percent": 0.0, "SR": 0, "cheat": False, "sus": False, "reason": "有效轨道少于2个，无法分析"}
    
    # 合并所有按压时间
    all_data = np.concatenate(non_empty)

    # 1. 计算轨道间相似度（使用10ms bin）
    coarse_bins = int(max_time / 10)
    hist_list = []
    for data in non_empty:
        hist, _ = np.histogram(data, bins=coarse_bins, range=(0, max_time))
        hist = hist.astype(float)
        if hist.sum() > 0:
            hist /= hist.sum()
        hist_list.append(hist)

    n = len(hist_list)
    sim_matrix = np.zeros((n, n))
    for i in range(n):
        for j in range(i+1, n):
            a = hist_list[i]
            b = hist_list[j]
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)
            if norm_a > 0 and norm_b > 0:
                cos_sim = np.dot(a, b) / (norm_a * norm_b)
            else:
                cos_sim = 0
            sim_matrix[i, j] = cos_sim
            sim_matrix[j, i] = cos_sim

    avg_sim = np.mean(sim_matrix[np.triu_indices(n, k=1)]) if n > 1 else 0
    similarity_percent = avg_sim * 100
    
    if sample_rate > config.low_sample_rate_threshold and not mr_flag:
        # 2. 构建1ms精度直方图（用于异常高峰检测）
        bins = int(max_time / config.bin_width)
        hist_all, bin_edges = np.histogram(all_data, bins=bins, range=(0, max_time))
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

        # 3. 异常高峰检测

        # 辅助函数：检测区间内是否有异常峰
        def check_band(band_start, band_end, threshold_ratio, min_count=10):
            band_mask = (bin_centers >= band_start) & (bin_centers < band_end)
            band_counts = hist_all[band_mask]
            if band_counts.sum() == 0:
                return False, None, None
            max_count = band_counts.max()
            max_idx = np.argmax(band_counts) + np.where(band_mask)[0][0]
            if max_count > threshold_ratio * band_counts.sum() and max_count > min_count:
                return True, max_count, bin_centers[max_idx]
            return False, None, None

        # 短按区间：
        short_abnormal, short_count, short_time = check_band(SHORT_BAND[0], SHORT_BAND[1], config.abnormal_peak_threshold)
        if short_abnormal:
            abnormal_peak = True
            reasons.append(f"{short_time:.0f}ms出现异常高峰({short_count}次)")

        # 长按区间：
        long_abnormal, long_count, long_time = check_band(LONG_BAND[0], LONG_BAND[1], config.abnormal_peak_threshold)
        if long_abnormal:
            abnormal_peak = True
            reasons.append(f"{long_time:.0f}ms出现异常高峰({long_count}次)")

        # 全局多峰检测（仅当未触发区间异常时，避免重复）
        if not abnormal_peak:
                peaks, properties = find_peaks(hist_all, height=0.1 * np.max(hist_all), distance=5)
                peak_heights = properties['peak_heights']
                if len(peaks) >= 2:
                    sorted_idx = np.argsort(peak_heights)[::-1]
                    main_peak = peaks[sorted_idx[0]]
                    second_peak = peaks[sorted_idx[1]]
                    main_height = peak_heights[sorted_idx[0]]
                    second_height = peak_heights[sorted_idx[1]]
                    main_center = bin_centers[main_peak]
                    second_center = bin_centers[second_peak]
                    if (second_height > 0.2 * main_height) and (abs(second_center - main_center) > 50):
                        abnormal_peak = True
                        reasons.append(f"整体分布出现双峰({main_center:.0f}ms和{second_center:.0f}ms)")

    # 5. 综合判定
    cheat = False
    suspicious = False
    if avg_sim > config.sim_right_cheat_threshold:
        cheat = True
        suspicious = True
        reasons.append(f"轨道相似度极高({similarity_percent:.1f}%)")
    if avg_sim < config.sim_left_cheat_threshold:
        cheat = True
        suspicious = True
        reasons.append(f"轨道相似度极低({similarity_percent:.1f}%)")
    if avg_sim > config.sim_right_sus_threshold and not cheat:
        suspicious = True
        reasons.append(f"轨道相似度过高({similarity_percent:.1f}%)")
    if avg_sim < config.sim_left_sus_threshold and not cheat:
        suspicious = True
        reasons.append(f"轨道相似度过低({similarity_percent:.1f}%)")
    if abnormal_peak:
        suspicious = True

    if not suspicious and not cheat:
        reason = "时域与按压时长分析：正常"
    else:
        reason = "时域与按压时长分析： " + "; ".join(reasons)
    return {"cheat": cheat, "sus": suspicious, "reason": reason} 

def analyze_delta_t(osr_obj: osr_file, osu_obj: osu_file):
    """
    基于 delta_t 分析作弊嫌疑
    返回字典:
        - cheat: bool
        - sus: bool
        - reason: str
    """
    delta_list, matched_pairs = match_notes_and_presses(osu_obj, osr_obj)

    if not delta_list:
        return {"cheat": False, "sus": False, "reason": "无匹配数据", "stats": {}}

    deltas = np.array([d for _, d in delta_list])

    # 基本统计
    # mean = np.mean(deltas)
    std = np.std(deltas)
    unique_count = len(np.unique(deltas))
    # 峰度
    # kurt = np.mean((deltas - mean)**4) / (std**4) if std > 0 else 0

    cheat = False
    sus = False
    reasons = []
    risk_score = 0

    # 极低标准差且独特值少 → 作弊
    if std < 2.0 and unique_count < 10:
        cheat = True
        risk_score += 3
        reasons.append(f"delta_t 标准差极小 ({std:.2f}ms) 且独特值少 ({unique_count})")
    elif std < 2.0:
        sus = True
        risk_score += 2
        reasons.append(f"delta_t 标准差极小 ({std:.2f}ms)")
    elif unique_count < 10:
        sus = True
        risk_score += 1
        reasons.append(f"delta_t 独特值少 ({unique_count})")

    # 将匹配对按物件时间排序，供序列型特征使用
    sorted_pairs = sorted(matched_pairs, key=lambda x: x[1])
    sorted_notes = [n for _, n, _ in sorted_pairs]
    sorted_deltas = np.array([p - n for _, n, p in sorted_pairs], dtype=float)

    # 高密度区稳定性：真人在高密度下波动通常会增大，脚本常表现过稳
    if len(sorted_notes) >= 300:
        radius_ms = config.delta_dense_radius_ms
        density = []
        for i, t in enumerate(sorted_notes):
            l = bisect.bisect_left(sorted_notes, t - radius_ms)
            r = bisect.bisect_right(sorted_notes, t + radius_ms)
            density.append(r - l - 1)
        density_arr = np.array(density, dtype=float)

        high_th = np.percentile(density_arr, 85)
        low_th = np.percentile(density_arr, 30)
        high_idx = density_arr >= high_th
        low_idx = density_arr <= low_th

        if np.sum(high_idx) >= 60 and np.sum(low_idx) >= 60:
            high_mad = float(np.median(np.abs(sorted_deltas[high_idx] - np.median(sorted_deltas[high_idx]))))
            low_mad = float(np.median(np.abs(sorted_deltas[low_idx] - np.median(sorted_deltas[low_idx]))))
            ratio = high_mad / low_mad if low_mad > 1e-6 else 1.0

            if high_mad < config.delta_dense_hard_mad and ratio < config.delta_dense_hard_ratio:
                sus = True
                risk_score += 2
                reasons.append(
                    f"高密度区波动异常稳定(MAD高密={high_mad:.2f}ms, 比值={ratio:.2f})"
                )
            elif high_mad < config.delta_dense_soft_mad and ratio < config.delta_dense_soft_ratio:
                sus = True
                risk_score += 1
                reasons.append(
                    f"高密度区稳定性偏高(MAD高密={high_mad:.2f}ms, 比值={ratio:.2f})"
                )

    # 列间一致性：真人常有手/指差异，脚本更容易出现列间统计过于一致
    col_delta = {}
    for col, d in delta_list:
        col_delta.setdefault(col, []).append(float(d))
    valid_col = {c: np.array(v, dtype=float) for c, v in col_delta.items() if len(v) >= 80}
    if len(valid_col) >= 3:
        col_std = np.array([np.std(v) for v in valid_col.values()], dtype=float)
        col_median = np.array([np.median(v) for v in valid_col.values()], dtype=float)
        std_cv = float(np.std(col_std) / np.mean(col_std)) if np.mean(col_std) > 1e-6 else 0.0
        med_span = float(np.max(col_median) - np.min(col_median)) if len(col_median) > 1 else 0.0
        if std_cv < 0.08 and med_span < 4.0 and std < 9.0:
            sus = True
            risk_score += 1
            reasons.append(
                f"列间统计过于一致(Std-CV={std_cv:.3f}, 中位差={med_span:.2f}ms)"
            )

    # 多押同时性检测（基于分布，不使用超分辨率硬阈值）
    # 按物件时间分组（时间差 < 1ms）
    note_times_flat = []
    for col, times in osu_obj.note_times.items():
        for t in times:
            note_times_flat.append((col, t))
    note_times_flat.sort(key=lambda x: x[1])
    chord_groups = []
    i = 0
    while i < len(note_times_flat):
        group = [note_times_flat[i]]
        j = i + 1
        while j < len(note_times_flat) and abs(note_times_flat[j][1] - note_times_flat[i][1]) < 1:
            group.append(note_times_flat[j])
            j += 1
        if len(group) > 1:
            chord_groups.append(group)
        i = j

    # 对于每个多押组，找出对应的按下时间
    # 建立物件时间到按下时间的映射（从 matched_pairs）
    note_to_press = {(col, note): press for col, note, press in matched_pairs}
    chord_spans = []
    for group in chord_groups:
        press_times = []
        for col, note in group:
            if (col, note) in note_to_press:
                press_times.append(note_to_press[(col, note)])
        if len(press_times) > 1:
            chord_spans.append(float(max(press_times) - min(press_times)))

    if chord_spans:
        chord_spans_arr = np.array(chord_spans)
        near_sync_ratio = float(np.mean(chord_spans_arr <= 1.2))
        p90_span = float(np.percentile(chord_spans_arr, 90))
        p95_span = float(np.percentile(chord_spans_arr, 95))
        if (
            len(chord_spans) >= config.delta_chord_hard_min_count
            and near_sync_ratio >= config.delta_chord_hard_ratio
            and p95_span <= config.delta_chord_hard_p95
        ):
            cheat = True
            sus = True
            risk_score += 3
            reasons.append(
                f"多押同步性异常高({near_sync_ratio*100:.1f}%, P95跨度={p95_span:.2f}ms)"
            )
        elif (
            len(chord_spans) >= config.delta_chord_soft_min_count
            and near_sync_ratio >= config.delta_chord_soft_ratio
            and p90_span <= config.delta_chord_soft_p90
        ):
            sus = True
            risk_score += 2
            reasons.append(
                f"多押近同步比例偏高({near_sync_ratio*100:.1f}%, P90跨度={p90_span:.2f}ms)"
            )

    # 空敲行为画像（仅在长空段上下文统计，避免误伤正常补拍）
    replay_events = getattr(osr_obj, "press_events_float", None)
    if not replay_events:
        replay_events = osr_obj.press_events

    all_notes = [t for times in osu_obj.note_times.values() for t in times]
    if replay_events and all_notes:
        min_note = min(all_notes)
        max_note = max(all_notes)
        buffer = 5000
        considered_press_times = [
            t for _, t in replay_events if min_note - buffer <= t <= max_note + buffer
        ]
        total_considered = len(considered_press_times)
        matched_count = len(matched_pairs)
        unmatched_ratio = (
            max(0.0, (total_considered - matched_count) / total_considered)
            if total_considered > 0 else 0.0
        )

        sorted_notes = sorted(all_notes)
        long_gaps = []
        for i in range(1, len(sorted_notes)):
            gap_start = sorted_notes[i - 1]
            gap_end = sorted_notes[i]
            if gap_end - gap_start >= 1200:
                long_gaps.append((gap_start + 120, gap_end - 120))

        long_gap_press_count = 0
        if long_gaps and considered_press_times:
            starts = [g[0] for g in long_gaps]
            for t in considered_press_times:
                idx = bisect.bisect_right(starts, t) - 1
                if idx >= 0:
                    g_start, g_end = long_gaps[idx]
                    if g_start <= t <= g_end:
                        long_gap_press_count += 1

        long_gap_press_ratio = (
            (long_gap_press_count / total_considered)
            if total_considered > 0 else 0.0
        )

        if (
            total_considered >= 120
            and unmatched_ratio > config.delta_gap_unmatched_ratio
            and long_gap_press_ratio > config.delta_gap_press_ratio
        ):
            sus = True
            risk_score += 1
            reasons.append(
                f"长空段空敲画像异常(未匹配率={unmatched_ratio*100:.1f}%, 长空段占比={long_gap_press_ratio*100:.1f}%)"
            )

    # 多信号融合：避免单特征漏检
    if not cheat and risk_score >= config.delta_risk_cheat_score:
        cheat = True
        sus = True
        reasons.append(f"多项特征叠加异常(风险分={risk_score})")
    elif not cheat and risk_score >= config.delta_risk_sus_score:
        sus = True

    if not reasons:
        reason = "偏移分析：正常"
    else:
        reason = "偏移分析：" + "; ".join(reasons)

    return {
        "cheat": cheat,
        "sus": sus,
        "reason": reason,
    }

def analyze_pulse_spectrum(data: dict) -> dict:
    """
    对脉冲序列进行频谱分析，返回分析结果。
    参数:
        data: osr_file.get_data 返回的字典
    返回字典:
        cheat: 是否作弊
        suspicious: 是否可疑
        reason: 原因描述
    """
    press_times = data["press_times"]
    intervals = data["intervals"]
    sample_rate = data["fft_analysis"]["peak_frequency"] if (data["fft_analysis"] != None and data["fft_analysis"]["peak_frequency"] != 0) else data["sample_rate"]

    if not press_times or not intervals:
        return {
            "cheat": False,
            "sus": False,
            "reason": "频谱分析失败，无有效按键事件"
        }

    if data["player_name"] == "ConvertedFromMalody":
        return {
            "cheat": False,
            "sus": False,
            "reason": "频谱分析: 无法对mr分析。"
        }
    # 如果采样率未估算，重新计算
    if sample_rate is None or sample_rate == float('inf'):
        if intervals:
            interval_counts = Counter(intervals)
            most_common_interval, _ = interval_counts.most_common(1)[0]
            sample_rate = 1000 / most_common_interval
        else:
            sample_rate = 0

    total_duration = max(press_times)
    if total_duration <= 0:
        return {
            "cheat": False,
            "sus": False,
            "reason": "频谱分析失败，无效时长"
        }

    # 构建脉冲信号
    pulse_signal = np.zeros(total_duration + 1, dtype=int)
    for t in press_times:
        if 0 <= t <= total_duration:
            pulse_signal[t] += 1

    # FFT
    fs = 1000
    n = len(pulse_signal)
    yf = fft(pulse_signal)
    xf = fftfreq(n, 1/fs)[:n//2]
    amplitude = 2.0/n * np.abs(yf[0:n//2])

    mask = (xf >= 1) & (xf <= 500)
    search_xf = xf[mask]
    search_amp = amplitude[mask]

    if len(search_amp) == 0:
        return {
            "cheat": False,
            "sus": False,
            "reason": "频谱分析失败，无有效频率"
        }

    peak_idx = np.argmax(search_amp)
    peak_hz = search_xf[peak_idx]
    peak_amp = search_amp[peak_idx]

    # 局部信噪比
    local_range = 10
    local_mask = (xf >= peak_hz - local_range) & (xf <= peak_hz + local_range)
    local_avg = np.mean(amplitude[local_mask]) if np.any(local_mask) else 0
    snr = peak_amp / local_avg if local_avg > 0 else 0

    global_avg = np.mean(search_amp)
    significant = (snr > 50.0 and peak_amp > 10 * global_avg)

    device_peak = False
    if sample_rate > 0 and (abs(peak_hz - sample_rate) < 2 or
                            (sample_rate % peak_hz < 1e-6 and peak_hz < sample_rate)):
        device_peak = True


    # 生成简短描述
    if significant:
        if device_peak:
            reason = f"脉冲序列分析：主峰频率 {peak_hz:.0f} Hz 与设备采样率相关。"
            sus = False
            cheat = False
        else:
            if peak_hz < 30:
                reason = f"脉冲序列分析：主峰 {peak_hz:.1f} Hz (信噪比={snr:.1f})，低频峰，正常。"
                sus = False
                cheat = False
            elif peak_hz >= 30 and peak_hz < 50:
                reason = f"脉冲序列分析：主峰 {peak_hz:.1f} Hz (信噪比={snr:.1f})，标记为可疑。"
                sus = True
                cheat = False
            else:
                reason = f"脉冲序列分析：主峰 {peak_hz:.1f} Hz (信噪比={snr:.1f})，标记为作弊。"
                sus = True
                cheat = True                
            
    else:
        reason = "脉冲序列分析：正常"
        cheat = False
        sus = False

    return {
        "cheat": cheat,
        "sus": sus,
        "reason": reason
    }
    
def analyze_cheating(osr: osr_file, osu: osu_file=None) -> dict:
    """
    综合分析作弊嫌疑
    参数:
        data: osr_file.get_data 返回的字典
    返回:
        字典，包含:
        - cheat: 是否确定作弊 (bool)
        - sus: 是否可疑 (bool)
        - reason: 原因描述 (str)
    """
    data = osr.get_data()
    # 时域分析
    time_result = analyze_time_domain(data)
    spectrum_result = analyze_pulse_spectrum(data)
    if osu:
        delta_result = analyze_delta_t(osr, osu)
    else:
        delta_result = {"cheat": False, "sus": False, "reason": "未分析delta_t。"}

    cheat = time_result["cheat"] or spectrum_result["cheat"] or delta_result["cheat"]
    sus = time_result["sus"] or spectrum_result["sus"] or delta_result["sus"]

    # 合并原因
    reasons = []
    reasons.append(time_result["reason"])
    reasons.append(spectrum_result["reason"])
    reasons.append(delta_result["reason"])

    return {
        "cheat": cheat,
        "sus": sus,
        "reasons": reasons,
    }