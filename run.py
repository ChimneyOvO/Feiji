"""
飞记 (FeiJi) 根目录快捷启动脚本
"""

import sys
import os

# 将当前根目录添加至 Python 模块搜索路径
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from feiji.main import main

if __name__ == "__main__":
    main()
