from pydantic import BaseModel


class Config(BaseModel):
    """Plugin Config Here"""

    # 缓存文件最大保留时间（小时），默认 24 小时
    omtk_cache_max_age: int = 24
