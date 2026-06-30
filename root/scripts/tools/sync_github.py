#!/usr/bin/env python3
# -*- coding: utf-8 -*-
beizhu = "📥 同步 GitHub 仓库（镜像 /root/scripts/ 结构）"

"""
同步规则：
  - 仓库 root/scripts/ 子目录 → /root/scripts/
  - 仓库 root/scripts/tools/ 子目录 → /root/scripts/tools/
"""
import os, sys, json, urllib.request, urllib.error

DEBUG = False

CONFIG = {
    "repo_url": "https://github.com/evol5201314/exetese",
    "branch": "main",
}

def log(msg):
    if DEBUG:
        print(msg)

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
        return {"username": parts[0], "repo": parts[1], "branch": branch, "token": token}
    return None

def fetch_api(url, token=None):
    req = urllib.request.Request(url)
    if token:
        req.add_header("Authorization", f"token {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8")
    except Exception as e:
        log(f"请求失败: {e}")
        return None

def sync_dir(repo_url, target_dir, sub_path=""):
    parsed = parse_github_url(repo_url)
    if not parsed:
        return False, "解析失败"
    username, repo, token, branch = parsed["username"], parsed["repo"], parsed["token"], parsed["branch"]
    if sub_path:
        api_url = f"https://api.github.com/repos/{username}/{repo}/contents/{sub_path}?ref={branch}"
    else:
        api_url = f"https://api.github.com/repos/{username}/{repo}/contents?ref={branch}"
    log(f"📡 请求: {api_url}")
    resp = fetch_api(api_url, token)
    if resp is None:
        return False, "API请求失败"
    try:
        files = json.loads(resp)
    except:
        return False, "JSON解析失败"
    if isinstance(files, dict) and "message" in files:
        return False, files["message"]
    if not isinstance(files,
