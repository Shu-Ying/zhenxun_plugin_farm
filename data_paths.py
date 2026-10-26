"""农场数据目录选择。"""

from pathlib import Path


def data_directory(base, configured=None):
    if configured:
        return Path(configured).expanduser()
    return Path(base) / 'farm_db'
