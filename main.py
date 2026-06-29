import requests
import time

# ====================== 【顶部统一配置区，所有标的在这里增删】 ======================
PUSH_TOKEN = "cdc7db6c36da46c1b877543016be3cba"
TIMEOUT = 12

# 1. A股/场内基金列表，自动区分沪sh/深sz
STOCK_LIST = [
    "518880",
    # "600036",
    # "000001",
    # "300750"
]

# 2. 美股指数列表
US_INDEX_LIST = [
    "int_nasdaq",    # 纳斯达克
    "int_sp500"      # 标普500
    # "int_dji"       # 道琼斯（取消注释启用）
]

# 3. 虚拟币配置：btc eth，可自行添加
CRYPTO_LIST = ["btc", "eth"]

# 黄金行情数据源
API_LIST = [
    "https://api.freejk.com/shuju/jinjia/",
    "https://xaus.com/api/v1/spot",
    "https://freegoldapi.com/data/latest.json"
]
ETF_CODE = "518880"
ETF_GRAM_PER_SHARE = 0.01

# 全局请求头
HEADERS = {
    "User-Agent": "Mozilla/5.0 Linux Chrome/124.0 Safari/537.36",
    "Referer": "http://finance.sina.com.cn"
}
# ==============================================================================

# 微信推送函数
def push_wechat(title, content):
    try:
        requests.post(
            "http://www.pushplus.plus/send",
            json={"token": PUSH_TOKEN, "title": title, "content": content},
            timeout=10
        )
    except Exception as e:
        print("推送失败:", e)

# 获取金价、美元兑人民币汇率
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

# A股批量行情
def get_stock_info(code_list):
    code_param = ""
    for code in code_list:
        code_param += f"sh{code}," if code.startswith("6") else f"sz{code},"
    code_param = code_param.rstrip(",")
    url = f"http://hq.sinajs.cn/list={code_param}"
    buf = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        for line in r.text.split(";"):
            line = line.strip()
            if not line or '="' not in line:
                continue
            arr = line.split('"')[1].split(",")
            if len(arr) < 30:
                buf.append("个股数据残缺，读取失败")
                buf.append("-" * 30)
                continue
            stock_code = line.split("=")[0].split("_")[-1]
            name = arr[0]
            now_price = float(arr[3])
            last_close = float(arr[2])
            change = round(now_price - last_close, 2)
            change_pct = round((change / last_close) * 100, 2)

            buf.append(f"【{stock_code} {name}】")
            buf.append(f"现价：{now_price} 元")
            buf.append(f"昨收：{last_close} 元")
            buf.append(f"今日涨跌：{change} 元（{change_pct}%）")
            buf.append("-" * 30)
    except Exception as e:
        buf.append(f"股票接口请求失败：{e}")
    return "\n".join(buf)

# 美股指数批量行情
def get_us_index(rate, index_list):
    code_str = ",".join(index_list)
    url = f"http://hq.sinajs.cn/list={code_str}"
    buf = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        for line in r.text.split(";"):
            line = line.strip()
            if not line or '="' not in line:
                continue
            data = line.split('"')[1].split(",")
            if len(data) < 4:
                buf.extend(["指数数据残缺，跳过", "-"*30])
                continue
            try:
                idx_name = data[0]
                now = float(data[1])
                change = float(data[2])
                change_pct = float(data[3])
                yesterday_point = float(data[4]) if len(data)>=5 else now
            except ValueError:
                buf.extend([f"{data[0]} 数值解析失败", "-"*30])
                continue
            last_close = round(now - change, 2)
            day_chg = round(last_close - yesterday_point, 2)
            day_pct = round((day_chg / yesterday_point)*100, 2) if yesterday_point !=0 else 0
            rmb_price = round(now * rate, 2)
            buf += [
                idx_name,
                f"点位：{now} | 折合人民币{rmb_price}",
                f"昨收：{last_close} 点",
                f"当日涨跌：{change}点（{change_pct}%）",
                f"前日涨跌：{day_chg}点（{day_pct}%）",
                "-"*30
            ]
    except Exception as e:
        buf.append(f"美股指数接口失败：{e}")
    return "\n".join(buf)

# 新增：虚拟币 BTC/ETH 行情
def get_crypto_info(crypto_list, usd_rate):
    buf = []
    try:
        ids = ",".join(crypto_list)
        url = f"https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids={ids}&order=market_cap_desc"
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        coin_data = resp.json()
        for coin in coin_data:
            symbol = coin["symbol"].upper()
            usd_price = round(coin["current_price"], 2)
            cny_price = round(usd_price * usd_rate, 2)
            change_24h = round(coin["price_change_percentage_24h"], 2)
            buf.append(f"【{symbol}】")
            buf.append(f"美元价：${usd_price}")
            buf.append(f"人民币：¥{cny_price}")
            buf.append(f"24小时涨跌幅：{change_24h}%")
            buf.append("-" * 30)
    except Exception as e:
        buf.append(f"虚拟币接口获取失败：{str(e)}")
    return "\n".join(buf)

if __name__ == "__main__":
    try:
        # 获取黄金与汇率
        gold_data = get_gold_data()
        usd_rate = gold_data["usd_cny_rate"]
        gram_price = gold_data["cny_gram"]
        etf_theory = round(gram_price * ETF_GRAM_PER_SHARE, 2)

        # 黄金板块
        gold_text = "\n".join([
            "===== 黄金行情 =====",
            f"数据源：{gold_data['source']}",
            f"伦敦金：{gold_data['usd_oz']} 美元/盎司",
            f"美元汇率：1USD = {usd_rate}",
            f"国内金价：{gram_price} 元/克",
            f"{ETF_CODE}理论净值：{etf_theory} 元/份",
            "-" * 40
        ])

        # A股
        stock_text = "===== 持仓股票行情 =====\n" + get_stock_info(STOCK_LIST)
        # 美股指数
        us_text = "===== 美股宽基指数 =====\n" + get_us_index(usd_rate, US_INDEX_LIST)
        # 虚拟币
        crypto_text = "===== 虚拟币行情 =====\n" + get_crypto_info(CRYPTO_LIST, usd_rate)

        # 合并推送内容
        full_msg = f"{gold_text}\n{stock_text}\n{us_text}\n{crypto_text}"
        push_wechat("黄金+股票+美股+BTC/ETH行情播报", full_msg)
        print("推送完成！\n", full_msg)

    except Exception as err:
        err_msg = f"脚本全局异常：{str(err)}"
        push_wechat("行情脚本异常提醒", err_msg)
        print(err_msg)
