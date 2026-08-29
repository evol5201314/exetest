#!/usr/bin/env python3
# -*- coding: utf-8 -*-
beizhu = "📈 监控股价"
# popup: stockConfigModal
# html: stock_config.html
"""
================================================================
🎯 脚本功能说明（供后续修改参考）
【基本用途】
实时监控A股/国内ETF、美股指数、虚拟币（BTC/ETH等）的价格。
支持在面板中配置多条监控记录（同一只股票可以有多行，对应不同的报警价）。
美股：第0位=雅虎代码，第1位=用户备注名称，第2位=低于报警，第3位=高于报警；已移除腾讯备用通道
脚本运行后，会拉取当前价格、昨收价、前日收盘价，并计算“今日涨幅”和“昨日涨幅”。
脚本默认不推送消息（只打印在CMD中作为预览），但预留了推送接口，可以随时接入。
【运行模式】
1. `python monitor_stock.py`          —— 普通监控，仅报警触发推送
2. `python monitor_stock.py --manual-push` —— 手动强制推送完整快照，无视报警条件
3. `python monitor_stock.py --get`    —— 读取当前配置输出JSON
4. `python monitor_stock.py --set '{"..."}'` —— 保存配置写入 stock_config.py
5. `python monitor_stock.py --get-price` —— 只拉取当前价格返回JSON
================================================================
================================================================
🎯 脚本功能说明
1. PUSH_ENABLE：推送总开关；开启后，普通模式仅报警触发推送；--manual‑push强制推送
2. VERBOSE_LOG：调试输出【严格二态】
    True = 完整控制台调试打印；False = 完全静默，stdout无输出，降低路由器IO
3. --get / --set / --get‑price / --manual‑push 工具命令不受VERBOSE_LOG控制
================================================================
"""
import os, sys, json, argparse, requests, re
from concurrent.futures import ThreadPoolExecutor, as_completed
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass
if os.name == 'nt':
    BASE_DIR = r"D:\tmp\scripts"
else:
    BASE_DIR = "/root/scripts"
CONFIG_FILE = os.path.join(BASE_DIR, "stock_config.py")
YAHOO_HEADERS = {
    "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
TENCENT_HEADERS = {
    "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
# 全局 Session 复用连接
tencent_session = requests.Session()
tencent_session.headers.update(TENCENT_HEADERS)
yahoo_session = requests.Session()
yahoo_session.headers.update(YAHOO_HEADERS)
okx_session = requests.Session()
okx_session.headers.update({"User-Agent": "Mozilla/5.0"})

def pushplus_send(token, title, content):
    if not token:
        return False
    try:
        url = "http://www.pushplus.plus/send"
        payload = {
            "token": token,
            "title": title,
            "content": content
        }
        r = requests.post(url, json=payload, timeout=10)
        return r.status_code == 200
    except Exception:
        return False
def load_config():
    try:
        if BASE_DIR not in sys.path:
            sys.path.insert(0, BASE_DIR)
        import stock_config
        push_enable = getattr(stock_config, "PUSH_ENABLE", False)
        verbose_log = getattr(stock_config, "VERBOSE_LOG", False)
        return push_enable, verbose_log, stock_config.PUSH_TOKEN, stock_config.STOCK_CONFIG, stock_config.US_CONFIG, stock_config.CRYPTO_CONFIG
    except Exception:
        return (False,
                False,
                "cdc7db6c36da46c1b877543016be3cba",
                [["sh518880", "", 0, 0], ["", "", 0, 0], ["", "", 0, 0], ["", "", 0, 0], ["", "", 0, 0], ["", "", 0, 0], ["", "", 0, 0], ["", "", 0, 0], ["", "", 0, 0], ["", "", 0, 0]],
                [["^IXIC", "", 0, 0], ["^GSPC", "", 0, 0], ["", "", 0, 0], ["", "", 0, 0], ["", "", 0, 0], ["", "", 0, 0], ["", "", 0, 0], ["", "", 0, 0], ["", "", 0, 0], ["", "", 0, 0]],
                [["BTC", "", 0, 0], ["ETH", "", 0, 0], ["", "", 0, 0], ["", "", 0, 0], ["", "", 0, 0], ["", "", 0, 0], ["", "", 0, 0], ["", "", 0, 0], ["", "", 0, 0], ["", "", 0, 0]])
PUSH_ENABLE, VERBOSE_LOG, PUSH_TOKEN, STOCK_CONFIG, US_CONFIG, CRYPTO_CONFIG = load_config()

def resolve_tencent_code(raw_code):
    return raw_code.strip()

# ========== A股数据获取（合并为一次K线请求） ==========
def get_a_stock_recent_three_days(code):
    """
    获取A股最近三天数据：今日（当前价、最高、最低），昨日（收、高、低），前日（收、高、低）
    使用腾讯K线接口一次获取，减少请求次数。
    """
    tencent_code = resolve_tencent_code(code)
    result = {
        "today": {"current": 0.0, "high": 0.0, "low": 0.0},
        "yesterday": {"close": 0.0, "high": 0.0, "low": 0.0},
        "prev_day": {"close": 0.0, "high": 0.0, "low": 0.0},
    }
    try:
        url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={tencent_code},day,,,5,"
        r = tencent_session.get(url, timeout=8)
        j = r.json()
        stock_node = j.get("data", {}).get(tencent_code, {})
        day_list = stock_node.get("day", [])
        if len(day_list) >= 1:
            # 今日K线（可能未收盘）
            today = day_list[-1]
            # 腾讯K线数组：[日期, 开盘, 收盘, 最高, 最低, 成交量, ...]
            result["today"]["current"] = float(today[2]) if today[2] else 0.0
            result["today"]["high"] = float(today[3]) if today[3] else 0.0
            result["today"]["low"] = float(today[4]) if today[4] else 0.0
        if len(day_list) >= 2:
            yesterday = day_list[-2]
            result["yesterday"]["close"] = float(yesterday[2]) if yesterday[2] else 0.0
            result["yesterday"]["high"] = float(yesterday[3]) if yesterday[3] else 0.0
            result["yesterday"]["low"] = float(yesterday[4]) if yesterday[4] else 0.0
        if len(day_list) >= 3:
            prev_day = day_list[-3]
            result["prev_day"]["close"] = float(prev_day[2]) if prev_day[2] else 0.0
            result["prev_day"]["high"] = float(prev_day[3]) if prev_day[3] else 0.0
            result["prev_day"]["low"] = float(prev_day[4]) if prev_day[4] else 0.0
    except Exception:
        pass
    return result

# ========== 美股数据获取（雅虎财经） ==========
def get_us_stock_recent_three_days(yahoo_code):
    """
    获取美股最近三天数据：今日（当前价、最高、最低），昨日（收、高、低），前日（收、高、低）
    """
    result = {
        "today": {"current": 0.0, "high": 0.0, "low": 0.0},
        "yesterday": {"close": 0.0, "high": 0.0, "low": 0.0},
        "prev_day": {"close": 0.0, "high": 0.0, "low": 0.0},
    }
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_code}?range=5d&interval=1d"
        r = yahoo_session.get(url, timeout=6)
        j = r.json()
        res = j["chart"]["result"][0]
        meta = res["meta"]
        quote = res["indicators"]["quote"][0]

        result["today"]["current"] = float(meta["regularMarketPrice"])
        result["today"]["high"] = float(meta["regularMarketDayHigh"])
        result["today"]["low"] = float(meta["regularMarketDayLow"])

        closes = quote["close"]
        highs = quote["high"]
        lows = quote["low"]

        if len(closes) >= 2:
            result["yesterday"]["close"] = float(closes[-2]) if closes[-2] is not None else 0.0
            result["yesterday"]["high"] = float(highs[-2]) if highs[-2] is not None else 0.0
            result["yesterday"]["low"] = float(lows[-2]) if lows[-2] is not None else 0.0
        if len(closes) >= 3:
            result["prev_day"]["close"] = float(closes[-3]) if closes[-3] is not None else 0.0
            result["prev_day"]["high"] = float(highs[-3]) if highs[-3] is not None else 0.0
            result["prev_day"]["low"] = float(lows[-3]) if lows[-3] is not None else 0.0
    except Exception:
        pass
    return result

# ========== 虚拟币数据获取（OKX） ==========
def get_crypto_recent_three_days(code):
    """
    获取虚拟币最近三天数据：今日（当前价、最高、最低），昨日（收、高、低），前日（收、高、低）
    使用OKX日K线接口，limit=3
    """
    result = {
        "today": {"current": 0.0, "high": 0.0, "low": 0.0},
        "yesterday": {"close": 0.0, "high": 0.0, "low": 0.0},
        "prev_day": {"close": 0.0, "high": 0.0, "low": 0.0},
    }
    try:
        url = f"https://www.okx.com/api/v5/market/history-candles?instId={code}-USDT&bar=1D&limit=3"
        r = okx_session.get(url, timeout=8)
        data = r.json().get('data', [])
        if len(data) >= 1:
            result["today"]["current"] = float(data[0][4])
            result["today"]["high"] = float(data[0][2])
            result["today"]["low"] = float(data[0][3])
        if len(data) >= 2:
            result["yesterday"]["close"] = float(data[1][4])
            result["yesterday"]["high"] = float(data[1][2])
            result["yesterday"]["low"] = float(data[1][3])
        if len(data) >= 3:
            result["prev_day"]["close"] = float(data[2][4])
            result["prev_day"]["high"] = float(data[2][2])
            result["prev_day"]["low"] = float(data[2][3])
    except Exception:
        pass
    return result

# ========== 计算涨幅 ==========
def calc_pct(current, prev):
    return ((current - prev) / prev * 100) if prev > 1e-6 else 0.0

# ========== 统一推送格式（美化版） ==========
def format_entry(section_title, index, code, name, data):
    """
    data: {
        "today": {"current": float, "high": float, "low": float},
        "yesterday": {"close": float, "high": float, "low": float},
        "prev_day": {"close": float, "high": float, "low": float}
    }
    返回格式化字符串
    """
    today_current = data["today"]["current"]
    yesterday_close = data["yesterday"]["close"]
    prev_day_close = data["prev_day"]["close"]
    today_pct = calc_pct(today_current, yesterday_close) if yesterday_close > 0 else 0.0
    yesterday_pct = calc_pct(yesterday_close, prev_day_close) if prev_day_close > 0 else None

    lines = []
    lines.append(f"【{section_title}】第{index}行")
    lines.append(f"【{name}】 ({code})")
    lines.append("=" * 30)
    today_str = f"现{today_current:.2f}" if today_current else "现N/A"
    today_high_str = f"{data['today']['high']:.2f}" if data['today']['high'] else "N/A"
    today_low_str = f"{data['today']['low']:.2f}" if data['today']['low'] else "N/A"
    lines.append(f"【今日】{today_str} | 高{today_high_str} | 低{today_low_str}")
    y_close_str = f"{data['yesterday']['close']:.2f}" if data['yesterday']['close'] else "N/A"
    y_high_str = f"{data['yesterday']['high']:.2f}" if data['yesterday']['high'] else "N/A"
    y_low_str = f"{data['yesterday']['low']:.2f}" if data['yesterday']['low'] else "N/A"
    lines.append(f"【昨日】收{y_close_str} | 高{y_high_str} | 低{y_low_str}")
    p_close_str = f"{data['prev_day']['close']:.2f}" if data['prev_day']['close'] else "N/A"
    p_high_str = f"{data['prev_day']['high']:.2f}" if data['prev_day']['high'] else "N/A"
    p_low_str = f"{data['prev_day']['low']:.2f}" if data['prev_day']['low'] else "N/A"
    lines.append(f"【前日】收{p_close_str} | 高{p_high_str} | 低{p_low_str}")
    yp_str = f"{yesterday_pct:+.2f}%" if yesterday_pct is not None else "N/A"
    lines.append(f"【涨幅】今日{today_pct:+.2f}% | 昨日{yp_str}")
    lines.append("=" * 30)
    return "\n".join(lines)

# ========== 报警判断抽象函数 ==========
def check_alerts(section, index, code, name, data, low, high):
    """
    检查今日现价、最高、最低，昨日收盘、最高、最低共6个价格是否触发报警。
    返回报警信息列表。
    """
    alerts = []
    if not low and not high:
        return alerts
    # 收集所有待检查的价格
    prices_to_check = []
    # 今日现价
    if data["today"]["current"] > 0:
        prices_to_check.append(("今日现价", data["today"]["current"]))
    # 今日最高
    if data["today"]["high"] > 0:
        prices_to_check.append(("今日最高价", data["today"]["high"]))
    # 今日最低
    if data["today"]["low"] > 0:
        prices_to_check.append(("今日最低价", data["today"]["low"]))
    # 昨日收盘
    if data["yesterday"]["close"] > 0:
        prices_to_check.append(("昨日收盘价", data["yesterday"]["close"]))
    # 昨日最高
    if data["yesterday"]["high"] > 0:
        prices_to_check.append(("昨日最高价", data["yesterday"]["high"]))
    # 昨日最低
    if data["yesterday"]["low"] > 0:
        prices_to_check.append(("昨日最低价", data["yesterday"]["low"]))

    for price_type, price_val in prices_to_check:
        if low:
            low_val = float(low)
            if price_val <= low_val:
                alerts.append(f"【{section}】第{index}行 {code} {name} {price_type} {price_val:.2f} 跌破报警线 {low_val}！")
        if high:
            high_val = float(high)
            if price_val >= high_val:
                alerts.append(f"【{section}】第{index}行 {code} {name} {price_type} {price_val:.2f} 突破报警线 {high_val}！")
    return alerts

# ========== 并发获取所有数据 ==========
def fetch_all_data():
    """
    使用三个线程分别获取A股、美股、虚拟币数据，返回三个列表，元素为(code, data)。
    """
    stock_results = []
    us_results = []
    crypto_results = []

    def fetch_a_stock_all():
        res = []
        for cfg in STOCK_CONFIG:
            code = cfg[0]
            if code:
                data = get_a_stock_recent_three_days(code)
                res.append((code, data))
        return res

    def fetch_us_all():
        res = []
        for cfg in US_CONFIG:
            code = cfg[0]
            if code:
                data = get_us_stock_recent_three_days(code)
                res.append((code, data))
        return res

    def fetch_crypto_all():
        res = []
        for cfg in CRYPTO_CONFIG:
            code = cfg[0]
            if code:
                data = get_crypto_recent_three_days(code)
                res.append((code, data))
        return res

    with ThreadPoolExecutor(max_workers=3) as executor:
        future_a = executor.submit(fetch_a_stock_all)
        future_us = executor.submit(fetch_us_all)
        future_crypto = executor.submit(fetch_crypto_all)
        stock_results = future_a.result()
        us_results = future_us.result()
        crypto_results = future_crypto.result()

    return stock_results, us_results, crypto_results

def build_full_report():
    entries = []
    stock_results, us_results, crypto_results = fetch_all_data()
    # A股
    for idx, (code, data) in enumerate(stock_results, 1):
        cfg = STOCK_CONFIG[idx-1]  # 保持与原配置顺序一致
        remark = cfg[1]
        name = remark.strip() if remark.strip() else code
        entries.append(format_entry("A/港国内股", idx, code, name, data))
    # 美股
    for idx, (code, data) in enumerate(us_results, 1):
        cfg = US_CONFIG[idx-1]
        remark = cfg[1]
        name = remark.strip() if remark.strip() else code
        entries.append(format_entry("美股指数", idx, code, name, data))
    # 虚拟币
    for idx, (code, data) in enumerate(crypto_results, 1):
        cfg = CRYPTO_CONFIG[idx-1]
        remark = cfg[1]
        name = remark.strip() if remark.strip() else code
        entries.append(format_entry("虚拟币", idx, code, name, data))
    return "\n\n".join(entries)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--get', action='store_true')
    parser.add_argument('--set', type=str, default='')
    parser.add_argument('--get-price', action='store_true')
    parser.add_argument('--manual-push', action='store_true', help="手动强制推送完整行情快照，不判断报警条件")
    args = parser.parse_args()
    if args.get:
        print(json.dumps({
            "PUSH_ENABLE": PUSH_ENABLE,
            "VERBOSE_LOG": VERBOSE_LOG,
            "PUSH_TOKEN": PUSH_TOKEN,
            "STOCK_CONFIG": STOCK_CONFIG,
            "US_CONFIG": US_CONFIG,
            "CRYPTO_CONFIG": CRYPTO_CONFIG
        }, ensure_ascii=False))
        sys.exit(0)
    if args.set:
        try:
            new_config = json.loads(args.set)
            token = new_config.get("PUSH_TOKEN", "").strip()
            push_enable_flag = bool(new_config.get("PUSH_ENABLE", False))
            verbose_flag = bool(new_config.get("VERBOSE_LOG", False))
            if not token:
                token = "cdc7db6c36da46c1b877543016be3cba"
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                f.write('Yingcang = True\n')
                f.write(f'PUSH_ENABLE = {push_enable_flag}\n')
                f.write(f'VERBOSE_LOG = {verbose_flag}\n')
                f.write(f'PUSH_TOKEN = "{token}"\n')
                f.write(f'STOCK_CONFIG = {json.dumps(new_config.get("STOCK_CONFIG", []), ensure_ascii=False)}\n')
                f.write(f'US_CONFIG = {json.dumps(new_config.get("US_CONFIG", []), ensure_ascii=False)}\n')
                f.write(f'CRYPTO_CONFIG = {json.dumps(new_config.get("CRYPTO_CONFIG", []), ensure_ascii=False)}\n')
        except Exception:
            pass
        sys.exit(0)
    if args.get_price:
        result = {"stocks": {}, "us": {}, "crypto": {}}
        stock_results, us_results, crypto_results = fetch_all_data()
        for code, data in stock_results:
            result["stocks"][code] = data["today"]["current"]
        for code, data in us_results:
            result["us"][code] = data["today"]["current"]
        for code, data in crypto_results:
            result["crypto"][code] = data["today"]["current"]
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(0)
    # =========手动强制推送模式=========
    if args.manual_push:
        rep = build_full_report()
        if PUSH_ENABLE:
            ok = pushplus_send(PUSH_TOKEN, "📈手动行情快照", rep)
            print("手动推送完成，已发送pushplus" if ok else "推送失败，请检查token或网络")
        else:
            print("PUSH_ENABLE关闭，仅预览内容：\n"+rep)
        sys.exit(0)
    # =========普通定时监控模式=========
    alerts = []
    push_entries = []
    try:
        stock_results, us_results, crypto_results = fetch_all_data()
        # A股处理
        for idx, (code, data) in enumerate(stock_results, 1):
            cfg = STOCK_CONFIG[idx-1]
            remark = cfg[1]
            low = cfg[2]
            high = cfg[3]
            name = remark.strip() if remark.strip() else code
            push_entries.append(format_entry("A/港国内股", idx, code, name, data))
            alerts.extend(check_alerts("股票", idx, code, name, data, low, high))
        # 美股处理
        for idx, (code, data) in enumerate(us_results, 1):
            cfg = US_CONFIG[idx-1]
            remark = cfg[1]
            low = cfg[2]
            high = cfg[3]
            name = remark.strip() if remark.strip() else code
            push_entries.append(format_entry("美股指数", idx, code, name, data))
            alerts.extend(check_alerts("美股", idx, code, name, data, low, high))
        # 虚拟币处理
        for idx, (code, data) in enumerate(crypto_results, 1):
            cfg = CRYPTO_CONFIG[idx-1]
            remark = cfg[1]
            low = cfg[2]
            high = cfg[3]
            name = remark.strip() if remark.strip() else code
            push_entries.append(format_entry("虚拟币", idx, code, name, data))
            alerts.extend(check_alerts("虚拟币", idx, code, name, data, low, high))

        if VERBOSE_LOG:
            print("=" * 50)
            print("开始进行价格监控检查...")
            print(f"消息推送开关：{'✅开启' if PUSH_ENABLE else '❌关闭(仅预览)'}")
            print("=" * 50)
            for entry in push_entries:
                print(entry)
                print("-" * 30)
            if alerts:
                print("\n❗ 报警触发情况：")
                for alert in alerts:
                    print(f"  → {alert}")
            else:
                print("\n✅ 当前没有报警触发，一切正常。")
        full_report = "\n\n".join(push_entries)
        if alerts:
            alert_text = "\n".join(alerts)
            full_report += f"\n\n❗====触发报警====\n{alert_text}"
        if PUSH_ENABLE and len(alerts) > 0:
            pushplus_send(PUSH_TOKEN, "📈股价监控快照", full_report)
    except Exception:
        pass
