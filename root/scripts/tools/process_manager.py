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
    cmdline = ''
    try:
        with open(f'/proc/{pid}/cmdline', 'rb') as f:
            data = f.read().replace(b'\x00', b' ').decode('utf-8', errors='ignore').strip()
            cmdline = data
    except:
        pass

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

def get_cmdline(pid):
    """获取指定进程的完整命令行（不含参数分隔符）"""
    try:
        with open(f'/proc/{pid}/cmdline', 'rb') as f:
            return f.read().replace(b'\x00', b' ').decode('utf-8', errors='ignore').strip()
    except:
        return ''

def process_exists_with_same_cmdline(target_cmdline):
    """检查当前系统中是否存在与 target_cmdline 完全相同的进程命令行"""
    if not target_cmdline:
        return False
    for pid_path in glob.glob('/proc/[0-9]*/cmdline'):
        try:
            with open(pid_path, 'rb') as f:
                cmd = f.read().replace(b'\x00', b' ').decode('utf-8', errors='ignore').strip()
                if cmd == target_cmdline:
                    return True
        except:
            continue
    return False

def restart_process(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False, f"❌ 进程 {pid} 已不存在"
    except Exception as e:
        return False, f"❌ 检查失败: {e}"

    # 保存原始命令行
    original_cmdline = get_cmdline(pid)
    if not original_cmdline:
        return False, f"❌ 进程 {pid} 命令行为空"

    # 发送 SIGTERM
    try:
        os.kill(pid, signal.SIGTERM)
    except Exception as e:
        return False, f"❌ 发送信号失败: {e}"

    # 等待进程退出（最多 3 秒）
    waited = 0
    while waited < 3.0:
        time.sleep(0.2)
        waited += 0.2
        try:
            os.kill(pid, 0)
        except OSError:
            break
    else:
        # 超时后 SIGKILL
        try:
            os.kill(pid, signal.SIGKILL)
            time.sleep(0.5)
            try:
                os.kill(pid, 0)
                return False, f"❌ 进程 {pid} 无法被杀死"
            except OSError:
                pass
        except Exception as e:
            return False, f"❌ 强制终止失败: {e}"

    # 等待 3 秒，让可能的自动保活机制启动新进程
    time.sleep(3.0)

    # 检查是否有与原命令行完全相同的进程出现（系统自动重启）
    if process_exists_with_same_cmdline(original_cmdline):
        return True, f"✅ 进程已由系统自动重启 (原 PID: {pid})"

    # 没有自动重启，则手动启动
    try:
        subprocess.Popen(original_cmdline, shell=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True, f"✅ 已手动重启进程 (原 PID: {pid})"
    except Exception as e:
        return False, f"❌ 手动重启失败: {e}"

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
