import requests
import time

# ========== 【自定义配置区，在这里修改所有参数】 ==========
PUSH_TOKEN = "cdc7db6c36da46c1b877543016be3cba"
TIMEOUT = 12
# 黄金行情多备用接口
API_LIST = [
    "https://api.freejk.com/shuju/jinjia/",
    "https://xaus.com/api/v1/spot",
    "https://freegoldapi.com/data/latest.json"
]
ETF_CODE = "518880"
ETF_GRAM_PER_SHARE = 0.01
# A股/场内基金代码，空格分隔自行增删
STOCK_CODES = "518880 002594 600036"
# ==========================================================

def push_wechat(title, content):
    """PushPlus微信统一推送"""
    url = "http://www.pushplus.plus/send"
    payload = {
        "token": PUSH_TOKEN,
        "title": title,
        "content": content
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print("推送失败：", str(e))

def get_gold_data():
    """获取国际/国内金价，计算518880理论价"""
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"
    }
    for api in API_LIST:
        try:
            resp = requests.get(api, headers=headers, timeout=TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            if "freejk" in api:
                usd_oz = round(data["data"]["international_price"], 2)
                cny_gram = round(data["data"]["price"], 2)
                rate = round((data["data"]["price"] * 31.1035) / data["data"]["international_price"], 4)
                return {
                    "usd_oz": usd_oz,
                    "cny_gram": cny_gram,
                    "usd_cny_rate": rate,
                    "source": "freejk国内行情"
                }
            elif "xaus" in api:
                usd_oz = round(data["spot_usd_oz"], 2)
                usd_cny = round(data["currency_rates"]["USD_CNY"], 4)
                cny_oz = round(usd_oz * usd_cny, 2)
                cny_gram = round(cny_oz / 31.1035, 2)
                return {
                    "usd_oz": usd_oz,
                    "cny_gram": cny_gram,
                    "usd_cny_rate": usd_cny,
                    "source": "xaus国际现货"
                }
            elif "freegoldapi" in api:
                last_item = data[-1]
                usd_oz = round(last_item["price"], 2)
                usd_cny = 7.22
                cny_oz = round(usd_oz * usd_cny, 2)
                cny_gram = round(cny_oz / 31.1035, 2)
                return {
                    "usd_oz": usd_oz,
                    "cny_gram": cny_gram,
                    "usd_cny_rate": usd_cny,
                    "source": "freegold兜底数据源"
                }
        except Exception as e:
            print(f"接口 {api} 请求失败，切换下一个，错误：{str(e)}")
            time.sleep(1)
    raise Exception("所有金价接口均访问失败，请检查容器网络")

def get_stock_info(code_str):
    """批量获取A股/场内基金实时行情"""
    code_list = code_str.split()
    stock_msg = ""
    code_param = ""
    for code in code_list:
        if code.startswith("6"):
            code_param += f"sh{code},"
        else:
            code_param += f"sz{code},"
    code_param = code_param.rstrip(",")
    url = f"http://hq.sinajs.cn/list={code_param}"
    headers = {"User-Agent": "Mozilla/5.0 Python Script", "Referer": "http://finance.sina.com.cn"}
    try:
        res = requests.get(url, headers=headers, timeout=TIMEOUT)
        raw_text = res.text
        lines = raw_text.strip().split(";")
        for line in lines:
            if not line:
                continue
            data_part = line.split('"')[1]
            arr = data_part.split(",")
            if len(arr) < 30:
                continue
            name = arr[0]
            now_price = float(arr[3])
            yesterday = float(arr[2])
            diff = round(now_price - yesterday, 2)
            diff_rate = round((diff / yesterday) * 100, 2)
            stock_code = line.split("=")[0].split("_")[-1]
            stock_msg += f"{stock_code} {name} | 当前价:{now_price} | 涨跌:{diff}({diff_rate}%)\n"
    except Exception as e:
        stock_msg = f"股票行情查询失败：{str(e)}"
    return stock_msg

def get_us_index():
    """获取纳斯达克综合、标普500指数"""
    index_codes = ["int_nasdaq", "int_sp500"]
    url = f"http://hq.sinajs.cn/list={','.join(index_codes)}"
    headers = {"User-Agent": "Mozilla/5.0 Python Script", "Referer": "http://finance.sina.com.cn"}
    index_text = ""
    try:
        res = requests.get(url, headers=headers, timeout=TIMEOUT)
        raw = res.text.strip().split(";")
        for line in raw:
            if not line:
                continue
            data = line.split('"')[1].split(",")
            idx_name = data[0]
            idx_price = float(data[1])
            idx_change = float(data[2])
            idx_pct = float(data[3])
            index_text += f"{idx_name} | 当前点位:{idx_price} | 涨跌:{idx_change}({idx_pct}%)\n"
    except Exception as e:
        index_text = f"美股指数获取失败：{str(e)}"
    return index_text

if __name__ == "__main__":
    stock_codes = STOCK_CODES.split()

    try:
        # 黄金数据
        gold_res = get_gold_data()
        etf_theo_price = round(gold_res["cny_gram"] * ETF_GRAM_PER_SHARE, 2)
        gold_text = f"""
【黄金实时行情】
数据来源：{gold_res['source']}
场内黄金ETF：{ETF_CODE}（华安黄金ETF）
ETF理论参考价：{etf_theo_price} 元/份
伦敦金 XAUUSD：{gold_res['usd_oz']} 美元/盎司
美元兑人民币：1USD = {gold_res['usd_cny_rate']} CNY
国内现货金价：{gold_res['cny_gram']} 元/克
换算标准：1盎司=31.1035克，1份ETF=0.01克黄金
        """.strip()

        # A股持仓
        stock_text = f"\n【持仓A股/基金实时价格】\n{get_stock_info(STOCK_CODES)}".strip()

        # 美股指数
        us_index_text = f"\n【美股宽基指数】\n{get_us_index()}".strip()

        # 合并全部内容推送
        full_msg = gold_text + "\n\n" + stock_text + "\n\n" + us_index_text
        push_wechat("黄金+A股+纳指标普500实时报价", full_msg)
        print("查询完成，微信推送已发送！")
        print("="*50)
        print(full_msg)

    except Exception as err:
        err_text = f"行情查询异常：{str(err)}"
        push_wechat("行情脚本异常提醒", err_text)
        print(err_text)
