import os
import json
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

API_URL = "https://api.github.com/repos/evol5201314/exetest/contents/root/scripts?ref=main"
SAVE_DIR = r"D:\tmp\Scripts"
HEADERS = {'User-Agent': 'Python-Script'}

def download_file(item, base_dir):
    """下载单个文件，并打印状态"""
    file_path = os.path.join(base_dir, item['name'])
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    url = item['download_url']
    try:
        resp = requests.get(url, headers=HEADERS, stream=True, timeout=30)
        if resp.status_code == 200:
            with open(file_path, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"下载完成: {item['name']}")
            return True
        else:
            print(f"下载失败: {item['name']} (状态码 {resp.status_code})")
            return False
    except Exception as e:
        print(f"下载出错: {item['name']} - {e}")
        return False

def fetch_contents(api_url, base_dir):
    """递归获取目录内容，返回 (文件项, 本地存储目录) 的列表"""
    resp = requests.get(api_url, headers=HEADERS)
    resp.raise_for_status()
    items = resp.json()
    file_tasks = []
    for item in items:
        if item['type'] == 'file':
            file_tasks.append((item, base_dir))
        elif item['type'] == 'dir':
            sub_dir = os.path.join(base_dir, item['name'])
            os.makedirs(sub_dir, exist_ok=True)
            file_tasks.extend(fetch_contents(item['url'], sub_dir))
    return file_tasks

def main():
    os.makedirs(SAVE_DIR, exist_ok=True)
    print("正在获取文件列表...")
    tasks = fetch_contents(API_URL, SAVE_DIR)
    total = len(tasks)
    print(f"共发现 {total} 个文件，开始并发下载（线程数=8）...\n")

    success_count = 0
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(download_file, item, base) for item, base in tasks]
        for future in as_completed(futures):
            if future.result():
                success_count += 1

    print(f"\n所有文件下载完成！成功 {success_count}/{total} 个文件。")
    input("按回车键退出...")   # 防止窗口自动关闭

if __name__ == "__main__":
    main()
