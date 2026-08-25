#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# popup: editModal
# btn: ✏️ 编辑脚本
# group: script
# order: 30
# action: runScript:edit_script.py
# btn-class: btn-orange
beizhu = "✏️ 编辑脚本（支持修改内容和文件名）"

import os, sys, argparse

SCRIPTS_DIR = "/root/scripts"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', required=True, help='当前文件名')
    parser.add_argument('--content', required=True, help='新内容')
    parser.add_argument('--newname', default=None, help='新文件名（可选，不提供则不修改文件名）')
    args = parser.parse_args()

    old_name = args.name.strip()
    new_name = args.newname.strip() if args.newname else None
    content = args.content

    # 安全检查
    if '/' in old_name or '\\' in old_name:
        print("❌ 原文件名不合法")
        sys.exit(1)
    if new_name and ('/' in new_name or '\\' in new_name):
        print("❌ 新文件名不合法")
        sys.exit(1)

    old_path = os.path.join(SCRIPTS_DIR, old_name)
    if not os.path.exists(old_path):
        print(f"❌ 文件 {old_name} 不存在")
        sys.exit(1)

    # 如果提供了新名字且与原名字不同，则执行重命名
    if new_name and new_name != old_name:
        new_path = os.path.join(SCRIPTS_DIR, new_name)
        if os.path.exists(new_path):
            print(f"❌ 新文件名 {new_name} 已存在")
            sys.exit(1)
        # 写入新文件
        with open(new_path, 'w', encoding='utf-8') as f:
            f.write(content)
        # 删除旧文件
        os.remove(old_path)
        print(f"✅ 已将 {old_name} 重命名为 {new_name} 并保存内容")
    else:
        # 只保存内容
        with open(old_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ {old_name} 保存成功")

if __name__ == "__main__":
    main()
