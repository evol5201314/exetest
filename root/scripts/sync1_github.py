#!/usr/bin/env python3
# -*- coding: utf-8 -*-

beizhu = "📈 独立版：一键同步 GitHub 仓库（镜像同步 /root/scripts/，支持 .py 和 .html）"

"""
===== 【OpenWrt 低内存专用优化说明 请勿删除以下轻量化逻辑】 =====
硬件环境：路由可用内存仅≈30M，精简python3，峰值内存控制最小化
屏蔽stdout/stderr输出至/dev/null，不读写闪存，无日志文件占用存储空间
保留下方备注方便查看脚本详情
"""

"""
================================================================
🐍 GitHub 独立同步工具（递归镜像同步版）
================================================================

【功能】
  从 GitHub 仓库递归同步所有 .py 和 .html 文件到路由器
  完全镜像仓库结构：
    - 仓库 /root/scripts/ 目录及其所有子目录 → /root/scripts/
  支持文件类型：.py 和 .html

【依赖】
  ✅ Python 3 (python3-light 即可)
  ✅ urllib (标准库)
  ✅ json   (标准库)
  ✅ os     (标准库)

【使用方法】
  1. 修改下方的 CONFIG（仓库地址、Token）
  2. 运行: python3 sync_github.py

================================================================
"""

import os
import sys
import json
import urllib.request
import urllib.error

# ========== 配置区域（请修改） ==========
CONFIG = {
    "repo_url": "https://github.com/evol5201314/exetest",
    "branch": "main",
}

ENV_REPO = os.environ.get("GITHUB_REPO")
if ENV_REPO:
    CONFIG["repo_url"] = ENV_REPO

# 仓库子目录路径（根据你的仓库结构调整）
# - 如果文件在仓库根目录 → SUB_PATH = ""
# - 如果文件在 root/scripts/ 下 → SUB_PATH = "root/scripts"
SUB_PATH = "root/scripts"

# 支持的文件扩展名
SUPPORTED_EXTS = ('.py', '.html')

# ==========================================

def parse_github_url(raw_url):
    raw = raw_url.strip()
    if not raw:
        return None
    token = ""
    if raw.startswith("https://"):
        rest = raw[8:]
    elif raw.startswith("http://"):
        rest = raw[7:]
    else:
        rest = raw
    if "@" in rest and "github.com" in rest:
        token, rest = rest.split("@", 1)
    if rest.startswith("github.com/"):
        rest = rest[11:]
    elif rest.startswith("www.github.com/"):
        rest = rest[15:]
    else:
        return None
    branch = "main"
    if "/tree/" in rest:
        repo_part, branch = rest.split("/tree/", 1)
        branch = branch.split("/")[0]
        rest = repo_part
    parts = rest.split("/")
    if len(parts) >= 2:
        return {
            "username": parts[0],
            "repo": parts[1],
            "branch": branch,
            "token": token
        }
    return None

def fetch_api(url, token=None):
    req = urllib.request.Request(url)
    if token:
        req.add_header("Authorization", f"token {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8")
    except Exception:
        return None

def sync_dir(repo_url, local_root, remote_subpath=""):
    """
    递归同步 remote_subpath 下的所有 .py 和 .html 文件到 local_root
    返回 (success, message)
    """
    parsed = parse_github_url(repo_url)
    if not parsed:
        return False, "解析仓库地址失败"
    username = parsed["username"]
    repo = parsed["repo"]
    token = parsed["token"]
    branch = parsed.get("branch", "main")

    downloaded_total = 0

    def walk(remote_path, local_path):
        nonlocal downloaded_total
        # 构建 API URL
        if remote_path:
            api_url = f"https://api.github.com/repos/{username}/{repo}/contents/{remote_path}?ref={branch}"
        else:
            api_url = f"https://api.github.com/repos/{username}/{repo}/contents?ref={branch}"

        resp = fetch_api(api_url, token)
        if resp is None:
            return  # 网络或权限错误，跳过
        try:
            items = json.loads(resp)
        except Exception:
            return  # JSON 解析失败，跳过

        if isinstance(items, dict) and "message" in items:
            # GitHub API 返回错误信息
            return

        if not isinstance(items, list):
            return

        # 确保本地目录存在
        os.makedirs(local_path, exist_ok=True)

        for item in items:
            item_type = item.get("type")
            name = item.get("name", "")
            if item_type == "file" and name.endswith(SUPPORTED_EXTS):
                download_url = item.get("download_url")
                if not download_url:
                    continue
                try:
                    req = urllib.request.Request(download_url)
                    if token:
                        req.add_header("Authorization", f"token {token}")
                    with urllib.request.urlopen(req, timeout=30) as resp_file:
                        content = resp_file.read().decode("utf-8")
                        dest_path = os.path.join(local_path, name)
                        with open(dest_path, "w", encoding="utf-8") as out:
                            out.write(content)
                        downloaded_total += 1
                except Exception:
                    pass  # 单个文件下载失败不影响整体
            elif item_type == "dir":
                # 递归进入子目录
                new_remote = remote_path + "/" + name if remote_path else name
                new_local = os.path.join(local_path, name)
                walk(new_remote, new_local)

    # 开始递归
    walk(remote_subpath, local_root)
    return True, f"下载 {downloaded_total} 个文件"

if __name__ == "__main__":
    repo = CONFIG.get("repo_url")
    if not repo:
        print("❌ 未设置仓库地址")
        sys.exit(1)

    print("========================================")
    print("🐍 GitHub 独立同步工具 (递归镜像同步)")
    print(f"支持文件: {', '.join(SUPPORTED_EXTS)}")
    print("========================================")

    # 只同步一次，递归包含所有子目录
    ok, msg = sync_dir(repo, "/root/scripts", SUB_PATH)
    print(f"📁 /root/scripts/: {msg}")

    print("========================================")
    sys.exit(0 if ok else 1)
