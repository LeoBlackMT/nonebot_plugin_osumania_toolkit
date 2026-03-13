from nonebot import get_plugin_config, require, get_driver
from nonebot.plugin import PluginMetadata
require("nonebot_plugin_localstore")

from nonebot_plugin_localstore import get_plugin_cache_dir
from .matcher import *
from .config import Config
from .file.file import cleanup_old_cache

__plugin_meta__ = PluginMetadata(
    name="nonebot_plugin_osumania_toolkit",
    description="a nonebot plugin with some useful osu!mania utilities",
    usage="send /omtk for help",
    homepage = "https://github.com/LeoBlackMT/nonebot_plugin_osumania_toolkit",
    config=Config,
)

config = get_plugin_config(Config)

# 获取驱动器
driver = get_driver()

# 在 Bot 启动时清理旧缓存
@driver.on_startup
async def startup_cleanup():
    """Bot 启动时清理超过指定时间的旧缓存文件"""
    cache_dir = get_plugin_cache_dir()
    max_age = config.omtk_cache_max_age
    cleanup_old_cache(cache_dir, max_age_hours=max_age)

