#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# btn: 🔄 重启路由
# group: router
# order: 100
# action: runTool:btn_reboot.py
# btn-class: btn-dark-red

import subprocess

subprocess.run(['/sbin/reboot'])
print("✅ 重启命令已执行，路由器即将重启...")
