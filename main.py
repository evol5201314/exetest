import requests
import time

# ========== 配置区 ==========
PUSH_TOKEN = "cdc7db6c36da46c1b877543016be3cba"
TIMEOUT = 12
API_LIST = [
    "https://api.freejk.com/shuju/jinjia/",
    "https://xaus.com/api/v1/spot",
    "https://freegoldapi.com/data/latest.json"
]
ETF_CODE = "518880"
ETF_GRAM_PER_SHARE = 0.01
STOCK_CODES = "518880"
HEADERS = {
    "User-Agent": "Mozilla/5.0 Linux Chrome/124.0 Safari/537.36",
    "Referer": "http://finance.sina.com.cn"
}
# ===========================

def push_wechat(title, content):
    try:
        requests.post(
            "http://www.pushplus.plus/send",
            json={"token": PUSH_TOKEN, "title": title, "content": content},
            timeout=10
        )
    except Exception as e:
        print("推送失败:", e)

def get_gold_data():
    for api in API_LIST:
        try:
            r = requests.get(api, headers=HEADERS, timeout=TIMEOUT)
            r.raise_for_status()
            d = r.json()
            if "freejk" in api:
                oz = round(d["data"]["international_price"], 2)
                g = round(d["data"]["price"], 2)
                rate = round((g * 31.1035) / oz, 4)
                return {"usd_oz":oz, "cny_gram":g, "usd_cny_rate":rate, "source":"freejk国内行情"}
            elif "xaus" in api:
                oz = round(d["spot_usd_oz"], 2)
                rate = round(d["currency_rates"]["USD_CNY"], 4)
                g = round((oz * rate) / 31.1035, 2)
                return {"usd_oz":oz, "cny_gram":g, "usd_cny_rate":rate, "source":"xaus国际现货"}
            elif "freegoldapi" in api:
                last = d[-1]
                oz = round(last["price"], 2)
                rate = 7.22
                g = round((oz * rate) / 31.1035, 2)
                return {"usd_oz":oz, "cny_gram":g, "usd_cny_rate":rate, "source":"freegold兜底数据源"}
        except Exception as e:
            print(f"{api} 请求异常: {e}")
            time.sleep(1)
    raise Exception("所有金价接口全部失效")

def get_stock_info(code_str):
    param = ""
    for c in code_str.split():
        param += f"sh{c}," if c.startswith("6") else f"sz{c},"
    url = f"http://hq.sinajs.cn/list={param.rstrip(',')}"
    buf = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        for line in r.text.split(";"):
            if not line or '="' not in line:
                continue
            raw = line.split('"')[1].split(",")
            if len(raw) < 30:
                buf += ["行情字段缺失", "-"*30]
                continue
            name, now, close, yest = raw[0], float(raw[3]), float(raw[2]), float(raw[1])
            chg = round(now - close, 2)
            chg_pct = round((chg / close)*100, 2)
            day_chg = round(close - yest, 2)
            day_pct = round((day_chg / yest)*100, 2)
            code = line.split("=")[0].split("_")[-1]
            buf += [
                f"{code} {name}",
                f"现价{now} 昨收{close}",
                f"当日{chg}元({chg_pct}%)",
                f"前日{day_chg}元({day_pct}%)",
                "-"*30
            ]
    except Exception as e:
        buf.append(f"A股接口失败:{e}")
    return "\n".join(buf)

# 修复后美股指数函数
def get_us_index(rate):
    url = "http://hq.sinajs.cn/list=int_nasdaq,int_sp500"
    buf = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        content = r.text
        for line in content.split(";"):
            line = line.strip()
            if not line or '="' not in line:
                continue
            raw_str = line.split('"')[1]
            data = raw_str.split(",")
            if len(data) < 4:
                buf.extend([f"指数行数据残缺，跳过该行", "-"*30])
                continue
            try:
                idx_name = data[0]
                now = float(data[1])
                change = float(data[2])
                change_pct = float(data[3])
                yesterday_point = float(data[4]) if len(data)>=5 else now
            except ValueError:
                buf.extend([f"{data[0]} 数值转换失败", "-"*30])
                continue

            last_close = round(now - change, 2)
            last_day_change = round(last_close - yesterday_point, 2)
            last_day_pct = round((last_day_change / yesterday_point)*100, 2) if yesterday_point !=0 else 0
            rmb = round(now * rate, 2)

            buf += [
                idx_name,
                f"点位{now} 折合{rmb}元 昨收{last_close}",
                f"当日{change}点({change_pct}%)",
                f"前日{last_day_change}点({last_day_pct}%)",
                "-"*30
            ]
    except Exception as e:
        buf.append(f"美股接口整体请求失败:{e}")
    return "\n".join(buf)

if __name__ == "__main__":
    try:
        gd = get_gold_data()
        rt, gram = gd["usd_cny_rate"], gd["cny_gram"]
        etf_price = round(gram * ETF_GRAM_PER_SHARE, 2)
        msg_parts = [
            "【黄金行情】",
            f"数据源:{gd['source']}",
            f"伦敦金:{gd['usd_oz']}美元/盎司",
            f"汇率1USD={rt}",
            f"国内金价:{gram}元/克",
            f"{ETF_CODE}理论价:{etf_price}元/份",
            "-"*30,
            "\n【A股黄金ETF】",
            get_stock_info(STOCK_CODES),
            "\n【美股指数】",
            get_us_index(rt)
        ]
        full = "\n".join(msg_parts)
        push_wechat("黄金+A股+美股行情播报", full)
        print("执行完成\n", full)
    except Exception as err:
        err_txt = f"脚本全局异常：{err}"
        push_wechat("行情脚本异常提醒", err_txt)
        print(err_txt)
