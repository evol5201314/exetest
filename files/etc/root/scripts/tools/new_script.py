#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# popup: newModal
# btn: ➕ 新建脚本
# group: script
# order: 10
# action: runScript:new_script.py
# btn-class: btn-blue
beizhu = "📝 新建脚本（支持 .py 和 .html）"

import os, sys, argparse

SCRIPTS_DIR = "/root/scripts"
STATIC_DIR = "/root/scripts/static"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', required=True, help='文件名（不含后缀）')
    parser.add_argument('--content', required=True, help='文件内容')
    parser.add_argument('--type', default='py', choices=['py', 'html'], help='文件类型')
    args = parser.parse_args()

    name = args.name.strip()
    file_type = args.type

    # 根据类型确定后缀和保存目录
    if file_type == 'py':
        if not name.endswith('.py'):
            name += '.py'
        save_dir = SCRIPTS_DIR
    else:  # html
        if not name.endswith('.html'):
            name += '.html'
        save_dir = STATIC_DIR

    if '/' in name or '\\' in name:
        print("❌ 文件名不合法")
        sys.exit(1)

    path = os.path.join(save_dir, name)
    if os.path.exists(path):
        print(f"❌ 文件 {name} 已存在")
        sys.exit(1)

    os.makedirs(save_dir, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(args.content)

    print(f"✅ {name} 创建成功（保存于 {save_dir}）")

if __name__ == "__main__":
    main()
