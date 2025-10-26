from zhenxun.services.log import logger

from .database import CSqlManager


class CUserPlantCountDB(CSqlManager):
    @classmethod
    async def initDB(cls):
        userPlantCount = {
            "uid": "TEXT NOT NULL",  # 用户Uid
            "plant": "TEXT NOT NULL",  # 植物名称
            "count": "INTEGER NOT NULL DEFAULT 0",  # 数量
            "PRIMARY KEY": "(uid, plant)",
        }

        await cls.ensureTableSchema("userPlantCount", userPlantCount)

    @classmethod
    async def addUserPlantCountByUid(cls, uid: str, plant: str, count: int = 1) -> bool:
        """根据用户uid添加植物的收获次数

        Args:
            uid (str): 用户uid
            plant (str): 植物名称
            count (int): 数量

        Returns:
            bool: 是否添加成功
        """
        try:
            async with cls._transaction():
                async with cls.m_pDB.execute(
                    "SELECT count FROM userPlantCount WHERE uid = ? AND plant = ?",
                    (uid, plant),
                ) as cursor:
                    row = await cursor.fetchone()

                if row:
                    newCount = row[0] + count
                    await cls.m_pDB.execute(
                        "UPDATE userPlantCount SET count = ? WHERE uid = ? AND plant = ?",
                        (newCount, uid, plant),
                    )
                else:
                    newCount = count
                    await cls.m_pDB.execute(
                        "INSERT INTO userPlantCount (uid, plant, count) VALUES (?, ?, ?)",
                        (uid, plant, count),
                    )

                if newCount <= 0:
                    await cls.m_pDB.execute(
                        "DELETE FROM userPlantCount WHERE uid = ? AND plant = ?",
                        (uid, plant),
                    )
            return True
        except Exception as e:
            logger.warning("addUserPlantByUid 失败！", e=e)
            return False

    @classmethod
    async def getUserPlantCountByUid(cls, uid: str) -> dict:
        """根据用户Uid获取该用户的所有植物的收获次数

        Args:
            uid (str): 用户uid

        Returns:
            dict: 植物信息
        """

        cursor = await cls.m_pDB.execute(
            "SELECT plant, count FROM userPlantCount WHERE uid=?", (uid,)
        )
        rows = await cursor.fetchall()
        return {row["plant"]: row["count"] for row in rows}

    @classmethod
    async def getUserPlantCountByPlantName(cls, uid: str, plant: str) -> int:
        """根据用户Uid和植物名称获取该对应的收获次数

        Args:
            uid (str): 用户uid
            plant (str): 植物名称

        Returns:
            int: 收获次数
        """
        cursor = await cls.m_pDB.execute(
            "SELECT count FROM userPlantCount WHERE uid = ? AND plant = ?",
            (uid, plant),
        )
        row = await cursor.fetchone()
        return row["count"] if row else 0

    @classmethod
    async def updateUserPlantCountByName(cls, uid: str, plant: str, count: int) -> bool:
        """根据植物名称更新植物的收获次数

        Args:
            uid (str): 用户uid
            plant (str): 植物名称
            count (int): 收获次数

        Returns:
            bool: 是否成功
        """
        try:
            if count <= 0:
                return await cls.deleteUserPlantCountByName(uid, plant)

            async with cls._transaction():
                await cls.m_pDB.execute(
                    "UPDATE userPlantCount SET count = ? WHERE uid = ? AND plant = ?",
                    (count, uid, plant),
                )
            return True
        except Exception as e:
            logger.warning("updateUserPlantByName失败！", e=e)
            return False

    @classmethod
    async def deleteUserPlantCountByName(cls, uid: str, plant: str) -> bool:
        """根据植物名称从植物仓库中删除植物

        Args:
            uid (str): 用户uid
            seed (str): 种子名称

        Returns:
            bool: 是否成功
        """
        try:
            async with cls._transaction():
                await cls.m_pDB.execute(
                    "DELETE FROM userPlantCount WHERE uid = ? AND plant = ?",
                    (uid, plant),
                )
            return True
        except Exception as e:
            logger.warning("deleteUserPlantCountByName 删除失败！", e=e)
            return False
