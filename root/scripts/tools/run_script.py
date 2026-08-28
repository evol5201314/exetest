#!/usr/bin/env python3
# -*- coding: utf-8 -*-
beizhu = "▶ 运行指定脚本（包装脚本，用于显示输出）"
r"""
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
  5. 所有独立脚本放在 /root/scripts/ 目录下（Windows 测试环境为 D:\tmp\scripts），支持子目录，例如 tools/xxx.py
  6. 所有弹窗 HTML 动态加载，不写死在主面板中
================================================================
"""
import os, sys, subprocess, argparse, io
from datetime import datetime

# ========== 修复 Windows 控制台 UTF-8 支持 ==========
if sys.platform == 'win32':
    # 防止重复包装stdout/stderr
    if not isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    if not isinstance(sys.stderr, io.TextIOWrapper):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
# =====================================================

# ========== 平台兼容路径配置 ==========
if os.name == 'nt':
    SCRIPTS_DIR = r"D:\tmp\scripts"
    LOGS_DIR = r"D:\tmp\scripts\logs"
else:
    SCRIPTS_DIR = "/root/scripts"
    LOGS_DIR = "/root/scripts/logs"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', required=True, help='脚本名，支持子目录例如 tools/demo.py')
    args = parser.parse_args()

    script_path = os.path.join(SCRIPTS_DIR, args.name)
    log_name = args.name
    # 本次运行固定屏幕时间戳（全程复用）
    screen_ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if not os.path.exists(script_path):
        print(f"[{screen_ts}] ❌ 脚本 {args.name} 不存在")
        sys.exit(1)

    # 确保日志目录存在，IO异常不崩溃
    try:
        os.makedirs(LOGS_DIR, exist_ok=True)
    except Exception:
        pass
    log_path = os.path.join(LOGS_DIR, f"{log_name}.log")

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
            print(f"[{screen_ts}] ⚠️ 脚本退出码: {result.returncode}")

        # 仅存在输出内容才打印分隔标记，避免空块
        if output.strip():
            print(f"[{screen_ts}] ----脚本输出开始----")
            print(output)
            print(f"[{screen_ts}] ----脚本输出结束----")

        # ---------- 遵守核心原则：有输出时才写日志文件 ----------
        if output.strip():
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            log_content = f"=== {timestamp} ===\n{output}"
            try:
                with open(log_path, 'w', encoding='utf-8') as f:
                    f.write(log_content)
            except Exception:
                # 日志写入失败静默丢弃，不影响业务脚本返回码
                pass
        # ------------------------------------------------------------

        sys.exit(result.returncode)

    except subprocess.TimeoutExpired as e:
        partial_out = (e.stdout or '') + (e.stderr or '')
        msg = "⏱ 执行超时（300秒）"
        full_display = partial_out + msg

        if partial_out.strip():
            print(f"[{screen_ts}] ----脚本输出开始----")
            print(full_display)
            print(f"[{screen_ts}] ----脚本输出结束----")
        else:
            print(f"[{screen_ts}] {msg}")

        # 仅当脚本本体有非空输出才写日志；包装器超时提示不算业务输出
        if partial_out.strip():
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            log_content = f"=== {timestamp} ===\n{full_display}"
            try:
                with open(log_path, 'w', encoding='utf-8') as f:
                    f.write(log_content)
            except Exception:
                pass
        sys.exit(1)

    except Exception as e:
        msg = f"❌ 执行异常: {e}"
        print(f"[{screen_ts}] {msg}")
        # 包装器自身异常，无脚本业务输出，不写日志文件
        sys.exit(1)

if __name__ == "__main__":
    main()
