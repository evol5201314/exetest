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
美股：第0位=雅虎代码，第1位=新浪备用代码，第2位=低于报警，第3位=高于报警
脚本运行后，会拉取当前价格、昨收价、前日收盘价，并计算“今日涨幅”和“昨日涨幅”。
脚本默认不推送消息（只打印在CMD中作为预览），但预留了推送接口，可以随时接入。
【运行模式】
1. `python monitor_stock.py`          —— 直接运行，执行监控、报警判断，并打印“推送预览”文本。
2. `python monitor_stock.py --get`    —— 读取当前配置（PUSH_TOKEN、STOCK_CONFIG、US_CONFIG、CRYPTO_CONFIG），以JSON格式输出。
3. `python monitor_stock.py --set '{"..."}'` —— 保存配置（JSON格式），写入 stock_config.py 文件。
4. `python monitor_stock.py --get-price` —— 只拉取当前价格，返回JSON，供面板的“当前价位”显示使用。
【配置格式变更说明】
US_CONFIG = [["雅虎代码", "新浪备用代码", 低于报警, 高于报警], ...]
面板前端：雅虎代码 | 国内备用(新浪) | 低于报警 | 高于报警 | 当前价位
================================================================
"""
import os, sys, json, argparse, requests, re
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except:
    pass
if os.name == 'nt':
    BASE_DIR = r"D:\tmp\scripts"
else:
    BASE_DIR = "/root/scripts"
CONFIG_FILE = os.path.join(BASE_DIR, "stock_config.py")
YAHOO_HEADERS = {
    "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
def load_config():
    try:
        if BASE_DIR not in sys.path:
            sys.path.insert(0, BASE_DIR)
        import stock_config
        return stock_config.PUSH_TOKEN, stock_config.STOCK_CONFIG, stock_config.US_CONFIG, stock_config.CRYPTO_CONFIG
    except:
        # ========== 修复兜底配置：【0雅虎代码，1新浪备用】 ==========
        return ("cdc7db6c36da46c1b877543016be3cba",
                [["518880", 0, 0], ["", 0, 0], ["", 0, 0], ["", 0, 0], ["", 0, 0], ["", 0, 0], ["", 0, 0], ["", 0, 0], ["", 0, 0], ["", 0, 0]],
                [["^IXIC", "int_nasdaq", 0, 0], ["^GSPC", "int_sp500", 0, 0], ["", "", 0, 0], ["", "", 0, 0], ["", "", 0, 0], ["", "", 0, 0], ["", "", 0, 0], ["", "", 0, 0], ["", "", 0, 0], ["", "", 0, 0]],
                [["BTC", 0, 0], ["ETH", 0, 0], ["", 0, 0], ["", 0, 0], ["", 0, 0], ["", 0, 0], ["", 0, 0], ["", 0, 0], ["", 0, 0], ["", 0, 0]])
PUSH_TOKEN, STOCK_CONFIG, US_CONFIG, CRYPTO_CONFIG = load_config()
# ★★★★★ A股获取前天收盘价（新浪优先，东财备用） ★★★★★
def get_a_stock_prev_close(code):
    if code.startswith(("6", "50", "51")):
        prefix = "sh"
        secid = "1." + code
    else:
        prefix = "sz"
        secid = "0." + code
    # 源1：新浪K线
    try:
        url = f"https://quotes.sina.cn/cn/api/json_v2.php/CN_MarketDataService.getKLineData?symbol={prefix}{code}&scale=240&ma=no&datalen=5"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
        data = r.json()
        if data and len(data) >= 3:
            return float(data[-3]["close"])
    except Exception:
        pass
    # 源2：东方财富备用
    try:
        url = f"https://push2.eastmoney.com/api/qt/stock/kline/get?secid={secid}&fields1=f1&fields2=f51&klt=101&fqt=0&end=20990101&lmt=5"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
        j = r.json()
        klines = j.get("data", {}).get("klines", [])
        if len(klines) >= 3:
            third_last = klines[-3].split(",")
            return float(third_last[2])
    except Exception:
        pass
    return 0.0
# ★★★★★ A股抓取逻辑 ★★★★★
def fetch_a_stock_price(code):
    if code.startswith(("6", "50", "51")):
        prefix = "sh"
    else:
        prefix = "sz"
    try:
        r = requests.get(f"http://hq.sinajs.cn/list={prefix}{code}", headers={"User-Agent": "Mozilla/5.0", "Referer": "http://finance.sina.com.cn"}, timeout=8)
        r.encoding = 'gbk'
        text = r.text.replace('\u0000', '').strip()
        if '="' in text:
            arr = text.split('="')[1].split('"')[0].split(",")
            if len(arr) > 3 and arr[3] and arr[3] != "0.00":
                return str(float(arr[3]))
            elif len(arr) > 2 and arr[2] and arr[2] != "0.00":
                return str(float(arr[2]))
    except Exception:
        pass
    return "查无"
def get_a_stock_detail(code):
    if code.startswith(("6", "50", "51")):
        prefix = "sh"
    else:
        prefix = "sz"
    name = code
    current = 0.0
    yesterday = 0.0
    try:
        r = requests.get(f"http://hq.sinajs.cn/list={prefix}{code}", headers={"User-Agent": "Mozilla/5.0", "Referer": "http://finance.sina.com.cn"}, timeout=8)
        r.encoding = 'gbk'
        text = r.text.replace('\u0000', '').strip()
        if '="' in text:
            arr = text.split('="')[1].split('"')[0].split(",")
            name = arr[0]
            current = float(arr[3]) if arr[3] else 0.0
            yesterday = float(arr[2]) if arr[2] else 0.0
    except Exception:
        pass
    prev_close = get_a_stock_prev_close(code)
    today_pct = ((current - yesterday) / yesterday * 100) if yesterday else 0.0
    if prev_close > 1e-6:
        yesterday_pct = ((yesterday - prev_close) / prev_close * 100)
    else:
        yesterday_pct = None
    return {
        "code": code,
        "name": name,
        "current": current,
        "yesterday": yesterday,
        "prev_close": prev_close,
        "today_pct": today_pct,
        "yesterday_pct": yesterday_pct
    }
# ====================== 美股：优先雅虎v8，失败才使用新浪备用（仅现价） ======================
def fetch_us_price(yahoo_code, sina_backup_code):
    """给--get-price调用，拿现价"""
    # 优先雅虎
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
    # 雅虎失败，降级新浪备用
    if not sina_backup_code:
        return "查无"
    try:
        r = requests.get(f"http://hq.sinajs.cn/list={sina_backup_code}", headers={"Referer":"https://finance.sina.com.cn"}, timeout=6)
        r.encoding = "gbk"
        text = r.text.replace("\x00","").strip()
        if '="' in text:
            arr = text.split('="')[1].split(',')
            if len(arr)>1 and arr[1]:
                return str(float(arr[1]))
    except Exception:
        pass
    return "查无"

def get_us_stock_detail(yahoo_code, sina_backup_code):
    """优先雅虎拿完整日线；雅虎失败，新浪备用只填充current，yesterday/prev_close置0
    名称策略：优先新浪备用代码的中文名称，获取失败则使用雅虎英文名称
    """
    name = yahoo_code
    sina_cn_name = ""
    current = 0.0
    yesterday = 0.0
    prev_close = 0.0
    today_pct = 0.0
    yesterday_pct = None

    # 尝试从新浪备用接口提取中文名称
    if sina_backup_code:
        try:
            r = requests.get(f"http://hq.sinajs.cn/list={sina_backup_code}", headers={"Referer":"https://finance.sina.com.cn"}, timeout=4)
            r.encoding = "gbk"
            text = r.text.replace("\x00","").strip()
            if '="' in text:
                arr = text.split('="')[1].split(',')
                if len(arr)>=1 and arr[0].strip():
                    sina_cn_name = arr[0].strip()
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
        # 名称优先级：新浪中文 > 雅虎英文
        name = sina_cn_name if sina_cn_name else yahoo_name
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
        # 雅虎全部失败，尝试新浪备用，只拿current
        if sina_backup_code:
            try:
                r = requests.get(f"http://hq.sinajs.cn/list={sina_backup_code}", headers={"Referer":"https://finance.sina.com.cn"}, timeout=6)
                r.encoding = "gbk"
                text = r.text.replace("\x00","").strip()
                if '="' in text:
                    arr = text.split('="')[1].split(',')
                    if sina_cn_name:
                        name = sina_cn_name
                    else:
                        name = arr[0] if len(arr)>0 else yahoo_code
                    if len(arr)>1 and arr[1]:
                        current = float(arr[1])
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

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--get', action='store_true')
    parser.add_argument('--set', type=str, default='')
    parser.add_argument('--get-price', action='store_true')
    args = parser.parse_args()
    if args.get:
        print(json.dumps({"PUSH_TOKEN": PUSH_TOKEN, "STOCK_CONFIG": STOCK_CONFIG, "US_CONFIG": US_CONFIG, "CRYPTO_CONFIG": CRYPTO_CONFIG}, ensure_ascii=False))
        sys.exit(0)
    if args.set:
        try:
            new_config = json.loads(args.set)
            token = new_config.get("PUSH_TOKEN", "").strip()
            if not token:
                token = "cdc7db6c36da46c1b877543016be3cba"
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                f.write(f'PUSH_TOKEN = "{token}"\n')
                f.write(f'STOCK_CONFIG = {json.dumps(new_config.get("STOCK_CONFIG", []), ensure_ascii=False)}\n')
                f.write(f'US_CONFIG = {json.dumps(new_config.get("US_CONFIG", []), ensure_ascii=False)}\n')
                f.write(f'CRYPTO_CONFIG = {json.dumps(new_config.get("CRYPTO_CONFIG", []), ensure_ascii=False)}\n')
            print("✅ 配置已保存")
        except Exception as e:
            print(f"❌ 保存失败: {e}")
        sys.exit(0)
    if args.get_price:
        result = {"stocks": {}, "us": {}, "crypto": {}}
        for cfg in STOCK_CONFIG:
            code = cfg[0]
            if code:
                result["stocks"][code] = fetch_a_stock_price(code)
        
        for cfg in US_CONFIG:
            y_code = cfg[0]
            sina_bk = cfg[1] if len(cfg)>1 else ""
            if y_code:
                result["us"][y_code] = fetch_us_price(y_code, sina_bk)
        
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
                except Exception as e:
                    result["crypto"][code] = f"错误:{e}"
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(0)
    # ========== 监控报警 + 预览推送内容（不发送） ==========
    try:
        print("=" * 50)
        print("开始进行价格监控检查...")
        print("=" * 50)
        alerts = []
        push_content_list = []
        # 1. A股
        for index, cfg in enumerate(STOCK_CONFIG):
            code, low, high = cfg[0], cfg[1], cfg[2]
            if code:
                detail = get_a_stock_detail(code)
                if not detail:
                    print(f"❌ 第{index+1}行 - 股票 {code} 获取失败")
                    continue
                name = detail["name"]
                current = detail["current"]
                yesterday = detail["yesterday"]
                prev_close_val = detail["prev_close"]
                today_pct = detail["today_pct"]
                yesterday_pct = detail["yesterday_pct"]
                print(f"--- 股票 {index+1}行 {code} ---")
                print(f"名称: {name}")
                print(f"当前价格: {current}")
                print(f"昨日价格: {yesterday}")
                if prev_close_val > 1e-6:
                    print(f"前日价格: {prev_close_val}")
                    pc_text = f"{prev_close_val}"
                else:
                    print(f"前日价格: N/A")
                    pc_text = "N/A"
                print(f"当前涨幅: {today_pct:.2f}%")
                if yesterday_pct is not None:
                    print(f"昨日涨幅: {yesterday_pct:.2f}%")
                    yp_text = f"{yesterday_pct:.2f}%"
                else:
                    print(f"昨日涨幅: N/A(接口未获取前日收盘价)")
                    yp_text = "N/A"
                push_content_list.append(
                    f"【A/港国内股】\n行号: {index+1}\n号码: {code}\n名称: {name}\n"
                    f"当前价格: {current}\n昨日价格: {yesterday}\n前日价格: {pc_text}\n"
                    f"当前涨幅: {today_pct:.2f}%\n昨日涨幅: {yp_text}"
                )
                if low and current <= float(low):
                    alerts.append(f"【股票】第{index+1}行 {code} {name} 现价 {current} 跌破报警线 {low}！")
                if high and current >= float(high):
                    alerts.append(f"【股票】第{index+1}行 {code} {name} 现价 {current} 突破报警线 {high}！")
        # 2. 美股
        for index, cfg in enumerate(US_CONFIG):
            y_code = cfg[0]
            sina_bk = cfg[1] if len(cfg) > 1 else ""
            low = cfg[2] if len(cfg) > 2 else 0
            high = cfg[3] if len(cfg) > 3 else 0
            if y_code:
                detail = get_us_stock_detail(y_code, sina_bk)
                name = detail["name"]
                current = detail["current"]
                yesterday = detail["yesterday"]
                prev_close_val = detail["prev_close"]
                today_pct = detail["today_pct"]
                yesterday_pct = detail["yesterday_pct"]
                print(f"--- 美股 {index+1}行 {y_code} ---")
                print(f"名称: {name}")
                print(f"当前价格: {current}")
                print(f"昨日价格: {yesterday}")
                if prev_close_val > 1e-6:
                    print(f"前日价格: {prev_close_val}")
                    pc_text = f"{prev_close_val}"
                else:
                    print(f"前日价格: N/A")
                    pc_text = "N/A"
                print(f"当前涨幅: {today_pct:.2f}%")
                if yesterday_pct is not None:
                    print(f"昨日涨幅: {yesterday_pct:.2f}%")
                    yp_text = f"{yesterday_pct:.2f}%"
                else:
                    print(f"昨日涨幅: N/A(雅虎失败降级新浪仅现价)")
                    yp_text = "N/A"
                push_content_list.append(
                    f"【美股指数】\n行号: {index+1}\n号码: {y_code}\n名称: {name}\n"
                    f"当前价格: {current}\n昨日价格: {yesterday}\n前日价格: {pc_text}\n"
                    f"当前涨幅: {today_pct:.2f}%\n昨日涨幅: {yp_text}"
                )
                if low and current <= float(low):
                    alerts.append(f"【美股】第{index+1}行 {y_code} {name} 现价 {current} 跌破报警线 {low}！")
                if high and current >= float(high):
                    alerts.append(f"【美股】第{index+1}行 {y_code} {name} 现价 {current} 突破报警线 {high}！")
        # 3. 虚拟币
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
                        print(f"--- 虚拟币 {index+1}行 {code} ---")
                        print(f"当前价格: {current}")
                        print(f"昨日价格: {open_24h}")
                        print(f"当前涨幅: {today_pct:.2f}%")
                        print(f"昨日涨幅: {yesterday_pct:.2f}%")
                        print(f"24小时涨幅: {pct_24h:.2f}%")
                        push_content_list.append(
                            f"【虚拟币】\n行号: {index+1}\n号码: {code}\n当前价格: {current}\n昨日价格: {open_24h}\n"
                            f"当前涨幅: {today_pct:.2f}%\n昨日涨幅: {yesterday_pct:.2f}%\n24小时涨幅: {pct_24h:.2f}%"
                        )
                        if low and current <= float(low):
                            alerts.append(f"【虚拟币】第{index+1}行 {code} 现价 {current} 跌破报警线 {low}！")
                        if high and current >= float(high):
                            alerts.append(f"【虚拟币】第{index+1}行 {code} 现价 {current} 突破报警线 {high}！")
                    else:
                        print(f"虚拟币 {code}: 价格获取失败")
                except Exception as e:
                    print(f"虚拟币 {code}: 价格获取失败 ({e})")
        print("\n" + "=" * 50)
        print("【推送预览】（未实际发送）")
        print("=" * 50)
        for content in push_content_list:
            print(content)
            print("-" * 30)
        print("\n" + "=" * 50)
        if alerts:
            print("❗ 报警触发情况：")
            for alert in alerts:
                print(f"  → {alert}")
        else:
            print("✅ 当前没有报警触发，一切正常。")
        print("=" * 50)
    except Exception as e:
        print(f"❌ 监控检查出错: {e}")
