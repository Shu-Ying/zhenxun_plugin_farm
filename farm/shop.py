import math

from zhenxun.services.log import logger
from zhenxun.utils._build_image import BuildImage
from zhenxun.utils.image_utils import ImageTemplate

from ..config import g_pJsonManager, g_sResourcePath
from ..database import g_pSqlManager


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
            "解锁等级",
            "种子单价",
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

        level = await g_pSqlManager.getUserLevelByUid(uid)

        if level[0] < int(plantInfo['level']):
            return "你的等级不够哦，努努力吧"

        point = await g_pSqlManager.getUserPointByUid(uid)
        total = int(plantInfo['price']) * num

        logger.debug(f"用户：{uid}购买{name}，数量为{num}。用户农场币为{point}，购买需要{total}")

        if point < total:
            return "你的农场币不够哦~ 快速速氪金吧！"
        else:
            await g_pSqlManager.updateUserPointByUid(uid, point - total)

            if await g_pSqlManager.addUserSeedByPlant(uid, name, num) == False:
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

        plant = await g_pSqlManager.getUserPlantByUid(uid)

        if plant == None:
            return "你仓库没有可以出售的作物"

        point = 0
        totalSold = 0
        remainingItems = []

        items = plant.split(',')
        if len(name) <= 0:
            #出售全部
            for item in items:
                if '|' in item:
                    plant_name, count_str = item.split('|', 1)
                    try:
                        count = int(count_str)
                        plant_info = g_pJsonManager.m_pPlant['plant'][plant_name]
                        point += plant_info['price'] * count
                    except Exception:
                        continue

            await g_pSqlManager.updateUserPlantByUid(uid, "")  # 清空仓库
        else:
            for item in items:
                if '|' in item:
                    plantName, countStr = item.split('|', 1)
                    try:
                        count = int(countStr)
                        if plantName == name:
                            sellAmount = min(num, count)
                            totalSold += sellAmount
                            remaining = count - sellAmount

                            if remaining > 0:
                                remainingItems.append(f"{plantName}|{remaining}")

                            num -= sellAmount
                            if num == 0:
                                break
                    except (ValueError, TypeError):
                        continue

        if num > 0:
            return f"出售作物{name}出错：数量不足"

        #计算收益
        try:
            plantInfo = g_pJsonManager.m_pPlant['plant'][name]
            totalPoint = plantInfo['price'] * totalSold
        except KeyError:
            return f"出售作物{name}出错：作物不存在"

        #更新剩余作物
        remainingPlant = ','.join(remainingItems) if remainingItems else ""
        await g_pSqlManager.updateUserPlantByUid(uid, remainingPlant)

        #更新农场币
        p = await g_pSqlManager.getUserPointByUid(uid)
        await g_pSqlManager.updateUserPointByUid(uid, p + totalPoint)

        if name:
            return f"成功出售{name}，获得农场币：{totalPoint}"
        else:
            return f"成功出售所有作物，获得农场币：{totalPoint}"

g_pShopManager = CShopManager()
