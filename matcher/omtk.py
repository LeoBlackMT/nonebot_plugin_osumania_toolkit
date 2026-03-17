from nonebot import on_command
from nonebot.adapters.onebot.v11 import MessageEvent
from nonebot.exception import FinishedException

from ..file.data import omtk_help_data

omtk = on_command("omtk")
# 数据
command_aliases = omtk_help_data.command_aliases
help_text = omtk_help_data.help_text

@omtk.handle()
async def handle_omtk(event: MessageEvent):
    page = 1
    
    try:
        cmd = event.get_plaintext().strip().split()
        match len(cmd):
            case 1:
                await omtk.finish(">osu!mania工具箱<\n发送/omtk显示此信息。发送/omtk <命令名> [页码]获取该命令的详细用法。\n\n可用命令：\n1. /rework - 星数重算\n2. /pressingtime 或 /按压 - 按键时间分析\n3. /analyze 或 /分析 - 作弊分析\n4. /delta 或 /偏差 - 判定偏差分析\n5. /lifebar 或 /血条 - 血条显示\n6. /spectrum 或 /频谱 - 频谱显示\n7. /scatter 或 /散点 - 散点图\n8. /acc 或 /单曲 - 单曲ACC计算\n") # 基础帮助信息
            case 2 | 3:
                if len(cmd) == 2:
                    cmd.append("1")  # 默认页码为1
                
                # 处理别名
                cmd_name = cmd[1].lower()
                if cmd_name in command_aliases:
                    cmd_name = command_aliases[cmd_name]
                
                for type, type_name, page, total_pages, text in help_text:
                    if cmd_name == type and cmd[2] == page:
                        if total_pages == "1":
                            await omtk.finish(type + "(" + type_name + "):\n" + text) # 详细帮助信息
                        await omtk.finish(type + "(" + type_name + "):\n" + text + "\n (第 " + page + " 页，共 " + total_pages + " 页)") # 分页详细帮助信息
                await omtk.finish("无效的命令类型或页码。")
            case _:
                await omtk.finish("请检查命令格式后重试。")
                
    except ValueError:
        await omtk.send("请检查命令格式后重试。")
        return
    except FinishedException:
        pass
    except Exception as e:
        await omtk.send(f"发生错误: {str(e)}")
        return
