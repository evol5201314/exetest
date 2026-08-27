#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# btn: 🌐 路由器
# group: router
# order: 10
# action: runTool:btn_luci.py
# btn-class: btn-dark-blue

import subprocess

try:
    ip = subprocess.run(["uci", "get", "network.lan.ipaddr"], capture_output=True, text=True, timeout=2).stdout.strip()
    if ip and '/' in ip:
        ip = ip.split('/')[0]
except:
    ip = "192.168.1.2"

if not ip:
    ip = "192.168.1.2"

print(f"REDIRECT:http://{ip}/cgi-bin/luci")
