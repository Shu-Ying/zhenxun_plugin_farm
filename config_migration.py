"""仅清理农场已废弃配置，保存备份并同步网页配置数据。"""

import logging
import shutil
from pathlib import Path


OBSOLETE_KEYS = (
    "绘制农场清晰度", "动态背景", "签到图片样式", "兑换倍数",
    "点券兑换倍数", "手续费", "服务地址",
)


def migrate_config(manager, module):
    group = manager.get(module)
    simple = manager._simple_data.get(module, {})
    removed = [key for key in OBSOLETE_KEYS
               if key in group.configs or key in simple]
    if not removed:
        return
    for source in (manager.file, manager._simple_file):
        source = Path(source)
        backup = source.with_name(source.name + ".farm-v1.bak")
        if source.exists() and not backup.exists():
            shutil.copy2(source, backup)
    for key in removed:
        group.configs.pop(key, None)
        simple.pop(key, None)
    manager.save(save_simple_data=True)
    logging.getLogger(__name__).info(
        "farm config migration module=%s removed_keys=%s", module, removed,
    )
