# -*- coding: utf-8 -*-
"""
股票回测系统 - 主模块
"""

import sys
import os

# 确保当前目录在路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui import start_server


def main():
    """主程序入口"""
    print("=" * 50)
    print("        股票回测系统 v1.0")
    print("=" * 50)
    print()
    print("启动Web服务...")
    print()
    
    # 启动Web服务器
    start_server(host='127.0.0.1', port=5000, debug=False)


if __name__ == "__main__":
    main()
