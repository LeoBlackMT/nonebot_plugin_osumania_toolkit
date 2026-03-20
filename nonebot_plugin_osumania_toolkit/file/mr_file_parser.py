import struct
import os
from typing import Tuple, List
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
        self.file_path = str(file_path)
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

        try:
            self._parse()
        except Exception as e:
            self.status = "ParseError"
            logger.error(f"初始化mr_file对象失败: {e}")

    def _read_string(self, data: bytes, offset: int) -> Tuple[str, int]:
        """读取带 Int32 长度前缀的 UTF-8 字符串，返回 (字符串, 新偏移)"""
        try:
            if offset + 4 > len(data):
                raise ValueError("文件过早结束，无法读取字符串长度")
            
            length = struct.unpack_from('<i', data, offset)[0]
            offset += 4
            
            # 处理长度异常
            if length < 0:
                logger.warning(f"字符串长度为负: {length}，视为空字符串")
                return "", offset
            elif length == 0:
                return "", offset
            elif length > 1000000:  # 合理上限
                logger.warning(f"字符串长度异常大: {length}，可能解析错误")
                return "", offset
            
            if offset + length > len(data):
                raise ValueError(f"字符串数据不足，需要{length}字节但只有{len(data)-offset}字节")
            
            # 尝试解码UTF-8，如果失败则使用错误处理
            try:
                s = data[offset:offset+length].decode('utf-8')
            except UnicodeDecodeError:
                # 尝试使用错误处理
                s = data[offset:offset+length].decode('utf-8', errors='replace')
                logger.warning(f"字符串包含无效UTF-8字符，已替换")
            
            offset += length
            return s, offset
            
        except struct.error as e:
            raise ValueError(f"解析字符串长度失败: {e}")
        except Exception as e:
            raise ValueError(f"读取字符串失败: {e}")

    def _parse(self):
        """解析.mr文件"""
        # 验证文件路径
        if not os.path.exists(self.file_path):
            self.status = "FileNotFound"
            logger.error(f"文件不存在: {self.file_path}")
            return
        
        if not self.file_path.lower().endswith('.mr'):
            self.status = "InvalidFileType"
            logger.error(f"文件不是.mr格式: {self.file_path}")
            return
        
        # 检查文件大小
        file_size = os.path.getsize(self.file_path)
        if file_size < 100:  # .mr文件至少应该有100字节
            self.status = "FileTooSmall"
            logger.error(f"文件过小: {file_size}字节")
            return
        
        try:
            with open(self.file_path, 'rb') as f:
                data = f.read()
            
            if len(data) < 100:
                self.status = "ParseError"
                logger.error("文件数据过少")
                return
                
            offset = 0

            # 1. 文件头 magic "mr format head"
            self.magic, offset = self._read_string(data, offset)
            if self.magic != "mr format head":
                self.status = "InvalidMagic"
                logger.error(f"无效的文件头: {self.magic}")
                return

            # 2. 版本 (4 bytes: patch, minor, major, 0)
            if offset + 4 > len(data):
                self.status = "ParseError"
                logger.error("文件过早结束: 版本字段")
                return
            patch, minor, major, _ = struct.unpack_from('<BBBB', data, offset)
            self.version = (major, minor, patch)
            offset += 4
            
            # 检查版本兼容性
            if major > 4 or minor > 3:  # 当前支持v4.3.x
                logger.warning(f"不常见的版本: v{major}.{minor}.{patch}")

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
                logger.error("文件过早结束: score字段")
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

            # 15. rank (0-4对应A-E)
            self.rank = struct.unpack_from('<i', data, offset)[0]
            if self.rank < 0 or self.rank > 4:
                logger.warning(f"异常的判定: {self.rank}")
            offset += 4

            # 16. data_magic "mr data"
            data_magic, offset = self._read_string(data, offset)
            if data_magic != "mr data":
                self.status = "InvalidDataMagic"
                logger.error(f"无效的数据段标识: {data_magic}")
                return

            # 17. version (与头版本相同，可跳过)
            if offset + 4 > len(data):
                self.status = "ParseError"
                logger.error("文件过早结束: 数据段版本")
                return
            offset += 4

            # 18. action_count
            if offset + 4 > len(data):
                self.status = "ParseError"
                logger.error("文件过早结束: action_count字段")
                return
            action_count = struct.unpack_from('<i', data, offset)[0]
            offset += 4
            
            # 验证action_count合理性
            if action_count < 0:
                self.status = "InvalidActionCount"
                logger.error(f"无效的动作数量: {action_count}")
                return
            if action_count > 1000000:  # 合理上限
                logger.warning(f"动作数量异常多: {action_count}")

            # 19. unknown_byte
            if offset + 1 > len(data):
                self.status = "ParseError"
                logger.error("文件过早结束: unknown_byte字段")
                return
            unknown_byte = data[offset]
            offset += 1

            # 20. timestamp (Unix 秒)
            if offset + 4 > len(data):
                self.status = "ParseError"
                logger.error("文件过早结束: timestamp字段")
                return
            self.timestamp = struct.unpack_from('<i', data, offset)[0]
            offset += 4
            
            # 验证时间戳合理性 (2000-01-01到当前时间)
            if self.timestamp < 946684800 or self.timestamp > 2147483647:
                logger.warning(f"异常的时间戳: {self.timestamp}")

            # 21. unknown_int 暂时未知作用
            if offset + 4 > len(data):
                self.status = "ParseError"
                logger.error("文件过早结束: unknown_int字段")
                return
            unknown_int = struct.unpack_from('<i', data, offset)[0]
            offset += 4

            # 22. 读取所有动作
            self.actions = []
            invalid_actions = 0
            for i in range(action_count):
                if offset + 6 > len(data):
                    self.status = "ParseError"
                    logger.error(f"文件过早结束: 动作{i+1}/{action_count}")
                    return
                time = struct.unpack_from('<i', data, offset)[0]
                action = data[offset + 4]
                column = data[offset + 5]
                
                # 验证动作数据
                if action not in (1, 2):  # 1=按下, 2=松开
                    logger.warning(f"动作{i+1}: 无效的action值 {action}")
                    invalid_actions += 1
                elif column >= 18:  # Malody最大支持18键
                    logger.warning(f"动作{i+1}: 无效的column值 {column}")
                    invalid_actions += 1
                elif time < 0:
                    logger.warning(f"动作{i+1}: 负的时间戳 {time}")
                    invalid_actions += 1
                else:
                    self.actions.append((time, action, column))
                
                offset += 6
            
            if invalid_actions > 0:
                logger.warning(f"发现{invalid_actions}个无效动作")

            # 检查动作列表是否为空
            if not self.actions:
                self.status = "NoValidActions"
                logger.error("没有有效的动作数据")
                return

            # 解析成功
            self.status = "OK"
            logger.debug(f"成功解析.mr文件: {len(self.actions)}个动作")
            
        except struct.error as e:
            self.status = "StructError"
            logger.error(f"二进制解析失败: {e}")
        except UnicodeDecodeError as e:
            self.status = "UnicodeError"
            logger.error(f"字符串解码失败: {e}")
        except Exception as e:
            self.status = "ParseError"
            logger.error(f"解析.mr文件失败: {e}")

    def get_data(self):
        """返回字典形式的完整数据"""
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
    
    def get_summary(self) -> dict:
        """Debug: 返回简化的摘要信息"""
        return {
            "status": self.status,
            "player": "Malody Player",  # Malody回放不存储玩家名
            "song": f"{self.song_title} - {self.song_artist}",
            "difficulty": self.difficulty_name,
            "score": self.score,
            "accuracy": self.calculate_accuracy(),
            "max_combo": self.max_combo,
            "judge": {
                "best": self.best_count,
                "cool": self.cool_count,
                "good": self.good_count,
                "miss": self.miss_count,
            },
            "mods": self.get_mods_list(),
            "action_count": len(self.actions),
            "timestamp": self.timestamp,
        }
    
    def calculate_accuracy(self) -> float:
        """计算Malody格式的准确率"""
        total_notes = self.best_count + self.cool_count + self.good_count + self.miss_count
        if total_notes == 0:
            return 0.0
        # best=100%, cool=75%, good=40%, miss=0%
        accuracy = (self.best_count * 100 + self.cool_count * 75 + self.good_count * 40) / (total_notes * 100) * 100
        return round(accuracy, 2)
    
    def get_mods_list(self) -> List[str]:
        """返回mods列表"""
        mods = []
        mod_mapping = {
            1: "Fair",
            2: "Luck",
            3: "Flip",
            4: "Const",
            5: "Dash", # 1.2
            6: "Rush", # 1.5
            7: "Hide",
            9: "Slow", # 0.8
            10: "Death",
        }
        
        for bit, mod_name in mod_mapping.items():
            if self.mods_flags & (1 << (bit - 1)):  # bit是1-based
                mods.append(mod_name)
        
        return mods
    
    def is_valid(self) -> bool:
        """检查文件是否有效"""
        return self.status == "OK" and len(self.actions) > 0
    
    def get_action_stats(self) -> dict:
        """Debug: 获取动作统计信息"""
        if not self.actions:
            return {}
        
        times = [a[0] for a in self.actions]
        actions = [a[1] for a in self.actions]
        columns = [a[2] for a in self.actions]
        
        return {
            "total_actions": len(self.actions),
            "key_down_count": actions.count(1),
            "key_up_count": actions.count(2),
            "min_time": min(times) if times else 0,
            "max_time": max(times) if times else 0,
            "duration_ms": max(times) - min(times) if len(times) >= 2 else 0,
            "unique_columns": len(set(columns)),
            "column_distribution": {col: columns.count(col) for col in set(columns)},
        }
