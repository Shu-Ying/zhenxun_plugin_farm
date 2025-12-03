from zhenxun.configs.config import Config
from zhenxun.services.log import logger
from zhenxun.utils._build_image import BuildImage
from zhenxun.utils.image_utils import ImageTemplate
from zhenxun.utils.platform import PlatformUtils

from ...core import CPlayer
from ...core.dbService import g_pDBService
from .. import config, getJsonManager, getToolManager, utils


class CDarwFarm:
    @classmethod
    async def drawFarmByUid(cls, uid: str) -> bytes:
        """绘制用户农场

        Args:
            uid (str): 用户UID

        Returns:
            bytes: 返回绘制结果
        """
        dynamic = Config.get_config("zhenxun_plugin_farm", "动态背景")

        img, soilSize, soilPos, grass = await cls.createBaseCanvas(dynamic)

        player = await getToolManager().getPlayerByUid(uid)
        if not player:
            return img.pic2bytes()

        soilUnlock = int(player.user.get("soil", 3))

        isFirstExpansion = True  # 首次添加扩建图片
        isFirstRipe = True

        for index in range(0, 30):
            x = soilPos[str(index + 1)]["x"]
            y = soilPos[str(index + 1)]["y"]

            # 已解锁格子
            if index < soilUnlock:
                isRipe = await cls.drawUnlockedTile(img, uid, index + 1, x, y, soilSize)
                if isRipe and isFirstRipe:
                    await cls.pasteRipeOnce(img, x, y, soilSize)
                    isFirstRipe = False
            else:
                addedExpansion = await cls.drawLockedTile(
                    img, x, y, soilSize, grass, isFirstExpansion
                )
                if addedExpansion:
                    isFirstExpansion = False

        await cls.drawUserInfo(img, player, uid)

        await cls.applyDefinitionResize(img)

        return img.pic2bytes()

    @classmethod
    async def createBaseCanvas(
        cls, dynamic: bool
    ) -> tuple[BuildImage, tuple, dict, BuildImage]:
        """创建基础画布并返回 (img, soilSize, soilPos, grass)

        Returns:
            tuple: (主画布, 土地尺寸, 土地坐标映射, 草地图)
        """

        if dynamic:
            season = getToolManager().getSeason()

            backgroundPath = config.g_sResourcePath / "background/decorateIcon"

            # 节日优先级更高
            if season == utils.Season.SPRING:
                bgFile = backgroundPath / "decorate_spring_1.jpg"
            elif season == utils.Season.SUMMER:
                bgFile = backgroundPath / "decorate_summer_1.jpg"
            elif season == utils.Season.AUTUMN:
                bgFile = backgroundPath / "decorate_autumn_1.jpg"
            elif season == utils.Season.WINTER:
                bgFile = backgroundPath / "decorate_winter_1.jpg"
            else:
                bgFile = backgroundPath / "decorate_default_1.jpg"

            img = BuildImage(background=bgFile)
        else:
            img = BuildImage(
                background=config.g_sResourcePath
                / "background/decorateIcon/decorate_default_1jpg"
            )

        soil = await getJsonManager().getSoil()
        soilSize = soil["size"]
        soilPos = soil["soil"]

        grass = BuildImage(background=config.g_sResourcePath / "soil/草土地.png")
        await grass.resize(0, soilSize[0], soilSize[1])

        return img, soilSize, soilPos, grass

    @classmethod
    async def drawUnlockedTile(
        cls, img: BuildImage, uid: str, soilIndex: int, x: int, y: int, soilSize
    ) -> bool:
        """绘制已解锁土地格（包含土地贴图与作物），返回该格是否可收获

        Args:
            img (BuildImage): 主画布
            uid (str): 用户UID
            soilIndex (int): 土地索引（从1开始）
            x (int), y (int): 贴图位置
            soilSize: 土地贴图尺寸（[w,h] 或 (w,h)）

        Returns:
            bool: 是否有可收获作物（isRipe）
        """
        soilUrl = "soil/普通土地.png"
        soilInfo = await g_pDBService.userSoil.getUserSoil(uid, soilIndex)

        if soilInfo:
            soilLevel = soilInfo.get("soilLevel", 0)
            if soilLevel == 1:
                soilUrl = "soil/红土地.png"
            elif soilLevel == 2:
                soilUrl = "soil/黑土地.png"
            elif soilLevel == 3:
                soilUrl = "soil/金土地.png"

        soil = BuildImage(background=config.g_sResourcePath / soilUrl)
        await soil.resize(0, soilSize[0], soilSize[1])
        await img.paste(soil, (x, y))

        isPlant, plant, isRipe, offsetX, offsetY = await cls.drawSoilPlant(
            uid, soilIndex
        )
        if isPlant and plant is not None:
            await img.paste(
                plant,
                (
                    x + soilSize[0] // 2 - plant.width // 2 + offsetX,
                    y + soilSize[1] // 2 - plant.height // 2 + offsetY,
                ),
            )

        return bool(isRipe)

    @classmethod
    async def drawLockedTile(
        cls,
        img: BuildImage,
        x: int,
        y: int,
        soilSize,
        grass: BuildImage,
        isFirstExpansion: bool,
    ) -> bool:
        """绘制未解锁格子并在首次出现时绘制扩建图标

        Returns:
            bool: 是否在此格绘制了扩建图标（仅首次返回 True）
        """
        await img.paste(grass, (x, y))

        if isFirstExpansion:
            expansion = BuildImage(
                background=config.g_sResourcePath / "background/expansion.png"
            )
            await expansion.resize(0, 69, 69)
            await img.paste(
                expansion,
                (
                    x + soilSize[0] // 2 - expansion.width // 2,
                    y + soilSize[1] // 2 - expansion.height,
                ),
            )
            return True

        return False

    @classmethod
    async def pasteRipeOnce(cls, img: BuildImage, x: int, y: int, soilSize):
        """首次发现成熟作物时贴上成熟提示图（ripe）"""
        ripe = BuildImage(background=config.g_sResourcePath / "background/ripe.png")
        await img.paste(
            ripe,
            (x + soilSize[0] // 2 - ripe.width // 2, y - ripe.height // 2),
        )

    @classmethod
    async def drawUserInfo(cls, img: BuildImage, player: CPlayer, uid: str):
        """绘制左上角用户信息（头像、框、昵称、经验、等级、货币等）
        TODO 需要详细的绘制头像框

        Args:
            img (BuildImage): 主画布
            player(CPlayer): 用户
            uid (str): 用户Uid
        """
        # 背景板
        background = BuildImage(
            background=config.g_sResourcePath / "background/userInfo.png"
        )
        await img.paste(background, (100, 30))

        # 头像
        image = await PlatformUtils.get_user_avatar(uid, "qq")
        if image:
            avatar = BuildImage(background=image)
            await avatar.resize(0, 140, 150)
            await img.paste(avatar, (125, 85))

        # 头像框
        frame = BuildImage(
            background=config.g_sResourcePath / "background/frame/frame.png"
        )
        await img.paste(frame, (75, 44))

        nameImg = await BuildImage.build_text_image(
            player.user["name"], size=24, font_color=(77, 35, 4)
        )
        await img.paste(nameImg, (300, 92))

        level = await player.getUserLevel()
        beginX = 309
        endX = 627
        width = int((level[2] / level[1]) * (endX - beginX)) if level[1] else 0
        await img.rectangle((beginX, 188, beginX + width, 222), (171, 194, 41))

        # 经验
        expImg = await BuildImage.build_text_image(
            f"{level[2]} / {level[1]}", size=24, font_color=(102, 120, 19)
        )
        await img.paste(expImg, (390, 193))

        # 等级
        levelImg = await BuildImage.build_text_image(
            str(level[0]), size=32, font_color=(214, 111, 1)
        )
        await img.paste(levelImg, (660, 187))

        # 农场币
        pointImg = await BuildImage.build_text_image(
            str(player.user.get("point", 0)), size=24, font_color=(253, 253, 253)
        )
        await img.paste(pointImg, (330, 255))

        # 点券
        bondsImg = await BuildImage.build_text_image(
            "0", size=24, font_color=(253, 253, 253)
        )
        await img.paste(bondsImg, (570, 255))

    @classmethod
    async def drawUserDecorateIcon(cls, img: BuildImage, player: CPlayer) -> bool:
        """绘制用户装饰图标

        Args:
            img (BuildImage): 主画布
            player (CPlayer): 用户

        Returns:
            bool: 是否成功绘制
        """

        decorateIconId = player.user.get("decorateIcon", 0)
        if decorateIconId <= 0:
            return False

        iconPath = (
            config.g_sResourcePath / f"decorateIcon/DecorateIcon{decorateIconId}.png"
        )
        if not iconPath.exists():
            return False

        icon = BuildImage(background=iconPath)
        await icon.resize(0, 100, 100)
        await img.paste(icon, (x, y))

        return True

    @classmethod
    async def applyDefinitionResize(cls, img: BuildImage):
        """根据配置调整绘制清晰度（original/medium/hight/其他）"""
        definition = Config.get_config("zhenxun_plugin_farm", "绘制农场清晰度")
        if definition == "medium":
            await img.resize(0.6)
        elif definition == "hight":
            await img.resize(0.8)
        elif definition == "original":
            pass
        else:
            await img.resize(0.4)

    @classmethod
    async def drawDetailFarmByUid(cls, uid: str) -> list:
        """绘制用户详细信息

        Args:
            uid (str): 用户Uid

        Returns:
            list:
        """

        info = []
        farm = await cls.drawFarmByUid(uid)
        player = await getToolManager().getPlayerByUid(uid)
        if not player:
            return info

        info.append(BuildImage.open(farm))

        dataList = []
        columnName = [
            "-",
            "土地ID",
            "土地等级",
            "作物名称",
            "成熟时间",
            "土地状态",
            "被偷数量",
            "剩余产出",
        ]

        icon = ""
        soilNumber = player.user.get("soil", 3)

        for i in range(1, soilNumber + 1):
            soilInfo = await g_pDBService.userSoil.getUserSoil(uid, i)

            if not soilInfo:
                continue

            match soilInfo.get("soilLevel", 0):
                case 1:
                    name = "红土地.png"
                case 2:
                    name = "黑土地.png"
                case 3:
                    name = "金土地.png"
                case _:
                    name = "普通土地.png"
            iconPath = config.g_sResourcePath / "soil" / name

            if iconPath.exists():
                icon = (iconPath, 33, 33)

            plantName = soilInfo.get("plantName", "-")

            if plantName == "-":
                matureTime = "-"
                soilStatus = "-"
                totalNumber = "-"
                plantNumber = "-"
            else:
                matureTime = (
                    getToolManager()
                    .dateTime()
                    .fromtimestamp(int(soilInfo.get("matureTime", 0)))
                    .strftime("%Y-%m-%d %H:%M:%S")
                )
                soilStatus = await g_pDBService.userSoil.getUserSoilStatus(uid, i)

                totalNumber = await g_pDBService.userSteal.getTotalStolenCount(uid, i)
                planInfo = await g_pDBService.plant.getPlantByName(plantName)

                if not planInfo:
                    plantNumber = "None"
                else:
                    plantNumber = f"{planInfo['harvest'] - totalNumber}"

            dataList.append(
                [
                    icon,
                    i,
                    await g_pDBService.userSoil.getSoilLevelText(soilInfo["soilLevel"]),
                    plantName,
                    matureTime,
                    soilStatus,
                    totalNumber,
                    plantNumber,
                ]
            )

            if len(dataList) >= 15:
                result = await ImageTemplate.table_page(
                    "土地详细信息",
                    "",
                    columnName,
                    dataList,
                )

                info.append(result.copy())
                dataList.clear()

            if i >= soilNumber:
                result = await ImageTemplate.table_page(
                    "土地详细信息",
                    "",
                    columnName,
                    dataList,
                )

                info.append(result.copy())
                dataList.clear()

        return info

    @classmethod
    async def drawSoilPlant(
        cls, uid: str, soilIndex: int
    ) -> tuple[bool, BuildImage, bool, int, int]:
        """绘制植物资源

        Args:
            uid (str): 用户Uid
            soilIndex (int): 土地索引 从1开始

        Returns:
            tuple[bool, BuildImage]: [绘制是否成功，资源图片, 是否成熟]
        """

        plant = None
        soilInfo = await g_pDBService.userSoil.getUserSoil(uid, soilIndex)

        if not soilInfo:
            return False, None, False, 0, 0  # type: ignore

        # 是否枯萎
        if int(soilInfo.get("wiltStatus", 0)) == 1:
            plant = BuildImage(background=config.g_sResourcePath / "plant/basic/9.png")
            await plant.resize(0, 150, 212)
            return True, plant, False, 0, 0

        # 获取作物详细信息
        plantInfo = await g_pDBService.plant.getPlantByName(soilInfo["plantName"])
        if not plantInfo:
            logger.error(f"绘制植物资源失败: {soilInfo['plantName']}")
            return False, None, False, 0, 0  # type: ignore

        offsetX = plantInfo.get("officX", 0)
        offsetY = plantInfo.get("officY", 0)
        offsetW = plantInfo.get("officW", 0)
        offsetH = plantInfo.get("officH", 0)

        currentTime = getToolManager().dateTime().now().timestamp()
        phaseList = await g_pDBService.plant.getPlantPhaseByName(soilInfo["plantName"])

        # 如果当前时间大于成熟时间 说明作物成熟
        if currentTime >= soilInfo["matureTime"]:
            plant = BuildImage(
                background=config.g_sResourcePath
                / f"plant/{soilInfo['plantName']}/{len(phaseList)}.png"
            )

            return True, plant, True, offsetX, offsetY
        else:
            # 如果是多阶段作物 且没有成熟 #早期思路 多阶段作物 直接是倒数第二阶段图片
            # if soilInfo["harvestCount"] >= 1:
            #     plant = BuildImage(
            #         background=g_sResourcePath
            #         / f"plant/{soilInfo['plantName']}/{plantInfo['phase'] - 1}.png"
            #     )

            #     return True, plant, False, offsetX, offsetY

            # 如果没有成熟 则根据当前阶段进行绘制
            elapsedTime = currentTime - soilInfo["plantTime"]
            currentStage = currentStage = sum(
                1 for thr in phaseList if elapsedTime >= thr
            )

            if currentStage <= 0:
                if not plantInfo["general"]:
                    plant = BuildImage(
                        background=config.g_sResourcePath
                        / f"plant/{soilInfo['plantName']}/0.png"
                    )
                else:
                    plant = BuildImage(
                        background=config.g_sResourcePath / "plant/basic/0.png"
                    )
                await plant.resize(0, 35 + offsetW, 58 + offsetH)
            else:
                plant = BuildImage(
                    background=config.g_sResourcePath
                    / f"plant/{soilInfo['plantName']}/{currentStage}.png"
                )

        return True, plant, False, offsetX, offsetY
