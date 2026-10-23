"""真寻农场独立预览插件入口。"""

from nonebot.plugin import PluginMetadata
from zhenxun.configs.utils import Command, PluginExtraData, RegisterConfig

from ._version import __version__
from .runtime import COMMANDS, HELP

__plugin_meta__ = PluginMetadata(
    name="真寻农场", description="快乐的农场时光",
    usage=HELP, type="application",
    homepage="https://github.com/Shu-Ying/zhenxun_plugin_farm",
    supported_adapters={"~onebot.v11", "~qq"},
    extra=PluginExtraData(
        author="Shu-Ying", version=__version__, menu_type="群内小游戏",
        commands=[Command(command=name) for name in COMMANDS],
        configs=[RegisterConfig(
            key="农场图片质量", value=75, default_value=75, type=int,
            help="全部农场图片的编码质量，整数1～95，默认75；"
                 "数值越高通常越清晰、文件越大。仅我的农场支持高清，"
                 "高清质量不低于85。PNG为无损格式，不受此值影响。",
        ), RegisterConfig(
            key='资源获取地址', value='Github', default_value='Github',
            type=str, help='Github、Gitea或farm_service，默认Github；重载生效。',
        ), RegisterConfig(
            key='farm_service 地址', value='', default_value='', type=str,
            help='独立服务基础地址，用于资源及后续活动服务；HTTPS。',
        )],
    ).to_dict(),
)

from . import commands
