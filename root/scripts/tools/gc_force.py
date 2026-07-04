#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# btn: 🧹 清理脚本
# group: script
# order: 70
# action: runTool:gc_force.py
# btn-class: btn-gray
beizhu = "🧹 强制垃圾回收"

import gc
gc.collect()
print("✅ 垃圾回收已执行")
