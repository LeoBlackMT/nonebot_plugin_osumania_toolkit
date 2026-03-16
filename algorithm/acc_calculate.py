import asyncio

from typing import Tuple, List
from pathlib import Path

from ..file.osu_file_parser import osu_file

# ==================== 内置单曲数据 ====================

def acc_data():
    """
    段位物量数据
    数据来源：
    https://github.com/uzxn/acc/blob/main/data.js
    返回: dict, 键为段位名，值为:
        [n, note1, ..., noteN] 或
        [n, note1, ..., noteN, sv2_note1, ..., sv2_noteN]
    """
    return {
        "4ln2_1": [4, 717, 336, 176, 613, 893, 512, 282, 1014],
        "4ln2_10": [4, 2377, 1656, 1689, 2185, 3925, 3120, 3366, 3655],
        "4ln2_11": [4, 1864, 1493, 2338, 2529, 3507, 2512, 4430, 4525],
        "4ln2_12": [4, 1798, 2633, 1822, 2449, 2986, 4811, 3552, 4390],
        "4ln2_13": [4, 2570, 2452, 2123, 2818, 4725, 4203, 3651, 5061],
        "4ln2_14": [4, 2319, 2408, 2483, 2158, 4415, 4320, 4318, 3947],
        "4ln2_15": [4, 3216, 3209, 3278, 3149, 6153, 5661, 5904, 5963],
        "4ln2_2": [4, 805, 805, 377, 805, 1184, 1414, 705, 1610],
        "4ln2_3": [4, 836, 921, 612, 1157, 1305, 1342, 880, 1695],
        "4ln2_4": [4, 907, 1053, 413, 1067, 1469, 1605, 781, 2133],
        "4ln2_5": [4, 1904, 887, 1380, 1220, 2956, 1613, 1913, 1881],
        "4ln2_6": [4, 1365, 745, 1219, 1534, 2324, 1412, 1891, 2421],
        "4ln2_7": [4, 1394, 1119, 832, 1666, 2076, 1971, 1664, 2386],
        "4ln2_8": [4, 1445, 1318, 1258, 1694, 2694, 2424, 2486, 2560],
        "4ln2_9": [4, 2500, 1461, 1321, 2307, 4069, 2593, 2425, 3699],
        "7_0": [4, 1018, 851, 1023, 1223],
        "7_1": [4, 1436, 1814, 1312, 1673],
        "7_10": [4, 3081, 2366, 2511, 3438],
        "7_2": [4, 1411, 1436, 1784, 2154],
        "7_3": [4, 1970, 1906, 1871, 1982],
        "7_4": [4, 2189, 1853, 2108, 2264],
        "7_5": [4, 2087, 2166, 1975, 2391],
        "7_6": [4, 1576, 2818, 2368, 3003],
        "7_7": [4, 2689, 2876, 1938, 2847],
        "7_8": [4, 2366, 2508, 2825, 2936],
        "7_9": [4, 2420, 2672, 2230, 3343],
        "7_a": [4, 3644, 3174, 3260, 4141],
        "7_g": [4, 3085, 2500, 2707, 3711],
        "7_s": [4, 4000, 4502, 3314, 4568],
        "7_z": [4, 3624, 2722, 3258, 4974],
        "7ln_0": [4, 820, 600, 215, 247, 1122, 898, 430, 424],
        "7ln_1": [4, 1068, 682, 537, 428, 1819, 1075, 1074, 707],
        "7ln_10": [4, 2151, 2496, 1845, 1708, 4297, 4812, 3690, 3402],
        "7ln_2": [4, 1242, 1198, 760, 1221, 1598, 1831, 1520, 2315],
        "7ln_3": [4, 1512, 1350, 323, 899, 2358, 2106, 646, 1606],
        "7ln_4": [4, 1309, 1518, 543, 736, 2129, 2724, 1086, 1381],
        "7ln_5": [4, 1516, 2695, 602, 618, 2687, 4695, 1204, 1059],
        "7ln_6": [4, 1635, 1902, 756, 1081, 2829, 3488, 1512, 2060],
        "7ln_7": [4, 1796, 2093, 1359, 1391, 3386, 3475, 2718, 2738],
        "7ln_8": [4, 2230, 2136, 1465, 1362, 4238, 3638, 2930, 2603],
        "7ln_9": [4, 1900, 2159, 1597, 1677, 3601, 4213, 3194, 3341],
        "7ln_a": [4, 3029, 2472, 2553, 2926, 5867, 4915, 5106, 5849],
        "7ln_g": [4, 2551, 2326, 2273, 2165, 4962, 4505, 4546, 4306],
        "7ln_s": [4, 4073, 3454, 3196, 3721, 6954, 6325, 6392, 7391],
        "7ln_z": [4, 3240, 3025, 3181, 2904, 6314, 5918, 6362, 5756],
        "haku": [4, 2379, 3073, 3561, 962],
        "m2_1": [4, 831, 955, 907, 654],
        "m2_10": [4, 2659, 2188, 2194, 2187],
        "m2_2": [4, 1152, 850, 950, 969],
        "m2_3": [4, 1169, 1143, 974, 1347],
        "m2_4": [4, 1400, 1402, 1685, 1599],
        "m2_5": [4, 1953, 2250, 2166, 1667],
        "m2_6": [4, 1487, 1424, 1381, 1587],
        "m2_7": [4, 1909, 1814, 1777, 2681],
        "m2_8": [4, 1962, 1067, 2388, 1772],
        "m2_9": [4, 1799, 2023, 2281, 1787],
        "m2_e1": [4, 2164, 1952, 1823, 3249],
        "m2_e2": [4, 2871, 2024, 1871, 2452],
        "m2_e2_v15": [4, 2457, 2239, 2024, 2561],
        "m2_e2_v175": [4, 1944, 2024, 2561, 3089],
        "m2_e3": [4, 2327, 1593, 2166, 2200],
        "m2_e4": [4, 2731, 2653, 2033, 2796],
        "m2_e5": [4, 3229, 2731, 2561, 2109],
        "m2_e6": [4, 1766, 1861, 3171, 1680],
        "m2_e6_v175": [4, 2504, 2027, 2444, 3526],
        "m2_e7": [4, 2339, 2461, 2511, 2177],
        "m2_e7_v175": [4, 2725, 2166, 2545, 3691],
        "m2_e8": [4, 1929, 2380, 2710, 4675],
        "m2_e9": [4, 3987, 1874, 4363, 3843],
        "m2_e9_v175": [4, 4427, 3660, 4323, 3044],
        "m2_ef": [4, 3468, 3335, 3698, 5061],
        "m2s_e1": [4, 1952, 2316, 2098, 2048],
        "m2s_e2": [4, 2158, 1953, 2196, 3160],
        "m2s_e3": [4, 2299, 2378, 2677, 2640],
        "m2s_e4": [4, 1738, 1876, 2079, 2008],
        "m2s_e5": [4, 2731, 2109, 2365, 2691],
        "m2s_e6": [4, 1766, 2525, 2167, 3214],
        "m2s_e7": [4, 2339, 2461, 2142, 3167],
        "m2s_e8": [4, 2647, 3253, 3204, 4046],
        "m2s_e9": [4, 2828, 3663, 2865, 2777],
        "m3_0": [4, 492, 529, 595, 681],
        "m3_1": [4, 695, 621, 718, 1279],
        "m3_10": [4, 2034, 1740, 2270, 2166],
        "m3_2": [4, 1397, 1090, 805, 1212],
        "m3_3": [4, 1055, 1489, 1288, 1789],
        "m3_4": [4, 1865, 1434, 1284, 1839],
        "m3_5": [4, 1282, 1706, 1473, 1939],
        "m3_6": [4, 1694, 1636, 1803, 2115],
        "m3_7": [4, 1701, 1799, 2132, 1899],
        "m3_8": [4, 2237, 2081, 2280, 2000],
        "m3_9": [4, 2374, 1889, 2142, 1810],
        "m3_e1": [4, 1952, 2013, 1953, 2111],
        "m3_e2": [4, 2107, 1953, 2386, 2674],
        "m3_e3": [4, 2518, 2636, 2326, 2511],
        "m3_e4": [4, 2634, 2212, 2336, 2602],
        "m3_e5": [4, 2734, 2417, 3089, 2974],
        "m3_e6": [4, 2483, 2276, 2921, 3194],
        "m3_e7": [4, 2846, 2260, 2333, 3347],
        "m3_e8": [4, 3789, 3663, 2424, 3255],
        "m3_e9": [4, 3888, 3030, 3581, 3700],
        "m3_ef": [4, 2828, 3362, 3393, 5100],
        "rf_1": [4, 878, 696, 954, 1167],
        "rf_10": [4, 1906, 1460, 1723, 2392],
        "rf_2": [4, 1107, 905, 955, 1487],
        "rf_3": [4, 1008, 797, 1047, 1259],
        "rf_4": [4, 905, 1499, 1283, 2071],
        "rf_5": [4, 1293, 1722, 1632, 1903],
        "rf_6": [4, 1487, 1266, 1378, 2186],
        "rf_7": [4, 2114, 1777, 1081, 2734],
        "rf_8": [4, 2177, 1309, 1608, 1589],
        "rf_9": [4, 2114, 2070, 1674, 2272],
        "rf_a": [4, 2265, 1528, 2300, 3334],
        "rf_b": [4, 2274, 2308, 1740, 2301],
        "rf_d": [4, 2018, 2711, 3268, 2629],
        "rf_e": [4, 2128, 2552, 2194, 2829],
        "rf_g": [4, 1973, 1980, 1429, 3979],
        "rf_z": [4, 2895, 1292, 1958, 4911],
        "rff_et": [4, 3889, 3860, 3863, 3837],
        "rff_z": [4, 3447, 3424, 3409, 3291],
        "rfsp_ea": [4, 2531, 2675, 3560, 2855],
        "rfsp_eb": [4, 1973, 1943, 2411, 3732],
        "rfsp_z": [4, 2438, 1964, 2925, 3497],
        "sp_1": [4, 752, 1004, 940, 1045],
        "sp_10": [4, 1933, 1929, 1734, 1930],
        "sp_2": [4, 978, 791, 1440, 1405],
        "sp_3": [4, 1242, 1297, 1358, 1378],
        "sp_4": [4, 1848, 1592, 1558, 1677],
        "sp_5": [4, 1536, 1877, 1841, 1583],
        "sp_6": [4, 1523, 1705, 1722, 2111],
        "sp_7": [4, 1464, 1509, 2052, 2076],
        "sp_8": [4, 1811, 1771, 2211, 2021],
        "sp_9": [4, 2096, 1955, 2091, 1957],
        "sp_e1": [4, 2425, 1733, 1978, 2233],
        "sp_e2": [4, 2428, 2632, 1799, 2668],
        "sp_e3": [4, 2148, 2932, 2975, 2052],
        "sp_e4": [4, 2362, 2064, 1996, 2752],
        "sp_e5": [4, 2715, 2181, 2350, 3748],
        "sp_e6": [4, 2472, 2179, 2573, 2606],
        "sp_e7": [4, 2816, 2516, 2867, 3503],
        "sp_e8": [4, 3131, 2211, 2689, 3552],
        "sp_e9": [4, 3486, 3175, 3592, 3189],
        "sp_ef": [4, 4207, 3352, 3080, 3450],
        "wds0_1": [4, 2100, 2050, 2344, 2236],
        "wds0_10": [4, 4099, 3284, 3212, 3200],
        "wds0_2": [4, 2148, 3246, 2054, 2125],
        "wds0_3": [4, 2434, 2952, 2735, 2312],
        "wds0_4": [4, 2229, 2585, 2022, 2552],
        "wds0_5": [5, 2597, 3050, 2453, 2361, 2492],
        "wds0_6": [4, 2581, 3165, 2524, 2513],
        "wds0_7": [4, 2824, 3045, 3280, 3073],
        "wds0_8": [4, 3407, 3493, 3195, 2087],
        "wds0_9": [4, 4444, 2602, 2853, 2411],
        "wds0_f": [5, 3699, 2966, 5315, 4643, 8438],
        "wds0_j": [4, 3372, 3940, 2680, 2467],
        "wds0_n": [4, 3134, 2504, 1040, 2398],
    }


def extract_note_counts_from_dan(entry: List, sv2_flag: bool = False) -> Tuple:
    """
    从段位条目中提取对应模式的物量列表。

    entry 格式:
        [n, note1..noteN] 或 [n, note1..noteN, sv2_note1..sv2_noteN]
    """
    if not isinstance(entry, (list, tuple)) or not entry:
        return None, "段位数据格式错误"

    try:
        num_songs = int(entry[0])
    except (TypeError, ValueError):
        return None, "段位数据格式错误"

    if num_songs <= 0:
        return None, "段位歌曲数量必须大于0"

    if len(entry) < 1 + num_songs:
        return None, "段位物量数据不完整"

    normal_notes = list(entry[1:1 + num_songs])
    if not sv2_flag:
        return normal_notes, None

    if len(entry) >= 1 + 2 * num_songs:
        return list(entry[1 + num_songs:1 + 2 * num_songs]), None

    return None, "该段位不支持 ScoreV2 数据"

# ==================== 计算函数 ====================

def calculate_acc(note_counts: List, acc_str: str) -> Tuple:
    """
    使用自定义物量计算单曲ACC
    
    参数:
        note_counts: 物量列表
        acc_str: ACC字符串 (格式: acc1-acc2-acc3-acc4)
    
    返回:
        tuple: (单曲ACC列表, 错误信息)
    """
    try:
        # 解析ACC字符串
        acc_parts = acc_str.split('-')
        if len(acc_parts) != len(note_counts):
            return None, f"ACC变化需要{len(note_counts)}个值，但提供了{len(acc_parts)}个"
        
        acc_change = [float(acc) for acc in acc_parts]
        
        # 计算单曲ACC
        single_accs = []
        for i in range(len(acc_change)):
            if i == 0:
                # 第一首: acc1 = i1
                acc = acc_change[0]
            else:
                total_notes_prev = sum(note_counts[:i])
                total_notes_curr = sum(note_counts[:i+1])
                
                # 计算单曲ACC: acc_i = (i_i * T_i - i_{i-1} * T_{i-1}) / n_i
                prev_product = acc_change[i-1] * total_notes_prev
                curr_product = acc_change[i] * total_notes_curr
                
                if note_counts[i] == 0:
                    acc = 0.0
                else:
                    acc = (curr_product - prev_product) / note_counts[i]
            
            single_accs.append(round(acc, 2))
        
        return single_accs, None
        
    except ValueError as e:
        return None, f"格式错误: {str(e)}"
    except ZeroDivisionError:
        return None, "物量不能为0"
    except Exception as e:
        return None, f"计算错误: {str(e)}"
    
def calculate_acc_from_dan(dan_name, acc_str, sv2_flag: bool = False) -> Tuple:
    """
    根据段位名和ACC变化字符串计算单曲ACC
    
    参数:
        dan_name: str, 段位名
        cumulative_acc_str: str, ACC变化字符串，用"-"分隔
    
    返回:
        tuple: (单曲ACC列表, 错误信息)
    """
    data = acc_data()
    if dan_name not in data:
        return None, f"段位 '{dan_name}' 不存在。"

    entry = data[dan_name]
    note_counts, data_err = extract_note_counts_from_dan(entry, sv2_flag)
    if data_err:
        return None, data_err

    try:
        single_acc, err_msg = calculate_acc(note_counts, acc_str)
        if err_msg:
            return None, err_msg
        return single_acc, None

    except ValueError as e:
        return None, f"格式错误: {str(e)}"
    except Exception as e:
        return None, f"计算错误: {str(e)}"

# ==================== 辅助函数 ====================

def parse_acc_cmd(cmd_text: str) -> Tuple:
    """
    解析acc命令参数
    
    参数:
        cmd_text: str, 命令文本
    
    返回:
        tuple: (段位名, ACC字符串, bid, num_songs, sv2_flag, 错误信息)
    """
    # 移除命令前缀
    cmd_text = cmd_text.strip()
    prefixes = ["/acc ", "acc ", "/单曲 ", "单曲 "]
    for prefix in prefixes:
        if cmd_text.startswith(prefix):
            cmd_text = cmd_text[len(prefix):].strip()
            break
    
    if not cmd_text:
        return None, None, None, 4, False, None  # 进入交互模式 默认4段
    
    cmd_parts = cmd_text.split()
    err_msg = []
    
    bid = None
    num_songs = 4
    acc_str = None
    dan_name = None
    sv2_flag = False
    
    # 解析命令
    i = 0
    while i < len(cmd_parts):
        part = cmd_parts[i]

        # sv2加权模式
        if part.lower() == "-sv2":
            sv2_flag = True
            i += 1
            continue
        
        # 获取bid
        if part.lower().startswith("b"):
            try:
                bid = int(part[1:])
            except ValueError:
                err_msg.append(f"无效的谱面ID: {part[1:]}; ")
            i += 1
            continue
        
        # 获取num_songs
        elif part.isdigit():
            try:
                num_songs = int(part)
                if num_songs <= 0 or num_songs >= 10:
                    err_msg.append("单曲个数必须属于区间(0,10)。")
            except ValueError:
                err_msg.append(f"无效的单曲个数: {part}; ")
            i += 1
            continue
            
        # 获取 acc 变化字符串
        elif '-' in part:
            try:
                acc_str = part
            except ValueError:
                err_msg.append(f"无效的acc变化: {part}; ")
            i += 1
            continue
        
        # 如果都不是上面的情况 则视为段位名
        elif validate_dan_name(part, sv2_flag):
            try:
                dan_name = part
            except ValueError:
                err_msg.append(f"无效的段位名: {part}; ")
            i += 1
            continue
        
        # 未定义的参数
        else:
            i += 1

    return dan_name, acc_str, bid, num_songs, sv2_flag, err_msg

def get_available_dans():
    """
    获取所有可用的段位名
    
    返回:
        list, 按字典序升序排列的段位名列表
    """
    data = list(acc_data().keys())
    data.sort()
    return data

def validate_dan_name(dan_name: str, sv2_flag: bool = None):
    """
    验证段位名是否有效，并可选择性匹配 sv2_flag

    参数:
        dan_name: str, 段位名
        sv2_flag: bool|None: 如果为 True/False，则校验该模式下是否有可用物量数据；
                             如果为 None，则只检查段位名是否存在。

    返回:
        bool: 是否有效
    """
    data = acc_data()
    if dan_name not in data:
        return False

    if sv2_flag is None:
        return True

    entry = data[dan_name]
    _, err_msg = extract_note_counts_from_dan(entry, bool(sv2_flag))
    return err_msg is None

def get_acc_result_text(
    mode: str,
    display_name: str = "",
    note_counts: List = None,
    acc_str: str = "",
    single_accs: List = None,
    sv2_flag: bool = False
) -> str:
    """
    构建ACC计算结果消息
    
    参数:
        mode: 模式 "predefined", "bid", "file", "custom"
        display_name: 显示名称
        note_counts: 物量列表
        acc_str: ACC字符串
        single_accs: 单曲ACC列表
    
    返回:
        格式化结果消息
    """
    result_msg = ""
    
    if mode == "predefined":
        result_msg += f"\n段位: {display_name}\n"
    elif mode in ["bid", "file", "custom"]:
        result_msg += f"\n谱面: {display_name}\n"
        if note_counts:
            result_msg += f"物量分布: {'-'.join(str(n) for n in note_counts)}\n"

    if sv2_flag:
        result_msg += "Mods: ScoreV2\n"
    
    if acc_str:
        result_msg += f"ACC变化: {acc_str}\n\n"
    
    if single_accs:
        result_msg += "单曲ACC计算结果:\n"
        i = 1
        for acc_value in single_accs:
            result_msg += f"第{i}首: {acc_value}\n"
            i += 1
    
    return result_msg.strip()

# ==================== 谱面分析函数 ====================

async def calculate_map_notes(file_path: Path, num_songs: int = 4, sv2_flag: bool = False) -> List:
    """
    分析谱面物量分布（异步）
    
    参数:
        file_path: .osu文件路径
        num_songs: 分段数量，默认为4
        
    返回:
        num_songs段物量列表
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, calculate_note_counts, parse_osu_file(file_path), num_songs, sv2_flag)

def parse_osu_file(file_path: Path) -> List:
    """
    解析.osu文件，提取物件信息
    调用统一的 osu_file 解析器，与项目内其他功能一致
    
    参数:
        file_path: .osu文件路径
        
    返回:
        list of (time, type, end_time)
        type: 1=RC, 128=LN
    """
    osu_obj = osu_file(file_path)
    osu_obj.process()

    if str(osu_obj.GameMode) != '3':
        raise ValueError("该谱面不是 mania 模式")

    objects = []
    for start_time, obj_type, raw_end_time in zip(osu_obj.note_starts, osu_obj.note_types, osu_obj.note_ends):
        start = int(start_time)
        note_type = int(obj_type)

        if note_type & 128:
            end = int(raw_end_time)
            if end < start:
                end = start
        else:
            end = start

        objects.append((start, note_type, end))

    return objects

def _get_note_weight(note_type: int, sv2_flag: bool) -> int:
    """
    计算单个物件权重
    sv2_flag=False: RC/LN均计1
    sv2_flag=True:  RC计1，LN计2
    """
    if sv2_flag and (note_type & 128):
        return 2
    return 1


def calculate_note_counts(objects: List, num_songs: int = 4, sv2_flag: bool = False) -> List:
    """
    计算分段物量
    修改自： https://github.com/uzxn/osu-split/blob/main/osu-split.c
    
    参数:
        objects: 物件列表
        num_songs: 分段数量
        sv2_flag: 是否使用sv2加权（LN按2计）
        
    返回:
        各段物量列表
    """
    if not objects:
        return [0] * num_songs
    
    # 按时间排序
    objects.sort(key=lambda x: x[0])
    
    # 计算总时间范围
    start_time = objects[0][0]
    end_time = max(obj[2] for obj in objects)
    total_duration = end_time - start_time
    
    if total_duration <= 0:
        return [0] * num_songs
    
    # 计算分段点（按时间均匀分段）
    segment_duration = total_duration / num_songs
    segment_points = [start_time + i * segment_duration for i in range(1, num_songs)]
    
    # 计算各段物量
    segment_counts = [0] * num_songs
    current_segment = 0
    
    for obj in objects:
        obj_time = obj[0]
        
        # 找到物件所属的段
        while current_segment < len(segment_points) and obj_time > segment_points[current_segment]:
            current_segment += 1
        
        if current_segment < num_songs:
            segment_counts[current_segment] += _get_note_weight(obj[1], sv2_flag)
    
    return segment_counts
