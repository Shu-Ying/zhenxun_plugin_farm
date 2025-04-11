from nonebot.adapters import Event, MessageTemplate
from nonebot.rule import to_me
from nonebot.typing import T_State
from nonebot_plugin_alconna import (Alconna, AlconnaQuery, Args, Arparma, At,
                                    Match, MultiVar, Option, Query, Subcommand,
                                    on_alconna, store_true)
from nonebot_plugin_uninfo import Uninfo
from nonebot_plugin_waiter import waiter

from zhenxun.services.log import logger
from zhenxun.utils.message import MessageUtils

from .database import g_pSqlManager
from .farm.farm import g_pFarmManager
from .farm.shop import g_pShopManager


async def isRegisteredByUid(uid: str) -> bool:
    point = await g_pSqlManager.getUserPointByUid(uid)

    if point < 0:
        await MessageUtils.build_message("尚未开通农场，快at我发送 开通农场 开通吧").send()
        return False

    return True


diuse_register = on_alconna(
    Alconna("开通农场"),
    priority=5,
    rule=to_me(),
    block=True,
)

@diuse_register.handle()
async def _(session: Uninfo):
    uid = str(session.user.id)

    user = await g_pSqlManager.getUserInfoByUid(uid)

    if user:
        await MessageUtils.build_message("你已经有啦").send(reply_to=True)
    else:
        aaa = await g_pSqlManager.initUserInfoByUid(uid, str(session.user.name), 0, 100)

        await MessageUtils.build_message(str(aaa)).send(reply_to=True)

diuse_farm = on_alconna(
    Alconna(
        "我的农场",
        Option("--all", action=store_true),
        Subcommand("my-point", help_text="我的农场币"),
        Subcommand("seed-shop", Args["num?", int], help_text="种子商店"),
        Subcommand("buy-seed", Args["name?", str]["num?", int], help_text="购买种子"),
        Subcommand("my-seed", help_text="我的种子"),
        Subcommand("sowing", Args["name?", str]["num?", int], help_text="播种"),
        Subcommand("harvest", help_text="收获"),
        Subcommand("eradicate", help_text="铲除"),
        Subcommand("my-plant", help_text="我的作物"),
        # Subcommand("reclamation", Args["isBool?", str], help_text="开垦"),
        Subcommand("sell-plant", Args["name?", str]["num?", int], help_text="出售作物"),
        Subcommand("stealing", Args["target?", At], help_text="偷菜"),
        Subcommand("buy-point", Args["num?", int], help_text="购买农场币"),
        #Subcommand("sell-point", Args["num?", int], help_text="转换金币")
    ),
    priority=5,
    block=True,
)

@diuse_farm.assign("$main")
async def _(session: Uninfo):
    uid = str(session.user.id)

    if await isRegisteredByUid(uid) == False:
        return

    image = await g_pFarmManager.drawFarmByUid(uid)
    await MessageUtils.build_message(image).send(reply_to=True)

diuse_farm.shortcut(
    "我的农场币",
    command="我的农场",
    arguments=["my-point"],
    prefix=True,
)

@diuse_farm.assign("my-point")
async def _(session: Uninfo):
    uid = str(session.user.id)
    point = await g_pSqlManager.getUserPointByUid(uid)

    if point < 0:
        await MessageUtils.build_message("尚未开通农场，快at我发送 开通农场 开通吧").send()
        return False

    await MessageUtils.build_message(f"你的当前农场币为: {point}").send(reply_to=True)

diuse_farm.shortcut(
    "种子商店(.*?)",
    command="我的农场",
    arguments=["seed-shop"],
    prefix=True,
)

@diuse_farm.assign("seed-shop")
async def _(session: Uninfo, num: Query[int] = AlconnaQuery("num", 0)):
    uid = str(session.user.id)

    if await isRegisteredByUid(uid) == False:
        return

    image = await g_pShopManager.getSeedShopImage(num.result)
    await MessageUtils.build_message(image).send()

diuse_farm.shortcut(
    "购买种子(?P<name>.*?)",
    command="我的农场",
    arguments=["buy-seed", "{name}"],
    prefix=True,
)

@diuse_farm.assign("buy-seed")
async def _(session: Uninfo, name: Match[str], num: Query[int] = AlconnaQuery("num", 1),):
    if not name.available:
        await MessageUtils.build_message(
            "请在指令后跟需要购买的种子名称"
        ).finish(reply_to=True)

    uid = str(session.user.id)

    if await isRegisteredByUid(uid) == False:
        return

    result = await g_pShopManager.buySeed(uid, name.result, num.result)
    await MessageUtils.build_message(result).send(reply_to=True)

diuse_farm.shortcut(
    "我的种子",
    command="我的农场",
    arguments=["my-seed"],
    prefix=True,
)

@diuse_farm.assign("my-seed")
async def _(session: Uninfo):
    uid = str(session.user.id)

    if await isRegisteredByUid(uid) == False:
        return

    result = await g_pFarmManager.getUserSeedByUid(uid)
    await MessageUtils.build_message(result).send(reply_to=True)

diuse_farm.shortcut(
    "播种(?P<name>.*?)",
    command="我的农场",
    arguments=["sowing", "{name}"],
    prefix=True,
)

@diuse_farm.assign("sowing")
async def _(session: Uninfo, name: Match[str], num: Query[int] = AlconnaQuery("num", -1),):
    if not name.available:
        await MessageUtils.build_message(
            "请在指令后跟需要播种的种子名称"
        ).finish(reply_to=True)

    uid = str(session.user.id)

    if await isRegisteredByUid(uid) == False:
        return

    result = await g_pFarmManager.sowing(uid, name.result, num.result)
    await MessageUtils.build_message(result).send(reply_to=True)


diuse_farm.shortcut(
    "收获",
    command="我的农场",
    arguments=["harvest"],
    prefix=True,
)

@diuse_farm.assign("harvest")
async def _(session: Uninfo):
    uid = str(session.user.id)

    if await isRegisteredByUid(uid) == False:
        return

    result = await g_pFarmManager.harvest(uid)
    await MessageUtils.build_message(result).send(reply_to=True)

diuse_farm.shortcut(
    "铲除",
    command="我的农场",
    arguments=["eradicate"],
    prefix=True,
)

@diuse_farm.assign("eradicate")
async def _(session: Uninfo):
    uid = str(session.user.id)

    if await isRegisteredByUid(uid) == False:
        return

    result = await g_pFarmManager.eradicate(uid)
    await MessageUtils.build_message(result).send(reply_to=True)


diuse_farm.shortcut(
    "我的作物",
    command="我的农场",
    arguments=["my-plant"],
    prefix=True,
)

@diuse_farm.assign("my-plant")
async def _(session: Uninfo):
    uid = str(session.user.id)

    if await isRegisteredByUid(uid) == False:
        return

    result = await g_pFarmManager.getUserPlantByUid(uid)
    await MessageUtils.build_message(result).send(reply_to=True)


reclamation = on_alconna(
    Alconna("开垦"),
    priority=5,
    block=True,
)

@reclamation.handle()
async def _(session: Uninfo):
    uid = str(session.user.id)

    if await isRegisteredByUid(uid) == False:
        return

    condition = await g_pFarmManager.reclamationCondition(uid)
    condition += "\n 回复是将执行开垦"
    await MessageUtils.build_message(condition).send(reply_to=True)

    @waiter(waits=["message"], keep_session=True)
    async def check(event: Event):
        return event.get_plaintext()

    resp = await check.wait(timeout=60)
    if resp is None:
        await MessageUtils.build_message("等待超时").send(reply_to=True)
        return
    if not resp == "是":
        return

    res = await g_pFarmManager.reclamation(uid)
    await MessageUtils.build_message(res).send(reply_to=True)

diuse_farm.shortcut(
    "出售作物(?P<name>.*?)",
    command="我的农场",
    arguments=["sell-plant", "{name}"],
    prefix=True,
)

@diuse_farm.assign("sell-plant")
async def _(session: Uninfo, name: Match[str], num: Query[int] = AlconnaQuery("num", 1),):
    if not name.available:
        await MessageUtils.build_message(
            "请在指令后跟需要出售的作物名称"
        ).finish(reply_to=True)

    uid = str(session.user.id)

    if await isRegisteredByUid(uid) == False:
        return

    result = await g_pShopManager.sellPlantByUid(uid, name.result, num.result)
    await MessageUtils.build_message(result).send(reply_to=True)

diuse_farm.shortcut(
    "偷菜",
    command="我的农场",
    arguments=["stealing"],
    prefix=True,
)

@diuse_farm.assign("stealing")
async def _(session: Uninfo, target: Match[At]):
    uid = str(session.user.id)

    if await isRegisteredByUid(uid) == False:
        return

    if not target.available:
        await MessageUtils.build_message("请在指令后跟需要at的人").finish(reply_to=True)

    tar = target.result
    point = await g_pSqlManager.getUserPointByUid(tar.target)

    if point < 0:
        await MessageUtils.build_message("目标尚未开通农场，快邀请ta开通吧").send()
        return None

    result = await g_pFarmManager.stealing(uid, tar.target)
    await MessageUtils.build_message(result).send(reply_to=True)

diuse_farm.shortcut(
    "购买农场币(.*?)",
    command="我的农场",
    arguments=["buy-point"],
    prefix=True,
)

@diuse_farm.assign("buy-point")
async def _(session: Uninfo, num: Query[int] = AlconnaQuery("num", 0)):
    if num.result <= 0:
        await MessageUtils.build_message(
            "请在指令后跟需要购买农场币的数量"
        ).finish(reply_to=True)

    uid = str(session.user.id)

    if await isRegisteredByUid(uid) == False:
        return

    result = await g_pFarmManager.buyPointByUid(uid, num.result)
    await MessageUtils.build_message(result).send(reply_to=True)
