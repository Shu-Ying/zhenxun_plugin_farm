"""真寻农场独立预览插件入口。"""

from nonebot.plugin import PluginMetadata
from zhenxun.configs.utils import Command, PluginExtraData

from ._version import __version__
from .runtime import COMMANDS, HELP

__plugin_meta__ = PluginMetadata(
    name="农场预览", description="共享农场核心的真寻预览版",
    usage=HELP, type="application",
    homepage="https://github.com/Shu-Ying/zhenxun_plugin_farm",
    supported_adapters={"~onebot.v11", "~qq"},
    extra=PluginExtraData(
        author="Shu-Ying", version=__version__, menu_type="群内小游戏",
        commands=[Command(command=name) for name in COMMANDS],
    ).to_dict(),
)

from . import commands
