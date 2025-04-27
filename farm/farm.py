import asyncio
import math
import random
from datetime import date, datetime
from io import StringIO
from typing import Dict, List, Tuple

from numpy import number

from zhenxun.configs.config import Config
from zhenxun.models.user_console import UserConsole
from zhenxun.services.log import logger
from zhenxun.utils._build_image import BuildImage
from zhenxun.utils.enum import GoldHandle
from zhenxun.utils.image_utils import ImageTemplate
from zhenxun.utils.platform import PlatformUtils

from ..config import g_pJsonManager, g_sResourcePath
from ..database import g_pSqlManager


class CFarmManager:
    @classmethod
    async def buyPointByUid(cls, uid: str, num: int) -> str:
        if num <= 0:
            return "你是怎么做到购买不是正数的农场币的"

        user = await UserConsole.get_user(uid)

        pro = float(Config.get_config("zhenxun_plugin_farm", "兑换倍数"))
        tax = float(Config.get_config("zhenxun_plugin_farm", "手续费"))

        #计算手续费
        fee = math.floor(num * tax)
        #实际扣费金额
        deduction = num + fee

        if user.gold < deduction:
            return f"你的金币不足或不足承担手续费。当前手续费为{fee}"

        await UserConsole.reduce_gold(uid, num, GoldHandle.PLUGIN , 'zhenxun_plugin_farm')
        await UserConsole.reduce_gold(uid, fee, GoldHandle.PLUGIN , 'zhenxun_plugin_farm')

        point = num * pro

        p = await g_pSqlManager.getUserPointByUid(uid)
        number = point + p

        await g_pSqlManager.updateUserPointByUid(uid, int(number))

        return f"充值{point}农场币成功，手续费{tax}金币，当前农场币：{number}"

    @classmethod
    async def drawFarmByUid(cls, uid: str, name: str) -> bytes:
        """绘制用户农场

        Args:
            uid (str): 用户UID

        Returns:
            bytes: 返回绘制结果
        """
        img = BuildImage(background = g_sResourcePath / "background/background.jpg")

        soilSize = g_pJsonManager.m_pSoil['size']

        #TODO 缺少判断用户土地资源状况
        soil = BuildImage(background = g_sResourcePath / "soil/普通土地.png")
        await soil.resize(0, soilSize[0], soilSize[1])

        grass = BuildImage(background = g_sResourcePath / "soil/草土地.png")
        await grass.resize(0, soilSize[0], soilSize[1])

        soilPos = g_pJsonManager.m_pSoil['soil']
        soilUnlock = await g_pSqlManager.getUserSoilByUid(uid)

        x = 0
        y = 0
        isFirstExpansion = True #首次添加扩建图片
        isFirstRipe = True
        plant = None
        for index in range(0, 30):
            x = soilPos[str(index + 1)]['x']
            y = soilPos[str(index + 1)]['y']

            #如果土地已经到达对应等级
            if index < soilUnlock:
                await img.paste(soil, (x, y))

                isPlant, plant, isRipe= await cls.drawSoilPlant(uid, f"soil{str(index + 1)}")

                if isPlant:
                    await img.paste(plant, (x + soilSize[0] // 2 - plant.width // 2,
                                            y + soilSize[1] // 2 - plant.height // 2))

                #1700 275
                #首次添加可收获图片
                if isRipe and isFirstRipe:
                    ripe = BuildImage(background = g_sResourcePath / "background/ripe.png")

                    await img.paste(ripe, (x + soilSize[0] // 2 - ripe.width // 2,
                                           y - ripe.height // 2))

                    isFirstRipe = False
            else:
                await img.paste(grass, (x, y))

                if isFirstExpansion:
                    isFirstExpansion = False

                    #首次添加扩建图片
                    expansion = BuildImage(background = g_sResourcePath / "background/expansion.png")
                    await expansion.resize(0, 69, 69)
                    await img.paste(expansion, (x + soilSize[0] // 2 - expansion.width // 2,
                                                y + soilSize[1] // 2 - expansion.height))

        #左上角绘制用户信息
        #头像
        image = await PlatformUtils.get_user_avatar(uid, "qq")

        if image:
            avatar = BuildImage(background = image)

            await img.paste(avatar, (125, 85))

        #头像框
        frame = BuildImage(background = g_sResourcePath / "background/frame.png")
        await img.paste(frame, (75, 44))

        #用户名
        nameImg = await BuildImage.build_text_image(name, size = 24, font_color = (77, 35, 4))
        await img.paste(nameImg, (300, 92))

        #经验值
        level = await g_pSqlManager.getUserLevelByUid(uid)

        beginX = 309
        endX = 627
        #绘制宽度计算公式为 (当前经验值 / 经验值上限) * 宽度
        width = int((level[2] / level[1]) * (endX - beginX))
        await img.rectangle((beginX, 188, beginX + width, 222), (171, 194, 41))

        expImg = await BuildImage.build_text_image(f"{level[2]} / {level[1]}", size = 24, font_color = (102, 120, 19))
        await img.paste(expImg, (390, 193))

        #等级
        levelImg = await BuildImage.build_text_image(str(level[0]), size = 32, font_color = (214, 111, 1))
        await img.paste(levelImg, (660, 187))

        #金币
        point = await g_pSqlManager.getUserPointByUid(uid)
        pointImg = await BuildImage.build_text_image(str(point), size = 24, font_color = (253, 253, 253))
        await img.paste(pointImg, (330, 255))

        #点券
        bonds = await g_pSqlManager.getUserPointByUid(uid)
        bondsImg = await BuildImage.build_text_image("0", size = 24, font_color = (253, 253, 253))
        await img.paste(bondsImg, (570, 255))

        #清晰度
        definition = Config.get_config("zhenxun_plugin_farm", "绘制农场清晰度")
        if definition == "medium":
            await img.resize(0.6)
        elif definition == "hight":
            await img.resize(0.8)
        elif definition == "original":
            pass
        else:
            await img.resize(0.4)

        return img.pic2bytes()

    @classmethod
    async def drawSoilPlant(cls, uid: str, soilid: str) -> tuple[bool, BuildImage, bool]:
        """绘制植物资源

        Args:
            uid (str): 用户Uid
            soilid (str): 土地id

        Returns:
            tuple[bool, BuildImage]: [绘制是否成功，资源图片, 是否成熟]
        """

        plant = None
        soilStatus, soilInfo = await g_pSqlManager.getUserSoilStatusBySoilID(uid, soilid)

        if soilStatus == True:
            return False, None, False
        else:
            soilInfo = soilInfo.split(',')

            if int(soilInfo[3]) == 4:
                plant = BuildImage(background = g_sResourcePath / f"plant/basic/9.png")
                await plant.resize(0, 150, 212)
                return True, plant, False

            plantInfo = g_pJsonManager.m_pPlant['plant'][soilInfo[0]]

            currentTime = datetime.now()
            matureTime = datetime.fromtimestamp(int(soilInfo[2]))

            if currentTime >= matureTime:
                phase = int(plantInfo['phase'])
                plant = BuildImage(background = g_sResourcePath / f"plant/{soilInfo[0]}/{phase - 1}.png")

                return True, plant, True
            else:
                plantedTime = datetime.fromtimestamp(int(soilInfo[1]))

                elapsedTime = currentTime - plantedTime
                elapsedHour = elapsedTime.total_seconds() / 60 / 60

                currentStage = int(elapsedHour / (plantInfo['time'] / (plantInfo['phase'] - 1)))

                if currentStage <= 0:
                    if plantInfo['general'] == False:
                        plant = BuildImage(background = g_sResourcePath / f"plant/{soilInfo[0]}/0.png")
                    else:
                        plant = BuildImage(background = g_sResourcePath / f"plant/basic/0.png")

                    await plant.resize(0, 35, 58)
                else:
                    plant = BuildImage(background = g_sResourcePath / f"plant/{soilInfo[0]}/{currentStage}.png")

        return True, plant, False

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
            "再次成熟时间（小时）",
            "是否可以上架交易行"
        ]

        # 从数据库获取结构化数据
        seedRecords = await g_pSqlManager.getUserSeedByUid(uid) or {}

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
                plantInfo = g_pJsonManager.m_pPlant['plant'][seedName]
                iconPath = g_sResourcePath / f"plant/{seedName}/icon.png"
                icon = (iconPath, 33, 33) if iconPath.exists() else ""
                sellable = "可以" if plantInfo['again'] else "不可以"

                dataList.append([
                    icon,
                    seedName,
                    count,
                    plantInfo['experience'],
                    plantInfo['harvest'],
                    plantInfo['time'],
                    plantInfo['crop'],
                    plantInfo['again'],
                    sellable
                ])
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
            count = await g_pSqlManager.getUserSeedByName(uid, name)
            if count is None:
                count = 0  # 如果返回 None，则视为没有种子

            if count <= 0:
                return f"没有在你的仓库发现{name}种子，快去买点吧！"

            # 如果播种数量超过仓库种子数量
            if count < num and num != -1:
                return f"仓库中的{name}种子数量不足，当前剩余{count}个种子"

            # 获取用户土地数量
            soilNumber = await g_pSqlManager.getUserSoilByUid(uid)

            # 如果播种数量为 -1，表示播种所有可播种的土地
            if num == -1:
                num = count

            # 记录是否成功播种
            successCount = 0
            for i in range(1, soilNumber + 1):
                if count > 0 and num > 0:
                    soilName = f"soil{i}"
                    success, message = await g_pSqlManager.getUserSoilStatusBySoilID(uid, soilName)
                    if success:
                        # 更新种子数量
                        num -= 1
                        count -= 1

                        # 记录种子消耗数量
                        successCount += 1

                        # 更新数据库
                        await g_pSqlManager.updateUserSoilStatusByPlantName(uid, soilName, name)

            # 确保用户仓库数量更新
            if successCount > 0:
                await g_pSqlManager.updateUserSeedByName(uid, name, count)

            # 根据播种结果给出反馈
            if num == 0:
                return f"播种{name}成功！仓库剩余{count}个种子"
            else:
                return f"播种数量超出开垦土地数量，已将可播种土地成功播种{name}！仓库剩余{count}个种子"

        except Exception as e:
            logger.warning(f"播种操作失败: {e}")
            return "播种失败，请稍后重试！"

    @classmethod
    async def harvest(cls, uid: str) -> str:
        """收获作物

        Args:
            uid (str): 用户Uid

        Returns:
            str: 返回
        """

        isStealingPlant = 0
        soilUnlock = await g_pSqlManager.getUserSoilByUid(uid)

        soilNames = [f"soil{i + 1}" for i in range(soilUnlock)]
        soilStatuses = await asyncio.gather(*[
            g_pSqlManager.getUserSoilStatusBySoilID(uid, name)
            for name in soilNames
        ])

        harvestRecords: List[str] = []
        experience = 0

        for (soil_name, (status, info)) in zip(soilNames, soilStatuses):
            if len(info) <= 0:
                continue

            soilInfo = info.split(',')
            if int(soilInfo[3]) == 4:
                continue

            plantId = soilInfo[0]
            plantInfo = g_pJsonManager.m_pPlant['plant'][plantId]

            currentTime = datetime.now()
            matureTime = datetime.fromtimestamp(int(soilInfo[2]))

            if currentTime >= matureTime:
                number = plantInfo['harvest']

                #判断该土地作物是否被透过
                if len(soilInfo[4]) > 0:
                    stealingStatus = soilInfo[4].split('|')
                    for isUser in stealingStatus:
                        user = isUser.split('-')
                        number -= int(user[1])

                isStealingPlant += 1

                experience += plantInfo['experience']
                harvestRecords.append(f"收获作物：{plantId}，数量为：{number}，经验为：{plantInfo['experience']}")

                #更新数据库操作
                await g_pSqlManager.addUserPlantByUid(uid, plantId, number)
                await g_pSqlManager.updateUserSoilStatusByPlantName(uid, soil_name, "", 4)

        if experience > 0:
            harvestRecords.append(f"\t累计获得经验：{experience}")
            exp = await g_pSqlManager.getUserExpByUid(uid)
            await g_pSqlManager.UpdateUserExpByUid(uid, exp + experience)

        if isStealingPlant <= 0:
            return "没有可收获的作物哦~ 不要试图拔苗助长"
        else:
            return "\n".join(harvestRecords)

    @classmethod
    async def eradicate(cls, uid: str) -> str:
        """铲除作物
        TODO 缺少随意铲除作物 目前只能铲除荒废作物
        Args:
            uid (str): 用户Uid

        Returns:
            str: 返回
        """

        soilUnlock = await g_pSqlManager.getUserSoilByUid(uid)

        soilNames = [f"soil{i + 1}" for i in range(soilUnlock)]
        soilStatuses = await asyncio.gather(*[
            g_pSqlManager.getUserSoilStatusBySoilID(uid, name)
            for name in soilNames
        ])

        experience = 0
        for (soil_name, (status, info)) in zip(soilNames, soilStatuses):
            if info:
                soilInfo = info.split(',')
                if int(soilInfo[3]) == 4:
                    experience += 3

                    #批量更新数据库操作
                    await g_pSqlManager.updateUserSoilStatusByPlantName(uid, soil_name, "", 0)

        if experience > 0:
            exp = await g_pSqlManager.getUserExpByUid(uid)
            await g_pSqlManager.UpdateUserExpByUid(uid, exp + experience)

            return f"成功铲除荒废作物，累计获得经验：{experience}"
        else:
            return "没有可以铲除的作物"

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
            "是否可以上架交易行"
        ]

        plant = await g_pSqlManager.getUserPlantByUid(uid)

        if plant is None:
            result = await ImageTemplate.table_page(
                "作物仓库",
                "播种示例：@小真寻 出售作物 大白菜 [数量]",
                column_name,
                data_list,
            )
            return result.pic2bytes()

        sell = ""
        for name, count in plant.items():  # 使用 .items() 来遍历字典
            plantInfo = g_pJsonManager.m_pPlant['plant'][name]
            icon = ""
            icon_path = g_sResourcePath / f"plant/{name}/icon.png"
            if icon_path.exists():
                icon = (icon_path, 33, 33)

            if plantInfo['again'] == True:
                sell = "可以"
            else:
                sell = "不可以"

            number = int(count) * plantInfo['price']

            data_list.append(
                [
                    icon,
                    name,
                    count,
                    plantInfo['price'],
                    number,
                    sell
                ]
            )

        result = await ImageTemplate.table_page(
            "作物仓库",
            "播种示例：@小真寻 出售作物 大白菜 [数量]",
            column_name,
            data_list,
        )

        return result.pic2bytes()

    @classmethod
    async def stealing(cls, uid: str, target: str) -> str:
        """偷菜

        Args:
            uid (str): 用户Uid
            target (str): 被偷用户Uid

        Returns:
            str: 返回
        """

        #用户信息
        userInfo = await g_pSqlManager.getUserInfoByUid(uid)
        #用户可偷次数
        userStealing = userInfo["stealing"].split('|')

        if userStealing[0] == '':
            userStealing[0] = date.today().strftime('%Y-%m-%d')
            userStealing.append(5)
        elif date.fromisoformat(userStealing[0]) != date.today():
            userStealing[0] = date.today().strftime('%Y-%m-%d')
            userStealing[1] = 5

        if int(userStealing[1]) <= 0:
            return "你今天可偷次数到达上限啦，手下留情吧"

        #获取用户解锁地块数量
        soilUnlockNum = int(userInfo["soil"])
        plant = {}

        #根据解锁土地，获取每块土地状态信息
        soilNames = [f"soil{i + 1}" for i in range(soilUnlockNum)]
        soilStatuses = await asyncio.gather(*[
            g_pSqlManager.getUserSoilStatusBySoilID(target, name)
            for name in soilNames
        ])

        isStealing = False
        harvestRecords: List[str] = []
        isStealingNumber = 0
        isStealingPlant = 0

        for (soilName, (status, info)) in zip(soilNames, soilStatuses):
            isStealing = False

            if not info:
                continue

            soilInfo = info.split(',')
            if int(soilInfo[3]) == 4:
                continue

            #作物ID
            plantId = soilInfo[0]
            #作物信息
            plantInfo = g_pJsonManager.m_pPlant['plant'][plantId]

            currentTime = datetime.now()
            matureTime = datetime.fromtimestamp(int(soilInfo[2]))

            #偷窃状态
            stealingStatus: list[str] = []
            #偷窃数量
            stealingNumber = 0
            if currentTime >= matureTime:
                if soilInfo[4]:
                    #先获取用户是否偷过该土地
                    stealingStatus = soilInfo[4].split('|')

                    for isUser in stealingStatus:
                        user = isUser.split('-')

                        if user[0] == uid:
                            isStealing = True
                            isStealingNumber += 1
                            break

                        stealingNumber -= int(user[1])

                #如果偷过，则跳过该土地
                if isStealing:
                    continue

                stealingNumber += plantInfo['harvest']
                randomNumber = random.choice([1, 2])
                randomNumber = min(randomNumber, stealingNumber)

                logger.info(f"{randomNumber}")

                if randomNumber > 0:
                    await g_pSqlManager.addUserPlantByUid(uid, plantId, randomNumber)

                    harvestRecords.append(f"成功偷到作物：{plantId}，数量为：{randomNumber}")
                    stealingStatus.append(f"{uid}-{randomNumber}")

                    isStealingPlant += 1

                    #如果将作物偷完，就直接更新状态 并记录用户偷取过
                    if plantInfo['harvest'] - randomNumber + stealingNumber == 0:
                        sql = f"UPDATE soil SET {soilName} = ',,,4,{'|'.join(stealingStatus)}' WHERE uid = '{target}'"
                    else:
                        sql = f"UPDATE soil SET {soilName} = '{soilInfo[0]},{soilInfo[1]},{soilInfo[2]},{soilInfo[3]},{'|'.join(stealingStatus)}' WHERE uid = '{target}'"

                    await g_pSqlManager.executeDB(sql)

        if isStealingPlant <= 0 and isStealingNumber <= 0:
            return "目标没有作物可以被偷"
        elif isStealingPlant <= 0 and isStealingNumber > 0:
            return "你已经偷过目标啦，请手下留情"
        else:
            userStealing[1] = int(userStealing[1]) - 1
            # 转换所有元素为字符串
            userStealing_str = [str(item) for item in userStealing]

            sql = f"UPDATE user SET stealing = '{userStealing[0]}|{userStealing[1]}' WHERE uid = {uid}"

            #更新用户每日偷取次数
            await g_pSqlManager.executeDB(sql)

            return "\n".join(harvestRecords)

    @classmethod
    async def reclamationCondition(cls, uid: str) -> str:
        userInfo = await g_pSqlManager.getUserInfoByUid(uid)
        rec = g_pJsonManager.m_pLevel["reclamation"]

        try:
            if userInfo['soil'] >= 30:
                return "你已经开垦了全部土地"

            rec = rec[f"{userInfo['soil'] + 1}"]

            level = rec['level']
            point = rec['point']
            item = rec['item']

            str = ""
            if len(item) == 0:
                str = f"下次升级所需条件：等级：{level}，农场币：{point}"
            else:
                str = f"下次升级所需条件：等级：{level}，农场币：{point}，物品：{item}"

            return str
        except Exception as e:
            return "获取升级土地条件失败！"

    @classmethod
    async def reclamation(cls, uid: str) -> str:
        userInfo = await g_pSqlManager.getUserInfoByUid(uid)
        level = await g_pSqlManager.getUserLevelByUid(uid)

        rec = g_pJsonManager.m_pLevel["reclamation"]

        try:
            if userInfo['soil'] >= 30:
                return "你已经开垦了全部土地"

            rec = rec[f"{userInfo['soil'] + 1}"]

            levelFileter = rec['level']
            point = rec['point']
            item = rec['item']

            logger.info(f"{level[0]}")

            if level[0] < levelFileter:
                return f"当前用户等级{level[0]}，升级所需等级为{levelFileter}"

            if userInfo['point'] < point:
                return f"当前用户农场币不足，升级所需农场币为{point}"

            #TODO 缺少判断需要的Item
            sql = f"UPDATE user SET point = '{userInfo['point'] - point}', soil = '{userInfo['soil'] + 1}' WHERE uid = {uid}"

            await g_pSqlManager.executeDB(sql)

            return "开垦土地成功！"
        except Exception as e:
            return "执行开垦失败！"

g_pFarmManager = CFarmManager()
