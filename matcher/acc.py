import os
import asyncio
import re

from nonebot import on_command
from nonebot.params import Arg, CommandArg
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, Message
from nonebot.matcher import Matcher
from nonebot.typing import T_State
from nonebot.exception import FinishedException, RejectedException

from nonebot_plugin_localstore import get_plugin_cache_dir

from ..file.file import safe_filename, download_file, cleanup_temp_file, get_file_url, download_file_by_id
from ..algorithm.acc_calculate import (
    calculate_acc_from_dan, 
    calculate_acc,
    validate_dan_name, 
    parse_acc_cmd, 
    calculate_map_notes,
    get_acc_result_text,
)
from ..algorithm.utils import parse_osu_filename

CACHE_DIR = get_plugin_cache_dir()
CACHE_DIR.mkdir(parents=True, exist_ok=True)

acc = on_command("acc", aliases={"单曲"}, block=True)

@acc.handle()
async def acc_handle_first(matcher: Matcher, event: MessageEvent, state: T_State, cmd: Message = CommandArg()):
    cmd_text = event.get_plaintext().strip()
    dan_name, acc_str, bid, num_songs, error_msg = parse_acc_cmd(cmd_text)
    
    state["status"] = "init"
    
    if error_msg:
        state["status"] = "Fail"
        await acc.finish(f"错误: {error_msg}")
        
    # 初始化所有state
    state["acc_str"] = acc_str
    state["display_name"] = None
    state["dan_name"] = dan_name
    state["bid"] = bid
    state["num_songs"] = num_songs
    state["note_counts"] = None
    state["osu_path"] = ""
    state["osu_name"] = None
    state["reject_time"] = 0
    
    # bid模式
    if bid:
        state["mode"] = "bid"
        try:
            osu_path, osu_name = await download_file_by_id(CACHE_DIR, bid)
            state["osu_path"] = osu_path
            state["osu_name"] = osu_name
            
            # 段位名称即谱面元信息
            meta_data = parse_osu_filename(osu_name)
            if meta_data:
                display_name = f"{meta_data['Artist']} - {meta_data['Title']} [{meta_data['Version']}]"
                state["display_name"] = display_name
            else:
                state["display_name"] = osu_name
            
            # 计算各单曲物量
            note_counts = await calculate_map_notes(osu_path, num_songs)
            state["note_counts"] = note_counts
            
            if acc_str:
                # 有ACC字符串，数据已满足计算条件，到第二个got统一计算
                state["status"] = "Ready"
                matcher.set_arg("handle_second", cmd) # 跳转到第一个got
                return
            else:
                # 没有ACC字符串，进入第一个got获取
                acc_format = "-".join([f"acc{i+1}" for i in range(len(note_counts))])
                await acc.send(f"谱面物量分布: {'-'.join(str(n) for n in note_counts)}\n请输入ACC变化 (格式: {acc_format}):")
                return
        
        except FinishedException:
            pass
        except Exception as e:
            state["status"] = "Fail"
            await acc.send(f"处理谱面时出错: {str(e)}")
            return
        finally:
            osu_path = state.get("osu_path")
            if osu_path and osu_path.exists():
                asyncio.create_task(cleanup_temp_file(osu_path))
    
    # 给定段位名模式
    elif dan_name and acc_str:
        state["mode"] = "predefined"
        if acc_str:
            state["status"] = "Ready"
            # 有ACC字符串，数据已满足计算条件，到第二个got统一计算
            matcher.set_arg("handle_second", cmd) # 跳转到第一个got
            return
        else:
            # 只有段位名，需要ACC字符串
            await acc.send(f"已选择段位: {dan_name}\n请输入ACC变化 (格式: acc1-acc2-acc3-acc4...):")
    
    # 用户未提供任何信息，进入交互模式，需要先询问段位名或谱面
    else:
        state["mode"] = "interactive"
        await acc.send("请输入要计算的段位名，或发送谱面文件，或输入自定义物量。输入0取消。")
        return

@acc.got("handle_second")
async def acc_handle_second(matcher: Matcher, bot: Bot, state: T_State, message: Message = Arg("handle_second")):
    """
    第二个handler:
    获取段位名、自定义物量、谱面文件或acc变化
    """
    
    match state["status"]:
        case "Finish" | "Fail":
            await acc.finish()
            osu_path = state["osu_path"]
            if osu_path and osu_path.exists():
                asyncio.create_task(cleanup_temp_file(osu_path))
        case "Ready":
            # 数据已满足计算条件，到第二个got统一计算
            matcher.set_arg("handle_third", message) # 跳转到第二个got
            return
        case _:
            pass
        
    if state["reject_time"] > 5:
        state["status"] = "Fail"
        await acc.finish("重试次数过多，已取消操作。")
    
    # 检查用户是否发送了文件
    file_seg = None
    for seg in message:
        if seg.type == "file":
            file_seg = seg
            break
    
    if file_seg:
        # 用户发送了文件
        file_info = await get_file_url(bot, file_seg)
        if not file_info:
            state["status"] = "Fail"
            await acc.finish("无法获取文件信息。")
        
        file_name, file_url = file_info
        file_name = os.path.basename(file_name)
        
        # todo: 新增对.mc文件的支持
        if not file_name.lower().endswith('.osu'):
            state["status"] = "Fail"
            await acc.finish("请发送.osu格式的谱面文件。")
        
        # 下载文件
        osu_path = CACHE_DIR / safe_filename(file_name)
        success = await download_file(file_url, osu_path)
        if not success:
            state["status"] = "Fail"
            await acc.finish("文件下载失败，请稍后再试。")
        
        # 保存到state 进入文件模式
        state["mode"] = "file"
        state["osu_path"] = osu_path
        state["osu_name"] = file_name
        
        # 解析谱面文件名
        meta_data = parse_osu_filename(file_name)
        if meta_data:
            display_name = f"{meta_data['Artist']} - {meta_data['Title']} [{meta_data['Version']}]"
            state["display_name"] = display_name
        else:
            state["display_name"] = file_name
        
        try:
            # 交互模式下 暂不支持自定义分段数
            # 猜测如果有file_seg没有text，下载后保存在state中，然后使用reject让用户对发送的文件回复并包含分段数
            # 此时file_seg和text同时存在，再进行自定义分段数处理 以增加对各种 "How to be like ..."谱面的支持。
            note_counts = await calculate_map_notes(osu_path, 4)
            state["note_counts"] = note_counts
            await acc.send(f"已收到文件: {state["display_name"]}\n谱面物量分布: {'-'.join(str(n) for n in note_counts)}\n请输入ACC变化 (格式: acc1-acc2-acc3-acc4...):")
            
        except Exception as e:
            state["status"] = "Fail"
            osu_path = state["osu_path"]
            if osu_path and osu_path.exists():
                asyncio.create_task(cleanup_temp_file(osu_path))
            await acc.send(f"处理时出错: {str(e)}")
            return
        
        # 转第二个got，获取acc变化。
        return
    
    # 不是文件，检查文本输入
    text_input = message.extract_plain_text().strip()
    
    # 输入0，取消操作
    if text_input == '0':
        state["status"] = "Finish"
        await acc.finish("操作已取消。")
    
    # 检查是否是自定义物量格式 (int,int,int...)
    if re.match(r'^\d+(?:,\d+)+$', text_input):
        # 自定义物量
        note_counts = [int(n) for n in text_input.split(',')]
        
        # 检查物量值是否有效
        if len(note_counts) < 1:
            state["reject_time"] += 1
            await acc.reject("至少需要一首歌的物量值。请重新输入:")
        
        if any(n <= 0 for n in note_counts):
            state["reject_time"] += 1
            await acc.reject("物量必须为正整数。请重新输入:")
            
        try:    
            # 进入自定义物量模式
            state["mode"] = "custom"
            state["note_counts"] = note_counts
            state["display_name"] = "自定义物量"
            
            # 根据物量个数生成ACC格式提示
            acc_format = "-".join([f"acc{i+1}" for i in range(len(note_counts))])
            await acc.send(f"已设置自定义物量: {text_input}\n请输入ACC变化 (格式: {acc_format}):")
            return
            # 转第二个got，获取acc变化。
        
        except RejectedException:
            pass
        except ValueError:
            state["status"] = "Fail"
            await acc.send("物量格式错误。请使用格式: 物量1,物量2,物量3...")
            return
        except Exception as e:
            state["status"] = "Fail"
            await acc.send(f"处理过程发生错误: {e}")
            return
    
    # 检查是否是段位名
    if validate_dan_name(text_input):
        state["mode"] = "predefined"
        state["dan_name"] = text_input
        await acc.send(f"已选择段位: {text_input}\n请输入ACC变化 (格式: acc1-acc2-acc3-acc4...):")
        return
    
    # 检查是否为acc变化
    # 获取 acc变化 并跳转到第三部分
    if (state["mode"] == "predefined" or state["mode"] == "bid") and re.match(r'^(\d+(?:\.\d+)?)(?:-(\d+(?:\.\d+)?))+$', text_input):
        matcher.set_arg("handle_third", message) # 跳转到第二个got
        return
    
    # 无效输入
    state["reject_time"] += 1
    await acc.reject("输入无效。请根据上一个消息的提示发送正确的内容，或输入0取消操作。\n请重新输入:")

@acc.got("handle_third")
async def acc_handle_third(matcher: Matcher, state: T_State, message: Message = Arg("handle_third")):
    """
    第三个handle
    获取ACC字符串与计算结果
    """
    match state["status"]:
        case "Finish" | "Fail":
            await acc.finish()
            osu_path = state["osu_path"]
            if osu_path and osu_path.exists():
                asyncio.create_task(cleanup_temp_file(osu_path))
        case _:
            pass
    
    if state["reject_time"] > 5:
        state["status"] = "Fail"
        await acc.finish("重试次数过多，已取消操作。")
    
    # 当数据不满足计算条件时，用户输入acc
    if state["status"] != "Ready":
        msg_text = message.extract_plain_text().strip()
        if msg_text == '0':
            state["status"] = "Finish"
            osu_path = state["osu_path"]
            if osu_path and osu_path.exists():
                asyncio.create_task(cleanup_temp_file(osu_path))
            await acc.finish("已取消操作")
        if re.match(r'^(\d+(?:\.\d+)?)(?:-(\d+(?:\.\d+)?))+$', msg_text):
            state["acc_str"] = msg_text
        else:
            state["reject_time"] += 1
            await acc.reject("格式错误。请重新输入，或输入0取消:")
    
    # 开始计算
    single_accs = None
    
    # 检查mode是否已定义
    mode = state.get("mode")
    if not mode:
        state["status"] = "Fail"
        await acc.finish("错误: 未获取到计算模式")
    
    if mode == "predefined":
        # 预定义段位模式
        try:
            dan_name = state["dan_name"]
            if not dan_name:
                state["status"] = "Fail"
                await acc.finish("错误: 未获取到段位名")
            
            single_accs, calc_error = calculate_acc_from_dan(dan_name, state["acc_str"])
            if calc_error:
                state["status"] = "Fail"
                await acc.finish(f"计算错误: {calc_error}")

            result_msg = get_acc_result_text("predefined", dan_name, None, state["acc_str"], single_accs)
            
        except FinishedException:
            pass
        except Exception as e:
            state["status"] = "Fail"
            await acc.send(f"发生错误：{e}")
            return
        finally:
            osu_path = state["osu_path"]
            if osu_path and osu_path.exists():
                asyncio.create_task(cleanup_temp_file(osu_path))
    
    elif mode in ["bid", "file", "custom"]:
        # 谱面或自定义物量模式
        try:
            note_counts = state["note_counts"]
            display_name = state.get("display_name", "未知")
            
            if not note_counts:
                state["status"] = "Fail"
                await acc.finish("错误: 未获取到物量数据")
            
            single_accs, calc_error = calculate_acc(note_counts, state["acc_str"])
            if calc_error:
                state["status"] = "Fail"
                await acc.finish(f"计算错误: {calc_error}")
            
            # 构建结果消息
            result_msg = get_acc_result_text(mode, display_name, note_counts, state["acc_str"], single_accs)
            
        except FinishedException:
            pass
        except Exception as e:
            state["status"] = "Fail"
            await acc.send(f"发生错误：{e}")
            return
        finally:
            osu_path = state["osu_path"]
            if osu_path and osu_path.exists():
                asyncio.create_task(cleanup_temp_file(osu_path))
    else:
        state["status"] = "Fail"
        await acc.finish("错误: 未知模式")
    
    # 发送结果
    state["status"] = "Finish"
    await acc.finish(result_msg, at_sender=True)
    return
    
    
    # 计划支持 scoreV2，增强谱面物量计算。