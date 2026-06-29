import requests, time, gc, os, sys
from requests.adapters import HTTPAdapter, Retry

# 屏蔽全部控制台输出，输出丢黑洞，零闪存擦写
sys.stdout = open(os.devnull, 'w')
sys.stderr = open(os.devnull, 'w')

# 网络全局参数 8秒统一超时 关闭长连接 自动重试
GLOBAL_TIMEOUT = 8
SESS = requests.Session()
SESS.keep_alive = False
# 重试策略：仅重试超时/5xx，不重复请求403封禁页面
retry_opt = Retry(total=2, backoff_factor=0.4, status_forcelist=[429,500,502,503,504])
SESS.mount("https://", HTTPAdapter(max_retries=retry_opt))
SESS.mount("http://", HTTPAdapter(max_retries=retry_opt))

# 完整浏览器UA，解决新浪403拦截
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Connection": "close",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept": "text/plain,text/html,*/*;q=0.8"
}

# ====================== 顶部配置区 所有标的增删位置 ======================
PUSH_TOKEN = "cdc7db6c36da46c1b877543016be3cba"
# 1.A股/基金新增位置（保留，默认不推送）
STOCK_LIST = [
    "518880",
    # "600036",
    # "002594"
]
# 2.美股指数新浪代码 int_nasdaq=纳斯达克 int_sp500=标普500
US_INDEX_LIST = ["int_nasdaq", "int_sp500"]
# 3.虚拟币新增位置【这里添加币种大写标识，自动拼接BTC-USDT】
CRYPTO_LIST = ["BTC", "ETH"]
# 黄金备用行情接口
API_LIST = [
    "https://api.freejk.com/shuju/jinjia/",
    "https://xaus.com/api/v1/spot",
    "https://freegoldapi.com/data/latest.json"
]
ETF_CODE, ETF_GRAM_PER_SHARE = "518880", 0.01
# =======================================================================

# 微信推送函数
def push_wechat(title, content):
    try:
        SESS.post(
            "http://www.pushplus.plus/send",
            json={"token": PUSH_TOKEN, "title": title, "content": content},
            timeout=GLOBAL_TIMEOUT,
            headers=HEADERS
        )
    except Exception:
        pass
    gc.collect()

# 黄金+美元汇率获取逻辑不变
def get_gold_data():
    for api in API_LIST:
        try:
            resp = SESS.get(api, headers=HEADERS, timeout=GLOBAL_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            del resp
            if "freejk" in api:
                oz = round(data["data"]["international_price"], 2)
                gram = round(data["data"]["price"], 2)
                rate = round((gram * 31.1035) / oz, 4)
                res = {"usd_oz": oz, "cny_gram": gram, "usd_cny_rate": rate, "source": "freejk国内行情"}
            elif "xaus" in api:
                oz = round(data["spot_usd_oz"], 2)
                rate = round(data["currency_rates"]["USD_CNY"], 4)
                gram = round((oz * rate) / 31.1035, 2)
                res = {"usd_oz": oz, "cny_gram": gram, "usd_cny_rate": rate, "source": "xaus国际现货"}
            else:
                last_item = data[-1]
                oz = round(last_item["price"], 2)
                rate, gram = 7.22, round((oz * rate) / 31.1035, 2)
                res = {"usd_oz": oz, "cny_gram": gram, "usd_cny_rate": rate, "source": "freegold兜底数据源"}
            del data
            gc.collect()
            return res
        except Exception:
            time.sleep(0.5)
            gc.collect()
    raise Exception("全部金价接口请求超时/失败")

# A股解析函数完整保留，启用只需解开主程序两行注释
def get_stock_info(code_list):
    code_param = ""
    for code in code_list:
        code_param += f"sh{code}," if code.startswith("6") else f"sz{code},"
    code_param = code_param.rstrip(",")
    url = f"http://hq.sinajs.cn/list={code_param}"
    buf = []
    try:
        r = SESS.get(url, headers=HEADERS, timeout=GLOBAL_TIMEOUT)
        raw_text = r.text
        del r
        for line in raw_text.split(";"):
            line = line.strip()
            if not line or '="' not in line:
                continue
            left, data_str = line.split('"', 1)
            data_str = data_str.rstrip('"')
            arr = data_str.split(",")
            stock_code = left.split("_")[-1]
            name = "未知标的"
            now_price = 0.0
            last_close = 0.0
            change = 0.0
            change_pct = 0.0
            if len(arr) >= 1:
                name = arr[0]
            if len(arr) >= 3:
                try:
                    last_close = float(arr[2])
                except:
                    pass
            if len(arr) >= 4:
                try:
                    now_price = float(arr[3])
                except:
                    pass
            if last_close != 0:
                change = round(now_price - last_close, 2)
                change_pct = round((change / last_close) * 100, 2)
            buf.append(f"【{stock_code} {name}】")
            buf.append(f"现价：{now_price} 元")
            buf.append(f"昨收：{last_close} 元")
            buf.append(f"当日涨跌：{change} 元（{change_pct}%）")
            buf.append("----------------------------------------")
        del raw_text
    except Exception as e:
        buf.append(f"股票接口整体请求失败：{e}")
    gc.collect()
    return "\n".join(buf)

# 美股指数：优化新浪请求头，解决403拦截，兜底空白提示
def get_us_index(rate, idx_list):
    buf = []
    url = f"http://hq.sinajs.cn/list={','.join(idx_list)}"
    try:
        resp = SESS.get(url, headers=HEADERS, timeout=GLOBAL_TIMEOUT)
        text_lines = resp.text.split(";")
        del resp
        # 判断返回空内容
        if not text_lines or len("".join(text_lines).strip()) == 0:
            buf.append("新浪接口返回空白数据，IP被403拦截")
            buf.append("----------------------------------------")
            return "\n".join(buf)
        for line in text_lines:
            line = line.strip()
            if not line or '="' not in line:
                continue
            field_arr = line.split('"')[1].split(",")
            if len(field_arr) < 4:
                buf.extend(["指数数据残缺，跳过", "----------------------------------------"])
                continue
            try:
                idx_name, now, chg, chg_pct, yest_pt = field_arr[0], float(field_arr[1]), float(field_arr[2]), float(field_arr[3]), float(field_arr[4]) if len(field_arr)>=5 else float(field_arr[1])
            except Exception:
                buf.extend([f"{field_arr[0]}数值解析失败", "----------------------------------------"])
                continue
            last_close = round(now - chg, 2)
            day_chg = round(last_close - yest_pt, 2)
            day_pct = round((day_chg / yest_pt)*100, 2) if yest_pt != 0 else 0
            rmb_price = round(now * rate, 2)
            buf += [
                idx_name,
                f"点位：{now} | 折合人民币{rmb_price}",
                f"昨收：{last_close} 点",
                f"当日涨跌：{chg}点（{chg_pct}%）",
                f"前日涨跌：{day_chg}点（{day_pct}%）",
                "----------------------------------------"
            ]
        del text_lines
        # 无有效数据兜底
        if len(buf) == 0:
            buf.append("未读取到任何美股指数行情")
            buf.append("----------------------------------------")
    except Exception as err:
        buf.append(f"美股指数拉取失败（新浪IP拦截/超时）：{str(err)}")
        buf.append("----------------------------------------")
    gc.collect()
    return "\n".join(buf)

# 虚拟币：OKX欧易公开无密钥API，原生sodUtc8=早8点今日开盘，三个涨幅字段不变
def get_crypto_info(coin_list, usd_rate):
    buf = []
    base_url = "https://www.okx.com/api/v5/market/ticker"
    for coin in coin_list:
        inst_id = f"{coin}-USDT"
        try:
            resp = SESS.get(f"{base_url}?instId={inst_id}", headers=HEADERS, timeout=GLOBAL_TIMEOUT)
            resp.raise_for_status()
            json_data = resp.json()
            del resp
            data = json_data["data"][0]
            # 原生字段读取，无多余计算失真
            sym = coin
            usd_now = round(float(data["last"]), 2)               # 当前现价
            usd_today_open = round(float(data["sodUtc8"]), 
