# popup: procModal
# html: proc.html
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# btn: 📊 进程管理
# group: router
# order: 20
# action: runScript:process_manager.py
# btn-class: btn-purple
beizhu = "📊 进程管理"

import os
import sys
import json
import signal
import glob
import argparse
import time
import subprocess

def get_cpu_count():
    """返回 CPU 核心数"""
    try:
        with open('/proc/stat', 'r') as f:
            return sum(1 for line in f if line.startswith('cpu'))
    except:
        return 1

def get_cpu_times():
    with open('/proc/stat', 'r') as f:
        line = f.readline()
    parts = line.split()
    idle = int(parts[4])
    total = sum(int(p) for p in parts[1:])
    return idle, total

def get_display_name(pid, status_name):
    """生成适合显示的进程名"""
    cmdline = ''
    try:
        with open(f'/proc/{pid}/cmdline', 'rb') as f:
            data = f.read().replace(b'\x00', b' ').decode('utf-8', errors='ignore').strip()
            cmdline = data
    except:
        pass

    # 对 Python 脚本提取文件名
    if status_name == 'python3' and cmdline:
        parts = cmdline.split()
        script = None
        for p in parts[1:]:
            if not p.startswith('-') and p.endswith('.py'):
                script = p
                break
        if script:
            return os.path.basename(script)[:25]
        if len(parts) > 1:
            return parts[1][:25] if parts[1] else 'python3'
        return 'python3'

    # 其他进程优先使用 cmdline 的可执行文件名
    if cmdline:
        executable = cmdline.split()[0] if cmdline else ''
        if executable:
            return os.path.basename(executable)[:25]

    return status_name[:25]

def get_process_info():
    processes = []
    total_mem_kb = 0
    try:
        with open('/proc/meminfo', 'r') as f:
            for line in f:
                if line.startswith('MemTotal:'):
                    total_mem_kb = int(line.split(':')[1].strip().split()[0])
                    break
    except:
        pass

    idle1, total1 = get_cpu_times()
    time.sleep(0.1)
    idle2, total2 = get_cpu_times()
    cpu_count = get_cpu_count()

    for pid_path in glob.glob('/proc/[0-9]*/status'):
        try:
            pid = int(pid_path.split('/')[2])
            if pid <= 10:
                continue

            status_name = ''
            with open(pid_path, 'r') as f:
                for line in f:
                    if line.startswith('Name:'):
                        status_name = line.split(':', 1)[1].strip()
                        break
            if not status_name or status_name.startswith('['):
                continue

            rss_kb = 0
            with open(pid_path, 'r') as f:
                for line in f:
                    if line.startswith('VmRSS:'):
                        rss_kb = int(line.split(':', 1)[1].strip().split()[0])
                        break

            try:
                with open(f'/proc/{pid}/stat', 'r') as f:
                    stat = f.read().split()
                    utime = int(stat[13]) if len(stat) > 14 else 0
                    stime = int(stat[14]) if len(stat) > 15 else 0
                    cutime = int(stat[15]) if len(stat) > 16 else 0
                    cstime = int(stat[16]) if len(stat) > 17 else 0
                    total_cpu = utime + stime + cutime + cstime
            except:
                total_cpu = 0

            display_name = get_display_name(pid, status_name)

            cpu_percent = 0.0
            total_system_diff = (total2 - total1)
            if total_system_diff > 0 and cpu_count > 0:
                cpu_percent = (total_cpu / total_system_diff) * 100.0 / cpu_count
                if cpu_percent > 100:
                    cpu_percent = 0.0

            mem_percent = round((rss_kb / total_mem_kb * 100), 1) if total_mem_kb > 0 else 0

            processes.append({
                'pid': pid,
                'name': display_name,
                'rss_mb': round(rss_kb / 1024, 2),
                'mem_percent': mem_percent,
                'cpu_percent': round(cpu_percent, 1),
                'cmdline': display_name
            })
        except:
            continue
    return processes

def kill_process(pid):
    """发送 SIGTERM 终止进程"""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False, f"❌ 进程 {pid} 已不存在"
    except Exception as e:
        return False, f"❌ 检查失败: {e}"
    try:
        os.kill(pid, signal.SIGTERM)
        time.sleep(0.3)
        try:
            os.kill(pid, 0)
            return False, f"❌ 进程 {pid} 仍在运行"
        except OSError:
            return True, f"✅ 已终止进程 (PID: {pid})"
    except Exception as e:
        return False, f"❌ 杀进程失败: {e}"

def restart_process(pid):
    """强杀进程（SIGKILL），不做重启"""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False, f"❌ 进程 {pid} 已不存在"
    except Exception as e:
        return False, f"❌ 检查失败: {e}"

    try:
        os.kill(pid, signal.SIGKILL)
        time.sleep(0.3)
        try:
            os.kill(pid, 0)
            return False, f"❌ 进程 {pid} 未被杀死（可能被保护）"
        except OSError:
            return True, f"✅ 已强制终止进程 (PID: {pid})"
    except Exception as e:
        return False, f"❌ 强杀失败: {e}"

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--sort', default='rss_mb', choices=['rss_mb', 'cpu_percent', 'mem_percent', 'pid'],
                        help='排序方式')
    parser.add_argument('--limit', type=int, default=30, help='显示数量')
    parser.add_argument('--json', action='store_true', help='输出 JSON')
    parser.add_argument('--kill', type=int, help='杀死指定 PID')
    parser.add_argument('--restart', type=int, help='强杀指定 PID（不重启）')
    args = parser.parse_args()

    if args.kill:
        success, msg = kill_process(args.kill)
        print(msg)
        sys.exit(0 if success else 1)

    if args.restart:
        success, msg = restart_process(args.restart)
        print(msg)
        sys.exit(0 if success else 1)

    procs = get_process_info()
    reverse = True if args.sort in ['rss_mb', 'cpu_percent', 'mem_percent'] else False
    procs.sort(key=lambda x: x.get(args.sort, 0), reverse=reverse)
    procs = procs[:args.limit]

    if args.json:
        print(json.dumps(procs))
    else:
        print(f"{'PID':>6} {'内存(MB)':>10} {'CPU%':>8} {'内存%':>8} {'名称'}")
        print('-' * 60)
        for p in procs:
            print(f"{p['pid']:>6} {p['rss_mb']:>10.2f} {p['cpu_percent']:>8.1f} {p['mem_percent']:>8.1f} {p['name'][:25]}")
