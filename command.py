import inspect

from nonebot.adapters import Event
from nonebot.rule import to_me
from nonebot_plugin_alconna import (
    Alconna,
    AlconnaQuery,
    Args,
    At,
    Match,
    MultiVar,
    Option,
    Query,
    Subcommand,
    on_alconna,
    store_true,
)
from nonebot_plugin_uninfo import Uninfo
from nonebot_plugin_waiter import waiter

from zhenxun.configs.config import BotConfig
from zhenxun.configs.path_config import DATA_PATH
from zhenxun.services.log import logger
from zhenxun.utils._build_image import BuildImage
from zhenxun.utils.message import MessageUtils

from .core.activity.sign_in import g_pSignInManager
from .core.dbService import g_pDBService
from .core.farm import g_pFarmManager
from .core.shop import g_pShopManager
from .utils.config import g_bSignStatus, g_sTranslation
from .utils.tool import g_pToolManager

diuse_register = on_alconna(
    Alconna("开通农场"),
    priority=5,
    rule=to_me(),
    block=True,
    use_cmd_start=True,
)


@diuse_register.handle()
async def handle_register(session: Uninfo):
    uid = str(session.user.id)
    player = await g_pToolManager.getPlayerByUid(uid)
    if player is not None and await player.isRegistered():
        await MessageUtils.build_message(g_sTranslation["register"]["repeat"]).send(
            reply_to=True
        )
        return

    try:
        raw_name = str(session.user.name)
        safe_name = g_pToolManager.sanitize_username(raw_name)

        success = await g_pDBService.user.initUserInfo(uid, safe_name)

        logger.info(f"用户 {uid} 选择的农场名称为: {raw_name} | 过滤后为: {safe_name}")

        msg = (
            g_sTranslation["register"]["success"].format(point=500)
            if success
            else g_sTranslation["register"]["error"]
        )
        logger.info(f"用户注册 {'成功' if success else '失败'}：{uid}")

    except Exception as e:
        msg = g_sTranslation["register"]["error"]
        logger.error(f"注册异常 | UID:{uid} | 错误：{e}")

    await MessageUtils.build_message(msg).send(reply_to=True)


diuse_farm = on_alconna(
    Alconna(
        "我的农场",
        Option("--all", action=store_true),
        Subcommand("detail", help_text="农场详述"),
        Subcommand("my-point", help_text="我的农场币"),
        Subcommand("seed-shop", Args["res?", MultiVar(str)], help_text="种子商店"),
        Subcommand("buy-seed", Args["name?", str]["num?", int], help_text="购买种子"),
        Subcommand("my-seed", help_text="我的种子"),
        Subcommand("sowing", Args["name?", str]["num?", int], help_text="播种"),
        Subcommand("harvest", help_text="收获"),
        Subcommand("eradicate", help_text="铲除"),
        Subcommand("my-plant", help_text="我的作物"),
        Subcommand("lock-plant", Args["name?", str], help_text="作物加锁"),
        Subcommand("unlock-plant", Args["name?", str], help_text="作物解锁"),
        Subcommand("sell-plant", Args["name?", str]["num?", int], help_text="出售作物"),
        Subcommand("stealing", Args["target?", At], help_text="偷菜"),
        Subcommand("buy-point", Args["num?", int], help_text="购买农场币"),
        # Subcommand("sell-point", Args["num?", int], help_text="转换金币")
        Subcommand("change-name", Args["name?", str], help_text="更改农场名"),
        Subcommand("sign-in", help_text="农场签到"),
        Subcommand("admin-up", Args["num?", int], help_text="农场下阶段"),
        Subcommand("point-to-vipPoint", Args["num?", int], help_text="点券兑换"),
        Subcommand("my-vipPoint", help_text="我的点券"),
        Subcommand("farm-help", help_text="农场帮助"),
        Subcommand("vipSeed-shop", Args["res?", MultiVar(str)], help_text="种子商店"),
    ),
    priority=5,
    block=True,
    use_cmd_start=True,
)


@diuse_farm.assign("$main")
async def _(session: Uninfo):
    uid = str(session.user.id)
    player = await g_pToolManager.getPlayerByUid(uid)
    if player is None or not await player.isRegistered():
        await g_pToolManager.repeat()
        return

    image = await g_pFarmManager.drawFarmByUid(uid)
    await MessageUtils.build_message(image).send(reply_to=True)


diuse_farm.shortcut(
    "农场详述",
    command="我的农场",
    arguments=["detail"],
    prefix=True,
)


@diuse_farm.assign("detail")
async def _(session: Uninfo):
    uid = str(session.user.id)
    player = await g_pToolManager.getPlayerByUid(uid)
    if player is None or not await player.isRegistered():
        await g_pToolManager.repeat()
        return

    info = await g_pFarmManager.drawDetailFarmByUid(uid)

    await MessageUtils.alc_forward_msg(
        [info], session.self_id, BotConfig.self_nickname
    ).send()


diuse_farm.shortcut(
    "我的农场币",
    command="我的农场",
    arguments=["my-point"],
    prefix=True,
)


@diuse_farm.assign("my-point")
async def _(session: Uninfo):
    uid = str(session.user.id)
    player = await g_pToolManager.getPlayerByUid(uid)
    if player is None or not await player.isRegistered():
        await g_pToolManager.repeat()
        return

    point = player.user["point"]

    if point < 0:
        await MessageUtils.build_message(g_sTranslation["basic"]["notFarm"]).send()
        return False

    await MessageUtils.build_message(
        g_sTranslation["basic"]["point"].format(point=point)
    ).send(reply_to=True)


diuse_farm.shortcut(
    "种子商店(.*?)",
    command="我的农场",
    arguments=["seed-shop"],
    prefix=True,
)


@diuse_farm.assign("seed-shop")
async def _(session: Uninfo, res: Match[tuple[str, ...]]):
    uid = str(session.user.id)
    player = await g_pToolManager.getPlayerByUid(uid)

    if player is None or not await player.isRegistered():
        await g_pToolManager.repeat()
        return

    if res.result is inspect._empty:
        raw = []
    else:
        raw = res.result

    filterKey: str | int | None = None
    page: int = 1

    if len(raw) >= 1 and raw[0] is not None:
        first = raw[0]
        if isinstance(first, str) and first.isdigit():
            page = int(first)
        else:
            filterKey = first

    if (
        len(raw) >= 2
        and raw[1] is not None
        and isinstance(raw[1], str)
        and raw[1].isdigit()
    ):
        page = int(raw[1])

    if filterKey is None:
        image = await g_pShopManager.getSeedShopImage(page, 0, 0)
    else:
        image = await g_pShopManager.getSeedShopImage(filterKey, page, 0)

    await MessageUtils.build_message(image).send()


diuse_farm.shortcut(
    "购买种子(?P<name>.*?)",
    command="我的农场",
    arguments=["buy-seed", "{name}"],
    prefix=True,
)


@diuse_farm.assign("buy-seed")
async def _(
    session: Uninfo, name: Match[str], num: Query[int] = AlconnaQuery("num", 1)
):
    if not name.available:
        await MessageUtils.build_message(g_sTranslation["buySeed"]["notSeed"]).finish(
            reply_to=True
        )

    uid = str(session.user.id)
    player = await g_pToolManager.getPlayerByUid(uid)
    if player is None or not await player.isRegistered():
        await g_pToolManager.repeat()
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
    player = await g_pToolManager.getPlayerByUid(uid)
    if player is None or not await player.isRegistered():
        await g_pToolManager.repeat()
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
async def _(
    session: Uninfo, name: Match[str], num: Query[int] = AlconnaQuery("num", -1)
):
    if not name.available:
        await MessageUtils.build_message(g_sTranslation["sowing"]["notSeed"]).finish(
            reply_to=True
        )

    uid = str(session.user.id)
    player = await g_pToolManager.getPlayerByUid(uid)
    if player is None or not await player.isRegistered():
        await g_pToolManager.repeat()
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
    player = await g_pToolManager.getPlayerByUid(uid)
    if player is None or not await player.isRegistered():
        await g_pToolManager.repeat()
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
    player = await g_pToolManager.getPlayerByUid(uid)
    if player is None or not await player.isRegistered():
        await g_pToolManager.repeat()
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
    player = await g_pToolManager.getPlayerByUid(uid)
    if player is None or not await player.isRegistered():
        await g_pToolManager.repeat()
        return

    result = await g_pFarmManager.getUserPlantByUid(uid)
    await MessageUtils.build_message(result).send(reply_to=True)


diuse_farm.shortcut(
    "作物加锁(?P<name>)",
    command="我的农场",
    arguments=["lock-plant", "{name}"],
    prefix=True,
)


@diuse_farm.assign("lock-plant")
async def _(session: Uninfo, name: Match[str]):
    uid = str(session.user.id)
    player = await g_pToolManager.getPlayerByUid(uid)
    if player is None or not await player.isRegistered():
        await g_pToolManager.repeat()
        return

    result = await g_pFarmManager.lockUserPlantByUid(uid, name.result, 1)
    await MessageUtils.build_message(result).send(reply_to=True)


diuse_farm.shortcut(
    "作物解锁(?P<name>)",
    command="我的农场",
    arguments=["unlock-plant", "{name}"],
    prefix=True,
)


@diuse_farm.assign("unlock-plant")
async def _(session: Uninfo, name: Match[str]):
    uid = str(session.user.id)
    player = await g_pToolManager.getPlayerByUid(uid)
    if player is None or not await player.isRegistered():
        await g_pToolManager.repeat()
        return

    result = await g_pFarmManager.lockUserPlantByUid(uid, name.result, 0)
    await MessageUtils.build_message(result).send(reply_to=True)


diuse_farm.shortcut(
    "出售作物(?P<name>.*?)",
    command="我的农场",
    arguments=["sell-plant", "{name}"],
    prefix=True,
)


@diuse_farm.assign("sell-plant")
async def _(
    session: Uninfo, name: Match[str], num: Query[int] = AlconnaQuery("num", -1)
):
    uid = str(session.user.id)
    player = await g_pToolManager.getPlayerByUid(uid)
    if player is None or not await player.isRegistered():
        await g_pToolManager.repeat()
        return

    result = await g_pShopManager.sellPlantByUid(uid, name.result, num.result)
    await MessageUtils.build_message(result).send(reply_to=True)


reclamation = on_alconna(
    Alconna("开垦"),
    priority=5,
    block=True,
    use_cmd_start=True,
)


@reclamation.handle()
async def _(session: Uninfo):
    uid = str(session.user.id)
    player = await g_pToolManager.getPlayerByUid(uid)
    if player is None or not await player.isRegistered():
        await g_pToolManager.repeat()
        return

    condition = await g_pFarmManager.reclamationCondition(uid)
    condition += f"\n{g_sTranslation['reclamation']['confirm']}"
    await MessageUtils.build_message(condition).send(reply_to=True)

    @waiter(waits=["message"], keep_session=True)
    async def check(event: Event):
        return event.get_plaintext()

    resp = await check.wait(timeout=60)
    if resp is None:
        await MessageUtils.build_message(g_sTranslation["reclamation"]["timeOut"]).send(
            reply_to=True
        )
        return
    if not resp == "是":
        return

    res = await g_pFarmManager.reclamation(uid)
    await MessageUtils.build_message(res).send(reply_to=True)


diuse_farm.shortcut(
    "偷菜",
    command="我的农场",
    arguments=["stealing"],
    prefix=True,
)


@diuse_farm.assign("stealing")
async def _(session: Uninfo, target: Match[At]):
    uid = str(session.user.id)
    player = await g_pToolManager.getPlayerByUid(uid)
    if player is None or not await player.isRegistered():
        await g_pToolManager.repeat()
        return

    if not target.available:
        await MessageUtils.build_message(g_sTranslation["stealing"]["noTarget"]).finish(
            reply_to=True
        )

    tar = target.result
    result = await g_pDBService.user.isRegistered(tar.target)

    if not result:
        await MessageUtils.build_message(
            g_sTranslation["stealing"]["targetNotFarm"]
        ).send()
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
        await MessageUtils.build_message("请在指令后跟需要购买农场币的数量").finish(
            reply_to=True
        )

    uid = str(session.user.id)
    player = await g_pToolManager.getPlayerByUid(uid)
    if player is None or not await player.isRegistered():
        await g_pToolManager.repeat()
        return

    result = await g_pFarmManager.buyPointByUid(uid, num.result)
    await MessageUtils.build_message(result).send(reply_to=True)


diuse_farm.shortcut(
    "更改农场名(?P<name>)",
    command="我的农场",
    arguments=["change-name", "{name}"],
    prefix=True,
)


@diuse_farm.assign("change-name")
async def _(session: Uninfo, name: Match[str]):
    if not name.available:
        await MessageUtils.build_message(g_sTranslation["changeName"]["noName"]).finish(
            reply_to=True
        )

    uid = str(session.user.id)
    player = await g_pToolManager.getPlayerByUid(uid)
    if player is None or not await player.isRegistered():
        await g_pToolManager.repeat()
        return

    player = await g_pToolManager.getPlayerByUid(uid)
    if player is None:
        await MessageUtils.build_message(g_sTranslation["changeName"]["error1"]).send(
            reply_to=True
        )
        return

    result = await player.updateName(name.result)
    await MessageUtils.build_message(g_sTranslation["changeName"][result]).send(
        reply_to=True
    )


diuse_farm.shortcut(
    "农场签到",
    command="我的农场",
    arguments=["sign-in"],
    prefix=True,
)


@diuse_farm.assign("sign-in")
async def _(session: Uninfo):
    uid = str(session.user.id)
    player = await g_pToolManager.getPlayerByUid(uid)
    if player is None or not await player.isRegistered():
        await g_pToolManager.repeat()
        return

    # 判断签到是否正常加载
    if not g_bSignStatus:
        await MessageUtils.build_message(g_sTranslation["signIn"]["error"]).send()
        return

    message = await g_pSignInManager.signInByUid(uid)
    await MessageUtils.build_message(message).send()


soil_upgrade = on_alconna(
    Alconna("土地升级", Args["index", int]),
    priority=5,
    block=True,
    use_cmd_start=True,
)


@soil_upgrade.handle()
async def _(session: Uninfo, index: Query[int] = AlconnaQuery("index", 1)):
    uid = str(session.user.id)
    player = await g_pToolManager.getPlayerByUid(uid)
    if player is None or not await player.isRegistered():
        await g_pToolManager.repeat()
        return

    condition = await g_pFarmManager.soilUpgradeCondition(uid, index.result)

    await MessageUtils.build_message(condition).send(reply_to=True)

    if not condition.startswith("将土地升级至："):
        return

    @waiter(waits=["message"], keep_session=True)
    async def check(event: Event):
        return event.get_plaintext()

    resp = await check.wait(timeout=60)
    if resp is None:
        await MessageUtils.build_message(g_sTranslation["soilInfo"]["timeOut"]).send(
            reply_to=True
        )
        return
    if not resp == "是":
        return

    res = await g_pFarmManager.soilUpgrade(uid, index.result)
    await MessageUtils.build_message(res).send(reply_to=True)


diuse_farm.shortcut(
    "农场下阶段(.*?)",
    command="我的农场",
    arguments=["admin-up"],
    prefix=True,
)


@diuse_farm.assign("admin-up")
async def _(session: Uninfo, num: Query[int] = AlconnaQuery("num", 0)):
    uid = str(session.user.id)
    player = await g_pToolManager.getPlayerByUid(uid)
    if player is None or not await player.isRegistered():
        await g_pToolManager.repeat()
        return

    await g_pDBService.userSoil.nextPhase(uid, num.result)


diuse_farm.shortcut(
    "点券兑换(.*?)",
    command="我的农场",
    arguments=["point-to-vipPoint"],
    prefix=True,
)


@diuse_farm.assign("point-to-vipPoint")
async def _(session: Uninfo, num: Query[int] = AlconnaQuery("num", 0)):
    if num.result <= 0:
        await MessageUtils.build_message("请在指令后跟需要购买点券的数量").finish(
            reply_to=True
        )

    uid = str(session.user.id)
    player = await g_pToolManager.getPlayerByUid(uid)
    if player is None or not await player.isRegistered():
        await g_pToolManager.repeat()
        return

    result = await g_pFarmManager.pointToVipPointByUid(uid, num.result)
    await MessageUtils.build_message(result).send(reply_to=True)


diuse_farm.shortcut(
    "我的点券",
    command="我的农场",
    arguments=["my-vipPoint"],
    prefix=True,
)


@diuse_farm.assign("my-vipPoint")
async def _(session: Uninfo):
    uid = str(session.user.id)
    player = await g_pToolManager.getPlayerByUid(uid)
    if player is None or not await player.isRegistered():
        await g_pToolManager.repeat()
        return

    await MessageUtils.build_message(
        g_sTranslation["basic"]["vipPoint"].format(vipPoint=player.user["vipPoint"])
    ).send(reply_to=True)


diuse_farm.shortcut(
    "农场帮助",
    command="我的农场",
    arguments=["farm-help"],
    prefix=True,
)


@diuse_farm.assign("farm-help")
async def _(session: Uninfo):
    savePath = DATA_PATH / "farm_res/html/help.png"

    image = BuildImage(background=savePath)

    await MessageUtils.build_message(image).send(reply_to=True)


diuse_farm.shortcut(
    "点券商店(.*?)",
    command="我的农场",
    arguments=["vipSeed-shop"],
    prefix=True,
)


@diuse_farm.assign("vipSeed-shop")
async def _(session: Uninfo, res: Match[tuple[str, ...]]):
    uid = str(session.user.id)
    player = await g_pToolManager.getPlayerByUid(uid)
    if player is None or not await player.isRegistered():
        await g_pToolManager.repeat()
        return

    if res.result is inspect._empty:
        raw = []
    else:
        raw = res.result

    filterKey: str | int | None = None
    page: int = 1

    if len(raw) >= 1 and raw[0] is not None:
        first = raw[0]
        if isinstance(first, str) and first.isdigit():
            page = int(first)
        else:
            filterKey = first

    if (
        len(raw) >= 2
        and raw[1] is not None
        and isinstance(raw[1], str)
        and raw[1].isdigit()
    ):
        page = int(raw[1])

    if filterKey is None:
        image = await g_pShopManager.getSeedShopImage(page, 0, 1)
    else:
        image = await g_pShopManager.getSeedShopImage(filterKey, page, 1)

    await MessageUtils.build_message(image).send()
