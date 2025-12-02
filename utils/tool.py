from datetime import datetime
import os
from pathlib import Path
from zoneinfo import ZoneInfo

from jinja2 import Template
from playwright.async_api import async_playwright
from zhdate import ZhDate

from zhenxun.services.log import logger
from zhenxun.utils.message import MessageUtils

from ..core import CPlayer, g_pUserPool
from . import utils


class CToolManager:
    @classmethod
    async def repeat(cls):
        await MessageUtils.build_message(
            "尚未开通农场，快at我发送 开通农场 开通吧"
        ).send()

    @classmethod
    async def getPlayerByUid(cls, uid: str) -> CPlayer | None:
        player = g_pUserPool.getUser(uid)
        if player is None:
            player = CPlayer()
            if not await player.init(uid):
                return None
            g_pUserPool.createUser(uid, player)

        return player

    @classmethod
    def sanitize_username(cls, username: str, max_length: int = 15) -> str:
        """
        安全处理用户名
        功能：
        1. 移除首尾空白
        2. 过滤危险字符
        3. 转义单引号
        4. 处理空值
        5. 限制长度
        """
        # 处理空值
        if not username:
            return "神秘农夫"

        # 基础清洗
        cleaned = username.strip()

        # 允许的字符白名单（可自定义扩展）
        # fmt: off
        safe_chars = {
            "_", "-", "!", "@", "#", "$", "%", "^", "&", "*", "(", ")",
            "+", "=", ".", ",", "~", "·", " ",
            "a","b","c","d","e","f","g","h","i","j","k","l","m",
            "n","o","p","q","r","s","t","u","v","w","x","y","z",
            "A","B","C","D","E","F","G","H","I","J","K","L","M",
            "N","O","P","Q","R","S","T","U","V","W","X","Y","Z",
            "0","1","2","3","4","5","6","7","8","9",
        }
        # fmt: on
        # 添加常用中文字符（Unicode范围）
        safe_chars.update(chr(c) for c in range(0x4E00, 0x9FFF + 1))

        # 过滤危险字符
        filtered = [
            c if c in safe_chars or 0x4E00 <= ord(c) <= 0x9FFF else "" for c in cleaned
        ]

        # 合并处理结果
        safe_str = "".join(filtered)

        # 转义单引号（双重保障）
        escaped = safe_str.replace("'", "''")

        # 处理空结果
        if not escaped:
            return "神秘农夫"

        # 长度限制
        return escaped[:max_length]

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

    @classmethod
    def getSeason(cls) -> utils.Season:
        month = cls.dateTime().month

        if month in [3, 4, 5]:
            return utils.Season.SPRING
        elif month in [6, 7, 8]:
            return utils.Season.SUMMER
        elif month in [9, 10, 11]:
            return utils.Season.AUTUMN
        elif month in [12, 1, 2]:
            return utils.Season.WINTER
        else:
            return utils.Season.NO

    @classmethod
    def getFestival(cls) -> utils.Festival:
        now = cls.dateTime()

        lunarDate = ZhDate.from_datetime(now)
        lunarMonth = lunarDate.lunar_month
        lunarDay = lunarDate.lunar_day

        festivalChecks = [
            (1, lambda: lunarMonth == 8 and lunarDay == 15),  # 中秋节
            (2, lambda: (now.month, now.day) == (10, 1)),  # 国庆节
            (3, lambda: lunarMonth == 1 and lunarDay == 15),  # 元宵节
            (4, lambda: lunarMonth == 5 and lunarDay == 5),  # 端午节
            (5, lambda: lunarMonth == 1 and lunarDay == 1),  # 春节
            (6, lambda: (now.month, now.day) == (10, 31)),  # 万圣节
            (7, lambda: (now.month, now.day) == (12, 25)),  # 圣诞节
            (8, lambda: (now.month, now.day) == (1, 1)),  # 新年
            (9, lambda: (now.month, now.day) == (2, 14)),  # 情人节
        ]

        for code, checkFunc in festivalChecks:
            if checkFunc():
                return utils.Festival(code)

        return utils.Festival.NO

    @classmethod
    def renderHtmlToFile(
        cls, path: Path | str, context: dict, output: Path | str
    ) -> None:
        """
        使用 Jinja2 渲染 HTML 模板并保存到指定文件，会自动创建父目录

        Args:
            path (str): 模板 HTML 路径
            context (dict): 用于渲染的上下文字典
            output (str): 输出 HTML 文件路径
        """
        templatePath = str(path)
        outputPath = str(output)

        templateStr = Path(templatePath).read_text(encoding="utf-8")
        template = Template(templateStr)
        rendered = template.render(**context)

        # 自动创建目录
        Path(outputPath).parent.mkdir(parents=True, exist_ok=True)

        Path(outputPath).write_text(rendered, encoding="utf-8")

    @classmethod
    async def screenshotHtmlToBytes(cls, path: str) -> bytes:
        """
        使用 Playwright 截图本地 HTML 文件并返回 PNG 图片字节数据

        Args:
            path (str): 本地 HTML 文件路径

        Returns:
            bytes: PNG 图片的原始字节内容
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page(
                viewport={"width": 1200, "height": 900}, device_scale_factor=1
            )
            file_url = Path(path).resolve().as_uri()
            await page.goto(file_url, wait_until="networkidle")
            await page.evaluate("""() => {
                return new Promise(r => setTimeout(r, 200));
            }""")
            image_bytes = await page.screenshot(full_page=True)
            await browser.close()

            return image_bytes

    @classmethod
    async def screenshotSave(
        cls, path: str, save: str, width: int, height: int
    ) -> None:
        """
        使用 Playwright 渲染本地 HTML 并将截图保存到指定路径

        Args:
            path (str): HTML 文件路径
            save (str): PNG 保存路径（如 output/image.png）
            width (int): 图片宽度
            height (int): 图片高度
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page(
                viewport={"width": width, "height": height}, device_scale_factor=1
            )

            file_url = Path(path).resolve().as_uri()
            await page.goto(file_url, wait_until="networkidle")
            await page.evaluate("""() => {
                return new Promise(r => setTimeout(r, 200));
            }""")

            # 确保保存目录存在
            Path(save).parent.mkdir(parents=True, exist_ok=True)

            # 截图并保存到本地文件
            await page.screenshot(path=save, full_page=True)
            await browser.close()
