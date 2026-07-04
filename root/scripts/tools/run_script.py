#!/usr/bin/env python3
# -*- coding: utf-8 -*-
beizhu = "▶ 运行指定脚本（包装脚本，用于显示输出）"
"""
================================================================
⚠️ 核心原则：轻量化是绝对核心 请勿删除或违反以下规则
================================================================

【硬件环境】
  路由可用内存仅≈30M，精简python3，峰值内存控制最小化

【核心原则】
  1. 日志规则遵循程序设定 不强制写日志
  2. 脚本本身输出日志才写日志到文件 无日志输出不写日志到文件 降低闪存读写
  3. 严禁将任何附属功能的代码合并到主面板 app.py 中
  4. 主面板 app.py 只负责：路由 + 调用独立脚本 + 显示结果
  5. 所有独立脚本放在 /root/scripts/tools/ 目录下
  6. 所有弹窗 HTML 动态加载，不写死在主面板中
  ================================================================
"""
import os, sys, subprocess, argparse

SCRIPTS_DIR = "/root/scripts"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', required=True, help='脚本名')
    args = parser.parse_args()
    
    script_path = os.path.join(SCRIPTS_DIR, args.name)
    if not os.path.exists(script_path):
        print(f"❌ 脚本 {args.name} 不存在")
        sys.exit(1)
    
    try:
        result = subprocess.run(
            ['python3', script_path],
            capture_output=True,
            text=True,
            timeout=300
        )
        output = result.stdout + result.stderr
        if result.returncode != 0:
            print(f"⚠️ 脚本退出码: {result.returncode}")
        print(output)
        sys.exit(result.returncode)
    except subprocess.TimeoutExpired:
        print("⏱ 执行超时（300秒）")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 执行异常: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
