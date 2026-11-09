"""日志配置。

一条日志要能回答四个问题：什么时候、谁、做了什么、结果如何。
"""

import logging
import sys


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
        force=True,
    )
    # httpx 每发一个请求都打一行 INFO，太吵，压到 WARNING
    logging.getLogger("httpx").setLevel(logging.WARNING)
