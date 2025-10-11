from pathlib import Path

from jinja2 import Template
from playwright.async_api import async_playwright

from zhenxun.configs.path_config import DATA_PATH
from zhenxun.services.log import logger

from ..config import g_sResourcePath


class CHelpManager:
    @classmethod
    def rendeerHtmlToFile(
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

    @classmethod
    async def createHelpImage(cls) -> bool:
        templatePath = g_sResourcePath / "html/help.html"
        outputPath = g_sResourcePath / "temp_html/help.html"
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
            cls.rendeerHtmlToFile(templatePath, context, outputPath)

            bytes = await cls.screenshotSave(str(outputPath), str(savePath), 1500, 2300)
        except Exception as e:
            logger.warning("绘制农场帮助菜单失败", e=e)
            return False

        return True


g_pHelpManager = CHelpManager()
