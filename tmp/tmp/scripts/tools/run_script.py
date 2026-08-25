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
from datetime import datetime

# 【新增】强制将标准输出和错误输出设置为 UTF-8，解决 Windows GBK 报错
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except:
    pass

# 兼容 Windows 和 Linux 的路径
if os.name == 'nt':
    SCRIPTS_DIR = r"D:\tmp\scripts"
    LOGS_DIR = r"D:\tmp\scripts\logs"
else:
    SCRIPTS_DIR = "/root/scripts"
    LOGS_DIR = "/root/scripts/logs"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', required=True, help='脚本名')
    args = parser.parse_args()
    
    script_path = os.path.join(SCRIPTS_DIR, args.name)
    if not os.path.exists(script_path):
        print(f"❌ 脚本 {args.name} 不存在")
        sys.exit(1)
    
    # 确保日志目录存在
    os.makedirs(LOGS_DIR, exist_ok=True)

    try:
        # 【修改】把 'python3' 改成 'sys.executable'，并在子进程输出时强制使用 utf-8 解码
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=300
        )
        # 【新增】防止 stdout 或 stderr 返回 None 导致报错
        output = (result.stdout or '') + (result.stderr or '')
        if result.returncode != 0:
            print(f"⚠️ 脚本退出码: {result.returncode}")
        print(output)

        # ---------- 遵守核心原则：有输出时才写日志文件 ----------
        if output.strip():
            log_path = os.path.join(LOGS_DIR, f"{args.name}.log")
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write(f"=== {timestamp} ===\n{output}")
        # ------------------------------------------------------------

        sys.exit(result.returncode)

    except subprocess.TimeoutExpired:
        msg = "⏱ 执行超时（300秒）"
        print(msg)
        log_path = os.path.join(LOGS_DIR, f"{args.name}.log")
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(msg)
        sys.exit(1)
    except Exception as e:
        msg = f"❌ 执行异常: {e}"
        print(msg)
        log_path = os.path.join(LOGS_DIR, f"{args.name}.log")
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(msg)
        sys.exit(1)

if __name__ == "__main__":
    main()