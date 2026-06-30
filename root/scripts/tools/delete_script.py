#!/usr/bin/env python3
# -*- coding: utf-8 -*-
beizhu = "🗑️ 删除脚本（交互式）"

import os, sys
SCRIPTS_DIR = "/root/scripts"

scripts = [f for f in os.listdir(SCRIPTS_DIR) if f.endswith('.py') and os.path.isfile(os.path.join(SCRIPTS_DIR, f))]
if not scripts:
    print("❌ 没有可删除的脚本")
    sys.exit(1)
print("📋 可用脚本:")
for i, s in enumerate(scripts):
    print(f"  {i+1}. {s}")
try:
    idx = int(input("选择脚本编号: ")) - 1
    name = scripts[idx]
except:
    print("❌ 无效选择")
    sys.exit(1)
confirm = input(f"确定删除 {name}？(y/N): ")
if confirm.lower() == 'y':
    os.remove(os.path.join(SCRIPTS_DIR, name))
    print(f"✅ {name} 已删除")
else:
    print("ℹ️ 取消删除")
