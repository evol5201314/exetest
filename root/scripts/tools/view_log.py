# popup: logModal
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
beizhu = "📄 查看脚本日志 / 清理日志"

import os, sys, json, argparse

LOGS_DIR = "/root/scripts/logs"          # 日志文件存放目录
SCRIPTS_DIR = "/root/scripts"

def get_latest_log():
    """返回最近修改的日志文件名和内容，若没有则返回 None"""
    if not os.path.exists(LOGS_DIR):
        return None
    log_files = [f for f in os.listdir(LOGS_DIR) if f.endswith('.log')]
    if not log_files:
        return None
    # 按修改时间排序，取最新的
    log_files.sort(key=lambda f: os.path.getmtime(os.path.join(LOGS_DIR, f)), reverse=True)
    latest_file = log_files[0]
    filepath = os.path.join(LOGS_DIR, latest_file)
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    return latest_file, content

def clear_log(name=None):
    """清除指定脚本的日志文件，返回操作信息"""
    if name is None:
        return "❌ 未指定脚本名"
    log_path = os.path.join(LOGS_DIR, f"{name}.log")
    if os.path.exists(log_path):
        os.remove(log_path)
        return f"✅ 已清除 {name} 的日志"
    else:
        return f"📭 {name} 暂无日志文件"

def clear_all_logs():
    """清空所有日志文件，返回操作信息"""
    if not os.path.exists(LOGS_DIR):
        return "📭 日志目录不存在"
    files = [f for f in os.listdir(LOGS_DIR) if f.endswith('.log')]
    if not files:
        return "📭 没有任何日志文件"
    for f in files:
        os.remove(os.path.join(LOGS_DIR, f))
    return f"✅ 已清空全部 {len(files)} 个日志文件"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', help='脚本名（如 test.py）')
    parser.add_argument('--list', action='store_true', help='列出所有脚本')
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
        print(clear_log(args.name))
        sys.exit(0)

    # ----- 查询操作 -----
    if args.list:
        scripts = [f for f in os.listdir(SCRIPTS_DIR) if f.endswith('.py') and os.path.isfile(os.path.join(SCRIPTS_DIR, f))]
        print(json.dumps(scripts))
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

    log_path = os.path.join(LOGS_DIR, f"{args.name}.log")
    if os.path.exists(log_path):
        with open(log_path, 'r', encoding='utf-8') as f:
            content = f.read()
        if content.strip():
            print(content)
        else:
            print("📭 日志文件为空")
    else:
        print("📭 暂无日志（该脚本尚未运行或未产生输出）")

if __name__ == "__main__":
    main()
