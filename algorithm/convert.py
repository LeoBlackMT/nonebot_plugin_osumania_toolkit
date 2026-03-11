import json
import os
from typing import List, Optional


def convert_mc_to_osu(mc_file_path: str, output_dir: Optional[str] = None) -> str:
    """
    将 .mc 文件转换为 .osu 文件
    
    Args:
        mc_file_path: .mc 文件路径
        output_dir: 输出目录，如果为 None 则输出到原文件所在目录
        
    Returns:
        转换后的 .osu 文件路径
        
    Raises:
        ValueError: 如果文件不是有效的 .mc 文件
        Exception: 转换过程中的其他错误
    """
    # 检查文件是否存在
    if not os.path.exists(mc_file_path):
        raise FileNotFoundError(f"文件不存在: {mc_file_path}")
    
    # 检查文件扩展名
    if not mc_file_path.lower().endswith('.mc'):
        raise ValueError(f"文件不是 .mc 格式: {mc_file_path}")
    
    # 读取 .mc 文件
    try:
        with open(mc_file_path, 'r', encoding='utf-8') as f:
            mc_data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"无效的 JSON 格式: {e}")
    except Exception as e:
        raise Exception(f"读取文件失败: {e}")
    
    # 验证 .mc 文件格式
    if 'meta' not in mc_data:
        raise ValueError("无效的 .mc 文件: 缺少 'meta' 字段")
    
    meta = mc_data['meta']
    
    # 检查是否为 Key 模式 (mode 0)
    if meta.get('mode') != 0:
        raise ValueError("只支持 Key 模式 (mode 0) 的 .mc 文件")
    
    # 获取必要字段
    if 'mode_ext' not in meta or 'column' not in meta['mode_ext']:
        raise ValueError("无效的 .mc 文件: 缺少 'mode_ext.column' 字段")
    
    keys = meta['mode_ext']['column']
    
    # 获取时间点信息
    if 'time' not in mc_data or not mc_data['time']:
        raise ValueError("无效的 .mc 文件: 缺少 'time' 字段或为空")
    
    time_data = mc_data['time']
    
    # 获取音符数据
    if 'note' not in mc_data:
        raise ValueError("无效的 .mc 文件: 缺少 'note' 字段")
    
    note_data = mc_data['note']
    
    # 获取音效数据（如果有）
    sound_data = None
    for note in note_data:
        if note.get('type', 0) != 0:
            sound_data = note
            break
    
    # 获取效果数据（SV，如果有）
    sv_data = mc_data.get('effect', [])
    
    # 计算 BPM 和偏移
    bpm_list = []
    bpm_offset_list = []
    
    # 辅助函数：将节拍转换为浮点数
    def beat_to_float(beat: List[int]) -> float:
        """将 [measure, nth_beat, divisor] 转换为浮点数"""
        return beat[0] + beat[1] / beat[2]
    
    # 辅助函数：将节拍转换为毫秒
    def beat_to_ms(beat: List[int], bpm: float, offset: float) -> float:
        """将节拍转换为毫秒"""
        beats = beat_to_float(beat)
        return 1000 * (60 / bpm) * beats + offset
    
    # 初始化第一个 BPM
    first_bpm = time_data[0]['bpm']
    bpm_list.append(first_bpm)
    bpm_offset_list.append(-sound_data.get('offset', 0) if sound_data else 0)
    
    # 计算其他 BPM 点
    if len(time_data) > 1:
        last_beat = time_data[0]['beat']
        for i in range(1, len(time_data)):
            current_beat = time_data[i]['beat']
            current_bpm = time_data[i]['bpm']
            
            bpm_list.append(current_bpm)
            bpm_offset = beat_to_ms(
                current_beat, 
                time_data[i-1]['bpm'], 
                bpm_offset_list[i-1]
            ) - beat_to_ms(
                last_beat,
                time_data[i-1]['bpm'],
                bpm_offset_list[i-1]
            )
            bpm_offset_list.append(bpm_offset_list[i-1] + bpm_offset)
            
            last_beat = current_beat
    
    # 获取元数据
    title = meta['song']['title']
    artist = meta['song']['artist']
    creator = meta['creator']
    version = meta['version']
    background = meta.get('background', '')
    
    # 获取原始标题和艺术家（如果有）
    title_org = meta['song'].get('titleorg', title)
    artist_org = meta['song'].get('artistorg', artist)
    
    # 获取预览时间
    preview_time = meta.get('preview', -1)
    
    # 获取音效文件名
    sound_file = sound_data.get('sound', '') if sound_data else ''
    
    # 确定输出路径
    if output_dir is None:
        output_dir = os.path.dirname(mc_file_path)
    
    output_path = os.path.join(
        output_dir, 
        f"{os.path.splitext(os.path.basename(mc_file_path))[0]}.osu"
    )
    
    # 生成 .osu 文件内容
    osu_lines = [
        'osu file format v14',
        '',
        '[General]',
        f'AudioFilename: {sound_file}',
        'AudioLeadIn: 0',
        f'PreviewTime: {preview_time}',
        'Countdown: 0',
        'SampleSet: None',
        'StackLeniency: 0.7',
        'Mode: 3',
        'LetterboxInBreaks: 0',
        'SpecialStyle: 0',
        'WidescreenStoryboard: 0',
        '',
        '[Editor]',
        'DistanceSpacing: 1.2',
        'BeatDivisor: 4',
        'GridSize: 8',
        'TimelineZoom: 2.4',
        '',
        '[Metadata]',
        f'Title:{title}',
        f'TitleUnicode:{title_org}',
        f'Artist:{artist}',
        f'ArtistUnicode:{artist_org}',
        f'Creator:{creator}',
        f'Version:{version}',
        'Source:Malody',
        'Tags:Malody Convert by Jakads',
        'BeatmapID:0',
        'BeatmapSetID:-1',
        '',
        '[Difficulty]',
        'HPDrainRate:8',
        f'CircleSize:{keys}',
        'OverallDifficulty:8',
        'ApproachRate:5',
        'SliderMultiplier:1.4',
        'SliderTickRate:1',
        '',
        '[Events]',
        '//Background and Video events',
        f'0,0,"{background}",0,0',
        '',
        '[TimingPoints]'
    ]
    
    # 添加 Timing Points
    for i in range(len(bpm_list)):
        beat_signature = time_data[i].get('sign', 4)
        osu_lines.append(f'{int(bpm_offset_list[i])},{60000/bpm_list[i]},{beat_signature},1,0,0,1,0')
    
    # 添加 SV 点（如果有）
    if sv_data:
        for sv in sv_data:
            # 找到对应的 BPM 段
            sv_beat = beat_to_float(sv['beat'])
            bpm_index = 0
            
            for j in range(len(time_data)):
                if beat_to_float(time_data[j]['beat']) > sv_beat:
                    bpm_index = j
                    break
            
            # 计算 SV 点的时间
            sv_time = beat_to_ms(
                sv['beat'],
                bpm_list[bpm_index],
                bpm_offset_list[bpm_index]
            )
            
            # 计算 SV 值（滚动速度）
            scroll = sv.get('scroll', 1.0)
            if scroll == 0:
                sv_value = "1E+308"  # 无限大
            else:
                sv_value = 100 / abs(scroll)
            
            osu_lines.append(f'{int(sv_time)},-{sv_value},{time_data[bpm_index].get("sign", 4)},1,0,0,0,0')
    
    osu_lines.append('')
    osu_lines.append('[HitObjects]')
    
    # 添加 HitObjects
    for note in note_data:
        # 跳过音效数据
        if note.get('type', 0) != 0:
            continue
        
        # 找到对应的 BPM 段
        note_beat = beat_to_float(note['beat'])
        bpm_index = 0
        
        for j in range(len(time_data)):
            if beat_to_float(time_data[j]['beat']) > note_beat:
                bpm_index = j
                break
        
        # 计算音符时间
        note_time = beat_to_ms(
            note['beat'],
            bpm_list[bpm_index],
            bpm_offset_list[bpm_index]
        )
        
        # 计算列位置
        column = note['column']
        x_position = int(512 * (2 * column + 1) / (2 * keys))
        
        # 检查是否为长按音符
        if 'endbeat' in note:
            # 长按音符
            end_beat = beat_to_float(note['endbeat'])
            end_bpm_index = 0
            
            for j in range(len(time_data)):
                if beat_to_float(time_data[j]['beat']) > end_beat:
                    end_bpm_index = j
                    break
            
            # 计算结束时间
            end_time = beat_to_ms(
                note['endbeat'],
                bpm_list[end_bpm_index],
                bpm_offset_list[end_bpm_index]
            )
            
            # 长按音符格式: x,y,time,type,hitSound,endTime:extras
            hit_sound = note.get('sound', 0)
            volume = note.get('vol', 100)
            
            osu_lines.append(f'{x_position},192,{int(note_time)},128,0,{int(end_time)}:0:0:0:{volume}:{hit_sound}')
        else:
            # 普通音符
            hit_sound = note.get('sound', 0)
            volume = note.get('vol', 100)
            
            osu_lines.append(f'{x_position},192,{int(note_time)},1,0,0:0:0:0:{volume}:{hit_sound}')
    
    # 写入文件
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(osu_lines))
    except Exception as e:
        raise Exception(f"写入 .osu 文件失败: {e}")
    
    return output_path