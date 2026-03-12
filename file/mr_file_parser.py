import struct
from typing import Tuple
from nonebot.log import logger

class ReplayEvent:
    def __init__(self, time_delta: int, keys: int):
        self.time_delta = time_delta
        self.keys = keys

class mr_file:
    """
    Malody 回放文件解析器。
    按照给定的 .mr 格式解析，提取所有字段并存储。
    """
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.status = "init"
        self.magic = ""
        self.version = (0, 0, 0)  # (major, minor, patch)
        self.beatmap_md5 = ""
        self.difficulty_name = ""
        self.song_title = ""
        self.song_artist = ""
        self.score = 0
        self.max_combo = 0
        self.best_count = 0
        self.cool_count = 0
        self.good_count = 0
        self.miss_count = 0
        self.unknown_count = 0
        self.mods_flags = 0
        self.rank = 0
        self.timestamp = 0  # Unix 时间戳（秒）
        self.actions = []   # 原始动作列表，每个元素 (time, action, column)

        self._parse()

    def _read_string(self, data: bytes, offset: int) -> Tuple[str, int]:
        """读取带 Int32 长度前缀的 UTF-8 字符串，返回 (字符串, 新偏移)"""
        if offset + 4 > len(data):
            raise ValueError("文件过早结束")
        length = struct.unpack_from('<i', data, offset)[0]
        offset += 4
        if length == 0:
            return "", offset
        if offset + length > len(data):
            raise ValueError("字符串数据不足")
        s = data[offset:offset+length].decode('utf-8')
        offset += length
        return s, offset

    def _parse(self):
        with open(self.file_path, 'rb') as f:
            data = f.read()
        offset = 0

        try:
            # 1. 文件头 magic "mr format head"
            self.magic, offset = self._read_string(data, offset)
            if self.magic != "mr format head":
                self.status = "ParseError"
                return

            # 2. 版本 (4 bytes: patch, minor, major, 0)
            if offset + 4 > len(data):
                self.status = "ParseError"
                return
            patch, minor, major, _ = struct.unpack_from('<BBBB', data, offset)
            self.version = (major, minor, patch)
            offset += 4

            # 3. beatmap_md5
            self.beatmap_md5, offset = self._read_string(data, offset)
            # 4. difficulty_name
            self.difficulty_name, offset = self._read_string(data, offset)
            # 5. song_title
            self.song_title, offset = self._read_string(data, offset)
            # 6. song_artist
            self.song_artist, offset = self._read_string(data, offset)

            # 7. score
            if offset + 4 > len(data):
                self.status = "ParseError"
                return
            self.score = struct.unpack_from('<i', data, offset)[0]
            offset += 4

            # 8. max_combo
            self.max_combo = struct.unpack_from('<i', data, offset)[0]
            offset += 4

            # 9. best_count
            self.best_count = struct.unpack_from('<i', data, offset)[0]
            offset += 4

            # 10. cool_count
            self.cool_count = struct.unpack_from('<i', data, offset)[0]
            offset += 4

            # 11. good_count
            self.good_count = struct.unpack_from('<i', data, offset)[0]
            offset += 4

            # 12. miss_count
            self.miss_count = struct.unpack_from('<i', data, offset)[0]
            offset += 4

            # 13. unknown_count
            self.unknown_count = struct.unpack_from('<i', data, offset)[0]
            offset += 4

            # 14. mods_flags
            self.mods_flags = struct.unpack_from('<i', data, offset)[0]
            offset += 4

            # 15. rank
            self.rank = struct.unpack_from('<i', data, offset)[0]
            offset += 4

            # 16. data_magic "mr data"
            data_magic, offset = self._read_string(data, offset)
            if data_magic != "mr data":
                self.status = "ParseError"
                return

            # 17. version (与头版本相同，可跳过)
            if offset + 4 > len(data):
                self.status = "ParseError"
                return
            offset += 4

            # 18. action_count
            if offset + 4 > len(data):
                self.status = "ParseError"
                return
            action_count = struct.unpack_from('<i', data, offset)[0]
            offset += 4

            # 19. unknown_byte
            if offset + 1 > len(data):
                self.status = "ParseError"
                return
            unknown_byte = data[offset]
            offset += 1

            # 20. timestamp (Unix 秒)
            if offset + 4 > len(data):
                self.status = "ParseError"
                return
            self.timestamp = struct.unpack_from('<i', data, offset)[0]
            offset += 4

            # 21. unknown_int
            if offset + 4 > len(data):
                self.status = "ParseError"
                return
            unknown_int = struct.unpack_from('<i', data, offset)[0]
            offset += 4

            # 22. 读取所有动作
            for _ in range(action_count):
                if offset + 6 > len(data):
                    self.status = "ParseError"
                    return
                time = struct.unpack_from('<i', data, offset)[0]
                action = data[offset + 4]
                column = data[offset + 5]
                self.actions.append((time, action, column))
                offset += 6

            # 解析成功
            self.status = "OK"
        except Exception as e:
            self.status = "ParseError"
            logger.error(f"解析 .mr 文件失败: {e}")
            return

    def get_data(self):
        """返回字典"""
        return {
            "status": self.status,
            "magic": self.magic,
            "version": self.version,
            "beatmap_md5": self.beatmap_md5,
            "difficulty_name": self.difficulty_name,
            "song_title": self.song_title,
            "song_artist": self.song_artist,
            "score": self.score,
            "max_combo": self.max_combo,
            "best_count": self.best_count,
            "cool_count": self.cool_count,
            "good_count": self.good_count,
            "miss_count": self.miss_count,
            "unknown_count": self.unknown_count,
            "mods_flags": self.mods_flags,
            "rank": self.rank,
            "timestamp": self.timestamp,
            "actions": self.actions,
        }
