#!/usr/bin/env python3
# -*- coding: utf-8 -*-
beizhu = "📄 查看脚本日志"

import os, sys, json, argparse

LOGS_DIR = "/root/scripts/logs"          # 日志文件存放目录
SCRIPTS_DIR = "/root/scripts"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', help='脚本名')
    parser.add_argument('--list', action='store_true', help='列出所有脚本')
    args = parser.parse_args()
    
    if args.list:
        scripts = [f for f in os.listdir(SCRIPTS_DIR) if f.endswith('.py') and os.path.isfile(os.path.join(SCRIPTS_DIR, f))]
        print(json.dumps(scripts))
        sys.exit(0)
    
    if not args.name:
        print("❌ 请指定脚本名 --name")
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
