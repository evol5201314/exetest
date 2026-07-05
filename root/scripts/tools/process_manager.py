
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

def get_cpu_times():
    with open('/proc/stat', 'r') as f:
        line = f.readline()
    parts = line.split()
    idle = int(parts[4])
    total = sum(int(p) for p in parts[1:])
    return idle, total

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

    for pid_path in glob.glob('/proc/[0-9]*/status'):
        try:
            pid = int(pid_path.split('/')[2])
            if pid <= 10:
                continue

            name = ''
            with open(pid_path, 'r') as f:
                for line in f:
                    if line.startswith('Name:'):
                        name = line.split(':', 1)[1].strip()
                        break
            if not name or name.startswith('['):
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

            cmdline = ''
            try:
                with open(f'/proc/{pid}/cmdline', 'rb') as f:
                    cmdline = f.read().replace(b'\x00', b' ').decode('utf-8', errors='ignore').strip()
            except:
                pass

            if 'process_manager.py' in cmdline:
                continue

            cpu_percent = 0.0
            if total_cpu > 0:
                total_diff = (total2 - total1)
                if total_diff > 0:
                    cpu_percent = ((total_cpu / 100) / total_diff) * 100
                    if cpu_percent > 100:
                        cpu_percent = 0.0

            mem_percent = round((rss_kb / total_mem_kb * 100), 1) if total_mem_kb > 0 else 0

            processes.append({
                'pid': pid,
                'name': name[:30],
                'rss_mb': round(rss_kb / 1024, 2),
                'mem_percent': mem_percent,
                'cpu_percent': round(cpu_percent, 1),
                'cmdline': cmdline[:80] if cmdline else name
            })
        except:
            continue
    return processes

def kill_process(pid):
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
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False, f"❌ 进程 {pid} 已不存在"
    except Exception as e:
        return False, f"❌ 检查失败: {e}"

    try:
        with open(f'/proc/{pid}/cmdline', 'rb') as f:
            cmdline_bytes = f.read()
        if not cmdline_bytes:
            return False, f"❌ 进程 {pid} 命令行为空"
        cmdline = cmdline_bytes.replace(b'\x00', b' ').decode('utf-8', errors='ignore').strip()
        if not cmdline:
            return False, f"❌ 进程 {pid} 命令行解析为空"
    except FileNotFoundError:
        return False, f"❌ 进程 {pid} 已不存在"
    except Exception as e:
        return False, f"❌ 读取命令失败: {e}"

    cmdline = str(cmdline)
    try:
        os.kill(pid, signal.SIGTERM)
        time.sleep(0.5)
        os.system(cmdline + ' &')
        return True, f"✅ 已重启进程 (PID: {pid})"
    except ProcessLookupError:
        return False, f"❌ 进程 {pid} 已不存在"
    except PermissionError:
        return False, f"❌ 权限不足"
    except Exception as e:
        return False, f"❌ 重启失败: {e}"

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--sort', default='rss_mb', choices=['rss_mb', 'cpu_percent', 'mem_percent', 'pid'],
                        help='排序方式')
    parser.add_argument('--limit', type=int, default=30, help='显示数量')
    parser.add_argument('--json', action='store_true', help='输出 JSON')
    parser.add_argument('--kill', type=int, help='杀死指定 PID')
    parser.add_argument('--restart', type=int, help='重启指定 PID')
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
