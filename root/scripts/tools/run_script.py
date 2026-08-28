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
  5. 脚本存放：根脚本目录 /root/scripts，工具脚本放在子目录 /root/scripts/tools/
     Windows 测试环境根 D:\tmp\scripts，工具脚本 D:\tmp\scripts\tools
  6. 所有弹窗 HTML 动态加载，不写死在主面板中

【备注】
  使用capture_output缓存全部子进程输出；若脚本输出超大，存在内存压力。
================================================================
"""
import os
import sys
import subprocess
import argparse
import io
from datetime import datetime


def safe_get_stdio_wrapper():
    """修复Windows utf‑8，兼容管道重定向，避免 AttributeError"""
    if sys.platform == 'win32':
        try:
            if hasattr(sys.stdout, 'buffer'):
                sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
            if hasattr(sys.stderr, 'buffer'):
                sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
        except AttributeError:
            # stdout无buffer(管道/重定向)，跳过包装
            pass


# ========== 平台兼容路径配置（与主面板保持一致） ==========
if os.name == 'nt':
    SCRIPTS_DIR = r"D:\tmp\scripts"
    LOGS_DIR = r"D:\tmp\scripts\logs"
else:
    SCRIPTS_DIR = "/root/scripts"
    LOGS_DIR = "/root/scripts/logs"


def safe_write_log(log_path: str, content: str):
    """
    统一日志写入，捕获IO异常
    规则：内容为空不写入文件；使用覆盖写 w，不追加
    """
    content = content.strip()
    if not content:
        return
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_text = f"=== {timestamp} ===\n{content}\n"
    try:
        os.makedirs(LOGS_DIR, exist_ok=True)
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(log_text)
    except (OSError, IOError):
        # 磁盘满/权限不足，静默跳过写日志，不中断主流程
        pass


def main():
    safe_get_stdio_wrapper()
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', required=True,
                        help='脚本名，支持内部子目录如 tools/demo.py；禁止../和绝对路径')
    args = parser.parse_args()

    arg_name = args.name
    # 第一层防护：拦截绝对路径、向上回溯
    if os.path.isabs(arg_name) or ".." in arg_name:
        print(f"❌ 非法脚本路径，禁止绝对路径或向上跳转: {arg_name}")
        sys.exit(1)

    script_path = os.path.join(SCRIPTS_DIR, arg_name)

    # 【调整顺序】先判断文件是否存在，不存在直接退出，避免对不存在文件做realpath
    if not os.path.exists(script_path):
        print(f"❌ 脚本不存在: {script_path}")
        sys.exit(1)

    # 第二层防护：realpath展开，拦截符号链接逃逸
    real_script = os.path.realpath(script_path)
    real_base = os.path.realpath(SCRIPTS_DIR)
    if not real_script.startswith(real_base + os.sep):
        print(f"❌ 路径越界拦截：{arg_name}")
        sys.exit(1)

    env = os.environ.copy()
    env['PYTHONIOENCODING'] = 'utf-8'
    # 子目录脚本路径分隔符转为下划线，日志统一放在logs目录
    safe_log_filename = arg_name.replace("/", "_").replace("\\", "_") + ".log"
    log_path = os.path.join(LOGS_DIR, safe_log_filename)

    try:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=300,
            env=env
        )
        output = (result.stdout or '') + (result.stderr or '')
        if result.returncode != 0:
            print(f"⚠️ 脚本退出码: {result.returncode}")
        print(output)

        safe_write_log(log_path, output)
        sys.exit(result.returncode)

    except subprocess.TimeoutExpired as e:
        partial_out = ""
        if e.stdout:
            partial_out += str(e.stdout)
        if e.stderr:
            partial_out += str(e.stderr)
        msg = "⏱ 执行超时（300秒）\n" + partial_out
        print(msg)
        safe_write_log(log_path, msg)
        sys.exit(1)

    except Exception as e:
        msg = f"❌ 执行异常: {repr(e)}"
        print(msg)
        safe_write_log(log_path, msg)
        sys.exit(1)


if __name__ == "__main__":
    main()
