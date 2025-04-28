from datetime import date, datetime, timedelta
from typing import Optional

from database import CSqlManager

from zhenxun.services.log import logger

from ..config import g_pJsonManager
from ..dbService import g_pDBService


class CUserSoilDB(CSqlManager):
    @classmethod
    async def initDB(cls):
        #用户Uid
        #地块索引从1开始
        #作物名称
        #播种时间
        #成熟时间
        #土地等级 0=普通地，1=红土地，2=黑土地，3=金土地
        #枯萎状态 0=未枯萎，1=枯萎
        #施肥状态 0=未施肥，1=施肥
        #虫害状态 0=无虫害，1=有虫害
        #杂草状态 0=无杂草，1=有杂草
        #缺水状态 0=不缺水，1=缺水
        userSoil = {
            "uid": "TEXT NOT NULL",
            "soilIndex": "INTEGER NOT NULL",
            "plantName": "TEXT DEFAULT ''",
            "plantTime": "INTEGER DEFAULT 0",
            "matureTime": "INTEGER DEFAULT 0",
            "soilLevel": "INTEGER DEFAULT 0",
            "wiltStatus": "INTEGER DEFAULT 0",
            "fertilizerStatus": "INTEGER DEFAULT 0",
            "bugStatus": "INTEGER DEFAULT 0",
            "weedStatus": "INTEGER DEFAULT 0",
            "waterStatus": "INTEGER DEFAULT 0",
            "PRIMARY KEY": "(uid, soilIndex)"
        }

        await cls.ensureTableSchema("userSoil", userSoil)

    @classmethod
    async def getUserFarmByUid(cls, uid: str) -> dict:
        """获取指定用户的旧农场数据

        Args:
            uid (str): 用户ID

        Returns:
            dict: 包含字段名-值的字典; 若无数据则返回空字典
        """
        cursor = await cls.m_pDB.execute("SELECT * FROM soil WHERE uid = ?", (uid,))
        row = await cursor.fetchone()
        if not row:
            return {}
        columns = [description[0] for description in cursor.description]
        return dict(zip(columns, row))

    @classmethod
    async def migrateOldFarmData(cls):
        """迁移旧土地数据到新表 userSoil 并删除旧表

        Raises:
            aiosqlite.Error: 数据库操作失败时抛出

        Returns:
            None
        """
        async with cls._transaction():
            users = await g_pDBService.user.getAllUsers()
            for uid in users:
                farmInfo = await cls.getUserFarmByUid(uid)
                for i in range(1, 31):
                    soilName = f"soil{i}"
                    if soilName not in farmInfo:
                        continue
                    soilData = farmInfo[soilName]
                    if not soilData:
                        continue

                    fields = soilData.split(',')
                    if len(fields) < 6:
                        continue

                    plantName = fields[0]
                    plantTime = int(fields[1])
                    matureTime = int(fields[2])
                    soilLevel = int(fields[5])

                    # 构建新的土地数据
                    soilInfo = {
                        "uid": uid,
                        "soilIndex": i,
                        "plantName": plantName,
                        "plantTime": plantTime,
                        "matureTime": matureTime,
                        "soilLevel": soilLevel,
                        "wiltStatus":0,
                        "fertilizerStatus": 0,
                        "bugStatus": 0,
                        "weedStatus": 0,
                        "waterStatus": 0
                    }

                    await cls.insertUserSoil(soilInfo)

            # 彻底清除旧表
            await cls.m_pDB.execute("DROP TABLE soil")

    @classmethod
    async def insertUserSoil(cls, soilInfo: dict):
        """插入一条新的 userSoil 记录

        Args:
            soilInfo (dict): 新土地数据

        Returns:
            None
        """
        async with cls._transaction():
            await cls.m_pDB.execute(
                "INSERT INTO userSoil (uid, soilIndex, plantName, plantTime, matureTime, soilLevel, fertilizerStatus, bugStatus, weedStatus, waterStatus) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    soilInfo["uid"],
                    soilInfo["soilIndex"],
                    soilInfo.get("plantName", ""),
                    soilInfo.get("plantTime", 0),
                    soilInfo.get("matureTime", 0),
                    soilInfo.get("soilLevel", 0),
                    soilInfo.get("fertilizerStatus", 0),
                    soilInfo.get("bugStatus", 0),
                    soilInfo.get("weedStatus", 0),
                    soilInfo.get("waterStatus", 0)
                )
            )

    @classmethod
    async def getUserSoil(cls, uid: str, soilIndex: int) -> Optional[dict]:
        """获取指定用户某块土地的详细信息

        Args:
            uid (str): 用户ID
            soilIndex (int): 土地索引

        Returns:
            Optional[dict]: 记录存在返回字段-值字典，否则返回 None
        """
        async with cls._transaction():
            cursor = await cls.m_pDB.execute(
                "SELECT * FROM userSoil WHERE uid = ? AND soilIndex = ?",
                (uid, soilIndex)
            )
            row = await cursor.fetchone()
            if not row:
                return None
            columns = [description[0] for description in cursor.description]
            return dict(zip(columns, row))

    @classmethod
    async def updateUserSoil(cls, uid: str, soilIndex: int, field: str, value):
        """更新指定用户土地的单个字段

        Args:
            uid (str): 用户ID
            soilIndex (int): 土地索引
            field (str): 需更新的字段名
            value: 新值

        Returns:
            None
        """
        async with cls._transaction():
            await cls.m_pDB.execute(
                f"UPDATE userSoil SET {field} = ? WHERE uid = ? AND soilIndex = ?",
                (value, uid, soilIndex)
            )

    @classmethod
    async def deleteUserSoil(cls, uid: str, soilIndex: int):
        """删除指定用户的土地记录

        Args:
            uid (str): 用户ID
            soilIndex (int): 土地索引

        Returns:
            None
        """
        async with cls._transaction():
            await cls.m_pDB.execute(
                "DELETE FROM userSoil WHERE uid = ? AND soilIndex = ?",
                (uid, soilIndex)
            )

    @classmethod
    async def isSoilPlanted(cls, uid: str, soilIndex: int) -> bool:
        """判断指定用户的指定土地是否已种植

        Args:
            uid (str): 用户ID
            soilIndex (int): 土地索引

        Returns:
            bool: 如果 plantName 不为空且 plantTime 大于 0，则视为已种植，返回 True；否则 False
        """
        soilInfo = await cls.getUserSoil(uid, soilIndex)
        if not soilInfo:
            return False

        return bool(soilInfo.get("plantName")) and soilInfo.get("plantTime", 0) > 0

    @classmethod
    async def sowingByPlantName(cls, uid: str, soilIndex: int, plantName: str) -> bool:
        """播种指定作物到用户土地区

        Args:
            uid (str): 用户ID
            soilIndex (int): 土地区索引
            plantName (str): 植物名

        Returns:
            bool: 播种成功返回 True，否则返回 False
        """
        # 校验土地区是否已种植
        soilRecord = await cls.getUserSoil(uid, soilIndex)
        if soilRecord and soilRecord.get("plantName"):
            return False

        # 获取植物配置
        plantCfg = g_pJsonManager.m_pPlant.get("plant", {}).get(plantName)
        if not plantCfg:
            logger.error(f"未知植物: {plantName}")
            return False

        nowTs = int(datetime.now().timestamp())
        matureTs = nowTs + int(plantCfg.get("time", 0)) * 3600

        try:
            async with cls._transaction():
                # 复用原有记录字段，保留土壤状态等信息
                prev = soilRecord or {}
                await cls.deleteUserSoil(uid, soilIndex)
                await cls.insertUserSoil({
                    "uid": uid,
                    "soilIndex": soilIndex,
                    "plantName": plantName,
                    "plantTime": nowTs,
                    "matureTime": matureTs,
                    # 保留之前的土壤等级和状态字段，避免数据丢失
                    "soilLevel": prev.get("soilLevel", 0),
                    "wiltStatus": prev.get("wiltStatus", 0),
                    "fertilizerStatus": prev.get("fertilizerStatus", 0),
                    "bugStatus": prev.get("bugStatus", 0),
                    "weedStatus": prev.get("weedStatus", 0),
                    "waterStatus": prev.get("waterStatus", 0)
                })
            return True
        except Exception as e:
            logger.error(f"真寻农场播种失败！", e=e)
            return False
