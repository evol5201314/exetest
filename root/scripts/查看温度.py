#!/usr/bin/env python3

with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
    temp_raw = int(f.read().strip())

temp = temp_raw / 1000
print(f"CPU温度：{temp:.1f}℃")
