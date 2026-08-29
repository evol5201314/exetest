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

# ========== A股数据获取（腾讯） ==========
def get_a_stock_recent_three_days(code):
    """
    获取A股最近三天数据：今日（当前价、最高、最低），昨日（收、高、低），前日（收、高、低）
    返回字典，若无数据则对应值为0.0
    """
    tencent_code = resolve_tencent_code(code)
    result = {
        "today": {"current": 0.0, "high": 0.0, "low": 0.0},
        "yesterday": {"close": 0.0, "high": 0.0, "low": 0.0},
        "prev_day": {"close": 0.0, "high": 0.0, "low": 0.0},
    }
    # 1. 实时接口：获取当前价、昨收、今日最高、今日最低
    try:
        r = requests.get(f"http://qt.gtimg.cn/q={tencent_code}", headers=TENCENT_HEADERS, timeout=8)
        text = r.text.replace("\x00","").strip()
        if '="' in text:
            body = text.split('="')[1].split('"')[0]
            arr = body.split("~")
            if len(arr) >= 35:
                # 索引3：当前价；索引33：今日最高；索引34：今日最低；索引4：昨收
                result["today"]["current"] = float(arr[3]) if arr[3] else 0.0
                result["today"]["high"] = float(arr[33]) if arr[33] else 0.0
                result["today"]["low"] = float(arr[34]) if arr[34] else 0.0
                result["yesterday"]["close"] = float(arr[4]) if arr[4] else 0.0
    except Exception:
        pass

    # 2. K线接口：获取最近3根日K，取倒数第二、第三根作为昨日和前日
    try:
        url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={tencent_code},day,,,5,"
        r = requests.get(url, headers=TENCENT_HEADERS, timeout=8)
        j = r.json()
        stock_node = j.get("data", {}).get(tencent_code, {})
        day_list = stock_node.get("day", [])
        if len(day_list) >= 2:
            # 腾讯K线数组结构：[日期, 开盘, 收盘, 最高, 最低, 成交量, ...]
            # 昨日
            if len(day_list) >= 2:
                y_close = float(day_list[-2][2])
                y_high = float(day_list[-2][3])
                y_low = float(day_list[-2][4])
                if y_close > 0:
                    result["yesterday"]["close"] = y_close
                result["yesterday"]["high"] = y_high
                result["yesterday"]["low"] = y_low
            # 前日
            if len(day_list) >= 3:
                p_close = float(day_list[-3][2])
                p_high = float(day_list[-3][3])
                p_low = float(day_list[-3][4])
                result["prev_day"]["close"] = p_close
                result["prev_day"]["high"] = p_high
                result["prev_day"]["low"] = p_low
    except Exception:
        pass

    return result

# ========== 美股数据获取（雅虎财经） ==========
def get_us_stock_recent_three_days(yahoo_code):
    """
    获取美股最近三天数据：今日（当前价、最高、最低），昨日（收、高、低），前日（收、高、低）
    返回字典，若无数据则对应值为0.0
    """
    result = {
        "today": {"current": 0.0, "high": 0.0, "low": 0.0},
        "yesterday": {"close": 0.0, "high": 0.0, "low": 0.0},
        "prev_day": {"close": 0.0, "high": 0.0, "low": 0.0},
    }
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_code}?range=5d&interval=1d"
        r = requests.get(url, headers=YAHOO_HEADERS, timeout=6)
        j = r.json()
        res = j["chart"]["result"][0]
        meta = res["meta"]
        quote = res["indicators"]["quote"][0]

        # 今日数据来自meta
        result["today"]["current"] = float(meta["regularMarketPrice"])
        result["today"]["high"] = float(meta["regularMarketDayHigh"])
        result["today"]["low"] = float(meta["regularMarketDayLow"])

        # 历史K线数组：close, high, low
        closes = quote["close"]
        highs = quote["high"]
        lows = quote["low"]

        # 昨日（倒数第二根）
        if len(closes) >= 2:
            result["yesterday"]["close"] = float(closes[-2]) if closes[-2] is not None else 0.0
            result["yesterday"]["high"] = float(highs[-2]) if highs[-2] is not None else 0.0
            result["yesterday"]["low"] = float(lows[-2]) if lows[-2] is not None else 0.0
        # 前日（倒数第三根）
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
    使用OKX日K线接口，数据最新在前，limit=3
    """
    result = {
        "today": {"current": 0.0, "high": 0.0, "low": 0.0},
        "yesterday": {"close": 0.0, "high": 0.0, "low": 0.0},
        "prev_day": {"close": 0.0, "high": 0.0, "low": 0.0},
    }
    try:
        url = f"https://www.okx.com/api/v5/market/history-candles?instId={code}-USDT&bar=1D&limit=3"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
        data = r.json().get('data', [])
        # data[0] 今日，data[1] 昨日，data[2] 前日
        if len(data) >= 1:
            # 今日K线：索引1开盘，2最高，3最低，4收盘（即最新价）
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
    # 计算涨幅
    today_current = data["today"]["current"]
    yesterday_close = data["yesterday"]["close"]
    prev_day_close = data["prev_day"]["close"]
    today_pct = calc_pct(today_current, yesterday_close) if yesterday_close > 0 else 0.0
    yesterday_pct = calc_pct(yesterday_close, prev_day_close) if prev_day_close > 0 else None

    lines = []
    lines.append(f"【{section_title}】第{index}行")
    lines.append(f"【{name}】 ({code})")
    lines.append("=" * 30)
    # 今日行
    today_str = f"现{today_current:.2f}" if today_current else "现N/A"
    today_high_str = f"{data['today']['high']:.2f}" if data['today']['high'] else "N/A"
    today_low_str = f"{data['today']['low']:.2f}" if data['today']['low'] else "N/A"
    lines.append(f"【今日】{today_str} | 高{today_high_str} | 低{today_low_str}")
    # 昨日行
    y_close_str = f"{data['yesterday']['close']:.2f}" if data['yesterday']['close'] else "N/A"
    y_high_str = f"{data['yesterday']['high']:.2f}" if data['yesterday']['high'] else "N/A"
    y_low_str = f"{data['yesterday']['low']:.2f}" if data['yesterday']['low'] else "N/A"
    lines.append(f"【昨日】收{y_close_str} | 高{y_high_str} | 低{y_low_str}")
    # 前日行
    p_close_str = f"{data['prev_day']['close']:.2f}" if data['prev_day']['close'] else "N/A"
    p_high_str = f"{data['prev_day']['high']:.2f}" if data['prev_day']['high'] else "N/A"
    p_low_str = f"{data['prev_day']['low']:.2f}" if data['prev_day']['low'] else "N/A"
    lines.append(f"【前日】收{p_close_str} | 高{p_high_str} | 低{p_low_str}")
    # 涨幅行
    yp_str = f"{yesterday_pct:+.2f}%" if yesterday_pct is not None else "N/A"
    lines.append(f"【涨幅】今日{today_pct:+.2f}% | 昨日{yp_str}")
    lines.append("=" * 30)
    return "\n".join(lines)

def build_full_report():
    entries = []
    # A股
    for idx, cfg in enumerate(STOCK_CONFIG, 1):
        code, remark, low, high = cfg[0], cfg[1], cfg[2], cfg[3]
        if not code:
            continue
        data = get_a_stock_recent_three_days(code)
        name = remark.strip() if remark.strip() else code  # 优先备注名
        entries.append(format_entry("A/港国内股", idx, code, name, data))
    # 美股
    for idx, cfg in enumerate(US_CONFIG, 1):
        y_code, remark, low, high = cfg[0], cfg[1], cfg[2], cfg[3]
        if not y_code:
            continue
        data = get_us_stock_recent_three_days(y_code)
        name = remark.strip() if remark.strip() else y_code
        entries.append(format_entry("美股指数", idx, y_code, name, data))
    # 虚拟币
    for idx, cfg in enumerate(CRYPTO_CONFIG, 1):
        code, remark, low, high = cfg[0], cfg[1], cfg[2], cfg[3]
        if not code:
            continue
        data = get_crypto_recent_three_days(code)
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
        for cfg in STOCK_CONFIG:
            code = cfg[0]
            if code:
                data = get_a_stock_recent_three_days(code)
                result["stocks"][code] = data["today"]["current"]
        for cfg in US_CONFIG:
            y_code = cfg[0]
            if y_code:
                data = get_us_stock_recent_three_days(y_code)
                result["us"][y_code] = data["today"]["current"]
        for cfg in CRYPTO_CONFIG:
            code = cfg[0]
            if code:
                data = get_crypto_recent_three_days(code)
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
        # A股
        for index, cfg in enumerate(STOCK_CONFIG, 1):
            code, remark, low, high = cfg[0], cfg[1], cfg[2], cfg[3]
            if not code:
                continue
            data = get_a_stock_recent_three_days(code)
            name = remark.strip() if remark.strip() else code
            # 构建推送条目
            push_entries.append(format_entry("A/港国内股", index, code, name, data))
            # 报警判断
            if low or high:
                # 今日价格
                today_current = data["today"]["current"]
                today_high = data["today"]["high"]
                today_low = data["today"]["low"]
                # 昨日价格
                y_close = data["yesterday"]["close"]
                y_high = data["yesterday"]["high"]
                y_low = data["yesterday"]["low"]
                # 检查低报警线
                if low:
                    low_val = float(low)
                    # 今日现价
                    if today_current > 0 and today_current <= low_val:
                        alerts.append(f"【股票】第{index}行 {code} {name} 今日现价 {today_current:.2f} 跌破报警线 {low_val}！")
                    # 今日最高
                    if today_high > 0 and today_high <= low_val:
                        alerts.append(f"【股票】第{index}行 {code} {name} 今日最高价 {today_high:.2f} 跌破报警线 {low_val}！")
                    # 今日最低
                    if today_low > 0 and today_low <= low_val:
                        alerts.append(f"【股票】第{index}行 {code} {name} 今日最低价 {today_low:.2f} 跌破报警线 {low_val}！")
                    # 昨日收盘
                    if y_close > 0 and y_close <= low_val:
                        alerts.append(f"【股票】第{index}行 {code} {name} 昨日收盘价 {y_close:.2f} 跌破报警线 {low_val}！")
                    # 昨日最高
                    if y_high > 0 and y_high <= low_val:
                        alerts.append(f"【股票】第{index}行 {code} {name} 昨日最高价 {y_high:.2f} 跌破报警线 {low_val}！")
                    # 昨日最低
                    if y_low > 0 and y_low <= low_val:
                        alerts.append(f"【股票】第{index}行 {code} {name} 昨日最低价 {y_low:.2f} 跌破报警线 {low_val}！")
                if high:
                    high_val = float(high)
                    if today_current > 0 and today_current >= high_val:
                        alerts.append(f"【股票】第{index}行 {code} {name} 今日现价 {today_current:.2f} 突破报警线 {high_val}！")
                    if today_high > 0 and today_high >= high_val:
                        alerts.append(f"【股票】第{index}行 {code} {name} 今日最高价 {today_high:.2f} 突破报警线 {high_val}！")
                    if today_low > 0 and today_low >= high_val:
                        alerts.append(f"【股票】第{index}行 {code} {name} 今日最低价 {today_low:.2f} 突破报警线 {high_val}！")
                    if y_close > 0 and y_close >= high_val:
                        alerts.append(f"【股票】第{index}行 {code} {name} 昨日收盘价 {y_close:.2f} 突破报警线 {high_val}！")
                    if y_high > 0 and y_high >= high_val:
                        alerts.append(f"【股票】第{index}行 {code} {name} 昨日最高价 {y_high:.2f} 突破报警线 {high_val}！")
                    if y_low > 0 and y_low >= high_val:
                        alerts.append(f"【股票】第{index}行 {code} {name} 昨日最低价 {y_low:.2f} 突破报警线 {high_val}！")
        # 美股
        for index, cfg in enumerate(US_CONFIG, 1):
            y_code, remark, low, high = cfg[0], cfg[1], cfg[2], cfg[3]
            if not y_code:
                continue
            data = get_us_stock_recent_three_days(y_code)
            name = remark.strip() if remark.strip() else y_code
            push_entries.append(format_entry("美股指数", index, y_code, name, data))
            if low or high:
                today_current = data["today"]["current"]
                today_high = data["today"]["high"]
                today_low = data["today"]["low"]
                y_close = data["yesterday"]["close"]
                y_high = data["yesterday"]["high"]
                y_low = data["yesterday"]["low"]
                if low:
                    low_val = float(low)
                    if today_current > 0 and today_current <= low_val:
                        alerts.append(f"【美股】第{index}行 {y_code} {name} 今日现价 {today_current:.2f} 跌破报警线 {low_val}！")
                    if today_high > 0 and today_high <= low_val:
                        alerts.append(f"【美股】第{index}行 {y_code} {name} 今日最高价 {today_high:.2f} 跌破报警线 {low_val}！")
                    if today_low > 0 and today_low <= low_val:
                        alerts.append(f"【美股】第{index}行 {y_code} {name} 今日最低价 {today_low:.2f} 跌破报警线 {low_val}！")
                    if y_close > 0 and y_close <= low_val:
                        alerts.append(f"【美股】第{index}行 {y_code} {name} 昨日收盘价 {y_close:.2f} 跌破报警线 {low_val}！")
                    if y_high > 0 and y_high <= low_val:
                        alerts.append(f"【美股】第{index}行 {y_code} {name} 昨日最高价 {y_high:.2f} 跌破报警线 {low_val}！")
                    if y_low > 0 and y_low <= low_val:
                        alerts.append(f"【美股】第{index}行 {y_code} {name} 昨日最低价 {y_low:.2f} 跌破报警线 {low_val}！")
                if high:
                    high_val = float(high)
                    if today_current > 0 and today_current >= high_val:
                        alerts.append(f"【美股】第{index}行 {y_code} {name} 今日现价 {today_current:.2f} 突破报警线 {high_val}！")
                    if today_high > 0 and today_high >= high_val:
                        alerts.append(f"【美股】第{index}行 {y_code} {name} 今日最高价 {today_high:.2f} 突破报警线 {high_val}！")
                    if today_low > 0 and today_low >= high_val:
                        alerts.append(f"【美股】第{index}行 {y_code} {name} 今日最低价 {today_low:.2f} 突破报警线 {high_val}！")
                    if y_close > 0 and y_close >= high_val:
                        alerts.append(f"【美股】第{index}行 {y_code} {name} 昨日收盘价 {y_close:.2f} 突破报警线 {high_val}！")
                    if y_high > 0 and y_high >= high_val:
                        alerts.append(f"【美股】第{index}行 {y_code} {name} 昨日最高价 {y_high:.2f} 突破报警线 {high_val}！")
                    if y_low > 0 and y_low >= high_val:
                        alerts.append(f"【美股】第{index}行 {y_code} {name} 昨日最低价 {y_low:.2f} 突破报警线 {high_val}！")
        # 虚拟币
        for index, cfg in enumerate(CRYPTO_CONFIG, 1):
            code, remark, low, high = cfg[0], cfg[1], cfg[2], cfg[3]
            if not code:
                continue
            data = get_crypto_recent_three_days(code)
            name = remark.strip() if remark.strip() else code
            push_entries.append(format_entry("虚拟币", index, code, name, data))
            if low or high:
                today_current = data["today"]["current"]
                today_high = data["today"]["high"]
                today_low = data["today"]["low"]
                y_close = data["yesterday"]["close"]
                y_high = data["yesterday"]["high"]
                y_low = data["yesterday"]["low"]
                if low:
                    low_val = float(low)
                    if today_current > 0 and today_current <= low_val:
                        alerts.append(f"【虚拟币】第{index}行 {code} {name} 今日现价 {today_current:.2f} 跌破报警线 {low_val}！")
                    if today_high > 0 and today_high <= low_val:
                        alerts.append(f"【虚拟币】第{index}行 {code} {name} 今日最高价 {today_high:.2f} 跌破报警线 {low_val}！")
                    if today_low > 0 and today_low <= low_val:
                        alerts.append(f"【虚拟币】第{index}行 {code} {name} 今日最低价 {today_low:.2f} 跌破报警线 {low_val}！")
                    if y_close > 0 and y_close <= low_val:
                        alerts.append(f"【虚拟币】第{index}行 {code} {name} 昨日收盘价 {y_close:.2f} 跌破报警线 {low_val}！")
                    if y_high > 0 and y_high <= low_val:
                        alerts.append(f"【虚拟币】第{index}行 {code} {name} 昨日最高价 {y_high:.2f} 跌破报警线 {low_val}！")
                    if y_low > 0 and y_low <= low_val:
                        alerts.append(f"【虚拟币】第{index}行 {code} {name} 昨日最低价 {y_low:.2f} 跌破报警线 {low_val}！")
                if high:
                    high_val = float(high)
                    if today_current > 0 and today_current >= high_val:
                        alerts.append(f"【虚拟币】第{index}行 {code} {name} 今日现价 {today_current:.2f} 突破报警线 {high_val}！")
                    if today_high > 0 and today_high >= high_val:
                        alerts.append(f"【虚拟币】第{index}行 {code} {name} 今日最高价 {today_high:.2f} 突破报警线 {high_val}！")
                    if today_low > 0 and today_low >= high_val:
                        alerts.append(f"【虚拟币】第{index}行 {code} {name} 今日最低价 {today_low:.2f} 突破报警线 {high_val}！")
                    if y_close > 0 and y_close >= high_val:
                        alerts.append(f"【虚拟币】第{index}行 {code} {name} 昨日收盘价 {y_close:.2f} 突破报警线 {high_val}！")
                    if y_high > 0 and y_high >= high_val:
                        alerts.append(f"【虚拟币】第{index}行 {code} {name} 昨日最高价 {y_high:.2f} 突破报警线 {high_val}！")
                    if y_low > 0 and y_low >= high_val:
                        alerts.append(f"【虚拟币】第{index}行 {code} {name} 昨日最低价 {y_low:.2f} 突破报警线 {high_val}！")
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
