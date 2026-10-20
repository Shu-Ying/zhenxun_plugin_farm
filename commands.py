"""宿主依赖止于接入层；保持旧版中文入口，不新增测试前缀。"""

import asyncio
import logging
import time

from nonebot import get_driver, on_command, require
from nonebot.adapters import Bot, Event, Message
from nonebot.params import CommandArg

require("nonebot_plugin_uninfo")
from nonebot_plugin_uninfo import Uninfo
from zhenxun.configs.path_config import DATA_PATH, FONT_PATH
from zhenxun.utils.message import MessageUtils
from zhenxun.utils.platform import PlatformUtils

from .runtime import COMMANDS, Runtime
from .data_paths import data_directories
from .config_migration import migrate_config

logger = logging.getLogger(__name__)
driver = get_driver()
data_dir, legacy_data_dir = data_directories(
    DATA_PATH, getattr(driver.config, 'farm_preview_data_dir', None),
)
runtime = Runtime(
    data_dir,
    getattr(driver.config, "farm_preview_font", None),
    getattr(driver.config, "farm_preview_deployment", "zhenxun-preview"),
    str(getattr(driver.config, "farm_preview_image_format", "AUTO")).upper(),
    font_dir=FONT_PATH,
    legacy_data_dir=legacy_data_dir,
)
async def start_runtime():
    from zhenxun.configs.config import Config

    migrate_config(Config, __package__.split(".")[-1])
    await runtime.start()


driver.on_startup(start_runtime)
driver.on_shutdown(runtime.close)
_avatars = {}


async def avatar_for(user_id, platform):
    if platform not in ("OneBot V11", "QQ"):
        return None
    key = (platform, user_id)
    now = time.monotonic()
    cached = _avatars.get(key)
    if cached and cached[0] > now:
        return cached[1]
    try:
        content = await asyncio.wait_for(
            PlatformUtils.get_user_avatar(user_id, "qq"), timeout=2,
        )
        if content and len(content) > 2 * 1024 * 1024:
            content = None
    except Exception:
        content = None
        logger.warning("farm preview avatar unavailable; using default")
    while len(_avatars) >= 16:
        _avatars.pop(next(iter(_avatars)))
    _avatars[key] = (now + (300 if content else 30), content)
    return content


def handler_for(action):
    async def handle(
        bot: Bot, event: Event, session: Uninfo,
        args: Message = CommandArg(),
    ):
        platform = bot.adapter.get_name()
        user_id = str(session.user.id)
        message_id = getattr(event, "message_id", None)
        if message_id is None:
            message_id = getattr(event, "id", None)
        try:
            avatar = (await avatar_for(user_id, platform)
                      if action == "farm" else None)
            response = await runtime.execute(
                action, args.extract_plain_text(), bot_id=str(bot.self_id),
                platform=platform, user_id=user_id, message_id=message_id,
                display_name=session.user.name or "农场玩家", avatar=avatar,
            )
        except Exception as error:
            logger.error(
                "farm preview request failed type=%s", type(error).__name__,
            )
            response = "农场服务异常，请查看服务器日志。"
        await MessageUtils.build_message(response).send(reply_to=True)
    return handle


for command, action in COMMANDS.items():
    matcher = on_command(command, priority=5, block=True)
    matcher.handle()(handler_for(action))
