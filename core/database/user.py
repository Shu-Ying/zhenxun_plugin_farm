import math

from ...utils.tool import g_pToolManager
from .database import CSqlManager


class CUserDB(CSqlManager):
    def __init__(self):
        self.currencies: list[str] = ["point", "vipPoint"]

    async def initDB(self):
        userInfo = {
            "uid": "TEXT PRIMARY KEY",  # 用户Uid
            "name": "TEXT NOT NULL",  # 农场名称
            "exp": "INTEGER DEFAULT 0",  # 经验值
            "point": "INTEGER DEFAULT 0",  # 金币
            "vipPoint": "INTEGER DEFAULT 0",  # 点券
            "soil": "INTEGER DEFAULT 3",  # 解锁土地数量
            "stealTime": "TEXT DEFAULT ''",  # 偷菜时间字符串
            "stealCount": "INTEGER DEFAULT 0",  # 剩余偷菜次数
        }

        await self.ensureTableSchema("user", userInfo)

    async def initUserInfo(self, uid: str, name: str) -> bool:
        """初始化用户信息

        Args:
            uid (str): 用户ID
            name (str): 农场名称

        Returns:
            bool: 是否成功初始化用户信息
        """
        nowStr = g_pToolManager.dateTime().date().today().strftime("%Y-%m-%d")

        result = await self.insert(
            "user",
            data={
                "uid": uid,
                "name": name,
                "exp": 0,
                "point": 500,
                "soil": 3,
                "stealTime": nowStr,
                "stealCount": 5,
            },
        )

        return result

    async def getUserInfoByUid(self, uid: str) -> dict:
        """根据用户ID获取用户信息

        Args:
            uid (str): 用户ID

        Returns:
            dict: 用户信息字典，未找到返回空字典
        """
        if uid == "":
            return {}

        records = await self.select("user", where={"uid": uid})

        return records[0] if records else {}

    async def isRegistered(self, uid: str) -> bool:
        """检查用户是否注册农场

        Args:
            uid (str): 用户ID

        Returns:
            bool: 是否注册农场
        """
        if uid == "":
            return False

        return await self.exists("user", where={"uid": uid})

    async def updatePoint(self, uid: str, type: str, index: int) -> bool:
        """更新货币

        Args:
            uid (str): 用户ID
            type (str): 货币类型 point/vipPoint
            index (int): 更新后的数量

        Returns:
            bool: 是否成功更新货币
        """
        if type not in self.currencies:
            return False

        if index < 0:
            index = 0

        await self.update("user", {type: index}, {"uid": uid})

        return True

    async def updateExp(self, uid: str, exp: int) -> bool:
        """更新经验值

        Args:
            uid (str): 用户ID
            exp (int): 更新后的经验值

        Returns:
            bool: 是否成功更新经验值
        """
        if exp < 0:
            exp = 0

        return await self.update("user", {"exp": exp}, {"uid": uid})

    async def updateName(self, uid: str, name: str) -> str:
        """更新农场名称

        Args:
            uid (str): 用户ID
            name (str): 农场名称

        Returns:
            bool: 是否成功更新农场名称
        """
        safeName = g_pToolManager.sanitize_username(name)

        if safeName == "神秘农夫":
            return "error"

        if await self.update("user", {"name": safeName}, {"uid": uid}):
            return "success"

        return "error1"

    async def getUserLevelByUid(self, uid: str) -> tuple[int, int, int]:
        """获取用户等级信息

        Args:
            uid (str): 用户Uid

        Returns:
            tuple[int, int, int]: 成功返回(当前等级, 升至下级还需经验, 当前等级已获经验)
            失败返回(-1, -1, -1)
        """
        if not uid:
            return -1, -1, -1

        records = await self.select("user", where={"uid": uid}, columns=["exp"])

        if not records:
            return -1, -1, -1

        try:
            exp = int(records[0].get("exp", 0))
        except Exception:
            exp = 0

        levelStep = 200  # 每级经验增量

        discriminant = 1 + 8 * exp / levelStep
        level = int((-1 + math.sqrt(discriminant)) // 2)
        if level < 0:
            level = 0

        def cumExp(k: int) -> int:
            return levelStep * k * (k + 1) // 2

        totalExpCurrentLevel = cumExp(level)
        totalExpNextLevel = cumExp(level + 1)

        currentExp = exp - totalExpCurrentLevel

        return level, totalExpNextLevel, currentExp

    async def getUserSoilByUid(self, uid: str) -> int:
        """获取用户解锁土地数量

        Args:
            uid (str): 用户Uid

        Returns:
            int: 解锁土地数量，失败返回-1
        """
        if not uid:
            return -1

        records = await self.select("user", where={"uid": uid}, columns=["soil"])

        if not records:
            return -1

        try:
            soil = int(records[0].get("soil", 3))
        except Exception:
            soil = 3

        return soil

    async def updateFieldByUid(self, uid: str, field: str, value) -> bool:
        """更新单字段信息

        Args:
            uid (str): 用户Uid
            field (str): 字段名称

        Returns:
            bool: 是否成功更新字段
        """
        if not uid or not field:
            return False

        return await self.update("user", {field: value}, {"uid": uid})
