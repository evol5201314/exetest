#!/usr/bin/env python3
# -*- coding: utf-8 -*-
beizhu = "📤 上传脚本（从当前目录选择 .py 文件）"

import os, sys, shutil
SCRIPTS_DIR = "/root/scripts"
print("📤 上传脚本（请将要上传的 .py 文件放在当前目录）")
files = [f for f in os.listdir('.') if f.endswith('.py') and os.path.isfile(f)]
if not files:
    print("❌ 当前目录没有 .py 文件")
    sys.exit(1)
print("📋 可用文件:")
for i, f in enumerate(files):
    print(f"  {i+1}. {f}")
try:
    idx = int(input("选择文件编号: ")) - 1
    name = files[idx]
except:
    print("❌ 无效选择")
    sys.exit(1)
dst = os.path.join(SCRIPTS_DIR, name)
if os.path.exists(dst):
    overwrite = input(f"⚠️ {name} 已存在，覆盖？(y/N): ")
    if overwrite.lower() != 'y':
        print("ℹ️ 取消上传")
        sys.exit(0)
shutil.copy2(name, dst)
print(f"✅ {name} 上传成功")
