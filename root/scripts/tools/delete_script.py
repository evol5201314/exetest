#!/usr/bin/env python3
# -*- coding: utf-8 -*-
beizhu = "🗑️ 删除脚本（支持参数）"

import os, sys, argparse
SCRIPTS_DIR = "/root/scripts"

parser = argparse.ArgumentParser()
parser.add_argument('--name', required=True)
args = parser.parse_args()

name = args.name.strip()
if '/' in name or '\\' in name:
    print("❌ 文件名不合法")
    sys.exit(1)
path = os.path.join(SCRIPTS_DIR, name)
if not os.path.exists(path):
    print(f"❌ 文件 {name} 不存在")
    sys.exit(1)
os.remove(path)
print(f"✅ {name} 已删除")
