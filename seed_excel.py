#!/usr/bin/env python3
"""
ECS项目管理系统 - Excel数据导入工具
用法: python3 seed_excel.py /path/to/OGD甘特图数据.xlsx
"""
import sys
sys.path.insert(0, 'app')
from seed import import_excel

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('用法: python3 seed_excel.py /path/to/OGD甘特图数据.xlsx')
        sys.exit(1)
    import_excel(sys.argv[1])
