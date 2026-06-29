import requests, time, gc, os, sys
# 屏蔽控制台输出，零闪存写入
sys.stdout = open(os.devnull, 'w')
sys.stderr = open(os.devnull, 'w')

# 网络全局参数 8秒超时 关闭长连接 0重试防卡死
requests.adapters.DEFAULT_RETRIES = 0
SESS = requests.Session()
SESS.keep_alive = False
GLOBAL_TIMEOUT = 8
HEADERS = {
    "User-Agent": "Mozilla/5.0 Linux Chrome/124.0 Safari/537.36",
    "Referer": "http://finance.sina.com.cn",
    "Connection": "close"
}

# ====================== 顶部配置区 所有标的增删位置 ======================
PUSH_TOKEN = "cdc7db6c36da46c1b877543016be3cba"
# 1.A股新增位置
STOCK_LIST = [
    "518880",
    # "600036",
    # "002594"
]
# 2.美股指数新增位置
US_INDEX_LIST = ["int_nasdaq", "int_sp500"]
# 3.虚拟币新增位置（BTC/ETH在这里加）
CRYPTO_LIST = ["bitcoin", "ethereum"]
# 黄金备用接口
API_LIST = [
    "https://api.freejk.com/shuju/jinjia/",
    "https://xaus.com/api/v1/spot",
    "https://freegoldapi.com/data/latest.json"
]
ETF_CODE, ETF_GRAM_PER_SHARE = "518880", 0.01
# =======================================================================

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

# A股完整保留，顶部STOCK_LIST增删，默认不输出
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

def get_us_index(rate, idx_list):
    buf = []
    url = f"http://hq.sinajs.cn/list={','.join(idx_list)}"
    try:
        resp = SESS.get(url, headers=HEADERS, timeout=GLOBAL_TIMEOUT)
        text_lines = resp.text.split(";")
        del resp
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
    except Exception:
        buf.append("美股指数接口请求失败")
    gc.collect()
    return "\n".join(buf)

def get_crypto_info(coin_list, usd_rate):
    buf = []
    coin_ids = ",".join(coin_list)
    domain_pool = ["https://api.coingecko.com/api/v3", "https://pro-api.coingecko.com/api/v3"]
    target_resp = None
    for domain in domain_pool:
        try:
            req_url = f"{domain}/coins/markets?vs_currency=usd&ids={coin_ids}&order=market_cap_desc&price_change_percentage=24h"
            target_resp = SESS.get(req_url, headers=HEADERS, timeout=GLOBAL_TIMEOUT)
            target_resp.raise_for_status()
            break
        except Exception:
            time.sleep(0.5)
    if not target_resp:
        buf.append("虚拟币全部接口访问失败")
        gc.collect()
        return "\n".join(buf)
    coin_data = target_resp.json()
    del target_resp
    for coin in coin_data:
        sym = coin["symbol"].upper()
        usd_now = round(coin["current_price"], 2)
        usd_yest = round(usd_now - coin["price_change_24h"], 2)
        usd_before_yest = round(usd_yest - (coin["price_change_24h"] / (1 + coin["price_change_percentage_24h"] / 100)), 2)
        cny_now, cny_yest = round(usd_now * usd_rate, 2), round(usd_yest * usd_rate, 2)
        chg_now_usd = round(coin["price_change_24h"], 2)
        chg_now_pct = round(coin["price_change_percentage_24h"], 2)
        chg_prev_usd = round(usd_yest - usd_before_yest, 2)
        chg_prev_pct = round((chg_prev_usd / usd_before_yest)*100, 2) if usd_before_yest != 0 else 0
        pct_24h = round(coin["price_change_percentage_24h"], 2)
        buf += [
            f"{sym}",
            f"现价：${usd_now} | 折合人民币¥{cny_now}",
            f"昨收：${usd_yest} 折合¥{cny_yest}",
            f"当日涨跌：${chg_now_usd}（{chg_now_pct}%）",
            f"昨日涨幅：${chg_prev_usd}（{chg_prev_pct}%）",
            f"24小时涨幅：{pct_24h}%",
            "----------------------------------------"
        ]
    del coin_data
    gc.collect()
    return "\n".join(buf)

# 移除kill_self强制杀进程函数，避免内存瞬间暴涨触发OOM
# 脚本执行完毕解释器自动正常退出，操作系统自动回收全部RAM

if __name__ == "__main__":
    try:
        # 分步获取+分步释放，降低内存峰值
        gold_info = get_gold_data()
        usd_ex = gold_info["usd_cny_rate"]
        gram_price = gold_info["cny_gram"]
        etf_price = round(gram_price * ETF_GRAM_PER_SHARE, 2)
        gold_block = [
            "===== 黄金行情 =====",
            f"数据源：{gold_info['source']}",
            f"伦敦金：{gold_info['usd_oz']} 美元/盎司",
            f"美元汇率：1USD = {usd_ex}",
            f"国内金价：{gram_price} 元/克",
            f"{ETF_CODE}理论净值：{etf_price} 元/份",
            "----------------------------------------"
        ]
        gold_text = "\n".join(gold_block)
        # 先推送黄金，立刻释放黄金内存
        push_wechat("黄金行情片段", gold_text)
        del gold_info, gold_block, gold_text
        gc.collect()

        # 获取美股，推送后释放
        us_text = "===== 美股宽基指数 =====\n" + get_us_index(usd_ex, US_INDEX_LIST)
        push_wechat("美股指数片段", us_text)
        del us_text
        gc.collect()

        # 获取虚拟币，推送后释放
        crypto_text = "===== 虚拟币行情 =====\n" + get_crypto_info(CRYPTO_LIST, usd_ex)
        push_wechat("虚拟币行情片段", crypto_text)
        del crypto_text
        gc.collect()

        # 如需合并一条推送（不拆分多条），注释上面分段推送，启用下面两行
        # full_msg = f"{gold_text}\n{us_text}\n{crypto_text}"
        # push_wechat("黄金+美股+BTC/ETH行情播报", full_msg)

    except Exception as err:
        push_wechat("行情脚本异常提醒", f"脚本全局异常：{str(err)}")
        gc.collect()
    # 无强制kill逻辑，代码执行完毕Python解释器自动正常退出，内存完全回收
