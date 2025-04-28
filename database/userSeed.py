from typing import Optional

from database import CSqlManager

from zhenxun.services.log import logger


class CUserSeedDB(CSqlManager):
    @classmethod
    async def initDB(cls):
        #用户Uid
        #种子名称
        #数量
        userSeed = {
            "uid": "INTEGER NOT NULL",
            "seed": "TEXT NOT NULL",
            "count": "INTEGER NOT NULL DEFAULT 0",
            "PRIMARY KEY": "(uid, seed)"
        }

        await cls.ensureTableSchema("userSeed", userSeed)

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
            logger.warning(f"真寻农场addUserSeedByUid 失败！", e=e)
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
            logger.warning(f"真寻农场getUserSeedByName 查询失败！", e=e)
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
            logger.warning(f"真寻农场updateUserSeedByName失败！", e=e)
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
            logger.warning(f"真寻农场deleteUserSeedByName 删除失败！", e=e)
            return False
