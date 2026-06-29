import requests
import time

# ====================== 【顶部统一配置区，所有标的在这里增删】 ======================
PUSH_TOKEN = "cdc7db6c36da46c1b877543016be3cba"
TIMEOUT = 12

# 美股指数列表
US_INDEX_LIST = [
    "int_nasdaq",    # 纳斯达克
    "int_sp500"      # 标普500
    # "int_dji"       # 道琼斯（取消注释启用）
]

# 虚拟币配置 coingecko标准id：bitcoin=BTC ethereum=ETH
CRYPTO_LIST = ["bitcoin", "ethereum"]

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

# 虚拟币函数：对齐美股格式，新增昨日价格、前日涨跌
def get_crypto_info(crypto_list, usd_rate):
    buf = []
    coin_ids = ",".join(crypto_list)
    domain_list = [
        "https://api.coingecko.com/api/v3",
        "https://pro-api.coingecko.com/api/v3"
    ]
    resp = None
    for domain in domain_list:
        try:
            url = f"{domain}/coins/markets?vs_currency=usd&ids={coin_ids}&order=market_cap_desc"
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            resp.raise_for_status()
            break
        except Exception as err:
            print(f"虚拟币域名 {domain} 访问失败：{err}")
            time.sleep(1)
    if resp is None:
        buf.append("全部虚拟币接口访问超时/被拦截，无法获取行情")
        return "\n".join(buf)
    coin_data = resp.json()
    for coin in coin_data:
        symbol = coin["symbol"].upper()
        usd_price = round(coin["current_price"], 2)
        cny_price = round(usd_price * usd_rate, 2)
        change_24h = round(coin["price_change_percentage_24h"], 2)
        change_usd = round(coin["price_change_24h"], 2)
        yesterday_usd = round(usd_price - change_usd, 2)
        yesterday_cny = round(yesterday_usd * usd_rate, 2)
        buf += [
            f"{symbol}",
            f"现价：${usd_price} | 折合人民币¥{cny_price}",
            f"昨收：${yesterday_usd} 折合¥{yesterday_cny}",
            f"24小时涨跌：${change_usd}（{change_24h}%）",
            "-"*30
        ]
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

        # 美股指数
        us_text = "===== 美股宽基指数 =====\n" + get_us_index(usd_rate, US_INDEX_LIST)
        # 虚拟币（对齐统一格式，新增昨日价格、前日涨跌）
        crypto_text = "===== 虚拟币行情 =====\n" + get_crypto_info(CRYPTO_LIST, usd_rate)

        # 合并推送内容（已删除股票板块）
        full_msg = f"{gold_text}\n{us_text}\n{crypto_text}"
        push_wechat("黄金+美股+BTC/ETH行情播报", full_msg)
        print("推送完成！\n", full_msg)

    except Exception as err:
        err_msg = f"脚本全局异常：{str(err)}"
        push_wechat("行情脚本异常提醒", err_msg)
        print(err_msg)
