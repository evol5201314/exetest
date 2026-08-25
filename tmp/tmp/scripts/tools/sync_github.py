#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# popup: syncModal
# btn: 📥 同步脚本
# group: script
# order: 60
# action: runScript:sync_github.py
# btn-class: btn-pink
beizhu = "📥 同步 GitHub（支持自动保存仓库地址到自身）"

import os, sys, json, urllib.request, urllib.error, argparse

CONFIG = {
    "repo_url": "https://github.com/evol5201314/exetest",
    "branch": "main",
}

def save_repo_to_self(new_repo):
    script_path = os.path.abspath(__file__)
    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        new_lines = []
        in_config = False
        for line in lines:
            stripped = line.lstrip()
            if stripped.startswith('CONFIG = {'):
                in_config = True
                new_lines.append(line)
                continue
            if in_config and '"repo_url"' in stripped:
                indent = line[:len(line) - len(line.lstrip())]
                new_lines.append(f'{indent}"repo_url": "{new_repo}",\n')
            elif in_config and '}' in stripped and not stripped.startswith('"'):
                in_config = False
                new_lines.append(line)
            else:
                new_lines.append(line)
        with open(script_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        return True
    except Exception as e:
        print(f"⚠️ 保存配置失败: {e}")
        return False

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
    except Exception:
        return None

def sync_dir(repo_url, target_dir, sub_path=""):
    """
    递归同步 sub_path 下的所有 .py 和 .html 文件到 target_dir
    返回 (success, message)
    """
    parsed = parse_github_url(repo_url)
    if not parsed:
        return False, "解析仓库地址失败"
    username = parsed["username"]
    repo = parsed["repo"]
    token = parsed["token"]
    branch = parsed["branch"]

    downloaded_total = 0

    def walk(remote_path, local_path):
        nonlocal downloaded_total
        if remote_path:
            api_url = f"https://api.github.com/repos/{username}/{repo}/contents/{remote_path}?ref={branch}"
        else:
            api_url = f"https://api.github.com/repos/{username}/{repo}/contents?ref={branch}"

        resp = fetch_api(api_url, token)
        if resp is None:
            return
        try:
            items = json.loads(resp)
        except:
            return
        if isinstance(items, dict) and "message" in items:
            return
        if not isinstance(items, list):
            return

        os.makedirs(local_path, exist_ok=True)

        for item in items:
            item_type = item.get("type")
            name = item.get("name", "")
            if item_type == "file" and name.endswith(('.py', '.html')):
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
                    pass
            elif item_type == "dir":
                new_remote = remote_path + "/" + name if remote_path else name
                new_local = os.path.join(local_path, name)
                walk(new_remote, new_local)

    walk(sub_path, target_dir)
    return True, f"下载 {downloaded_total} 个文件"

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', help='GitHub 仓库地址')
    parser.add_argument('--get-config', action='store_true', help='获取当前配置的仓库地址')
    args = parser.parse_args()

    if args.get_config:
        print(CONFIG.get("repo_url", ""))
        sys.exit(0)

    repo = args.repo if args.repo else CONFIG.get("repo_url")
    if not repo:
        print("❌ 未设置仓库地址")
        sys.exit(1)

    if args.repo and args.repo != CONFIG.get("repo_url"):
        if save_repo_to_self(args.repo):
            print(f"✅ 仓库地址已保存: {args.repo}")
        else:
            print("⚠️ 仓库地址保存失败，本次仍使用新地址同步")

    print("========================================")
    print("🐍 GitHub 同步工具 (递归镜像同步)")
    print(f"🔗 {repo}")
    print("========================================")

    # 只同步一次，递归包含所有子目录
    ok, msg = sync_dir(repo, "/root/scripts", "root/scripts")
    print(f"📁 /root/scripts/: {msg}")

    print("========================================")
    sys.exit(0 if ok else 1)
