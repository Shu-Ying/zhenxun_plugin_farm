import math
import os
import re
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from io import StringIO
from math import e
from typing import Any, Dict, List, Optional

import aiosqlite

from zhenxun.services.log import logger

from .config import g_pJsonManager, g_sDBFilePath, g_sDBPath


class CSqlManager:
    def __init__(self):
        g_sDBPath.mkdir(parents=True, exist_ok=True)

    @classmethod
    async def cleanup(cls):
        if cls.m_pDB:
            await cls.m_pDB.close()

    @classmethod
    async def init(cls) -> bool:
        bIsExist = os.path.exists(g_sDBFilePath)

        cls.m_pDB = await aiosqlite.connect(g_sDBFilePath)
        cls.m_pDB.row_factory = aiosqlite.Row

        await cls.checkDB()

        return True

    @classmethod
    @asynccontextmanager
    async def _transaction(cls):
        await cls.m_pDB.execute("BEGIN;")
        try:
            yield
        except:
            await cls.m_pDB.execute("ROLLBACK;")
            raise
        else:
            await cls.m_pDB.execute("COMMIT;")

    @classmethod
    async def getTableInfo(cls, tableName: str) -> list:
        if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', tableName):
            raise ValueError(f"Illegal table name: {tableName}")
        try:
            cursor = await cls.m_pDB.execute(f'PRAGMA table_info("{tableName}")')
            rows = await cursor.fetchall()
            return [{"name": row[1], "type": row[2]} for row in rows]
        except aiosqlite.Error:
            return []


    @classmethod
    async def ensureTableSchema(cls, tableName: str, columns: dict) -> bool:
        """由AI生成
        创建表或为已存在表添加缺失字段。
        返回 True 表示有变更（创建或新增列），False 则无操作

        Args:
            tableName (_type_): 表名
            columns (_type_): 字典

        Returns:
            _type_: _description_
        """

        info = await cls.getTableInfo(tableName)
        existing = {col['name']: col['type'].upper() for col in info}
        desired = {k: v.upper() for k, v in columns.items() if k != "PRIMARY KEY"}
        primaryKey = columns.get("PRIMARY KEY", "")

        if not existing:
            colsDef = ", ".join(f'"{k}" {v}' for k, v in desired.items())
            if primaryKey:
                colsDef += f", PRIMARY KEY {primaryKey}"
            await cls.m_pDB.execute(f'CREATE TABLE "{tableName}" ({colsDef});')
            return True

        toAdd = [k for k in desired if k not in existing]
        toRemove = [k for k in existing if k not in desired]
        typeMismatch = [k for k in desired if k in existing and existing[k] != desired[k]]

        if toAdd and not toRemove and not typeMismatch:
            for col in toAdd:
                await cls.m_pDB.execute(
                    f'ALTER TABLE "{tableName}" ADD COLUMN "{col}" {columns[col]}'
                )
            return True

        async with cls._transaction():
            tmpTable = f"{tableName}_new"
            colsDef = ", ".join(f'"{k}" {v}' for k, v in desired.items())
            if primaryKey:
                colsDef += f", PRIMARY KEY {primaryKey}"
            await cls.m_pDB.execute(f'CREATE TABLE "{tmpTable}" ({colsDef});')

            commonCols = [k for k in desired if k in existing]
            if commonCols:
                colsStr = ", ".join(f'"{c}"' for c in commonCols)
                await cls.m_pDB.execute(
                    f'INSERT INTO "{tmpTable}" ({colsStr}) SELECT {colsStr} FROM "{tableName}";'
                )
            await cls.m_pDB.execute(f'DROP TABLE "{tableName}";')
            await cls.m_pDB.execute(f'ALTER TABLE "{tmpTable}" RENAME TO "{tableName}";')
        return True

    @classmethod
    async def checkDB(cls) -> bool:
        #1. 用户表
        userInfo = {
            "uid": "INTEGER PRIMARY KEY AUTOINCREMENT",
            "name": "TEXT NOT NULL",
            "exp": "INTEGER DEFAULT 0",
            "point": "INTEGER DEFAULT 0",
            "soil": "INTEGER DEFAULT 3",
            "stealing": "TEXT DEFAULT NULL"
        }
        #2. 土地表
        userSoilInfo = {
            "uid": "INTEGER PRIMARY KEY AUTOINCREMENT",
            **{f"soil{i}": "TEXT DEFAULT ''" for i in range(1, 31)}
        }
        #3. 用户作物明细表
        userPlant = {
            "uid": "INTEGER NOT NULL",
            "plant": "TEXT NOT NULL",
            "count": "INTEGER NOT NULL DEFAULT 0",
            #建联合主键保证每个品种一行
            "PRIMARY KEY": "(uid, plant)"
        }
        #4. 用户种子明细表
        userSeed = {
            "uid": "INTEGER NOT NULL",
            "seed": "TEXT NOT NULL",
            "count": "INTEGER NOT NULL DEFAULT 0",
            "PRIMARY KEY": "(uid, seed)"
        }

        #建表（或增列）
        await cls.ensureTableSchema("user", userInfo)
        await cls.ensureTableSchema("soil", userSoilInfo)
        await cls.ensureTableSchema("userPlant", userPlant)
        await cls.ensureTableSchema("userSeed", userSeed)

        return True

    @classmethod
    async def executeDB(cls, command: str) -> bool:
        """执行自定义SQL

        Args:
            command (str): SQL语句

        Returns:
            bool: 是否执行成功
        """
        if len(command) <= 0:
            logger.warning("数据库语句长度为空！")
            return False

        try:
            async with cls._transaction():
                await cls.m_pDB.execute(command)
            return True
        except Exception as e:
            logger.warning("数据库语句执行出错:" + command)
            return False

    @classmethod
    async def initUserInfoByUid(cls, uid: str, name: str = "", exp: int = 0, point: int = 100):
        """初始化用户信息

        Args:
            uid (str): 用户Uid
            name (str): 农场名称
            exp (int): 农场经验
            point (int): 农场币
        """

        #用户信息
        userInfo =  f"""
            INSERT INTO user (uid, name, exp, point, soil, stealing) VALUES ({uid}, '{name}', {exp}, {point}, 3, '{date.today()}|5')
            """

        #用户仓库
        userStorehouse = f"""
            INSERT INTO storehouse (uid) VALUES ({uid});
            """

        #用户土地
        userSoilInfo = f"""
            INSERT INTO soil (uid) VALUES ({uid});
            """

        if not await cls.executeDB(userInfo):
            return False

        if not await cls.executeDB(userStorehouse):
            return False

        if not await cls.executeDB(userSoilInfo):
            return False

        return "开通农场成功"

    @classmethod
    async def getUserInfoByUid(cls, uid: str) -> dict:
        """根据用户Uid获取用户信息

        Args:
            uid (str): 用户Uid

        Returns:
            list[dict]: 用户信息
        """
        if len(uid) <= 0:
            return {}

        try:
            async with cls.m_pDB.execute(
                "SELECT * FROM user WHERE uid = ?", (uid,)
            ) as cursor:
                async for row in cursor:
                    userDict = {
                        "uid": row[0],
                        "name": row[1],
                        "exp": row[2],
                        "point": row[3],
                        "soil": row[4],
                        "stealing": row[5]
                    }

                    return userDict
            return {}
        except Exception as e:
            logger.warning(f"getUserInfoByUid查询失败: {e}")
            return {}

    @classmethod
    async def getUserPointByUid(cls, uid: str) -> int:
        """根据用户Uid获取用户农场币

        Args:
            uid (str): 用户Uid

        Returns:
            int: 用户农场币
        """
        if len(uid) <= 0:
            return -1

        try:
            async with cls.m_pDB.execute(f"SELECT point FROM user WHERE uid = {uid}") as cursor:
                async for row in cursor:
                    return int(row[0])

            return -1
        except Exception as e:
            logger.warning(f"getUserPointByUid查询失败: {e}")
            return -1

    @classmethod
    async def updateUserPointByUid(cls, uid: str, point: int) -> int:
        """根据用户Uid修改用户农场币

        Args:
            uid (str): 用户Uid
            point (int): 要更新的新农场币数量（需 ≥ 0）

        Returns:
            int: 更新后的农场币数量（成功时），-1（失败时）
        """

        if len(uid) <= 0:
            logger.warning("参数校验失败: uid为空或农场币值无效")
            return -1

        try:
            return await cls.executeDB(f"UPDATE user SET point = {point} WHERE uid = {uid}")
        except Exception as e:
            logger.error(f"金币更新失败: {e}")
            return -1

    @classmethod
    async def getUserExpByUid(cls, uid: str) -> int:
        """根据用户Uid获取用户经验

        Args:
            uid (str): 用户Uid

        Returns:
            int: 用户经验值
        """
        if len(uid) <= 0:
            return -1

        try:
            async with cls.m_pDB.execute(f"SELECT exp FROM user WHERE uid = {uid}") as cursor:
                async for row in cursor:
                    return int(row[0])

            return -1
        except Exception as e:
            logger.warning(f"getUserLevelByUid查询失败: {e}")
            return -1

    @classmethod
    async def UpdateUserExpByUid(cls, uid: str, exp: int) -> bool:
        """根据用户Uid刷新用户经验

        Args:
            uid (str): 用户Uid

        Returns:
            bool: 是否成功
        """
        if len(uid) <= 0:
            return False

        sql = f"UPDATE user SET exp = '{exp}' WHERE uid = {uid}"

        return await cls.executeDB(sql)

    @classmethod
    async def getUserLevelByUid(cls, uid: str) -> tuple[int, int, int]:
        """根据用户Uid获取用户等级

        Args:
            uid (str): 用户Uid

        Returns:
            tuple[int, int, int]: (当前等级, 下级所需经验, 当前等级剩余经验)
        """
        if len(uid) <= 0:
            return -1, -1, -1

        try:
            async with cls.m_pDB.execute(f"SELECT exp FROM user WHERE uid = {uid}") as cursor:
                async for row in cursor:
                    exp = int(row[0])

                    level = exp // 200
                    nextLevelExp = 200 * (level + 1)

                    currentLevelExp = level * 200
                    remainingExp = exp - currentLevelExp

                    return level, nextLevelExp, remainingExp

            return -1, -1, -1
        except Exception as e:
            logger.warning(f"getUserLevelByUid查询失败: {e}")
            return -1, -1, -1

    @classmethod
    async def getUserSoilByUid(cls, uid: str) -> int:
        """根据用户Uid获取解锁地块

        Args:
            uid (str): 用户Uid

        Returns:
            int: 解锁几块地
        """
        if len(uid) <= 0:
            return 0

        async with cls.m_pDB.execute(f"SELECT soil FROM user WHERE uid = {uid}") as cursor:
            async for row in cursor:
                if not row[0]:
                    return 0
                else:
                    return int(row[0])

        return 0

    @classmethod
    async def getUserSoilStatusBySoilID(cls, uid: str, soil: str) -> tuple[bool, str]:
        """根据土地块获取用户土地状态

        Args:
            uid (str): 用户Uid
            soil (str): 土地id

        Returns:
            tuple[bool, str]: [是否可以播种，土地信息]
        """
        if len(uid) <= 0:
            return False, ""

        async with cls.m_pDB.execute(f"SELECT {soil} FROM soil WHERE uid = {uid}") as cursor:
            async for row in cursor:
                if row[0] == None or len(row[0]) <= 0:
                    return True, ""
                else:
                    return False, row[0]

        return False, ""

    @classmethod
    async def updateUserSoilStatusByPlantName(cls, uid: str, soil: str,
                                              plant: str = "",
                                              status: int = 0) -> bool:
        """根据种子名称使用户播种

        Args:
            uid (str): 用户Uid
            soil (str): 土地id
            plant (str): 种子名称

        Returns:
            bool: 是否更新成功
        """

        if len(uid) <= 0:
            return False

        if len(plant) <= 0 and status == 4:
            s = f",,,{status},"
        elif len(plant) <= 0 and status != 4:
            s = ""
        else:
            #获取种子信息 这里能崩我吃
            plantInfo = g_pJsonManager.m_pPlant['plant'][plant]

            currentTime = datetime.now()
            newTime = currentTime + timedelta(hours=int(plantInfo['time']))

            #0: 种子名称
            #1: 种下时间
            #2: 预计成熟时间
            #3: 地状态：0：无 1：长草 2：生虫 3：缺水 4：枯萎
            #4: 是否被偷 示例：QQ号-偷取数量|QQ号-偷取数量
            #5: 土地等级 0：普通 1：红土地 2：黑土地 3：金土地 4：紫晶土地 5：蓝晶土地 6：黑晶土地
            s = f"{plant},{int(currentTime.timestamp())},{int(newTime.timestamp())},{status},,"

        sql = f"UPDATE soil SET {soil} = '{s}' WHERE uid = {uid}"

        return await cls.executeDB(sql)


    @classmethod
    async def addUserSeedByUid(cls, uid: str, seed: str, count: int = 1) -> bool:
        """根据用户uid添加种子信息

        Args:
            uid (str): 用户uid
            seed (str): 种子名称
            count (int): 数量

        Returns:
            bool: 是否添加成功
        """
        try:
            async with cls._transaction():
                #检查是否已存在该种子
                async with cls.m_pDB.execute(
                    "SELECT count FROM userSeed WHERE uid = ? AND seed = ?",
                    (uid, seed)
                ) as cursor:
                    row = await cursor.fetchone()

                if row:
                    #如果种子已存在，则更新数量
                    newCount = row[0] + count
                    await cls.m_pDB.execute(
                        "UPDATE userSeed SET count = ? WHERE uid = ? AND seed = ?",
                        (newCount, uid, seed)
                    )
                else:
                    #如果种子不存在，则插入新记录
                    newCount = count
                    await cls.m_pDB.execute(
                        "INSERT INTO userSeed (uid, seed, count) VALUES (?, ?, ?)",
                        (uid, seed, count)
                    )

                #如果种子数量为 0，删除记录
                if newCount <= 0:
                    await cls.m_pDB.execute(
                        "DELETE FROM userSeed WHERE uid = ? AND seed = ?",
                        (uid, seed)
                    )
            return True
        except Exception as e:
            logger.warning(f"真寻农场addUserSeedByUid 失败: {e}")
            return False

    @classmethod
    async def getUserSeedByName(cls, uid: str, seed: str) -> Optional[int]:
        """根据种子名称获取种子数量

        Args:
            uid (str): 用户uid
            seed (str): 种子名称

        Returns:
            Optional[int]: 种子数量
        """

        try:
            async with cls.m_pDB.execute(
                "SELECT count FROM userSeed WHERE uid = ? AND seed = ?",
                (uid, seed)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None
        except Exception as e:
            logger.warning(f"真寻农场getUserSeedByName 查询失败: {e}")
            return None

    @classmethod
    async def getUserSeedByUid(cls, uid: str) -> dict:
        """根据用户Uid获取仓库全部种子信息

        Args:
            uid (str): 用户uid

        Returns:
            dict: 种子信息
        """

        cursor = await cls.m_pDB.execute(
            "SELECT seed, count FROM userSeed WHERE uid=?",
            (uid,)
        )
        rows = await cursor.fetchall()
        return {row["seed"]: row["count"] for row in rows}

    @classmethod
    async def updateUserSeedByName(cls, uid: str, seed: str, count: int) -> bool:
        """根据种子名称更新种子数量

        Args:
            uid (str): 用户uid
            seed (str): 种子名称
            count (int): 种子数量

        Returns:
            bool: 是否成功
        """
        try:
            if count <= 0:
                return await cls.deleteUserSeedByName(uid, seed)

            async with cls._transaction():
                await cls.m_pDB.execute(
                    "UPDATE userSeed SET count = ? WHERE uid = ? AND seed = ?",
                    (count, uid, seed)
                )
            return True
        except Exception as e:
            logger.warning(f"真寻农场updateUserSeedByName失败:{e}")
            return False

    @classmethod
    async def deleteUserSeedByName(cls, uid: str, seed: str) -> bool:
        """根据种子名称从种子仓库中删除种子

        Args:
            uid (str): 用户uid
            seed (str): 种子名称

        Returns:
            bool: 是否成功
        """
        try:
            async with cls._transaction():
                await cls.m_pDB.execute(
                    "DELETE FROM userSeed WHERE uid = ? AND seed = ?",
                    (uid, seed)
                )
            return True
        except Exception as e:
            logger.warning(f"真寻农场deleteUserSeedByName 删除失败: {e}")
            return False

    @classmethod
    async def addUserPlantByUid(cls, uid: str, plant: str, count: int = 1) -> bool:
        """根据用户uid添加作物信息

        Args:
            uid (str): 用户uid
            plant (str): 作物名称
            count (int): 数量

        Returns:
            bool: 是否添加成功
        """
        try:
            async with cls._transaction():
                #检查是否已存在该作物
                async with cls.m_pDB.execute(
                    "SELECT count FROM userPlant WHERE uid = ? AND plant = ?",
                    (uid, plant)
                ) as cursor:
                    row = await cursor.fetchone()

                if row:
                    #如果作物已存在，则更新数量
                    new_count = row[0] + count
                    await cls.m_pDB.execute(
                        "UPDATE userPlant SET count = ? WHERE uid = ? AND plant = ?",
                        (new_count, uid, plant)
                    )
                else:
                    #如果作物不存在，则插入新记录
                    await cls.m_pDB.execute(
                        "INSERT INTO userPlant (uid, plant, count) VALUES (?, ?, ?)",
                        (uid, plant, count)
                    )
            return True
        except Exception as e:
            logger.warning(f"真寻农场addUserPlantByUid 失败: {e}")
            return False

    @classmethod
    async def getUserPlantByUid(cls, uid: str) -> Dict[str, int]:
        """根据用户uid获取全部作物信息

        Args:
            uid (str): 用户uid

        Returns:
            Dict[str, int]: 作物名称和数量
        """
        cursor = await cls.m_pDB.execute(
            "SELECT plant, count FROM userPlant WHERE uid=?",
            (uid,)
        )
        rows = await cursor.fetchall()
        return {row["plant"]: row["count"] for row in rows}

    @classmethod
    async def getUserPlantByName(cls, uid: str, plant: str) -> Optional[int]:
        """根据作物名称获取用户的作物数量

        Args:
            uid (str): 用户uid
            plant (str): 作物名称

        Returns:
            Optional[int]: 作物数量
        """
        try:
            async with cls.m_pDB.execute(
                "SELECT count FROM userPlant WHERE uid = ? AND plant = ?",
                (uid, plant)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None
        except Exception as e:
            logger.warning(f"真寻农场getUserPlantByName 查询失败: {e}")
            return None

    @classmethod
    async def updateUserPlantByName(cls, uid: str, plant: str, count: int) -> bool:
        """更新 userPlant 表中某个作物的数量

        Args:
            uid (str): 用户uid
            plant (str): 作物名称
            count (int): 新的作物数量

        Returns:
            bool: 是否更新成功
        """
        try:
            if count <= 0:
                return await cls.deleteUserPlantByName(uid, plant)

            async with cls._transaction():
                await cls.m_pDB.execute(
                    "UPDATE userPlant SET count = ? WHERE uid = ? AND plant = ?",
                    (count, uid, plant)
                )
            return True
        except Exception as e:
            logger.warning(f"真寻农场updateUserPlantByName失败:{e}")
            return False

    @classmethod
    async def deleteUserPlantByName(cls, uid: str, plant: str) -> bool:
        """从 userPlant 表中删除某个作物记录

        Args:
            uid (str): 用户uid
            plant (str): 作物名称

        Returns:
            bool: 是否删除成功
        """
        try:
            async with cls._transaction():
                await cls.m_pDB.execute(
                    "DELETE FROM userPlant WHERE uid = ? AND plant = ?",
                    (uid, plant)
                )
            return True
        except Exception as e:
            logger.warning(f"真寻农场deleteUserPlantByName 失败: {e}")
            return False

g_pSqlManager = CSqlManager()
