from pathlib import Path

from jinja2 import Template
from playwright.async_api import async_playwright

from zhenxun.configs.path_config import DATA_PATH
from zhenxun.services.log import logger

from ..config import g_sResourcePath


def rendeerHtmlToFile(path: Path | str, context: dict, output: Path | str) -> None:
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


async def screenshotHtmlToBytes(path: str) -> bytes:
    """
    使用 Playwright 截图本地 HTML 文件并返回 PNG 图片字节数据

    Args:
        path (str): 本地 HTML 文件路径

    Returns:
        bytes: PNG 图片的原始字节内容
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        file_url = Path(path).resolve().as_uri()
        await page.goto(file_url)
        image_bytes = await page.screenshot(full_page=True)
        await browser.close()

        return image_bytes


async def screenshotSave(path: str, save: str) -> None:
    """
    使用 Playwright 渲染本地 HTML 并将截图保存到指定路径

    Args:
        path (str): HTML 文件路径
        save (str): PNG 保存路径（如 output/image.png）
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        file_url = Path(path).resolve().as_uri()
        await page.goto(file_url)

        # 确保保存目录存在
        Path(save).parent.mkdir(parents=True, exist_ok=True)

        # 截图并保存到本地文件
        await page.screenshot(path=save, full_page=True)
        await browser.close()


async def createHelpImage() -> bool:
    templatePath = g_sResourcePath / "html/help.html"
    outputPath = DATA_PATH / "farm_res/html/help.html"

    context = {
        "title": "功能指令总览",
        "data": [
            {
                "command": "开通农场",
                "description": "首次进入游戏开通农场",
                "tip": "",
            },
            {
                "command": "购买种子",
                "description": "从商店中购买可用种子",
                "tip": "",
            },
            {"command": "播种", "description": "将种子种入土地中", "tip": "先开垦土地"},
            {
                "command": "收获",
                "description": "收获成熟作物获得收益",
                "tip": "",
            },
            {
                "command": "偷菜",
                "description": "从好友农场中偷取成熟作物",
                "tip": "1",
            },
        ],
    }

    try:
        rendeerHtmlToFile(templatePath, context, outputPath)

        image_bytes = await screenshot_html_to_bytes(html_output_path)
    except Exception as e:
        logger.warning("绘制农场帮助菜单失败", e=e)
        return False

    return True
