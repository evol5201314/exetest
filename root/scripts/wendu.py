# 极限轻量化温控脚本 带注释 无打印无日志
# 文件路径：/root/scripts/temp_fan_cron.py
# 运行方式：cron定时单次执行，跑完进程直接销毁，极低内存占用
import sys
# 加载pyserial库目录
sys.path.append("/root/scripts")
import serial
beizhu = "📈 监控温度开启风扇"
# ==========可自行修改配置参数==========
SER_DEV = "/dev/ttyUSB0"  # 继电器USB串口设备名
BAUD = 9600                 # 串口波特率，和继电器匹配
ON = bytes([0xA0,0x01,0x01,0xA2])  # 继电器吸合 开风扇指令
OFF = bytes([0xA0,0x01,0x00,0xA1])  # 继电器断开 关风扇指令
T_H = 58  # 温度≥58℃开启风扇
T_L = 55  # 温度≤55℃关闭风扇
# ========================================

# 获取路由器CPU温度
def gett():
    try:
        # 读取系统温度文件，数值单位毫摄氏度
        f = open("/sys/class/thermal/thermal_zone0/temp","r")
        temp_raw = int(f.read())
        f.close()
        # 换算成摄氏度返回
        return temp_raw / 1000
    except:
        # 读取温度出错静默处理，无报错输出
        return None

# 控制继电器开关风扇
# s=1 开风扇  s=0 关风扇
def fan(s):
    try:
        # 打开串口设备
        ser = serial.Serial(SER_DEV, BAUD, timeout=1)
        # 下发对应开关指令
        ser.write(ON if s else OFF)
        # 立即关闭串口释放硬件资源
        ser.close()
    except:
        # 串口操作失败直接跳过，无日志无提示
        pass

# 程序主逻辑，单次运行结束自动退出
def main():
    # 获取当前CPU温度
    temp = gett()
    # 温度读取失败直接结束程序
    if temp is None:
        return
    # 温度超标，开启散热风扇
    if temp >= T_H:
        fan(1)
    # 温度偏低，关闭散热风扇
    elif temp <= T_L:
        fan(0)

# 程序执行入口
if __name__=="__main__":
    main()
