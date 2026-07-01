#!/usr/bin/env python3
# -*- coding: utf-8 -*-
beizhu = "⏰ Cron 管理（独立脚本，用完销毁）"

import os, sys, subprocess, argparse, json

CRONTAB_FILE = "/etc/crontabs/root"

def list_crons_json():
    if not os.path.exists(CRONTAB_FILE):
        return []
    with open(CRONTAB_FILE, 'r') as f:
        lines = f.readlines()
    jobs = []
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#'):
            jobs.append(line)
    return jobs

def add_cron(schedule, command):
    try:
        if not os.path.exists(CRONTAB_FILE):
            with open(CRONTAB_FILE, 'w') as f:
                f.write("# OpenWrt crontab\n")
        with open(CRONTAB_FILE, 'r') as f:
            lines = f.readlines()
        for line in lines:
            if line.strip() == f"{schedule} {command}":
                print("⚠️ 该任务已存在")
                return
        with open(CRONTAB_FILE, 'a') as f:
            f.write(f"{schedule} {command}\n")
        subprocess.run(['/etc/init.d/cron', 'restart'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("✅ 任务已添加")
    except Exception as e:
        print(f"❌ 添加失败: {e}")

def delete_cron(full_line):
    try:
        with open(CRONTAB_FILE, 'r') as f:
            lines = f.readlines()
        new_lines = []
        deleted = False
        for line in lines:
            if line.strip() == full_line.strip():
                deleted = True
                continue
            new_lines.append(line)
        if not deleted:
            print("❌ 未找到该任务")
            return
        with open(CRONTAB_FILE, 'w') as f:
            f.writelines(new_lines)
        subprocess.run(['/etc/init.d/cron', 'restart'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("✅ 任务已删除")
    except Exception as e:
        print(f"❌ 删除失败: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--list-json', action='store_true')
    parser.add_argument('--add', nargs=2, metavar=('SCHEDULE', 'COMMAND'))
    parser.add_argument('--delete', metavar='LINE')
    args = parser.parse_args()

    if args.list_json:
        print(json.dumps(list_crons_json()))
    elif args.add:
        add_cron(args.add[0], args.add[1])
    elif args.delete:
        delete_cron(args.delete)
