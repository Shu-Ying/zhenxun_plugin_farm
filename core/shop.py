import math

from zhenxun.utils.image_utils import ImageTemplate

from ..core.dbService import g_pDBService
from ..utils.config import g_sResourcePath, g_sTranslation
from ..utils.tool import g_pToolManager


class CShopManager:
    @classmethod
    async def getSeedShopImage(
        cls, filterKey: str | int = 1, num: int = 1, isVip: int = 0
    ) -> bytes:
        """获取商店页面

        Args:
            filterKey (str|int):
                - 字符串: 根据关键字筛选种子名称
                - 整数: 翻至对应页（无筛选）
            num (int, optional): 当 filterKey 为字符串时，用于指定页码。Defaults to 1.

        Returns:
            bytes: 返回商店图片bytes
        """
        # 解析参数：区分筛选关键字和页码
        filterStr = None
        if isinstance(filterKey, int):
            page = filterKey
        else:
            filterStr = filterKey
            page = num

        # 表头定义
        columnName = [
            "-",
            "种子名称",
            "农场币",
            "解锁等级",
            "果实单价",
            "收获经验",
            "收获数量",
            "成熟时间（小时）",
            "收获次数",
            "是否可以上架交易行",
        ]

        # 查询所有可购买作物，并根据筛选关键字过滤
        plants = await g_pDBService.plant.listPlants()
        filteredPlants = []

        # 如果是点券商店
        if isVip:
            columnName[2] = "点券"
            for plant in plants:
                # 只留下点券购买的种子
                if plant["isVip"] == 0:
                    continue
                # 跳过未解锁购买的种子
                if plant["isBuy"] == 0:
                    continue
                # 字符串筛选
                if filterStr and filterStr not in plant["name"]:
                    continue
                filteredPlants.append(plant)
        else:
            for plant in plants:
                # 只留下农场币购买的种子
                if plant["isVip"] == 1:
                    continue
                # 跳过未解锁购买的种子
                if plant["isBuy"] == 0:
                    continue
                # 字符串筛选
                if filterStr and filterStr not in plant["name"]:
                    continue
                filteredPlants.append(plant)

        # 计算分页
        totalCount = len(filteredPlants)
        pageCount = math.ceil(totalCount / 15) if totalCount else 1
        startIndex = (page - 1) * 15
        pageItems = filteredPlants[startIndex : startIndex + 15]

        # 构建数据行
        dataList = []
        for plant in pageItems:
            # 图标处理
            icon = ""
            iconPath = g_sResourcePath / f"plant/{plant['name']}/icon.png"
            if iconPath.exists():
                icon = (iconPath, 33, 33)

            # 交易行标记
            sell = "可以" if plant["sell"] else "不可以"

            dataList.append(
                [
                    icon,
                    plant["name"],  # 种子名称
                    plant["buy"],  # 农场币种子单价
                    plant["level"],  # 解锁等级
                    plant["price"],  # 果实单价
                    plant["experience"],  # 收获经验
                    plant["harvest"],  # 收获数量
                    plant["time"],  # 成熟时间（小时）
                    plant["crop"],  # 收获次数
                    sell,  # 是否可上架交易行
                ]
            )
            if isVip:
                dataList[-1][2] = plant["vipBuy"]  # 点券种子单价

        # 页码标题
        title = f"种子商店 页数: {page}/{pageCount}"

        # 渲染表格并返回图片bytes
        result = await ImageTemplate.table_page(
            title,
            "购买示例：@小真寻 购买种子 大白菜 5",
            columnName,
            dataList,
        )
        return result.pic2bytes()

    @classmethod
    async def buySeed(cls, uid: str, name: str, num: int = 1) -> str:
        """购买种子

        Args:
            uid (str): 用户Uid
            name (str): 植物名称
            num (int, optional): 购买数量

        Returns:
            str:
        """
        if num <= 0:
            return g_sTranslation["buySeed"]["notNum"]

        player = await g_pToolManager.getPlayerByUid(uid)
        plantInfo = await g_pDBService.plant.getPlantByName(name)
        if not plantInfo or not player:
            return g_sTranslation["buySeed"]["error"]

        level = player.user.get("level", 0)

        if level < int(plantInfo["level"]):
            return g_sTranslation["buySeed"]["noLevel"]

        vipSeed = plantInfo.get("isVip", 0) == 1
        currencyType = "vipPoint" if vipSeed else "point"
        price = int(plantInfo["vipBuy" if vipSeed else "buy"])
        totalCost = price * num

        currentCurrency = player.user.get(currencyType, 0)
        if currentCurrency < totalCost:
            return g_sTranslation["buySeed"][f"no{'Vip' if vipSeed else ''}Point"]

        await player.addPoint(currencyType, currentCurrency - totalCost)

        if not await g_pDBService.userSeed.addUserSeedByUid(uid, name, num):
            return g_sTranslation["buySeed"]["errorSql"]

        success_key = "vipSuccess" if vipSeed else "success"
        remaining_currency = currentCurrency - totalCost

        return g_sTranslation["buySeed"][success_key].format(
            name=name, total=totalCost, point=remaining_currency
        )

    @classmethod
    async def sellPlantByUid(cls, uid: str, name: str = "", num: int = 1) -> str:
        """出售作物

        Args:
            uid (str): 用户Uid

        Returns:
            str:
        """
        if not isinstance(name, str) or name.strip() == "":
            name = ""

        plant = await g_pDBService.userPlant.getUserPlantByUid(uid)
        if not plant:
            return g_sTranslation["sellPlant"]["no"]

        point = 0
        totalSold = 0
        isAll = num == -1

        if name == "":
            for plantName, count in plant.items():
                isLock = await g_pDBService.userPlant.checkPlantLockByName(
                    uid, plantName
                )

                if isLock:
                    continue

                plantInfo = await g_pDBService.plant.getPlantByName(plantName)
                if not plantInfo:
                    continue

                point += plantInfo["price"] * count
                await g_pDBService.userPlant.updateUserPlantByName(uid, plantName, 0)
        else:
            if name not in plant:
                return g_sTranslation["sellPlant"]["error"].format(name=name)
            available = plant[name]
            sellAmount = available if isAll else min(available, num)
            if sellAmount <= 0:
                return g_sTranslation["sellPlant"]["error1"].format(name=name)
            await g_pDBService.userPlant.updateUserPlantByName(
                uid, name, available - sellAmount
            )
            totalSold = sellAmount

        if name == "":
            totalPoint = point
        else:
            plantInfo = await g_pDBService.plant.getPlantByName(name)
            if not plantInfo:
                price = 0
            else:
                price = plantInfo["price"]

            totalPoint = totalSold * price

        player = await g_pToolManager.getPlayerByUid(uid)
        if not player:
            return g_sTranslation["basic"]["error"]

        currentPoint = player.user.get("point", 0)
        await player.addPoint("point", currentPoint + totalPoint)

        result = "success1" if name == "" else "success"

        return g_sTranslation["sellPlant"][result].format(
            point=totalPoint, num=currentPoint + totalPoint
        )


g_pShopManager = CShopManager()
