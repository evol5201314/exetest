#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# popup: logModal
# btn: 📄 日志
# group: script
# order: 50
# action: runScript:view_log.py
# btn-class: btn-teal
beizhu = "📄 查看脚本日志 / 清理日志"

import os
import sys
import json
import argparse
import io

# ========== 修复 Windows 控制台 UTF-8 支持 ==========
def safe_wrap_stdio():
    if sys.platform == 'win32':
        try:
            if hasattr(sys.stdout, 'buffer'):
                sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
            if hasattr(sys.stderr, 'buffer'):
                sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
        except AttributeError:
            pass
# =====================================================

# ========== 平台兼容路径配置 ==========
if os.name == 'nt':
    SCRIPTS_DIR = r"D:\tmp\scripts"
    LOGS_DIR = r"D:\tmp\scripts\logs"
else:
    SCRIPTS_DIR = "/root/scripts"
    LOGS_DIR = "/root/scripts/logs"


def safe_log_name(name: str):
    """与runner脚本保持完全一致：把路径分隔符替换下划线生成日志文件名"""
    return name.replace("/", "_").replace("\\", "_") + ".log"


def read_log_file(filepath):
    """安全读取日志文件，自动处理编码问题"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        try:
            with open(filepath, 'r', encoding='gbk') as f:
                return f.read()
        except Exception:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
    except (OSError, IOError):
        return ""


def get_latest_log():
    """返回最近修改的日志文件名和内容，若没有则返回 None"""
    if not os.path.exists(LOGS_DIR):
        return None
    try:
        log_files = [f for f in os.listdir(LOGS_DIR) if f.endswith('.log')]
    except OSError:
        return None
    if not log_files:
        return None
    log_files.sort(key=lambda f: os.path.getmtime(os.path.join(LOGS_DIR, f)), reverse=True)
    latest_file = log_files[0]
    filepath = os.path.join(LOGS_DIR, latest_file)
    content = read_log_file(filepath)
    return latest_file, content


def clear_log(name=None):
    if name is None:
        return "❌ 未指定脚本名"
    log_filename = safe_log_name(name)
    log_path = os.path.join(LOGS_DIR, log_filename)
    try:
        if os.path.exists(log_path):
            os.remove(log_path)
            return f"✅ 已清除 {name} 的日志"
        else:
            return f"📭 {name} 暂无日志文件"
    except OSError:
        return f"❌ 删除失败，权限或磁盘异常：{name}"


def clear_all_logs():
    if not os.path.exists(LOGS_DIR):
        return "📭 日志目录不存在"
    try:
        files = [f for f in os.listdir(LOGS_DIR) if f.endswith('.log')]
        if not files:
            return "📭 没有任何日志文件"
        cnt = len(files)
        for f in files:
            os.remove(os.path.join(LOGS_DIR, f))
        return f"✅ 已清空全部 {cnt} 个日志文件"
    except OSError:
        return "❌ 清空日志失败，IO异常"


def list_all_scripts():
    """递归扫描scripts根目录 + tools子目录，返回相对路径列表，可直接传给runner --name"""
    ret = []
    for root, _, files in os.walk(SCRIPTS_DIR):
        for fname in files:
            if fname.endswith(".py"):
                full = os.path.join(root, fname)
                rel = os.path.relpath(full, SCRIPTS_DIR)
                # windows反斜杠统一转为 /，和runner参数格式统一
                rel = rel.replace(os.sep, "/")
                ret.append(rel)
    return ret


def main():
    safe_wrap_stdio()
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', help='脚本名（如 test.py 或 tools/demo.py）')
    parser.add_argument('--list', action='store_true', help='列出所有脚本（返回可直接给runner使用的相对路径）')
    parser.add_argument('--latest', action='store_true', help='显示最近运行的脚本日志')
    parser.add_argument('--clear', action='store_true', help='清除指定脚本的日志（需配合 --name）')
    parser.add_argument('--clear-all', action='store_true', help='清空所有日志文件')
    args = parser.parse_args()

    # ----- 清理操作 -----
    if args.clear_all:
        print(clear_all_logs())
        sys.exit(0)

    if args.clear:
        if not args.name:
            print("❌ 清除日志需要指定脚本名 --name")
            sys.exit(1)
        arg_name = args.name
        if os.path.isabs(arg_name) or ".." in arg_name:
            print("❌ 非法脚本名")
            sys.exit(1)
        print(clear_log(arg_name))
        sys.exit(0)

    # ----- 查询操作 -----
    if args.list:
        scripts = list_all_scripts()
        print(json.dumps(scripts, ensure_ascii=False))
        sys.exit(0)

    if args.latest:
        result = get_latest_log()
        if result is None:
            print("📭 暂无任何日志文件")
        else:
            latest_file, content = result
            print(f"📌 最新日志来自: {latest_file}\n")
            print(content if content.strip() else "📭 日志文件为空")
        sys.exit(0)

    if not args.name:
        print("❌ 请指定脚本名 --name，或使用 --latest 查看最新日志")
        sys.exit(1)

    arg_name = args.name
    # 参数防护，和runner对齐
    if os.path.isabs(arg_name) or ".." in arg_name:
        print("❌ 非法脚本路径")
        sys.exit(1)

    log_filename = safe_log_name(arg_name)
    log_path = os.path.join(LOGS_DIR, log_filename)
    if os.path.exists(log_path):
        content = read_log_file(log_path)
        if content.strip():
            print(content)
        else:
            print("📭 日志文件为空")
    else:
        print("📭 暂无日志（该脚本尚未运行或未产生输出）")


if __name__ == "__main__":
    main()
