"""真寻和NoneBot的日志生命周期；AstrBot构建使用宿主专用实现。"""

import logging


def has_console_handler(target):
    while target is not None:
        if any(isinstance(handler, logging.StreamHandler)
               and not isinstance(handler, logging.FileHandler)
               and handler.level <= logging.INFO
               for handler in target.handlers):
            return True
        target = target.parent if target.propagate else None
    return False


def open_logs(data_dir):
    target = logging.getLogger(__package__)
    file_handler = logging.FileHandler(
        data_dir / 'farm-preview.log', encoding='utf-8',
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s %(name)s %(message)s',
    ))
    target.setLevel(logging.INFO)
    target.addHandler(file_handler)
    console_handler = None
    if not has_console_handler(target):
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s [农场] %(message)s', datefmt='%H:%M:%S',
        ))
        target.addHandler(console_handler)
    return file_handler, console_handler


def close_logs(file_handler, console_handler):
    target = logging.getLogger(__package__)
    for handler in (file_handler, console_handler):
        if handler is not None:
            target.removeHandler(handler)
            handler.close()
