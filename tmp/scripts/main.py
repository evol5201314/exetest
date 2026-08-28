#!/usr/bin/env python3
# -*- coding: utf-8 -*-
beizhu = "📈 监控股价"

# popup: stockConfigModal
# html: stock_config.html

import os, sys, json, argparse, requests

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

def load_config():
    try:
        if BASE_DIR not in sys.path:
            sys.path.insert(0, BASE_DIR)
        import stock_config
        return stock_config.PUSH_TOKEN, stock_config.STOCK_CONFIG, stock_config.US_CONFIG, stock_config.CRYPTO_CONFIG
    except:
        return ("cdc7db6c36da46c1b877543016be3cba", 
                [["518880",0,0],["",0,0],["",0,0],["",0,0],["",0,0],["",0,0],["",0,0],["",0,0],["",0,0],["",0,0]], 
                [["int_nasdaq",0,0],["int_sp500",0,0],["",0,0],["",0,0],["",0,0],["",0,0],["",0,0],["",0,0],["",0,0],["",0,0]], 
                [["BTC",0,0],["ETH",0,0],["",0,0],["",0,0],["",0,0],["",0,0],["",0,0],["",0,0],["",0,0],["",0,0]])

PUSH_TOKEN, STOCK_CONFIG, US_CONFIG, CRYPTO_CONFIG = load_config()

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
            if not token: token = "cdc7db6c36da46c1b877543016be3cba"
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
        SESS = requests.Session()
        SESS.keep_alive = False
        HEADERS = {"User-Agent": "Mozilla/5.0", "Connection": "close"}

        # ---------- 股票/黄金ETF查询 (主力腾讯接口，极其稳定) ----------
        for cfg in STOCK_CONFIG:
            code = cfg[0]
            if code:
                try:
                    if code == "GOLD":
                        r = SESS.get("https://api.freejk.com/shuju/jinjia/", headers=HEADERS, timeout=8)
                        d = r.json()
                        result["stocks"]["GOLD"] = str(round(d["data"]["price"], 2))
                        continue

                    prefix = "sh" if code.startswith("6") else "sz"
                    
                    # ★ 先直接查腾讯接口：v_sh518880="1~黄金ETF~518880~现价~昨收~..."
                    r = SESS.get(f"http://qt.gtimg.cn/q={prefix}{code}", headers=HEADERS, timeout=8)
                    r.encoding = 'gbk'
                    raw_text = r.text
                    
                    # 提取引号内的数据
                    if '="' in raw_text:
                        data_str = raw_text.split('="')[1].split('"')[0]
                        arr = data_str.split("~")
                        
                        # 腾讯接口数据：索引3是当前价，索引4是昨收
                        if len(arr) > 3 and arr[3]:
                            # 过滤掉非数字字符，确保纯粹是价格
                            try:
                                price = float(arr[3])
                                result["stocks"][code] = str(price)
                            except:
                                result["stocks"][code] = "无数据"
                        else:
                            result["stocks"][code] = "查无"
                    else:
                        result["stocks"][code] = "查无"
                        
                except Exception as e:
                    result["stocks"][code] = f"错误:{e}"

        # ---------- 美股查询 (新浪接口稳定) ----------
        sina_map = {"int_nasdaq": "gb_ixic", "int_sp500": "gb_inx"}
        for cfg in US_CONFIG:
            code = cfg[0]
            if code:
                try:
                    r = SESS.get(f"http://hq.sinajs.cn/list={sina_map.get(code, code)}", headers={**HEADERS, "Referer": "http://finance.sina.com.cn"}, timeout=8)
                    raw_text = r.content.decode('gbk', errors='ignore')
                    if '="' in raw_text:
                        data_str = raw_text.split('="')[1].split('"')[0]
                        arr = data_str.split(",")
                        if len(arr) > 1:
                            try:
                                price = float(arr[1])
                                result["us"][code] = str(price)
                            except:
                                result["us"][code] = "无数据"
                        else:
                            result["us"][code] = "查无"
                    else:
                        result["us"][code] = "查无"
                except Exception as e:
                    result["us"][code] = f"错误:{e}"

        # ---------- 虚拟币查询 (币安接口) ----------
        for cfg in CRYPTO_CONFIG:
            code = cfg[0]
            if code:
                try:
                    r = SESS.get(f"https://api.binance.com/api/v3/ticker/24hr?symbol={code}USDT", headers=HEADERS, timeout=8)
                    d = r.json()
                    if "lastPrice" in d:
                        result["crypto"][code] = d["lastPrice"]
                    else:
                        result["crypto"][code] = "查无"
                except Exception as e:
                    result["crypto"][code] = f"错误:{e}"

        print(json.dumps(result, ensure_ascii=False))
        sys.exit(0)

    # 主任务（推送屏蔽输出）
    sys.stdout = open(os.devnull, 'w')
    sys.stderr = open(os.devnull, 'w')