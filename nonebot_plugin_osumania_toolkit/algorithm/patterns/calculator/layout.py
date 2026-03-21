# -*- coding: utf-8 -*-
"""
对应 prelude/src/Calculator/Utils.fs 的 Layout.keys_on_left_hand
"""

def keys_on_left_hand(keymode: int) -> int:
    if keymode == 3:
        return 2
    if keymode == 4:
        return 2
    if keymode == 5:
        return 3
    if keymode == 6:
        return 3
    if keymode == 7:
        return 4
    if keymode == 8:
        return 4
    if keymode == 9:
        return 5
    if keymode == 10:
        return 5
    raise ValueError(f"Invalid keymode {keymode}")