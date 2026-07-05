#!/usr/bin/env python3
# -*- coding: utf-8 -*-

beizhu = "📈 面板核心（Bottle 轻量化版本）"
"""
================================================================
⚠️ 面板核心原则：轻量化是绝对核心 请勿删除或违反以下规则
================================================================

【硬件环境】
  路由可用内存仅≈30M，精简python3，峰值内存控制最小化

【核心原则】
  1. 面板本身只保留：脚本列表展示 + 内存/缓存显示
  2. 所有操作（运行/停止/新建/编辑/删除/上传/日志/同步/定时/清理/进程管理）
     必须通过「独立脚本」实现，点击时临时启动，执行完毕立即释放内存
  3. 严禁将任何附属功能的代码合并到主面板 app.py 中
  4. 主面板 app.py 只负责：路由 + 调用独立脚本 + 显示结果
  5. 所有独立脚本放在 /root/scripts/tools/ 目录下
  6. 所有弹窗 HTML 动态加载，不写死在主面板中

【弹窗脚本添加规范】（所有功能统一走此规范）
  1. 在 tools/ 下的脚本前15行内添加 # popup: 弹窗ID 声明
  2. 在 modal_content.html 中添加对应的弹窗 HTML 和 window.init_弹窗ID() 函数
  3. 面板点击脚本卡片或按钮时自动检测 # popup 并弹出窗口，无需修改 app.py
  4. 弹窗的业务逻辑 JS 函数放在 modal_content.html 末尾的 <script> 中
  5. 初始化函数必须挂载到 window：window.init_弹窗ID = function() { ... }

【按钮动态生成规范】
  1. 在 tools/ 下的脚本前15行内添加：
     # btn: 按钮标题
     # group: script 或 router
     # order: 数字（越小越靠前）
     # action: runScript:脚本名.py 或 runTool:脚本名.py 或 func:函数名
     # btn-class: 颜色类名（btn-blue, btn-green, btn-red 等）
  2. app.py 会自动扫描生成按钮，无需手动修改 HTML

================================================================
"""

import os
import sys
import json
import subprocess
import signal
import gc
import re
from datetime import datetime
from bottle import Bottle, route, run, request, response, static_file

app = Bottle()

SCRIPTS_DIR = "/root/scripts"
TOOLS_DIR = "/root/scripts/tools"
STATUS_FILE = "/tmp/script_status.json"

def init_files():
    os.makedirs(SCRIPTS_DIR, exist_ok=True)
    os.makedirs(TOOLS_DIR, exist_ok=True)
    os.makedirs("/root/scripts/static", exist_ok=True)
    if not os.path.exists(STATUS_FILE):
        with open(STATUS_FILE, 'w') as f:
            json.dump({}, f)

def extract_beizhu(fp):
    try:
        with open(fp, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if i >= 20:
                    break
                if line.strip().startswith('beizhu ='):
                    v = line.split('=', 1)[1].strip()
                    if v.startswith('"') and v.endswith('"'): return v[1:-1]
                    if v.startswith("'") and v.endswith("'"): return v[1:-1]
                    return v
    except:
        pass
    return None

def get_meminfo():
    try:
        with open('/proc/meminfo', 'r') as f:
            lines = f.readlines()
        mem = {}
        for line in lines:
            if ':' in line:
                k, v = line.split(':', 1)
                mem[k] = int(v.strip().split()[0])
        total = mem.get('MemTotal', 0)
        avail = mem.get('MemAvailable', mem.get('MemFree', 0))
        used = total - avail if total > avail else 0
        return {'total_kb': total, 'used_kb': used, 'available_kb': avail,
                'percent': round((used / total * 100) if total > 0 else 0, 1)}
    except:
        return {'total_kb': 0, 'used_kb': 0, 'available_kb': 0, 'percent': 0}

def get_apk_cache_size():
    cache_dir = "/var/cache/apk/"
    if not os.path.exists(cache_dir):
        return 0
    total = 0
    try:
        for root, _, files in os.walk(cache_dir):
            for f in files:
                p = os.path.join(root, f)
                if os.path.exists(p):
                    total += os.path.getsize(p)
    except:
        pass
    return round(total / (1024*1024), 2)

def get_scripts():
    scripts = []
    if not os.path.exists(SCRIPTS_DIR):
        return scripts
    
    EXCLUDE_SCRIPTS = ['bottle.py', 'app.py', '__init__.py']
    
    with open(STATUS_FILE, 'r') as f:
        status_data = json.load(f)
    for fn in sorted(os.listdir(SCRIPTS_DIR)):
        full_path = os.path.join(SCRIPTS_DIR, fn)
        if fn in EXCLUDE_SCRIPTS:
            continue
        if fn.endswith('.py') and os.path.isfile(full_path):
            st = os.stat(full_path)
            s = status_data.get(fn, {'status': 'idle', 'pid': None})
            scripts.append({
                'name': fn,
                'size': st.st_size,
                'mtime': datetime.fromtimestamp(st.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                'status': s.get('status', 'idle'),
                'pid': s.get('pid'),
                'remark': extract_beizhu(full_path) or ''
            })
    return scripts

def kill_process_on_port(port=5000):
    try:
        for cmd in [f"netstat -tulpn 2>/dev/null | grep ':{port} ' | awk '{{print $7}}' | cut -d'/' -f1",
                    f"lsof -t -i:{port} 2>/dev/null"]:
            pids = subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip().split()
            if pids:
                for pid in pids:
                    try:
                        os.kill(int(pid), signal.SIGKILL)
                    except:
                        pass
                return True
    except:
        pass
    return True

def get_router_ip():
    try:
        ip = subprocess.run(["uci", "get", "network.lan.ipaddr"], capture_output=True, text=True, timeout=2).stdout.strip()
        if ip and '/' in ip:
            ip = ip.split('/')[0]
        return ip or "192.168.1.1"
    except:
        return "192.168.1.1"

# ========== 静态文件路由 ==========
@route('/static/<filename:path>')
def serve_static(filename):
    return static_file(filename, root="/root/scripts/static")

# ========== API 路由 ==========
@route('/')
def index():
    return HTML

@route('/api/scripts')
def api_scripts():
    response.content_type = 'application/json'
    return json.dumps(get_scripts())

@route('/api/meminfo')
def api_meminfo():
    response.content_type = 'application/json'
    return json.dumps(get_meminfo())

@route('/api/apk_cache_size')
def api_apk_cache_size():
    response.content_type = 'application/json'
    return json.dumps({'size_mb': get_apk_cache_size()})

@route('/api/router_ip')
def api_router_ip():
    response.content_type = 'application/json'
    return json.dumps({'ip': get_router_ip()})

# ========== 检查脚本是否为弹窗脚本（扫描前10行） ==========
@route('/api/check_popup/<name>')
def check_popup(name):
    if '/' in name or '\\' in name:
        return json.dumps({'popup': None})
    path = os.path.join(SCRIPTS_DIR, name)
    if not os.path.exists(path):
        path = os.path.join(TOOLS_DIR, name)
        if not os.path.exists(path):
            return json.dumps({'popup': None})
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if i >= 10:
                    break
                if line.strip().startswith('# popup:'):
                    popup_id = line.split(':', 1)[1].strip()
                    return json.dumps({'popup': popup_id})
    except:
        pass
    return json.dumps({'popup': None})

# ========== 获取动态按钮配置 ==========
@route('/api/buttons')
def api_buttons():
    buttons = {'script': [], 'router': []}
    if not os.path.isdir(TOOLS_DIR):
        return json.dumps(buttons)
    
    for fn in sorted(os.listdir(TOOLS_DIR)):
        if not fn.endswith('.py'):
            continue
        fp = os.path.join(TOOLS_DIR, fn)
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                lines = [f.readline() for _ in range(15)]
        except:
            continue
        
        btn_title = None
        group = 'script'
        order = 99
        action = None
        btn_class = 'btn-default'
        
        for line in lines:
            line = line.strip()
            if line.startswith('# btn:'):
                btn_title = line.split(':', 1)[1].strip()
            elif line.startswith('# group:'):
                group = line.split(':', 1)[1].strip()
            elif line.startswith('# order:'):
                try:
                    order = int(line.split(':', 1)[1].strip())
                except:
                    pass
            elif line.startswith('# action:'):
                action = line.split(':', 1)[1].strip()
            elif line.startswith('# btn-class:'):
                btn_class = line.split(':', 1)[1].strip()
        
        if btn_title and action:
            buttons.setdefault(group, []).append({
                'title': btn_title,
                'order': order,
                'action': action,
                'file': fn,
                'btnClass': btn_class
            })
    
    for group in buttons:
        buttons[group].sort(key=lambda x: x['order'])
    
    response.content_type = 'application/json'
    return json.dumps(buttons)

# ========== 停止脚本 ==========
@route('/api/stop/<name>', method='POST')
def stop_script(name):
    try:
        script_path = os.path.join(TOOLS_DIR, 'stop_script.py')
        if not os.path.exists(script_path):
            response.status = 500
            return json.dumps({'error': 'stop_script.py 不存在'})
        result = subprocess.run(
            ['python3', script_path, '--name', name],
            capture_output=True, text=True, timeout=30
        )
        output = result.stdout + result.stderr
        response.content_type = 'application/json'
        return json.dumps({'message': output.strip() or '执行完成'})
    except Exception as e:
        response.status = 500
        return json.dumps({'error': str(e)})

# ========== 获取脚本内容（编辑用） ==========
@route('/api/get/<name>')
def get_script(name):
    if '/' in name or '\\' in name:
        response.status = 400
        return json.dumps({'error': '文件名不合法'})
    path = os.path.join(SCRIPTS_DIR, name)
    if not os.path.exists(path):
        response.status = 404
        return json.dumps({'error': '脚本不存在'})
    with open(path, 'r') as f:
        content = f.read()
    response.content_type = 'application/json'
    return json.dumps({'name': name, 'content': content})

# ========== 统一工具调用 ==========
@route('/api/run_tool', method='POST')
def run_tool():
    data = request.json
    script = data.get('script', '')
    args = data.get('args', [])
    if not script:
        response.status = 400
        return json.dumps({'error': '未指定脚本'})
    if not script.endswith('.py') or '/' in script:
        response.status = 400
        return json.dumps({'error': '不安全的脚本名'})

    if script == 'kill_top_process.py':
        if '--exclude' not in str(args):
            args = ['--exclude', str(os.getpid())] + args

    script_path = os.path.join(TOOLS_DIR, script)
    if not os.path.exists(script_path):
        response.status = 404
        return json.dumps({'error': f'工具脚本 {script} 不存在'})
    try:
        cmd = ['python3', script_path] + [str(a) for a in args]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        output = result.stdout + result.stderr
        if not output.strip():
            output = '✅ 执行完成（无输出）'
        response.content_type = 'application/json'
        return json.dumps({'output': output})
    except subprocess.TimeoutExpired:
        response.status = 500
        return json.dumps({'output': '⏱ 执行超时（300秒）'})
    except Exception as e:
        response.status = 500
        return json.dumps({'output': f'❌ 执行失败: {e}'})

@route('/api/restart_router', method='POST')
def restart_router():
    try:
        subprocess.Popen(['reboot'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        response.content_type = 'application/json'
        return json.dumps({'message': '✅ 路由器正在重启...'})
    except Exception as e:
        response.status = 500
        return json.dumps({'error': str(e)})

# ==================== HTML 模板 ====================
HTML = r'''
<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>🐍 脚本面板</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f0f2f5;padding:16px}
.container{max-width:1200px;margin:0 auto}
.header{background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;padding:20px 24px;border-radius:12px;margin-bottom:20px}
.header h1{font-size:22px}.header .sub{opacity:.8;font-size:13px;margin-top:4px}
.stats{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:20px}
.stat-card{background:#fff;padding:12px 20px;border-radius:10px;box-shadow:0 1px 4px rgba(0,0,0,.06);flex:1;min-width:70px}
.stat-card .num{font-size:24px;font-weight:700;color:#333}
.stat-card .label{font-size:12px;color:#999}
.stat-card .mem-bar-wrap{width:100%;height:4px;background:#e0e0e0;border-radius:2px;margin-top:6px;overflow:hidden}
.stat-card .mem-bar{height:100%;border-radius:2px;transition:width 0.3s}
.actions-bar{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px;padding:8px 12px;background:#f8f9fa;border-radius:8px}
.actions-bar .group-label{font-size:11px;color:#999;font-weight:600;display:flex;align-items:center;margin-right:2px}

/* ==================== 按钮颜色类 ==================== */
.btn-default { background: #607d8b; color: #fff; border: none; border-radius: 8px; padding: 6px 14px; cursor: pointer; font-size: 13px; font-weight: 500; }
.btn-default:hover { background: #455a64; }
.btn-blue { background:#667eea; color:#fff; border:none; border-radius:8px; padding:6px 14px; cursor:pointer; font-size:13px; font-weight:500; }
.btn-blue:hover { background:#5a6fd6; }
.btn-green { background:#4caf50; color:#fff; border:none; border-radius:8px; padding:6px 14px; cursor:pointer; font-size:13px; font-weight:500; }
.btn-green:hover { background:#43a047; }
.btn-orange { background:#ff9800; color:#fff; border:none; border-radius:8px; padding:6px 14px; cursor:pointer; font-size:13px; font-weight:500; }
.btn-orange:hover { background:#f57c00; }
.btn-red { background:#f44336; color:#fff; border:none; border-radius:8px; padding:6px 14px; cursor:pointer; font-size:13px; font-weight:500; }
.btn-red:hover { background:#d32f2f; }
.btn-teal { background:#00897b; color:#fff; border:none; border-radius:8px; padding:6px 14px; cursor:pointer; font-size:13px; font-weight:500; }
.btn-teal:hover { background:#00695c; }
.btn-pink { background:#ff6b6b; color:#fff; border:none; border-radius:8px; padding:6px 14px; cursor:pointer; font-size:13px; font-weight:500; }
.btn-pink:hover { background:#e55a5a; }
.btn-gray { background:#607d8b; color:#fff; border:none; border-radius:8px; padding:6px 14px; cursor:pointer; font-size:13px; font-weight:500; }
.btn-gray:hover { background:#455a64; }
.btn-cyan { background:#00838f; color:#fff; border:none; border-radius:8px; padding:6px 14px; cursor:pointer; font-size:13px; font-weight:500; }
.btn-cyan:hover { background:#006064; }
.btn-purple { background:#7b1fa2; color:#fff; border:none; border-radius:8px; padding:6px 14px; cursor:pointer; font-size:13px; font-weight:500; }
.btn-purple:hover { background:#4a148c; }
.btn-dark-green { background:#00695c; color:#fff; border:none; border-radius:8px; padding:6px 14px; cursor:pointer; font-size:13px; font-weight:500; }
.btn-dark-green:hover { background:#004d40; }
.btn-dark-blue { background:#1565c0; color:#fff; border:none; border-radius:8px; padding:6px 14px; cursor:pointer; font-size:13px; font-weight:500; }
.btn-dark-blue:hover { background:#0d47a1; }
.btn-deep-orange { background:#e65100; color:#fff; border:none; border-radius:8px; padding:6px 14px; cursor:pointer; font-size:13px; font-weight:500; }
.btn-deep-orange:hover { background:#bf360c; }
.btn-dark-red { background:#c62828; color:#fff; border:none; border-radius:8px; padding:6px 14px; cursor:pointer; font-size:13px; font-weight:500; }
.btn-dark-red:hover { background:#b71c1c; }

/* ==================== 其他 ==================== */
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:14px}
.card{background:#fff;border-radius:10px;padding:16px 18px;box-shadow:0 1px 4px rgba(0,0,0,.06);border-left:4px solid #ddd}
.card.idle{border-left-color:#90a4ae}
.card.running{border-left-color:#ff9800;animation:pulse 1.2s infinite}
.card.success{border-left-color:#4caf50}
.card.failed{border-left-color:#f44336}
.card.timeout{border-left-color:#ff5722}
.card.error{border-left-color:#9c27b0}
.card.stopped{border-left-color:#78909c}
@keyframes pulse{0%,100%{border-left-color:#ff9800}50%{border-left-color:#ffcc80}}
.card .top{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:4px}
.card .name{font-weight:600;font-size:15px;word-break:break-all}
.remark-line{font-size:16px;font-weight:normal;color:#333;border:1px solid #d0d0d0;border-radius:20px;padding:2px 16px;display:inline-block;margin:4px 0 2px 0;background:#fafafa}
.badge{font-size:11px;padding:2px 12px;border-radius:20px;font-weight:500;flex-shrink:0;margin-left:10px}
.badge.idle{background:#eceff1;color:#546e7a}
.badge.running{background:#fff3e0;color:#e65100}
.badge.success{background:#e8f5e9;color:#1b5e20}
.badge.failed{background:#fce4ec;color:#b71c1c}
.badge.timeout{background:#fbe9e7;color:#bf360c}
.badge.error{background:#f3e5f5;color:#4a148c}
.badge.stopped{background:#eceff1;color:#455a64}
.card .info{margin-top:10px;font-size:13px;color:#666;line-height:1.6}
.card .info .lbl{color:#999}
.card .actions{margin-top:12px;display:flex;gap:6px;flex-wrap:wrap}
.card .actions button{padding:5px 14px;border:none;border-radius:6px;font-size:13px;cursor:pointer;font-weight:500}
.btn-run{background:#667eea;color:#fff}.btn-run:hover{background:#5a6fd6}
.btn-run:disabled{opacity:.5;cursor:not-allowed}
.btn-stop{background:#f44336;color:#fff}.btn-stop:hover{background:#d32f2f}
.empty{padding:60px 20px;text-align:center;color:#999}
.refresh-btn{background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;border:none;padding:8px 20px;border-radius:20px;cursor:pointer;font-size:13px;font-weight:600;transition:all 0.3s ease;box-shadow:0 2px 8px rgba(102,126,234,0.3);letter-spacing:0.5px}
.refresh-btn:hover{transform:translateY(-2px);box-shadow:0 4px 16px rgba(102,126,234,0.4);background:linear-gradient(135deg,#5a6fd6,#6a4292)}
.refresh-btn:active{transform:translateY(0px);box-shadow:0 1px 4px rgba(102,126,234,0.2)}
.modal{display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:999;justify-content:center;align-items:center}
.modal.active{display:flex}
.modal-box{background:#fff;border-radius:14px;padding:24px;max-width:720px;width:94%;max-height:85vh;overflow-y:auto}
.modal-box h2{font-size:17px;margin-bottom:4px}
.modal-box .meta{font-size:13px;color:#888;margin-bottom:12px}
.modal-box pre{background:#1e1e1e;color:#d4d4d4;padding:12px;border-radius:6px;font-size:12px;max-height:400px;overflow:auto;white-space:pre-wrap;word-break:break-all}
.close{float:right;font-size:24px;cursor:pointer;color:#888}.close:hover{color:#333}
input,textarea,select{width:100%;padding:8px;border:1px solid #ddd;border-radius:6px;margin:6px 0;font-size:14px;font-family:inherit}
textarea{min-height:180px;font-family:monospace;resize:vertical}
select{appearance:auto;background:#fff}
.modal-box .form-actions{display:flex;gap:8px;margin-top:12px;flex-wrap:wrap}
.modal-box .form-actions button{padding:6px 20px;border:none;border-radius:6px;cursor:pointer;font-weight:500}
.btn-primary{background:#667eea;color:#fff}.btn-primary:hover{background:#5a6fd6}
.btn-secondary{background:#eceff1;color:#333}.btn-secondary:hover{background:#d5d9de}
.btn-success{background:#4caf50;color:#fff}.btn-success:hover{background:#43a047}
.btn-danger{background:#f44336;color:#fff}.btn-danger:hover{background:#d32f2f}
@media(max-width:600px){.grid{grid-template-columns:1fr}}
</style></head>
<body>
<div class="container">
<div class="header"><h1>🐍 脚本面板</h1><div class="sub">📁 /root/scripts &nbsp;|&nbsp; ⏱ 自动刷新 10s</div></div>
<div class="stats" id="stats">
<div class="stat-card"><div class="num" id="total">0</div><div class="label">📄 总数</div></div>
<div class="stat-card"><div class="num" id="running">0</div><div class="label">🔄 运行中</div></div>
<div class="stat-card"><div class="num" id="success">0</div><div class="label">✅ 成功</div></div>
<div class="stat-card"><div class="num" id="failed">0</div><div class="label">❌ 失败</div></div>
<div class="stat-card" id="memCard"><div class="num" id="memText">-- MB</div><div class="label" id="memLabel">💾 内存使用</div><div class="mem-bar-wrap"><div class="mem-bar" id="memBar" style="width:0%;background:#4caf50"></div></div></div>
<div class="stat-card" id="cacheCard"><div class="num" id="cacheSize">-- MB</div><div class="label">📦 APK缓存</div></div>
<div class="stat-card" style="flex:0"><button class="refresh-btn" id="refreshBtn">↻ 刷新</button></div>
</div>

<div class="actions-bar" id="scriptBtns"><span class="group-label">📜 脚本</span></div>
<div class="actions-bar" id="routerBtns"><span class="group-label">⚙️ 路由</span></div>

<div id="modalContainer"></div>

<div class="grid" id="grid"></div>
</div>

<div class="modal" id="toolModal"><div class="modal-box">
<span class="close" onclick="closeModal('toolModal')">&times;</span>
<h2 id="toolTitle">工具执行</h2>
<pre id="toolOutput" style="background:#1e1e1e;color:#d4d4d4;padding:12px;border-radius:6px;font-size:12px;max-height:400px;overflow:auto;white-space:pre-wrap;word-break:break-all">执行中...</pre>
<div style="display:flex;justify-content:space-between;align-items:center;margin-top:12px;flex-wrap:wrap;gap:8px;">
    <label style="display:flex;align-items:center;gap:8px;font-size:14px;color:#555;cursor:pointer;user-select:none;">
        <input type="checkbox" id="keepOpenCheck" style="width:18px;height:18px;cursor:pointer;accent-color:#667eea;flex-shrink:0;"> 📌 保持打开（不自动关闭）
    </label>
    <button onclick="closeModal('toolModal')" style="padding:8px 28px;border:none;border-radius:20px;cursor:pointer;font-size:14px;font-weight:500;background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;transition:all 0.3s ease;box-shadow:0 2px 8px rgba(102,126,234,0.3);">关闭</button>
</div>
</div></div>

<script>
var routerIP = '';
window.modalLoaded = false;

function st(s){var map={idle:'待执行',running:'运行中',success:'成功',failed:'失败',timeout:'超时',error:'错误',stopped:'已停止'};return map[s]||s}
function badge(s){return'<span class="badge '+s+'">'+st(s)+'</span>'}
function openModal(id){document.getElementById(id).classList.add('active')}
function closeModal(id){document.getElementById(id).classList.remove('active')}

function fetchRouterIP(){
    fetch('/api/router_ip').then(r=>r.json()).then(d=>{routerIP=d.ip||window.location.hostname||'192.168.1.1'}).catch(()=>{routerIP=window.location.hostname||'192.168.1.1'})
}

function loadMem(){
    fetch('/api/meminfo').then(r=>r.json()).then(d=>{
        var total=d.total_kb||0, used=d.used_kb||0, p=d.percent||0
        document.getElementById('memText').textContent=(used/1024).toFixed(0)+'/'+(total/1024).toFixed(0)+' MB'
        document.getElementById('memLabel').textContent='💾 内存使用 '+p+'%'
        var bar=document.getElementById('memBar')
        bar.style.width=Math.min(p,100)+'%'
        bar.style.background=p>85?'#f44336':p>70?'#ff9800':'#4caf50'
    }).catch(()=>{})
}

function loadApkCache(){
    fetch('/api/apk_cache_size').then(r=>r.json()).then(d=>{document.getElementById('cacheSize').textContent=(d.size_mb||0).toFixed(1)+' MB'}).catch(()=>{document.getElementById('cacheSize').textContent='-- MB'})
}

function loadScripts() {
    fetch('/api/scripts').then(r => r.json()).then(data => {
        var g = document.getElementById('grid');
        if (!data || !data.length) {
            g.innerHTML = '<div class="empty">📂 暂无脚本</div>';
            updateStats(0, 0, 0, 0);
            return;
        }
        var rn = 0, su = 0, fa = 0, html = '';
        data.forEach(function(s) {
            var st = s.status || 'idle';
            if (st === 'running') rn++;
            if (st === 'success') su++;
            if (['failed', 'timeout', 'error'].indexOf(st) !== -1) fa++;
            var remark = s.remark ? '<div class="remark-line">' + s.remark + '</div>' : '';
            var stopBtn = st === 'running' ? '<button class="btn-stop" data-name="' + s.name + '" onclick="stopScript(\'' + s.name + '\')">⏹ 停止</button>' : '';
            var runBtn = '<button class="btn-run" data-name="' + s.name + '" onclick="runScript(\'' + s.name + '\')">▶ 运行</button>';
            html += '<div class="card ' + st + '">' +
                '<div class="top"><span class="name">' + s.name + '</span>' + badge(st) + '</div>' +
                remark +
                '<div class="info"><span class="lbl">📏</span> ' + (s.size / 1024).toFixed(1) + 'KB &nbsp; <span class="lbl">🕐</span> ' + s.mtime + '</div>' +
                '<div class="actions">' + runBtn + stopBtn + '</div></div>';
        });
        g.innerHTML = html;
        updateStats(data.length, rn, su, fa);
    }).catch(function() {});
}

function updateStats(t, r, s, f) {
    document.getElementById('total').textContent = t;
    document.getElementById('running').textContent = r;
    document.getElementById('success').textContent = s;
    document.getElementById('failed').textContent = f;
}
function loadAll() { loadScripts(); loadMem(); loadApkCache(); }

// ========== 运行脚本（自动检测 popup 标记） ==========
function runScript(name) {
    fetch('/api/check_popup/' + encodeURIComponent(name))
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.popup) {
                loadModal(data.popup);
                return;
            }
            doRunTool('run_script.py', ['--name', name], '▶ 运行 ' + name);
        })
        .catch(function() {
            doRunTool('run_script.py', ['--name', name], '▶ 运行 ' + name);
        });
}

// ========== 停止脚本 ==========
function stopScript(name) {
    if (!confirm('停止 "' + name + '" 吗？')) return;
    doRunTool('stop_script.py', ['--name', name], '⏹ 停止脚本');
}

// ========== 通用工具调用 ==========
function doRunTool(script, args, label) {
    var modal = document.getElementById('toolModal');
    document.getElementById('keepOpenCheck').checked = false;
    document.getElementById('toolTitle').textContent = '⏳ ' + label + ' ...';
    document.getElementById('toolOutput').textContent = '执行中...';
    openModal('toolModal');
    fetch('/api/run_tool', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ script: script, args: args })
    })
    .then(r => r.json())
    .then(d => {
        var output = d.output || '执行完成';
        var isError = output.indexOf('❌') !== -1 || 
                      output.indexOf('错误') !== -1 || 
                      output.indexOf('失败') !== -1 ||
                      output.indexOf('不存在') !== -1;
        var isSuccess = !isError;
        document.getElementById('toolTitle').textContent = (isSuccess ? '✅ ' : '❌ ') + label + ' 完成';
        document.getElementById('toolOutput').textContent = output;
        loadAll();
        if (isSuccess) {
            var keepOpen = document.getElementById('keepOpenCheck').checked;
            if (!keepOpen) {
                setTimeout(function() {
                    closeModal('toolModal');
                }, 3000);
            }
        }
    })
    .catch(e => {
        document.getElementById('toolTitle').textContent = '❌ ' + label + ' 失败';
        document.getElementById('toolOutput').textContent = '执行失败: ' + e.message;
    });
}

// ========== 通用弹窗加载器（使用普通 eval，自动调用 window.init_xxx） ==========
function loadModal(name) {
    var container = document.getElementById('modalContainer');
    if (window.modalLoaded) {
        document.querySelectorAll('#modalContainer .modal').forEach(function(el) {
            el.style.display = 'none';
        });
        var target = document.getElementById(name);
        if (target) {
            target.style.display = 'flex';
            var initFn = window['init_' + name];
            if (typeof initFn === 'function') {
                setTimeout(initFn, 100);
            }
        }
        return;
    }
    fetch('/static/modal_content.html')
        .then(function(r) { return r.text(); })
        .then(function(html) {
            var scriptCode = '';
            html = html.replace(/<script>([\s\S]*?)<\/script>/g, function(match, code) {
                scriptCode += code + '\n';
                return '';
            });
            container.innerHTML = html;
            window.modalLoaded = true;
            if (scriptCode) {
                try { eval(scriptCode); } catch(e) { console.log('弹窗 JS 执行失败:', e); }
            }
            document.querySelectorAll('#modalContainer .modal').forEach(function(el) {
                el.style.display = 'none';
            });
            var target = document.getElementById(name);
            if (target) {
                target.style.display = 'flex';
                var initFn = window['init_' + name];
                if (typeof initFn === 'function') {
                    setTimeout(initFn, 100);
                }
            }
        })
        .catch(function(e) { alert('加载模块失败: ' + e.message); });
}

// ========== 动态按钮生成 ==========
function loadButtons() {
    fetch('/api/buttons')
        .then(r => r.json())
        .then(data => {
            var scriptDiv = document.getElementById('scriptBtns');
            if (scriptDiv && data.script) {
                data.script.forEach(function(btn) {
                    var b = document.createElement('button');
                    b.textContent = btn.title;
                    b.className = btn.btnClass || 'btn-default';
                    b.onclick = function() { executeAction(btn.action, btn.title); };
                    scriptDiv.appendChild(b);
                });
            }
            var routerDiv = document.getElementById('routerBtns');
            if (routerDiv && data.router) {
                data.router.forEach(function(btn) {
                    var b = document.createElement('button');
                    b.textContent = btn.title;
                    b.className = btn.btnClass || 'btn-default';
                    b.onclick = function() { executeAction(btn.action, btn.title); };
                    routerDiv.appendChild(b);
                });
            }
        })
        .catch(e => console.log('加载按钮失败:', e));
}

function executeAction(action, label) {
    if (action.startsWith('runScript:')) {
        var script = action.split(':')[1];
        runScript(script);
    } else if (action.startsWith('runTool:')) {
        var script = action.split(':')[1];
        doRunTool(script, [], label || script);
    } else if (action.startsWith('func:')) {
        var funcName = action.split(':')[1];
        if (typeof window[funcName] === 'function') {
            window[funcName]();
        }
    }
}

document.getElementById('refreshBtn').onclick = loadAll;

fetchRouterIP();
loadAll();
loadButtons();
setInterval(loadAll, 10000);
</script>
</body></html>
'''

if __name__ == '__main__':
    init_files()
    kill_process_on_port(5000)
    print("🚀 Bottle 面板启动在 http://0.0.0.0:5000")
    run(host='0.0.0.0', port=5000, debug=False)
