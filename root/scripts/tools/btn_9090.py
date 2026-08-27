#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# btn: 🔧 后端
# group: router
# order: 15
# action: runTool:btn_9090.py
# btn-class: btn-deep-orange

import subprocess

try:
    ip = subprocess.run(["uci", "get", "network.lan.ipaddr"], capture_output=True, text=True, timeout=2).stdout.strip()
    if ip and '/' in ip:
        ip = ip.split('/')[0]
except:
    ip = "192.168.1.1"

if not ip:
    ip = "192.168.1.1"

print(f"REDIRECT:http://{ip}:9090/ui")
