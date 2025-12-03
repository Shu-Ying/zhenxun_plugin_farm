import threading
import time
from typing import Any

from zhenxun.services.log import logger


class CPlayerPool:
    """
    用户池管理类
    管理用户对象的生命周期，支持自动清理超时用户
    """

    def __init__(self, timeoutSeconds: int = 300, cleanupInterval: int = 3600):
        """
        初始化用户池

        Args:
            timeoutSeconds: 用户超时时间（秒），默认5分钟
            cleanupInterval: 清理间隔（秒），默认1小时
        """
        self._players: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()
        self.timeoutSeconds = timeoutSeconds
        self.cleanupInterval = cleanupInterval

        # 启动后台清理线程
        self._cleanupThread = threading.Thread(target=self._cleanupWorker, daemon=True)
        self._running = True
        self._cleanupThread.start()

    def createUser(self, uid: str, userObj: Any) -> bool:
        """
        创建并管理用户对象

        Args:
            uid: 用户ID
            userObj: 用户对象

        Returns:
            bool: 是否创建成功
        """
        with self._lock:
            if uid in self._players:
                logger.debug(f"用户 {uid} 已存在，正在覆盖")
                # 可以选择返回False或者覆盖，这里选择覆盖
                # return False

            self._players[uid] = {
                "object": userObj,
                "lastActive": time.time(),
                "activeCount": 0,
            }
            logger.debug(f"用户 {uid} 创建并开始管理")
            return True

    def getUser(self, uid: str) -> Any | None:
        """
        获取用户对象并刷新活跃时间

        Args:
            uid: 用户ID

        Returns:
            Optional[Any]: 用户对象，如果不存在或已超时则返回None
        """
        with self._lock:
            userData = self._players.get(uid)

            if not userData:
                logger.debug(f"用户 {uid} 不存在")
                return None

            # 检查是否已超时（防御性检查）
            currentTime = time.time()
            if currentTime - userData["lastActive"] > self.timeoutSeconds:
                logger.debug(f"用户 {uid} 在获取操作期间已超时")
                self._removeUser(uid)
                return None

            # 刷新活跃时间
            userData["lastActive"] = currentTime
            userData["activeCount"] += 1

            logger.debug(f"用户 {uid} 获取成功，活跃次数: {userData['activeCount']}")
            return userData["object"]

    def updateUser(self, uid: str, userObj: Any) -> bool:
        """
        更新用户对象

        Args:
            uid: 用户ID
            userObj: 新的用户对象

        Returns:
            bool: 是否更新成功
        """
        with self._lock:
            if uid not in self._players:
                logger.debug(f"用户 {uid} 不存在，无法更新")
                return False

            self._players[uid]["object"] = userObj
            self._players[uid]["lastActive"] = time.time()
            logger.debug(f"用户 {uid} 更新成功")
            return True

    def removeUser(self, uid: str) -> bool:
        """
        主动移除用户

        Args:
            uid: 用户ID

        Returns:
            bool: 是否移除成功
        """
        with self._lock:
            return self._removeUser(uid)

    def _removeUser(self, uid: str) -> bool:
        """内部移除用户方法"""
        if uid in self._players:
            userData = self._players.pop(uid)
            # 如果需要清理资源，可以在这里处理
            if hasattr(userData["object"], "close"):
                try:
                    userData["object"].close()
                except Exception as e:
                    logger.debug(f"关闭用户 {uid} 时出错: {e}")

            logger.debug(f"用户 {uid} 已移除，总活跃次数: {userData['activeCount']}")
            return True
        return False

    def _cleanupWorker(self):
        """后台清理线程的工作函数"""
        while self._running:
            try:
                self._cleanupExpiredUsers()
            except Exception as e:
                logger.debug(f"清理工作线程出错: {e}")

            # 休眠指定间隔
            time.sleep(self.cleanupInterval)

    def _cleanupExpiredUsers(self):
        """清理超时用户"""
        currentTime = time.time()
        expiredUsers = []

        # 首先收集过期的用户ID，避免在迭代中修改字典
        with self._lock:
            for uid, userData in self._players.items():
                if currentTime - userData["lastActive"] > self.timeoutSeconds:
                    expiredUsers.append(uid)

        # 移除过期用户
        for uid in expiredUsers:
            with self._lock:
                # 再次检查，防止在收集和移除之间用户被更新
                if (
                    uid in self._players
                    and currentTime - self._players[uid]["lastActive"]
                    > self.timeoutSeconds
                ):
                    self._removeUser(uid)

        if expiredUsers:
            logger.debug(f"已清理 {len(expiredUsers)} 个过期用户: {expiredUsers}")

    def getActiveUsers(self) -> dict[str, dict[str, Any]]:
        """
        获取当前活跃用户信息

        Returns:
            Dict: 用户信息字典
        """
        with self._lock:
            # 返回副本避免外部修改
            return {
                uid: {
                    "lastActive": data["lastActive"],
                    "activeCount": data["activeCount"],
                    "timeRemaining": self.timeoutSeconds
                    - (time.time() - data["lastActive"]),
                }
                for uid, data in self._players.items()
            }

    def userCount(self) -> int:
        """获取当前用户数量"""
        with self._lock:
            return len(self._players)

    def shutdown(self):
        """关闭用户池，清理资源"""
        self._running = False
        if self._cleanupThread.is_alive():
            self._cleanupThread.join(timeout=5)

        # 清理所有用户
        with self._lock:
            uids = list(self._players.keys())
            for uid in uids:
                self._removeUser(uid)

        logger.debug("用户池关闭完成")


g_pUserPool = CPlayerPool()
