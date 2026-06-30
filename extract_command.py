#!/usr/bin/python3
"""
===== 【OpenWrt 低内存专用优化说明 请勿删除以下轻量化逻辑】
硬件环境：路由可用内存仅≈30M，精简python3，峰值内存控制最小化
屏蔽stdout/stderr输出至/dev/null，不读写闪存，无日志文件占用存储空间
保留下方备注方便查看脚本详情
"""
beizhu = "📈 备份command脚本数据"
import os
LUCI_FILE = '/etc/config/luci'
COMMAND_FILE = '/etc/config/command'

def extract_command():
    if not os.path.exists(LUCI_FILE):
        print(f"Error: {LUCI_FILE} not found")
        return

    with open(LUCI_FILE, 'r') as f:
        lines = f.readlines()

    extracted = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith('config command'):
            # 记录整个段落
            extracted.append(line)
            i += 1
            while i < len(lines):
                if lines[i].strip().startswith('config '):
                    break
                extracted.append(lines[i])
                i += 1
            # 不加额外的空行，保持原样
        else:
            i += 1

    # 写入 command 文件（覆盖）
    with open(COMMAND_FILE, 'w') as f:
        f.writelines(extracted)

    print(f"Extracted {len(extracted)} lines to {COMMAND_FILE}")

if __name__ == '__main__':
    extract_command()
