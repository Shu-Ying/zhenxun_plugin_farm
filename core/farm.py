import math
import random
import re

from zhenxun.configs.config import Config
from zhenxun.models.user_console import UserConsole
from zhenxun.services.log import logger
from zhenxun.utils.enum import GoldHandle
from zhenxun.utils.image_utils import ImageTemplate

from ..core.dbService import g_pDBService
from ..event import g_pEventManager
from ..utils import config, getJsonManager, getToolManager


class CFarmManager:
    @classmethod
    async def buyPointByUid(cls, uid: str, num: int) -> str:
        if num <= 0:
            return "你是怎么做到购买不是正数的农场币的"

        user = await UserConsole.get_user(uid)

        pro = float(Config.get_config("zhenxun_plugin_farm", "兑换倍数"))
        tax = float(Config.get_config("zhenxun_plugin_farm", "手续费"))

        # 计算手续费
        fee = math.floor(num * tax)
        # 实际扣费金额
        deduction = num + fee

        if user.gold < deduction:
            return f"你的金币不足或不足承担手续费。当前手续费为{fee}"

        await UserConsole.reduce_gold(
            uid,
            num,
            GoldHandle.PLUGIN,  # type: ignore
            "zhenxun_plugin_farm",
        )
        await UserConsole.reduce_gold(
            uid,
            fee,
            GoldHandle.PLUGIN,  # type: ignore
            "zhenxun_plugin_farm",
        )

        point = num * pro
        player = await getToolManager().getPlayerByUid(uid)
        if not player:
            return config.g_sTranslation["basic"]["error"]

        await player.addPoint("point", int(point))

        return f"充值{point}农场币成功，手续费{tax}金币，当前农场币：{player.user.get('point', 0)}"

    @classmethod
    async def getUserSeedByUid(cls, uid: str) -> bytes:
        """获取用户种子仓库"""
        dataList = []
        columnNames = [
            "-",
            "种子名称",
            "数量",
            "收获经验",
            "收获数量",
            "成熟时间（小时）",
            "收获次数",
            "是否可以上架交易行",
        ]

        # 从数据库获取结构化数据
        seedRecords = await g_pDBService.userSeed.getUserSeedByUid(uid) or {}

        if not seedRecords:
            result = await ImageTemplate.table_page(
                "种子仓库",
                "播种示例：@小真寻 播种 大白菜 [数量]",
                columnNames,
                dataList,
            )
            return result.pic2bytes()

        for seedName, count in seedRecords.items():
            try:
                plantInfo = await g_pDBService.plant.getPlantByName(seedName)
                if not plantInfo:
                    continue

                iconPath = config.g_sResourcePath / f"plant/{seedName}/icon.png"
                icon = (iconPath, 33, 33) if iconPath.exists() else ""
                sellable = "可以" if plantInfo["sell"] else "不可以"

                dataList.append(
                    [
                        icon,
                        seedName,
                        count,
                        plantInfo["experience"],
                        plantInfo["harvest"],
                        plantInfo["time"],
                        plantInfo["crop"],
                        sellable,
                    ]
                )
            except KeyError:
                continue

        result = await ImageTemplate.table_page(
            "种子仓库",
            "播种示例：@小真寻 播种 大白菜 [数量]",
            columnNames,
            dataList,
        )
        return result.pic2bytes()

    @classmethod
    async def sowing(cls, uid: str, name: str, num: int = -1) -> str:
        """播种

        Args:
            uid (str): 用户Uid
            name (str): 播种种子名称
            num (int, optional): 播种数量

        Returns:
            str: 返回结果
        """
        try:
            # 获取用户的种子数量
            count = await g_pDBService.userSeed.getUserSeedByName(uid, name)
            if count is None:
                count = 0  # 如果返回 None，则视为没有种子

            if count <= 0:
                return config.g_sTranslation["sowing"]["noSeed"].format(name=name)

            # 如果播种数量超过仓库种子数量
            if count < num and num != -1:
                return config.g_sTranslation["sowing"]["noNum"].format(
                    name=name, num=count
                )

            # 获取用户土地数量
            player = await getToolManager().getPlayerByUid(uid)
            if not player:
                return config.g_sTranslation["basic"]["error"]
            soilNumber = player.user.get("soil", 3)

            # 如果播种数量为 -1，表示播种所有可播种的土地
            if num == -1:
                num = count

            # 发送播种前信号
            await g_pEventManager.m_beforePlant.emit(uid=uid, name=name, num=num)  # type: ignore

            # 记录是否成功播种
            successCount = 0
            for i in range(1, soilNumber + 1):
                if count > 0 and num > 0:
                    success = await g_pDBService.userSoil.sowingByPlantName(
                        uid, i, name
                    )
                    if success:
                        # 更新种子数量
                        num -= 1
                        count -= 1

                        # 记录种子消耗数量
                        successCount += 1

                        # 发送播种后信号
                        await g_pEventManager.m_afterPlant.emit(  # type: ignore
                            uid=uid, name=name, soilIndex=i
                        )

            # 确保用户仓库数量更新
            if successCount > 0:
                await g_pDBService.userSeed.updateUserSeedByName(uid, name, count)

            # 根据播种结果给出反馈
            if num == 0:
                return config.g_sTranslation["sowing"]["success"].format(
                    name=name, num=count
                )
            else:
                return config.g_sTranslation["sowing"]["success2"].format(
                    name=name, num=count
                )

        except Exception as e:
            logger.warning("播种操作失败！", e=e)
            return config.g_sTranslation["sowing"]["error"]

    @classmethod
    async def harvest(cls, uid: str) -> str:
        """收获作物

        Args:
            uid (str): 用户Uid

        Returns:
            str: 返回
        """
        try:
            await g_pEventManager.m_beforeHarvest.emit(uid=uid)  # type: ignore

            player = await getToolManager().getPlayerByUid(uid)
            if not player:
                return config.g_sTranslation["basic"]["error"]
            soilNumber = player.user.get("soil", 3)

            harvestRecords = []  # 收获日志记录
            experience = 0  # 总经验值
            harvestCount = 0  # 成功收获数量

            for i in range(1, soilNumber + 1):
                soilInfo = await g_pDBService.userSoil.getUserSoil(uid, i)
                if not soilInfo:
                    continue

                # 如果没有种植
                if soilInfo.get("isSoilPlanted", 1) == 0:
                    continue

                level = soilInfo.get("soilLevel", 0)

                # 如果是枯萎状态
                if soilInfo.get("wiltStatus", 1) == 1:
                    continue

                plantInfo = await g_pDBService.plant.getPlantByName(
                    soilInfo["plantName"]
                )
                if not plantInfo:
                    continue

                currentTime = getToolManager().dateTime().now()
                matureTime = (
                    getToolManager()
                    .dateTime()
                    .fromtimestamp(int(soilInfo["matureTime"]))
                )

                if currentTime >= matureTime:
                    number = plantInfo["harvest"]

                    # 处理偷菜扣除数量
                    stealNum = await g_pDBService.userSteal.getTotalStolenCount(uid, i)
                    number -= stealNum

                    # 处理土地等级带来的数量增长 向下取整
                    percent = await g_pDBService.userSoil.getSoilLevelHarvestNumber(
                        level
                    )
                    number = math.floor(number * (100 + percent) // 100)

                    if number <= 0:
                        continue

                    harvestCount += 1
                    experience += plantInfo["experience"]

                    # 处理土地等级带来的经验增长 向下取整
                    percent = await g_pDBService.userSoil.getSoilLevelHarvestExp(level)
                    experience = math.floor(experience * (100 + percent) // 100)

                    harvestRecords.append(
                        config.g_sTranslation["harvest"]["append"].format(
                            name=soilInfo["plantName"],
                            num=number,
                            exp=plantInfo["experience"],
                        )
                    )

                    await g_pDBService.userPlant.addUserPlantByUid(
                        uid, soilInfo["plantName"], number
                    )

                    # 统计收获次数
                    try:
                        # 处理星级前缀（只在前两字为 一星/二星/三星/四星/五星 时去掉前缀）
                        plant_name = soilInfo["plantName"]
                        m = re.match(r"^(?:一星|二星|三星|四星|五星)", plant_name)
                        if m:
                            plant_name = plant_name[len(m.group(0)) :]

                        await g_pDBService.userPlantCount.addUserPlantCountByUid(
                            uid, plant_name
                        )
                    except Exception:
                        # 忽略统计异常，避免影响主流程
                        pass

                    # 如果到达收获次数上限
                    if soilInfo["harvestCount"] + 1 >= plantInfo["crop"]:
                        await g_pDBService.userSoil.updateUserSoil(
                            uid, i, "wiltStatus", 1
                        )
                    else:
                        phase = await g_pDBService.plant.getPlantPhaseByName(
                            soilInfo["plantName"]
                        )

                        ts, hc = (
                            int(currentTime.timestamp()),
                            soilInfo["harvestCount"] + 1,
                        )
                        p1, p2, *rest = phase

                        await g_pDBService.userSoil.updateUserSoilFields(
                            uid,
                            i,
                            {
                                "harvestCount": hc,
                                "plantTime": ts - p1 - p2,
                                "matureTime": ts + p2 + sum(rest),
                            },
                        )

                    await g_pEventManager.m_afterHarvest.emit(  # type: ignore
                        uid=uid, name=soilInfo["plantName"], num=number, soilIndex=i
                    )

            if experience > 0:
                exp = player.user.get("exp", 0)
                await player.addExp(exp + experience)
                harvestRecords.append(
                    config.g_sTranslation["harvest"]["exp"].format(
                        exp=experience,
                    )
                )

            if harvestCount <= 0:
                return config.g_sTranslation["harvest"]["no"]
            else:
                return "\n".join(harvestRecords)

        except Exception as e:
            logger.warning("收获操作失败！", e=e)
            return config.g_sTranslation["harvest"]["error"]

    @classmethod
    async def eradicate(cls, uid: str) -> str:
        """铲除作物
        TODO 缺少随意铲除作物 目前只能铲除荒废作物
        Args:
            uid (str): 用户Uid

        Returns:
            str: 返回
        """
        player = await getToolManager().getPlayerByUid(uid)
        if not player:
            return config.g_sTranslation["basic"]["error"]
        soilNumber = player.user.get("soil", 3)

        await g_pEventManager.m_beforeEradicate.emit(uid=uid)  # type: ignore

        experience = 0
        for i in range(1, soilNumber + 1):
            soilInfo = await g_pDBService.userSoil.getUserSoil(uid, i)
            if not soilInfo:
                continue

            # 如果没有种植
            if soilInfo.get("isSoilPlanted", 1) == 0:
                continue

            # 如果不是枯萎状态
            if soilInfo.get("wiltStatus", 0) == 0:
                continue

            experience += 3

            if config.g_bIsDebug:
                experience += 999

            # 更新数据库操作
            await g_pDBService.userSoil.deleteUserSoil(uid, i)

            await g_pDBService.userSoil.updateUserSoilFields(
                uid,
                i,
                {
                    "plantName": "",
                    "plantTime": 0,
                    "matureTime": 0,
                    "wiltStatus": 0,
                    "isSoilPlanted": 0,
                },
            )

            # 铲除作物会将偷菜记录清空
            await g_pDBService.userSteal.deleteStealRecord(uid, i)

            await g_pEventManager.m_afterEradicate.emit(uid=uid, soilIndex=i)  # type: ignore

        if experience > 0:
            exp = player.user.get("exp", 0)
            await player.addExp(exp + experience)

            return config.g_sTranslation["eradicate"]["success"].format(exp=experience)
        else:
            return config.g_sTranslation["eradicate"]["error"]

    @classmethod
    async def getUserPlantByUid(cls, uid: str) -> bytes:
        """获取用户作物仓库

        Args:
            uid (str): 用户Uid

        Returns:
            bytes: 返回图片
        """
        data_list = []
        column_name = [
            "-",
            "作物名称",
            "数量",
            "单价",
            "总价",
            "是否上锁",
            "是否可以上架交易行",
        ]

        plant = await g_pDBService.userPlant.getUserPlantByUid(uid)

        if plant is None:
            result = await ImageTemplate.table_page(
                "作物仓库",
                "出售示例：@小真寻 出售作物 大白菜 [数量]",
                column_name,
                data_list,
            )
            return result.pic2bytes()

        sell = ""
        for name, count in plant.items():
            plantInfo = await g_pDBService.plant.getPlantByName(name)
            if not plantInfo:
                continue

            icon = ""
            icon_path = config.g_sResourcePath / f"plant/{name}/icon.png"
            if icon_path.exists():
                icon = (icon_path, 33, 33)

            if plantInfo["sell"]:
                sell = "可以"
            else:
                sell = "不可以"

            number = int(count) * plantInfo["price"]

            isLock = await g_pDBService.userPlant.checkPlantLockByName(uid, name)
            if isLock:
                lock = "上锁"
            else:
                lock = "未上锁"

            data_list.append(
                [icon, name, count, plantInfo["price"], number, lock, sell]
            )

        result = await ImageTemplate.table_page(
            "作物仓库",
            "出售示例：@小真寻 出售作物 大白菜 [数量]",
            column_name,
            data_list,
        )

        return result.pic2bytes()

    @classmethod
    async def lockUserPlantByUid(cls, uid: str, name: str, lock: int) -> str:
        """加/解 锁用户作物

        Args:
            uid (str): 用户uid
            name (str): 作物名称
            lock (int): 0=解锁 非0=加锁

        Returns:
            str: 返回
        """
        # 先判断该用户仓库是否有该作物
        if not await g_pDBService.userPlant.checkUserPlantByName(uid, name):
            return config.g_sTranslation["lockPlant"]["noPlant"]

        # 更改加锁状态
        if await g_pDBService.userPlant.lockUserPlantByName(uid, name, lock):
            if lock == 0:
                return config.g_sTranslation["lockPlant"]["unlockPlant"].format(
                    name=name
                )
            else:
                return config.g_sTranslation["lockPlant"]["lockPlant"].format(name=name)
        else:
            return config.g_sTranslation["lockPlant"]["error"]

    @classmethod
    async def stealing(cls, uid: str, target: str) -> str:
        """偷菜

        Args:
            uid (str): 用户Uid
            target (str): 被偷用户Uid

        Returns:
            str: 返回
        """
        # 用户信息
        player = await getToolManager().getPlayerByUid(uid)
        if not player:
            return config.g_sTranslation["basic"]["error"]

        stealTime = player.user.get("stealTime", "")
        stealCount = int(player.user["stealCount"])

        if stealTime == "" or not stealTime:
            stealTime = getToolManager().dateTime().date().today().strftime("%Y-%m-%d")
            stealCount = 5
        elif (
            getToolManager().dateTime().date().fromisoformat(stealTime)
            != getToolManager().dateTime().date().today()
        ):
            stealTime = getToolManager().dateTime().date().today().strftime("%Y-%m-%d")
            stealCount = 5

        if stealCount <= 0:
            return config.g_sTranslation["stealing"]["max"]

        # 获取用户解锁地块数量
        soilNumber = player.user.get("soil", 3)
        harvestRecords: list[str] = []
        isStealingNumber = 0
        isStealingPlant = 0

        for i in range(1, soilNumber + 1):
            soilInfo = await g_pDBService.userSoil.getUserSoil(target, i)
            if not soilInfo:
                continue

            # 如果没有种植
            if soilInfo.get("isSoilPlanted", 1) == 0:
                continue

            # 如果是枯萎状态
            if soilInfo.get("wiltStatus", 1) == 1:
                continue

            # 作物信息
            plantInfo = await g_pDBService.plant.getPlantByName(soilInfo["plantName"])
            if not plantInfo:
                continue

            currentTime = getToolManager().dateTime().now()
            matureTime = (
                getToolManager().dateTime().fromtimestamp(int(soilInfo["matureTime"]))
            )

            if currentTime >= matureTime:
                # 如果偷过，则跳过该土地
                if await g_pDBService.userSteal.hasStealed(target, i, uid):
                    isStealingNumber += 1
                    continue

                stealingNumber = plantInfo[
                    "harvest"
                ] - await g_pDBService.userSteal.getTotalStolenCount(target, i)
                randomNumber = random.choice([1, 2])
                randomNumber = min(randomNumber, stealingNumber)

                if randomNumber > 0:
                    await g_pDBService.userPlant.addUserPlantByUid(
                        uid, soilInfo["plantName"], randomNumber
                    )

                    harvestRecords.append(
                        config.g_sTranslation["stealing"]["info"].format(
                            name=soilInfo["plantName"], num=randomNumber
                        )
                    )

                    isStealingPlant += 1

                    # 如果将作物偷完，就直接更新状态 并记录用户偷取过
                    if plantInfo["harvest"] - randomNumber + stealingNumber == 0:
                        # 如果作物 是最后一阶段作物且偷完 则直接枯萎
                        if soilInfo["harvestCount"] + 1 >= plantInfo["crop"]:
                            await g_pDBService.userSoil.updateUserSoil(
                                target, i, "wiltStatus", 1
                            )
                        else:
                            phase = await g_pDBService.plant.getPlantPhaseByName(
                                soilInfo["plantName"]
                            )

                            ts, hc = (
                                int(currentTime.timestamp()),
                                soilInfo["harvestCount"] + 1,
                            )
                            p1, p2, *rest = phase

                            await g_pDBService.userSoil.updateUserSoilFields(
                                uid,
                                i,
                                {
                                    "harvestCount": hc,
                                    "plantTime": ts - p1 - p2,
                                    "matureTime": ts + p2 + sum(rest),
                                },
                            )

                            await g_pDBService.userSteal.addStealRecord(
                                target,
                                i,
                                uid,
                                randomNumber,
                                int(getToolManager().dateTime().now().timestamp()),
                            )

                    else:
                        await g_pDBService.userSteal.addStealRecord(
                            target,
                            i,
                            uid,
                            randomNumber,
                            int(getToolManager().dateTime().now().timestamp()),
                        )

        if isStealingPlant <= 0 and isStealingNumber <= 0:
            return config.g_sTranslation["stealing"]["noPlant"]
        elif isStealingPlant <= 0 and isStealingNumber > 0:
            return config.g_sTranslation["stealing"]["repeat"]
        else:
            stealCount -= 1

            await player.updateStealCountByUid(uid, stealTime, stealCount)

            return "\n".join(harvestRecords)

    @classmethod
    async def reclamationCondition(cls, uid: str) -> str:
        """获取开垦条件

        Args:
            uid (str): 用户Uid

        Returns:
            str: 返回条件文本信息
        """
        jLevel = await getJsonManager().getLevel()
        rec = jLevel["reclamation"]
        player = await getToolManager().getPlayerByUid(uid)
        if not player:
            return config.g_sTranslation["basic"]["error"]

        try:
            if player.user["soil"] >= 30:
                return config.g_sTranslation["reclamation"]["perfect"]

            rec = rec[f"{player.user['soil'] + 1}"]

            level = rec["level"]
            point = rec["point"]
            item = rec["item"]

            str = ""
            if len(item) == 0:
                str = config.g_sTranslation["reclamation"]["next"].format(
                    level=level, num=point
                )
            else:
                str = config.g_sTranslation["reclamation"]["next2"].format(
                    level=level, num=point, item=item
                )

            return str
        except Exception:
            return config.g_sTranslation["reclamation"]["error"]

    @classmethod
    async def reclamation(cls, uid: str) -> str:
        """开垦

        Args:
            uid (str): 用户Uid

        Returns:
            str: _description_
        """
        player = await getToolManager().getPlayerByUid(uid)
        if not player:
            return config.g_sTranslation["basic"]["error"]
        level = await player.getUserLevel()

        jsonLevel = await getJsonManager().getLevel()
        rec = jsonLevel["reclamation"]

        try:
            if player.user["soil"] >= 30:
                return config.g_sTranslation["reclamation"]["perfect"]

            rec = rec[f"{player.user['soil'] + 1}"]

            levelFileter = rec["level"]
            point = rec["point"]
            # item = rec["item"]

            if level[0] < levelFileter:
                return config.g_sTranslation["reclamation"]["nextLevel"].format(
                    level=level[0], next=levelFileter
                )

            if player.user["point"] < point:
                return config.g_sTranslation["reclamation"]["noNum"].format(num=point)

            # TODO 缺少判断消耗的item
            await player.subPoint("point", point)
            await player.updateField("soil", player.user["soil"] + 1)

            return config.g_sTranslation["reclamation"]["success"]
        except Exception:
            return config.g_sTranslation["reclamation"]["error1"]

    @classmethod
    async def soilUpgradeCondition(cls, uid: str, soilIndex: int) -> str:
        """获取土地升级条件

        Args:
            uid (str): 用户Uid
            soilIndex (str): 土地索引

        Returns:
            str: 返回土地升级条件
        """
        soilInfo = await g_pDBService.userSoil.getUserSoil(uid, soilIndex)

        if not soilInfo:
            return config.g_sTranslation["soilInfo"]["error"]

        soilLevel = soilInfo.get("soilLevel", 0) + 1
        if soilLevel >= config.g_iSoilLevelMax:
            return config.g_sTranslation["soilInfo"]["error1"]

        # 获取用户当前土地 的下一级土地 数量
        countSoil = await g_pDBService.userSoil.countSoilByLevel(uid, soilLevel)

        # 获取升级所需
        soilLevelText = await g_pDBService.userSoil.getSoilLevel(soilLevel)
        jSoil = await getJsonManager().getSoil()
        fileter = jSoil["upgrade"][soilLevelText][countSoil]

        nextLevel = await g_pDBService.userSoil.getSoilLevelText(soilLevel)

        lines = ["将土地升级至：" + nextLevel + "。", "所需："]
        fields = [
            ("level", "等级"),
            ("point", "金币"),
            ("vipPoint", "点券"),
        ]
        for key, label in fields:
            value = fileter.get(key, 0)
            if value > 0:
                lines.append(f"{label}：{value}")

        items = fileter.get("item", {})
        for name, qty in items.items():
            if qty:
                lines.append(f"{name}：{qty}")

        lines.append("回复“是”将执行升级")

        return "\n".join(lines)

    @classmethod
    async def soilUpgrade(cls, uid: str, soilIndex: int) -> str:
        """土地升级

        Args:
            uid (str): 用户Uid
            soilIndex (int): 土地索引

        Returns:
            str:
        """
        player = await getToolManager().getPlayerByUid(uid)
        if not player:
            return config.g_sTranslation["basic"]["error"]

        soilInfo = await g_pDBService.userSoil.getUserSoil(uid, soilIndex)
        if not soilInfo:
            return config.g_sTranslation["soilInfo"]["error"]

        soilLevel = soilInfo.get("soilLevel", 0) + 1
        if soilLevel >= config.g_iSoilLevelMax:
            return config.g_sTranslation["soilInfo"]["error1"]

        countSoil = await g_pDBService.userSoil.countSoilByLevel(uid, soilLevel)

        soilLevelText = await g_pDBService.userSoil.getSoilLevel(soilLevel)
        soil = await getJsonManager().getSoil()
        fileter = soil["upgrade"][soilLevelText][countSoil]

        getters = {
            "level": (await player.getUserLevel())[0],
            "point": player.user.get("point", 0),
            "vipPoint": player.user.get("vipPoint", 0),
        }

        requirements = {
            "level": "等级",
            "point": "金币",
            "vipPoint": "点券",
        }

        for key, val in getters.items():
            need = fileter.get(key, 0)
            if val < need:
                return f"你的{requirements[key]}不够哦~"

        # 缺少item判断

        # 更新数据库字段
        await g_pDBService.userSoil.updateUserSoil(
            uid, soilIndex, "soilLevel", soilLevel
        )

        # 如果有作物的话直接成熟
        await g_pDBService.userSoil.matureNow(uid, soilIndex)

        # 更新数据库字段
        await player.subPoint("point", fileter.get("point", 0))
        await player.subPoint("vipPoint", fileter.get("vipPoint", 0))

        return config.g_sTranslation["soilInfo"]["success"].format(
            name=await g_pDBService.userSoil.getSoilLevelText(soilLevel),
            text=config.g_sTranslation["soilInfo"][soilLevelText],
        )

    @classmethod
    async def pointToVipPointByUid(cls, uid: str, num: int) -> str:
        """点券兑换

        Args:
            uid (str): 用户Uid
            num (int): 兑换点券数量

        Returns:
            str: 返回结果
            兑换比例在配置文件中配置
            目前配置文件中默认是20倍
            100点券需要20000农场币
            赠送点券规则：
            小于2000点券：0
            2000-5000点券：100
            5000-50000点券：280
            大于50000点券：3000
        """
        if num < 100:
            return "点券兑换数量必须大于等于100"

        pro = int(Config.get_config("zhenxun_plugin_farm", "点券兑换倍数"))
        pro *= num

        player = await getToolManager().getPlayerByUid(uid)
        if not player:
            return config.g_sTranslation["basic"]["error"]

        point = player.user.get("point", 0)
        if point < pro:
            return f"你的农场币不足，当前农场币为{point}，兑换还需要{pro - point}农场币"

        giftPoints: int
        if num < 2000:
            giftPoints = 0
        elif num < 5000:
            giftPoints = 100
        elif num < 50000:
            giftPoints = 280
        else:
            giftPoints = 3000

        number = num + giftPoints
        await player.addPoint("vipPoint", number)
        await player.subPoint("point", pro)

        return f"兑换{num}点券成功，当前点券：{number}，赠送点券：{giftPoints}，当前农场币：{point}"
