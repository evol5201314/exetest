import sys
sys.path.append("/root/scripts")
import serial
import time
beizhu = "📈 监控温度开启风扇"
# 串口配置和你测试脚本完全一致
SER_DEV = "/dev/ttyUSB0"
BAUD_RATE = 9600
RELAY_ON = bytes([0xA0, 0x01, 0x01, 0xA2])
RELAY_OFF = bytes([0xA0, 0x01, 0x00, 0xA1])

TEMP_ON = 58    # 超58℃开风扇
TEMP_OFF = 55   # 低于55℃关风扇

# 读取CPU温度
def get_cpu_temp():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp_raw = int(f.read().strip())
        return round(temp_raw / 1000, 1)
    except Exception as e:
        print("读取温度失败:", e)
        return None

# 控制继电器
def set_fan(status):
    try:
        ser = serial.Serial(SER_DEV, BAUD_RATE, timeout=1)
        if status:
            ser.write(RELAY_ON)
            print("温度过高，开启散热风扇")
        else:
            ser.write(RELAY_OFF)
            print("温度正常，关闭散热风扇")
        ser.close()
    except Exception as e:
        print("串口继电器操作失败:", e)

# 单次检测逻辑（无循环，执行完直接结束）
def main():
    temp = get_cpu_temp()
    if temp is None:
        return
    print(f"本次检测CPU温度：{temp}℃")
    
    # 逻辑：高温开风扇，低温关风扇
    if temp >= TEMP_ON:
        set_fan(True)
    elif temp <= TEMP_OFF:
        set_fan(False)

if __name__ == "__main__":
    main()
