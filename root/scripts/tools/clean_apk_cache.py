#!/usr/bin/env python3
# -*- coding: utf-8 -*-
beizhu = "🧹 清理 APK 缓存"

import subprocess, sys

try:
    result = subprocess.run(['apk', 'cache', 'clean'], capture_output=True, text=True, timeout=30)
    if result.returncode == 0:
        print("✅ APK 缓存已清理")
    else:
        result = subprocess.run(['apk', 'cache', 'purge'], capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print("✅ APK 缓存已清理（purge）")
        else:
            print(f"❌ 清理失败: {result.stderr}")
            sys.exit(1)
except Exception as e:
    print(f"❌ 执行异常: {e}")
    sys.exit(1)
