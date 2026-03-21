import os
from pathlib import Path

from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, MessageEvent
from nonebot.exception import FinishedException
from nonebot_plugin_localstore import get_plugin_cache_dir

from ..algorithm.convert import convert_mc_to_osu
from ..algorithm.patterns import (
    PatternNotManiaError,
    PatternParseError,
    analyze_pattern_file,
    format_pattern_result_text,
)
from ..algorithm.utils import parse_cmd, is_mc_file, resolve_meta_data
from ..file.file import download_file, download_file_by_id, get_file_url


CACHE_DIR = get_plugin_cache_dir()
CACHE_DIR.mkdir(parents=True, exist_ok=True)


pattern = on_command("pattern", aliases={"键型"}, block=True)


@pattern.handle()
async def handle_pattern(bot: Bot, event: MessageEvent):
    cmd_text = event.get_plaintext().strip()
    _, _, _, bid, _, _ = parse_cmd(cmd_text)

    tmp_file: Path | None = None
    chart_file: Path | None = None

    try:
        if event.reply:
            reply = event.reply
            file_seg = None
            for seg in reply.message:
                if seg.type == "file":
                    file_seg = seg
                    break

            if not file_seg:
                await pattern.finish("回复的消息中没有找到文件。")

            file_info = await get_file_url(bot, file_seg)
            if not file_info:
                await pattern.finish("无法获取文件信息。请确保机器人有权限访问该文件，或者文件链接有效。")

            file_name, file_url = file_info
            file_name = os.path.basename(file_name)
            if not (file_name.lower().endswith(".osu") or file_name.lower().endswith(".mc")):
                await pattern.finish("请回复 .osu/.mc 格式的谱面文件。")

            tmp_file = CACHE_DIR / file_name
            if not await download_file(file_url, tmp_file):
                await pattern.finish("下载失败：文件可能过大或链接无效，请检查并重试。")

            chart_file = tmp_file
            if is_mc_file(str(chart_file)):
                try:
                    osu_file_path = convert_mc_to_osu(str(tmp_file), str(CACHE_DIR))
                    chart_file = Path(osu_file_path)
                    file_name = os.path.basename(osu_file_path)
                except Exception as e:
                    await pattern.finish(f".mc 文件转换失败: {e}")

            await pattern.send(f"已收到文件：{file_name}，请稍候...")
            report = await analyze_pattern_file(str(chart_file), rate=1.0)
            meta_data = resolve_meta_data(chart_file, file_name)
            await pattern.finish(format_pattern_result_text(meta_data, report, rate=1.0), at_sender=True)

        elif bid is not None:
            tmp_file, file_name = await download_file_by_id(CACHE_DIR, bid)
            chart_file = tmp_file

            report = await analyze_pattern_file(str(chart_file), rate=1.0)
            meta_data = resolve_meta_data(chart_file, file_name)
            await pattern.finish(format_pattern_result_text(meta_data, report, rate=1.0), at_sender=True)
        else:
            await pattern.finish("请回复包含 .osu 或 .mc 文件的消息，或使用 bid 指定谱面。")

    except FinishedException:
        raise
    except PatternNotManiaError:
        await pattern.finish("该谱面不是 mania 模式，无法分析键型。")
    except PatternParseError as e:
        await pattern.finish(f"谱面解析失败：{e}")
    except Exception as e:
        await pattern.finish(f"键型分析失败：{e}")
    finally:
        if tmp_file and tmp_file.exists():
            tmp_file.unlink()
        if chart_file and chart_file != tmp_file and chart_file.exists():
            chart_file.unlink()
