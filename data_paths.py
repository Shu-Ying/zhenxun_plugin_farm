"""农场数据目录选择。"""

from pathlib import Path


def data_directory(base, configured=None):
    if configured is not None:
        return Path(configured)
    return Path(base) / 'farm_db'
