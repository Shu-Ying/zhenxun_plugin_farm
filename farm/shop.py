import math
from re import I

from zhenxun.services.log import logger
from zhenxun.utils._build_image import BuildImage
from zhenxun.utils.image_utils import ImageTemplate

from ..config import g_pJsonManager, g_sResourcePath
from ..dbService import g_pDBService


class CShopManager:

    @classmethod
    async def getSeedShopImage(cls, num: int = 1) -> bytes:
        """获取商店页面

        Returns:
            bytes: 返回商店图片bytes
        """

        data_list = []
        column_name = [
            "-",
            "种子名称",
            "种子单价",
            "解锁等级",
            "果实单价",
            "收获经验",
            "收获数量",
            "成熟时间（小时）",
            "收获次数",
            "再次成熟时间（小时）",
            "是否可以上架交易行"
        ]

        sell = ""
        plants = list(g_pJsonManager.m_pPlant['plant'].items())
        start = (num - 1) * 15
        maxItems = min(len(plants) - start, 15)
        items = plants[start:start + maxItems]

        for key, plant in items:
            icon = ""
            icon_path = g_sResourcePath / f"plant/{key}/icon.png"
            if icon_path.exists():
                icon = (icon_path, 33, 33)

            if plant['again'] == True:
                sell = "可以"
            else:
                sell = "不可以"

            data_list.append(
                [
                    icon,
                    key,
                    plant['buy'],
                    plant['level'],
                    plant['price'],
                    plant['experience'],
                    plant['harvest'],
                    plant['time'],
                    plant['crop'],
                    plant['again'],
                    sell
                ]
            )

        count = math.ceil(len(g_pJsonManager.m_pPlant['plant']) / 15)
        title = f"种子商店 页数: {num}/{count}"

        result = await ImageTemplate.table_page(
            title,
            "购买示例：@小真寻 购买种子 大白菜 5",
            column_name,
            data_list,
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
            return "请输入购买数量！"

        plantInfo = None

        try:
            plantInfo = g_pJsonManager.m_pPlant['plant'][name]
        except Exception as e:
            return "购买出错！请检查需购买的种子名称！"

        level = await g_pDBService.user.getUserLevelByUid(uid)

        if level[0] < int(plantInfo['level']):
            return "你的等级不够哦，努努力吧"

        point = await g_pDBService.user.getUserPointByUid(uid)
        total = int(plantInfo['buy']) * num

        logger.debug(f"用户：{uid}购买{name}，数量为{num}。用户农场币为{point}，购买需要{total}")

        if point < total:
            return "你的农场币不够哦~ 快速速氪金吧！"
        else:
            await g_pDBService.user.updateUserPointByUid(uid, point - total)

            if await g_pDBService.userSeed.addUserSeedByUid(uid, name, num) == False:
                return "购买失败，执行数据库错误！"

            return f"成功购买{name}，花费{total}农场币, 剩余{point - total}农场币"

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
            return "你仓库没有可以出售的作物"

        point = 0
        totalSold = 0
        isAll = (num == -1)

        if name == "":
            for plantName, count in plant.items():
                plantInfo = g_pJsonManager.m_pPlant['plant'][plantName]
                point += plantInfo['price'] * count
                await g_pDBService.userPlant.updateUserPlantByName(uid, plantName, 0)
        else:
            if name not in plant:
                return f"出售作物{name}出错：仓库中不存在该作物"
            available = plant[name]
            sellAmount = available if isAll else min(available, num)
            if sellAmount <= 0:
                return f"出售作物{name}出错：数量不足"
            await g_pDBService.userPlant.updateUserPlantByName(uid, name, available - sellAmount)
            totalSold = sellAmount

        totalPoint = point if name == "" else totalSold * g_pJsonManager.m_pPlant['plant'][name]['price']
        currentPoint = await g_pDBService.user.getUserPointByUid(uid)
        await g_pDBService.user.updateUserPointByUid(uid, currentPoint + totalPoint)

        if name == "":
            return f"成功出售所有作物，获得农场币：{totalPoint}，当前农场币：{currentPoint + totalPoint}"
        else:
            return f"成功出售{name}，获得农场币：{totalPoint}，当前农场币：{currentPoint + totalPoint}"

g_pShopManager = CShopManager()
