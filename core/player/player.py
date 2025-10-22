from ..dbService import g_pDBService


class CPlayer:
    def __init__(self):
        self.user = {
            "uid": "",  # 用户Uid
            "name": "",  # 农场名称
            "exp": 0,  # 经验值
            "point": 0,  # 金币
            "vipPoint": 0,  # 点券
            "soil": 3,  # 解锁土地数量
            "stealTime": "",  # 偷菜时间字符串
            "stealCount": 0,  # 剩余偷菜次数
        }

    async def init(self, uid: str) -> bool:
        self.user["uid"] = uid
        return await self.loadFormDB()

    async def loadFormDB(self) -> bool:
        uid = self.user.get("uid", "")

        if uid == "":
            return False

        self.user = await g_pDBService.user.getUserInfoByUid(uid)

        return True

    async def isRegistered(self) -> bool:
        """检查用户是否注册农场

        Returns:
            bool: 是否注册农场
        """
        uid = self.user.get("uid", "")

        if uid == "":
            return False

        return await g_pDBService.user.isRegistered(uid)

    async def addPoint(self, type: str, index: int) -> bool:
        """增加货币

        Args:
            type (str): 货币类型 point/vipPoint
            index (int): 增加的数量

        Returns:
            bool: 是否成功增加货币
        """
        uid = self.user.get("uid", "")

        if uid == "" or type not in g_pDBService.user.currencies:
            return False

        if index == 0:
            return True

        nowIndex = self.user.get(type, 0) + index

        if nowIndex < 0:
            nowIndex = 0

        if await g_pDBService.user.updatePoint(uid, type, nowIndex):
            self.user[type] = nowIndex
            return True

        return False

    async def subPoint(self, type: str, index: int) -> bool:
        """减少货币

        Args:
            type (str): 货币类型 point/vipPoint
            index (int): 减少的数量

        Returns:
            bool: 是否成功减少货币
        """
        uid = self.user.get("uid", "")

        if uid == "" or type not in g_pDBService.user.currencies:
            return False

        if index == 0:
            return True

        nowIndex = self.user.get(type, 0) - index

        if nowIndex < 0:
            nowIndex = 0

        if await g_pDBService.user.updatePoint(uid, type, nowIndex):
            self.user[type] = nowIndex
            return True

        return False

    async def addExp(self, exp: int) -> bool:
        """增加经验值

        Args:
            exp (int): 增加的经验值

        Returns:
            bool: 是否成功增加经验值
        """
        uid = self.user.get("uid", "")

        if uid == "":
            return False

        if exp == 0:
            return True

        nowExp = self.user.get("exp", 0) + exp

        if nowExp < 0:
            nowExp = 0

        if await g_pDBService.user.updateExp(uid, nowExp):
            self.user["exp"] = nowExp
            return True

        return False

    async def subExp(self, exp: int) -> bool:
        """减少经验值

        Args:
            exp (int): 减少的经验值

        Returns:
            bool: 是否成功减少经验值
        """
        uid = self.user.get("uid", "")

        if uid == "":
            return False

        if exp == 0:
            return True

        nowExp = self.user.get("exp", 0) - exp

        if nowExp < 0:
            nowExp = 0

        if await g_pDBService.user.updateExp(uid, nowExp):
            self.user["exp"] = nowExp
            return True

        return False

    async def updateName(self, name: str) -> str:
        """更新农场名称

        Args:
            name (str): 农场名称

        Returns:
            str: success/error/error1
        """
        uid = self.user.get("uid", "")

        if uid == "":
            return "error"

        return await g_pDBService.user.updateName(uid, name)

    async def getUserLevel(self) -> tuple[int, int, int]:
        """获取用户等级信息

        Returns:
            tuple[int, int, int]: 成功返回(当前等级, 升至下级还需经验, 当前等级已获经验)
            失败返回(-1, -1, -1)
        """
        uid = self.user.get("uid", "")

        if uid == "":
            return -1, -1, -1

        return await g_pDBService.user.getUserLevelByUid(uid)

    async def updateStealCountByUid(
        self, uid: str, stealTime: str, stealCount: int
    ) -> bool:
        """根据用户Uid更新剩余偷菜次数

        Args:
            uid (str): 用户Uid
            stealTime (str): 偷菜日期
            stealCount (int): 新剩余偷菜次数

        Returns:
            bool: 是否更新成功
        """
        uid = self.user.get("uid", "")

        if uid == "":
            return False

        return await g_pDBService.user.updateStealCountByUid(uid, stealTime, stealCount)

    async def updateField(self, field: str, value) -> bool:
        """更新单字段信息

        Returns:
            bool: 是否成功更新单字段信息
        """
        uid = self.user.get("uid", "")

        if uid == "":
            return False

        return await g_pDBService.user.updateFieldByUid(uid, field, value)
