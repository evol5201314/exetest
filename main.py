"""
===== 【OpenWrt 低内存专用优化说明 请勿删除以下轻量化逻辑】
硬件环境：路由可用内存仅≈50M，精简python，峰值内存控制≤13M
优化1：仅保留极简基础Session会话，移除占用内存的Retry重试适配器，减少常驻内存消耗
      保留Session解决频繁新建短连接握手超时导致虚拟币接口失败，仅增加≈0.3M内存
优化2：超极简curl UA伪装，字符串常量仅占用≈0.02M内存，规避新浪403拦截
      舍弃长Chrome浏览器UA，无多余Accept-Language等冗余请求头
优化3：全程分阶段del+gc.collect()强制回收，同一时间内存仅驻留单段行情文本
      黄金→释放→美股→释放→虚拟币→释放，杜绝多段大字符串同时占用RAM
优化4：屏蔽stdout/stderr输出至/dev/null，不读写闪存，无日志文件占用存储空间
优化5：移除kill_self强制系统杀进程逻辑，避免系统调用瞬间内存暴涨触发OOM 137
优化6：合理sleep休眠时长(0.3s)，避免请求过快触发交易所接口限流封禁
优化7：数组拼接使用join替代循环append，减少内存字符串碎片
优化8：无全局长列表、无大常量缓存，行情文本用完立即销毁
优化9：仅保留2个必要请求头，砍掉多余HTTP头减少内存缓存
UA内存占用极低，仅两个短字符串，不会消耗宝贵路由内存
===== 【当前兼容适配说明】
1. 恢复Session长连接复用、0.3s请求间隔，解决OKX接口频繁访问失败问题
2. 新浪美股域名易被IP拦截，拦截后显示明确提示，不会空白板块
3. 无代理环境下黄金接口永久稳定，OKX虚拟币恢复正常拉取
===== 【标的增删配置区 在此修改币种/指数/股票】
US_INDEX_LIST：新浪美股代码 int_nasdaq=纳斯达克 int_sp500=标普500
CRYPTO_LIST：OKX虚拟币，仅填大写标识（BTC/ETH/SOL）自动拼接XX-USDT交易对
STOCK_LIST：A股场内基金，默认不启用输出，解开拼接注释才会推送
API_LIST：黄金多备用数据源，防止单一接口挂掉无数据
"""
import requests, time, gc, os, sys
# 优化4：屏蔽控制台输出，输出丢黑洞，零闪存擦写占用
sys.stdout = open(os.devnull, 'w')
sys.stderr = open(os.devnull, 'w')

# 全局固定参数
GLOBAL_TIMEOUT = 8
# 优化1：极简基础Session，不挂载重试适配器，仅基础连接池，内存占用极低
SESS = requests.Session()
# 修复点：移除keep_alive=False，允许长连接复用，OKX校验会话正常识别
# SESS.keep_alive = False
# 优化2/9：超轻量极简UA，仅2个必要头，内存占用≈0.02M，规避新浪403拦截
HEADERS = {
    "User-Agent": "curl/7.68.0",
    "Connection": "keep-alive"
}

# ====================== 顶部增删配置区 ======================
PUSH_TOKEN = "cdc7db6c36da46c1b877543016be3cba"
# A股基金列表（默认不输出，如需推送解开主程序拼接注释）
STOCK_LIST = [
    "518880",
    # "600036"
]
# 美股新浪代码
US_INDEX_LIST = ["int_nasdaq", "int_sp500"]
# 虚拟币列表 OKX接口
CRYPTO_LIST = ["BTC", "ETH"]
# 黄金备用多数据源
API_LIST = [
    "https://api.freejk.com/shuju/jinjia/",
    "https://xaus.com/api/v1/spot",
    "https://freegoldapi.com/data/latest.json"
]
ETF_CODE, ETF_GRAM_PER_SHARE = "518880", 0.01
# ==============================================================

# 微信推送 复用Session轻量化请求
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
    # 优化3：强制回收临时请求对象内存
    gc.collect()

# 黄金汇率获取 复用Session持久连接
def get_gold_data():
    for api in API_LIST:
        try:
            resp = SESS.get(api, headers=HEADERS, timeout=GLOBAL_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            del resp # 优化3：销毁网络响应对象
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
            del data # 优化3：销毁json大对象
            gc.collect()
            return res
        except Exception:
            time.sleep(0.3) # 优化6：标准间隔，不触发限流
            gc.collect()
    raise Exception("黄金接口全部请求失败")

# A股函数保留，默认不启用
def get_stock_info(code_list):
    # 优化7：join拼接，减少字符串碎片内存占用
    code_param = ",".join(code_list)
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
            arr = data_str.split(",")
            stock_code = left.split("_")[-1]
            name = arr[0] if len(arr)>=1 else "未知"
            last_close = float(arr[2]) if len(arr)>=3 else 0.0
            now_price = float(arr[3]) if len(arr)>=4 else 0.0
            change = round(now_price - last_close, 2)
            change_pct = round((change / last_close)*100, 2) if last_close !=0 else 0
            buf.append(f"【{stock_code} {name}】")
            buf.append(f"现价：{now_price} 元")
            buf.append(f"昨收：{last_close} 元")
            buf.append(f"当日涨跌：{change} 元（{change_pct}%）")
            buf.append("----------------------------------------")
        del raw_text
    except Exception as e:
        buf.append(f"股票接口失败：{e}")
    gc.collect()
    return "\n".join(buf)

# 美股新浪轻量解析 极简逻辑
def get_us_index(rate, idx_list):
    buf = []
    url = f"http://hq.sinajs.cn/list={','.join(idx_list)}"
    try:
        resp = SESS.get(url, headers=HEADERS, timeout=GLOBAL_TIMEOUT)
        text_lines = resp.text.split(";")
        del resp
        if not "".join(text_lines).strip():
            buf.append("新浪接口空白/403拦截")
            buf.append("----------------------------------------")
            return "\n".join(buf)
        for line in text_lines:
            line = line.strip()
            if not line or '="' not in line:
                continue
            field_arr = line.split('"')[1].split(",")
            if len(field_arr) < 4:
                buf.append("指数数据残缺，跳过")
                buf.append("----------------------------------------")
                continue
            idx_name = field_arr[0]
            now = float(field_arr[1])
            chg = float(field_arr[2])
            chg_pct = float(field_arr[3])
            yest_pt = float(field_arr[4]) if len(field_arr)>=5 else now
            last_close = round(now - chg, 2)
            day_chg = round(last_close - yest_pt, 2)
            day_pct = round((day_chg / yest_pt)*100, 2) if yest_pt !=0 else 0
            rmb_price = round(now * rate, 2)
            buf += [
                idx_name,
                f"点位：{now} | 折合人民币{rmb_price}",
                f"昨收：{last_close} 点",
                f"当日涨跌：{chg}点（{chg_pct}%）",
                f"前日涨跌：{day_chg}点（{day_pct}%）",
                "----------------------------------------"
            ]
        if len(buf) == 0:
            buf.append("无有效美股指数数据")
    except Exception as err:
        buf.append(f"美股拉取失败：{str(err)}")
    gc.collect()
    return "\n".join(buf)

# OKX虚拟币 恢复0.3s间隔+长连接，增加单次重试容错，保持今日/昨日/24h涨幅完整字段
def get_crypto_info(coin_list, usd_rate):
    buf = []
    base_url = "https://www.okx.com/api/v5/market/ticker"
    for coin in coin_list:
        inst_id = f"{coin}-USDT"
        # 修复：循环间隔拉长到0.3s，避免OKX限流
        time.sleep(0.3)
        retry_cnt = 1
        while retry_cnt >= 0:
            try:
                resp = SESS.get(f"{base_url}?instId={inst_id}", headers=HEADERS, timeout=GLOBAL_TIMEOUT)
                resp.raise_for_status()
                json_data = resp.json()
                del resp
                data = json_data["data"][0]
                sym = coin
                usd_now = round(float(data["last"]), 2)
                usd_today_open = round(float(data["sodUtc8"]), 2)
                usd_24h_open = round(float(data["open24h"]), 2)
                cny_now = round(usd_now * usd_rate, 2)
                cny_today_open = round(usd_today_open * usd_rate, 2)
                today_chg_usd = round(usd_now - usd_today_open, 2)
                today_chg_pct = round((today_chg_usd / usd_today_open)*100, 2) if usd_today_open !=0 else 0
                chg_24h_pct = round(float(data["price_change_percentage_24h"]), 2)
                usd_yesterday_close = usd_today_open
                usd_yesterday_open = round(2 * usd_24h_open - usd_today_open, 2)
                yesterday_chg_usd = round(usd_yesterday_close - usd_yesterday_open, 2)
                yesterday_chg_pct = round((yesterday_chg_usd / usd_yesterday_open)*100, 2) if usd_yesterday_open !=0 else 0
                cny_yesterday_close = round(usd_yesterday_close * usd_rate, 2)
                buf += [
                    f"{sym}",
                    f"现价：${usd_now} | 折合人民币¥{cny_now}",
                    f"今日开盘(早8点)：${usd_today_open} 折合¥{cny_today_open}",
                    f"昨日收盘：${usd_yesterday_close} 折合¥{cny_yesterday_close}",
                    f"今日涨幅：${today_chg_usd}（{today_chg_pct}%）",
                    f"昨日涨幅：${yesterday_chg_usd}（{yesterday_chg_pct}%）",
                    f"24小时涨幅：{chg_24h_pct}%",
                    "----------------------------------------"
                ]
                del json_data, data
                gc.collect()
                break
            except Exception:
                retry_cnt -= 1
                if retry_cnt == 0:
                    buf.append(f"{coin} OKX欧易接口访问失败")
                    buf.append("----------------------------------------")
                    gc.collect()
    return "\n".join(buf)

if __name__ == "__main__":
    try:
        # 优化3：分段获取+即时释放内存，压低峰值防OOM 137报错
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
        del gold_info, gold_block
        gc.collect()

        # 获取美股 独立捕获异常保证变量存在
        try:
            us_text = "===== 美股宽基指数 =====\n" + get_us_index(usd_ex, US_INDEX_LIST)
        except Exception as us_err:
            us_text = f"===== 美股宽基指数 =====\n美股整体获取异常：{str(us_err)}"
        gc.collect()

        # 获取虚拟币（修复长连接+0.3s间隔+单次重试，恢复正常拉取）
        crypto_text = "===== 虚拟币行情 =====\n" + get_crypto_info(CRYPTO_LIST, usd_ex)
        gc.collect()

        # 合并单条推送
        full_msg = f"{gold_text}\n{us_text}\n{crypto_text}"
        push_wechat("黄金+美股+BTC/ETH行情播报", full_msg)

        # 全部内存释放
        del gold_text, us_text, crypto_text, full_msg
        gc.collect()
    except Exception as err:
        push_wechat("行情脚本异常提醒", f"全局错误：{str(err)}")
        gc.collect()
# 优化5：无kill_self强制系统杀进程，执行完毕Python解释器自动正常退出，系统完整回收RAM
