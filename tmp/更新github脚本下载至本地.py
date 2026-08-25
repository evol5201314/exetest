import os
import subprocess
import json
import urllib.request

# GitHub API 地址，将其中的 'main' 替换为仓库实际的主分支名
api_url = "https://api.github.com/repos/evol5201314/exetest/contents/root/scripts?ref=main"

# 修改下载目录为 D:\tmp\Scripts
save_dir = r"D:\tmp\Scripts"  

def download_dir(path, url, dir_name):
    # 确保目录存在（会自动创建 D:\tmp 和 D:\tmp\Scripts）
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)
        
    req = urllib.request.Request(url, headers={'User-Agent': 'Python-Script'})
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read())
        
    for item in data:
        if item['type'] == 'file':
            # 使用 curl 下载文件，可保留原始文件名
            cmd = f'curl -L -o "{os.path.join(dir_name, item["name"])}" "{item["download_url"]}"'
            subprocess.run(cmd, shell=True)
            print(f"已下载: {item['name']}")
        elif item['type'] == 'dir':
            # 递归下载子目录
            print(f"发现子目录: {item['name']}，开始下载...")
            download_dir(item['name'], item['url'], os.path.join(dir_name, item['name']))

if __name__ == "__main__":
    print("开始从 GitHub 下载文件...")
    download_dir("scripts", api_url, save_dir)
    print("所有文件下载完成！")
