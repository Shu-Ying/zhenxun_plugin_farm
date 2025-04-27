import os

import httpx

from zhenxun.configs.config import Config
from zhenxun.services.log import logger


class CRequestManager:

    @classmethod
    async def download(cls, url: str, savePath: str, fileName: str) -> bool:
        """下载文件到指定路径并覆盖已存在的文件

        Args:
            url (str): 文件的下载链接
            savePath (str): 保存文件夹路径
            fileName (str): 保存后的文件名

        Returns:
            bool: 是否下载成功
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    fullPath = os.path.join(savePath, fileName)
                    os.makedirs(os.path.dirname(fullPath), exist_ok=True)
                    with open(fullPath, "wb") as f:
                        f.write(response.content)
                    return True
                else:
                    logger.warning(f"文件下载失败: HTTP {response.status_code} {response.text}")
                    return False
        except Exception as e:
            logger.warning(f"下载文件异常: {e}")
            return False

    @classmethod
    async def post(cls, endpoint: str, name: str = "", jsonData: dict = None, formData: dict = None) -> dict:
        """发送POST请求到指定接口，供其他方法统一调用

        Args:
            endpoint (str): 请求的接口路径
            name (str, optional): 操作名称用于日志记录
            jsonData (dict, optional): 以JSON格式发送的数据
            formData (dict, optional): 以表单格式发送的数据

        Raises:
            ValueError: 当jsonData和formData都未提供时抛出

        Returns:
            dict: 返回请求结果的JSON数据
        """
        if jsonData is None and formData is None:
            raise ValueError("post请求必须提供jsonData或formData其中之一")

        baseUrl = Config.get_config("zhenxun_plugin_farm", "服务地址")

        url = f"{baseUrl.rstrip('/')}/{endpoint.lstrip('/')}"

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                if jsonData is not None:
                    response = await client.post(url, json=jsonData)
                else:
                    response = await client.post(url, data=formData)

                if response.status_code == 200:
                    return response.json()
                else:
                    logger.warning(f"真寻农场{name}请求失败: HTTP {response.status_code} {response.text}")
                    return {}
        except httpx.RequestError as e:
            logger.warning(f"真寻农场{name}请求异常: {e}")
            return {}
        except Exception as e:
            logger.warning(f"真寻农场{name}处理异常: {e}")
            return {}


    @classmethod
    async def sign(cls, uid: str) -> str:
        a = await cls.post("http://diuse.work:9099/testPost", jsonData={"level":3})

        result = ""

        type = int(a["type"])
        if type == 1:
            result = f"签到成功 type = 1"
        elif type == 2:
            result = f"签到成功 type = 2"
        else:
            result = f"签到成功 type = {type}"

        return result


g_pRequestManager = CRequestManager()
