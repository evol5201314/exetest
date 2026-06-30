#!/usr/bin/env python3
# -*- coding: utf-8 -*-
beizhu = "📄 查看脚本执行日志（交互式）"

import json, sys, os
STATUS_FILE = "/tmp/script_status.json"
SCRIPTS_DIR = "/root/scripts"

scripts = [f for f in os.listdir(SCRIPTS_DIR) if f.endswith('.py') and os.path.isfile(os.path.join(SCRIPTS_DIR, f))]
if not scripts:
    print("❌ 没有脚本")
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

with open(STATUS_FILE, 'r') as f:
    data = json.load(f)
s = data.get(name, {})
print(f"\n📄 {name}")
print(f"状态: {s.get('status', 'idle')}")
print(f"PID: {s.get('pid', '无')}")
print(f"\n--- 输出 ---")
print(s.get('last_output', '暂无输出'))
