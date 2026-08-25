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
美股：第0位=雅虎代码，第1位=腾讯备用代码，第2位=低于报警，第3位=高于报警
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
                [["sh518880", 0, 0], ["", 0, 0], ["", 0, 0], ["", 0, 0], ["", 0, 0], ["", 0, 0], ["", 0, 0], ["", 0, 0], ["", 0, 0], ["", 0, 0]],
                [["^IXIC", "us.IXIC", 0, 0], ["^GSPC", "us.INX", 0, 0], ["", "", 0, 0], ["", "", 0, 0], ["", "", 0, 0], ["", "", 0, 0], ["", "", 0, 0], ["", "", 0, 0], ["", "", 0, 0], ["", "", 0, 0]],
                [["BTC", 0, 0], ["ETH", 0, 0], ["", 0, 0], ["", 0, 0], ["", 0, 0], ["", 0, 0], ["", 0, 0], ["", 0, 0], ["", 0, 0], ["", 0, 0]])
PUSH_ENABLE, VERBOSE_LOG, PUSH_TOKEN, STOCK_CONFIG, US_CONFIG, CRYPTO_CONFIG = load_config()

def resolve_tencent_code(raw_code):
    """
    完全不自动补前缀，输入原样返回，全部手动填写完整代码(sh/sz/hk/hf)
    """
    return raw_code.strip()

def get_kline_prev_two_close(tencent_code):
    """
    web.ifzq.gtimg.cn fqkline/get 获取日K
    return (yesterday_close(T‑1), prev_close(T‑2))
    day item: [date,open,high,low,close,volume,...]  item[4]=收盘价
    hf开头海外期货指数该K线接口会返回param error，直接返回(0.0,0.0)
    """
    yc = 0.0
    pc = 0.0
    if tencent_code.startswith("hf"):
        return (yc, pc)
    try:
        url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={tencent_code},day,,,30,"
        r = requests.get(url, headers=TENCENT_HEADERS, timeout=8)
        j = r.json()
        stock_node = j.get("data", {}).get(tencent_code, {})
        day_list = stock_node.get("day", [])
        if len(day_list) >= 2:
            yc = float(day_list[-2][4])
        if len(day_list) >= 3:
            pc = float(day_list[-3][4])
    except Exception:
        pass
    return (yc, pc)

def fetch_a_stock_price(code):
    tencent_code = resolve_tencent_code(code)
    try:
        r = requests.get(f"http://qt.gtimg.cn/q={tencent_code}", headers=TENCENT_HEADERS, timeout=8)
        text = r.text.replace("\x00","").strip()
        if '="' in text:
            body = text.split('="')[1].split('"')[0]
            arr = body.split("~")
            if len(arr)>=4 and arr[3]:
                return str(float(arr[3]))
    except Exception:
        pass
    return "查无"

def get_a_stock_detail(code):
    tencent_code = resolve_tencent_code(code)
    name = code
    current = 0.0
    yesterday = 0.0
    prev_close = 0.0
    # qt接口拿名称、现价、兜底昨收
    try:
        r = requests.get(f"http://qt.gtimg.cn/q={tencent_code}", headers=TENCENT_HEADERS, timeout=8)
        text = r.text.replace("\x00","").strip()
        if '="' in text:
            body = text.split('="')[1].split('"')[0]
            arr = body.split("~")
            name = arr[1] if len(arr)>1 else code
            current = float(arr[3]) if (len(arr)>3 and arr[3]) else 0.0
            yesterday = float(arr[4]) if (len(arr)>4 and arr[4]) else 0.0
    except Exception:
        pass
    # K线接口优先取真实昨日、前日收盘价
    kl_yc, kl_pc = get_kline_prev_two_close(tencent_code)
    if kl_yc > 1e-6:
        yesterday = kl_yc
    if kl_pc > 1e-6:
        prev_close = kl_pc
    today_pct = ((current - yesterday) / yesterday * 100) if yesterday else 0.0
    yesterday_pct = ((yesterday - prev_close) / prev_close * 100) if prev_close > 1e-6 else None
    return {
        "code": code,
        "name": name,
        "current": current,
        "yesterday": yesterday,
        "prev_close": prev_close,
        "today_pct": today_pct,
        "yesterday_pct": yesterday_pct
    }

def fetch_us_price(yahoo_code, tencent_backup_code):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_code}?range=5d&interval=1d"
        r = requests.get(url, headers=YAHOO_HEADERS, timeout=6)
        j = r.json()
        meta = j["chart"]["result"][0]["meta"]
        price = meta.get("regularMarketPrice")
        if price is not None:
            return str(float(price))
    except Exception:
        pass
    if not tencent_backup_code:
        return "查无"
    try:
        r = requests.get(f"http://qt.gtimg.cn/q={tencent_backup_code}", headers=TENCENT_HEADERS, timeout=6)
        text = r.text.replace("\x00","").strip()
        if '="' in text:
            body = text.split('="')[1].split('"')[0]
            arr = body.split("~")
            if len(arr)>=4 and arr[3]:
                return str(float(arr[3]))
    except Exception:
        pass
    return "查无"

def get_us_stock_detail(yahoo_code, tencent_backup_code):
    name = yahoo_code
    tencent_cn_name = ""
    current = 0.0
    yesterday = 0.0
    prev_close = 0.0
    today_pct = 0.0
    yesterday_pct = None
    if tencent_backup_code:
        try:
            r = requests.get(f"http://qt.gtimg.cn/q={tencent_backup_code}", headers=TENCENT_HEADERS, timeout=4)
            text = r.text.replace("\x00","").strip()
            if '="' in text:
                body = text.split('="')[1].split('"')[0]
                arr = body.split("~")
                if len(arr)>=2 and arr[1].strip():
                    tencent_cn_name = arr[1].strip()
        except Exception:
            pass
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_code}?range=5d&interval=1d"
        r = requests.get(url, headers=YAHOO_HEADERS, timeout=6)
        j = r.json()
        res = j["chart"]["result"][0]
        meta = res["meta"]
        closes = res["indicators"]["quote"][0]["close"]
        yahoo_name = meta.get("shortName", yahoo_code)
        name = tencent_cn_name if tencent_cn_name else yahoo_name
        current = meta["regularMarketPrice"]
        valid_closes = [c for c in closes if c is not None]
        if len(valid_closes)>=2:
            yesterday = valid_closes[-2]
        if len(valid_closes)>=3:
            prev_close = valid_closes[-3]
        if yesterday > 1e-6:
            today_pct = ((current - yesterday)/yesterday)*100
        if prev_close >1e-6:
            yesterday_pct = ((yesterday - prev_close)/prev_close)*100
    except Exception:
        if tencent_backup_code:
            try:
                r = requests.get(f"http://qt.gtimg.cn/q={tencent_backup_code}", headers=TENCENT_HEADERS, timeout=6)
                text = r.text.replace("\x00","").strip()
                if '="' in text:
                    body = text.split('="')[1].split('"')[0]
                    arr = body.split("~")
                    name = tencent_cn_name if tencent_cn_name else (arr[1] if len(arr)>1 else yahoo_code)
                    if len(arr)>=4 and arr[3]:
                        current = float(arr[3])
                    if len(arr)>=5 and arr[4]:
                        yesterday = float(arr[4])
                    if yesterday > 1e-6:
                        today_pct = ((current - yesterday) / yesterday) * 100
            except Exception:
                pass
    return {
        "code": yahoo_code,
        "name": name,
        "current": current,
        "yesterday": yesterday,
        "prev_close": prev_close,
        "today_pct": today_pct,
        "yesterday_pct": yesterday_pct
    }

def build_full_report():
    push_content_list = []
    # A股
    for index, cfg in enumerate(STOCK_CONFIG):
        code, low, high = cfg[0], cfg[1], cfg[2]
        if code:
            detail = get_a_stock_detail(code)
            name = detail["name"]
            current = detail["current"]
            yesterday = detail["yesterday"]
            prev_close_val = detail["prev_close"]
            today_pct = detail["today_pct"]
            yesterday_pct = detail["yesterday_pct"]
            pc_text = f"{prev_close_val}" if prev_close_val > 1e-6 else "N/A"
            yp_text = f"{yesterday_pct:.2f}%" if yesterday_pct is not None else "N/A"
            push_content_list.append(
                f"【A/港国内股】\n行号: {index+1}\n号码: {code}\n名称: {name}\n"
                f"当前价格: {current}\n昨日价格: {yesterday}\n前日价格: {pc_text}\n"
                f"当前涨幅: {today_pct:.2f}%\n昨日涨幅: {yp_text}"
            )
    # 美股
    for index, cfg in enumerate(US_CONFIG):
        y_code = cfg[0]
        tencent_bk = cfg[1] if len(cfg) > 1 else ""
        if y_code:
            detail = get_us_stock_detail(y_code, tencent_bk)
            name = detail["name"]
            current = detail["current"]
            yesterday = detail["yesterday"]
            prev_close_val = detail["prev_close"]
            today_pct = detail["today_pct"]
            yesterday_pct = detail["yesterday_pct"]
            pc_text = f"{prev_close_val}" if prev_close_val > 1e-6 else "N/A"
            yp_text = f"{yesterday_pct:.2f}%" if yesterday_pct is not None else "N/A"
            push_content_list.append(
                f"【美股指数】\n行号: {index+1}\n号码: {y_code}\n名称: {name}\n"
                f"当前价格: {current}\n昨日价格: {yesterday}\n前日价格: {pc_text}\n"
                f"当前涨幅: {today_pct:.2f}%\n昨日涨幅: {yp_text}"
            )
    # 虚拟币
    for index, cfg in enumerate(CRYPTO_CONFIG):
        code, low, high = cfg[0], cfg[1], cfg[2]
        if code:
            try:
                r = requests.get(f"https://www.okx.com/api/v5/market/ticker?instId={code}-USDT", headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
                d = r.json()
                if "data" in d and d["data"]:
                    item = d["data"][0]
                    current = float(item.get("last", 0))
                    open_24h = float(item.get("open24h", 0))
                    sod_utc8 = float(item.get("sodUtc8", 0))
                    today_pct = ((current - sod_utc8) / sod_utc8 * 100) if sod_utc8 else 0.0
                    yesterday_pct = ((sod_utc8 - open_24h) / open_24h * 100) if open_24h else 0.0
                    pct_24h = ((current - open_24h) / open_24h * 100) if open_24h else 0.0
                    push_content_list.append(
                        f"【虚拟币】\n行号: {index+1}\n号码: {code}\n当前价格: {current}\n昨日价格: {open_24h}\n"
                        f"当前涨幅: {today_pct:.2f}%\n昨日涨幅: {yesterday_pct:.2f}%\n24小时涨幅: {pct_24h:.2f}%"
                    )
            except Exception:
                pass
    full_report = "\n--------------------\n".join(push_content_list)
    return full_report

# =========================================================================================
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
                result["stocks"][code] = fetch_a_stock_price(code)
        for cfg in US_CONFIG:
            y_code = cfg[0]
            tencent_bk = cfg[1] if len(cfg)>1 else ""
            if y_code:
                result["us"][y_code] = fetch_us_price(y_code, tencent_bk)
        for cfg in CRYPTO_CONFIG:
            code = cfg[0]
            if code:
                try:
                    r = requests.get(f"https://www.okx.com/api/v5/market/ticker?instId={code}-USDT", headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
                    d = r.json()
                    if "data" in d and d["data"]:
                        result["crypto"][code] = d["data"][0]["last"]
                    else:
                        result["crypto"][code] = "查无"
                except Exception:
                    result["crypto"][code] = "查无"
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
    push_content_list = []
    try:
        # A股
        for index, cfg in enumerate(STOCK_CONFIG):
            code, low, high = cfg[0], cfg[1], cfg[2]
            if code:
                detail = get_a_stock_detail(code)
                name = detail["name"]
                current = detail["current"]
                yesterday = detail["yesterday"]
                prev_close_val = detail["prev_close"]
                today_pct = detail["today_pct"]
                yesterday_pct = detail["yesterday_pct"]
                pc_text = f"{prev_close_val}" if prev_close_val > 1e-6 else "N/A"
                yp_text = f"{yesterday_pct:.2f}%" if yesterday_pct is not None else "N/A"
                push_content_list.append(
                    f"【A/港国内股】\n行号: {index+1}\n号码: {code}\n名称: {name}\n"
                    f"当前价格: {current}\n昨日价格: {yesterday}\n前日价格: {pc_text}\n"
                    f"当前涨幅: {today_pct:.2f}%\n昨日涨幅: {yp_text}"
                )
                if low and current <= float(low):
                    alerts.append(f"【股票】第{index+1}行 {code} {name} 现价 {current} 跌破报警线 {low}！")
                if high and current >= float(high):
                    alerts.append(f"【股票】第{index+1}行 {code} {name} 现价 {current} 突破报警线 {high}！")
        # 美股
        for index, cfg in enumerate(US_CONFIG):
            y_code = cfg[0]
            tencent_bk = cfg[1] if len(cfg) > 1 else ""
            low = cfg[2] if len(cfg) > 2 else 0
            high = cfg[3] if len(cfg) > 3 else 0
            if y_code:
                detail = get_us_stock_detail(y_code, tencent_bk)
                name = detail["name"]
                current = detail["current"]
                yesterday = detail["yesterday"]
                prev_close_val = detail["prev_close"]
                today_pct = detail["today_pct"]
                yesterday_pct = detail["yesterday_pct"]
                pc_text = f"{prev_close_val}" if prev_close_val > 1e-6 else "N/A"
                yp_text = f"{yesterday_pct:.2f}%" if yesterday_pct is not None else "N/A"
                push_content_list.append(
                    f"【美股指数】\n行号: {index+1}\n号码: {y_code}\n名称: {name}\n"
                    f"当前价格: {current}\n昨日价格: {yesterday}\n前日价格: {pc_text}\n"
                    f"当前涨幅: {today_pct:.2f}%\n昨日涨幅: {yp_text}"
                )
                if low and current <= float(low):
                    alerts.append(f"【美股】第{index+1}行 {y_code} {name} 现价 {current} 跌破报警线 {low}！")
                if high and current >= float(high):
                    alerts.append(f"【美股】第{index+1}行 {y_code} {name} 现价 {current} 突破报警线 {high}！")
        # 虚拟币
        for index, cfg in enumerate(CRYPTO_CONFIG):
            code, low, high = cfg[0], cfg[1], cfg[2]
            if code:
                try:
                    r = requests.get(f"https://www.okx.com/api/v5/market/ticker?instId={code}-USDT", headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
                    d = r.json()
                    if "data" in d and d["data"]:
                        item = d["data"][0]
                        current = float(item.get("last", 0))
                        open_24h = float(item.get("open24h", 0))
                        sod_utc8 = float(item.get("sodUtc8", 0))
                        today_pct = ((current - sod_utc8) / sod_utc8 * 100) if sod_utc8 else 0.0
                        yesterday_pct = ((sod_utc8 - open_24h) / open_24h * 100) if open_24h else 0.0
                        pct_24h = ((current - open_24h) / open_24h * 100) if open_24h else 0.0
                        push_content_list.append(
                            f"【虚拟币】\n行号: {index+1}\n号码: {code}\n当前价格: {current}\n昨日价格: {open_24h}\n"
                            f"当前涨幅: {today_pct:.2f}%\n昨日涨幅: {yesterday_pct:.2f}%\n24小时涨幅: {pct_24h:.2f}%"
                        )
                        if low and current <= float(low):
                            alerts.append(f"【虚拟币】第{index+1}行 {code} 现价 {current} 跌破报警线 {low}！")
                        if high and current >= float(high):
                            alerts.append(f"【虚拟币】第{index+1}行 {code} 现价 {current} 突破报警线 {high}！")
                except Exception:
                    pass
        if VERBOSE_LOG:
            print("=" * 50)
            print("开始进行价格监控检查...")
            print(f"消息推送开关：{'✅开启' if PUSH_ENABLE else '❌关闭(仅预览)'}")
            print("=" * 50)
            for content in push_content_list:
                print(content)
                print("-" * 30)
            if alerts:
                print("\n❗ 报警触发情况：")
                for alert in alerts:
                    print(f"  → {alert}")
            else:
                print("\n✅ 当前没有报警触发，一切正常。")
        full_report = "\n--------------------\n".join(push_content_list)
        if alerts:
            alert_text = "\n".join(alerts)
            full_report += "\n\n❗====触发报警====\n" + alert_text
        if PUSH_ENABLE and len(alerts) > 0:
            pushplus_send(PUSH_TOKEN, "📈股价监控快照", full_report)
    except Exception:
        pass
