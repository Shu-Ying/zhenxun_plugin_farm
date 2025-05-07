from pathlib import Path

from zhenxun.configs.path_config import DATA_PATH

g_sDBPath = DATA_PATH / "farm_db"
g_sDBFilePath = DATA_PATH / "farm_db/farm.db"

g_sResourcePath = Path(__file__).resolve().parent / "resource"
