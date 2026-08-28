#!/usr/bin/env python3
# -*- coding: utf-8 -*-
beizhu = "▶ 运行指定脚本（包装脚本，用于显示输出）"
"""
================================================================
⚠️ 核心原则：轻量化是绝对核心 请勿删除或违反以下规则
================================================================

【硬件环境】
  路由可用内存仅≈30M，精简python3，峰值内存控制最小化
  自动适配 Windows/Linux/OpenWrt 平台

【核心原则】
  1. 日志规则遵循程序设定 不强制写日志
  2. 脚本本身输出日志才写日志到文件 无日志输出不写日志到文件 降低闪存读写
  3. 严禁将任何附属功能的代码合并到主面板 app.py 中
  4. 主面板 app.py 只负责：路由 + 调用独立脚本 + 显示结果
  5. 所有独立脚本放在 /root/scripts/tools/ 目录下（Windows 测试环境为 D:\tmp\scripts\tools）
  6. 所有弹窗 HTML 动态加载，不写死在主面板中
================================================================
"""
import os, sys, subprocess, argparse, io
from datetime import datetime

# ========== 修复 Windows 控制台 UTF-8 支持 ==========
if sys.platform == 'win32':
    # 重新包装 stdout/stderr，强制使用 UTF-8 编码
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
# =====================================================

# ========== 平台兼容路径配置（与主面板保持一致） ==========
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
        # ---------- 关键修复：强制子进程也使用 UTF-8 ----------
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'   # 让子进程的 print 也输出 UTF-8
        
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            encoding='utf-8',        # 解码子进程输出为 UTF-8
            timeout=300,
            env=env                  # 传递环境变量
        )
        # ------------------------------------------------
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
