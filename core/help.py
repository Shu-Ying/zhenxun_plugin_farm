from zhenxun.configs.path_config import DATA_PATH
from zhenxun.services.log import logger

from ..utils import config, getToolManager


class CHelpManager:
    @classmethod
    async def createHelpImage(cls) -> bool:
        templatePath = config.g_sResourcePath / "html/help.html"
        outputPath = config.g_sResourcePath / "temp_html/help.html"
        savePath = DATA_PATH / "farm_res/html/help.png"

        context = {
            "main_title": "真寻农场帮助菜单",
            "subtitle": "[]中为可选参数",
            "page_title": "真寻农场帮助菜单",
            "font_family": "MyFont",
            "contents": [
                {"title": "主要指令", "commands": ["指令A", "指令B"]},
                {"title": "B", "commands": ["指令D", "指令E", "指令M", "指令i"]},
            ],
        }

        try:
            getToolManager().renderHtmlToFile(templatePath, context, outputPath)

            bytes = await getToolManager().screenshotSave(
                str(outputPath), str(savePath), 1500, 2300
            )
        except Exception as e:
            logger.warning("绘制农场帮助菜单失败", e=e)
            return False

        return True
