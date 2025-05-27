import os
from datetime import datetime
from zoneinfo import ZoneInfo

from zhenxun.services.log import logger


class CToolManager:

    @classmethod
    def renameFile(cls, currentFilePath: str, newFileName: str) -> bool:
        """重命名文件，如果目标文件名已存在则先删除再重命名

        Args:
            currentFilePath (str): 当前文件的完整路径
            newFileName (str): 重命名后的文件名

        Returns:
            bool: 重命名成功返回 True，否则返回 False
        """
        try:
            dirPath = os.path.dirname(currentFilePath)
            newFilePath = os.path.join(dirPath, newFileName)

            if os.path.exists(newFilePath):
                os.remove(newFilePath)

            os.rename(currentFilePath, newFilePath)
            return True
        except Exception as e:
            logger.warning(f"文件重命名失败: {e}")
            return False

    @classmethod
    def dateTime(cls) -> datetime:
        tz = ZoneInfo("Asia/Shanghai")
        return datetime.now(tz)

g_pToolManager = CToolManager()
