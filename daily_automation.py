import os
import sys
import re
import glob
import json
import shutil
import datetime
import subprocess
import requests
import gdown

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(PROJECT_DIR, "automation_config.json")

def load_config():
    config = {}
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)

    if os.environ.get("DISCORD_WEBHOOK_URL"):
        config["discord_webhook_url"] = os.environ["DISCORD_WEBHOOK_URL"]
    if os.environ.get("GDRIVE_FOLDER_URL"):
        config["gdrive_folder_url"] = os.environ["GDRIVE_FOLDER_URL"]
    return config

def download_from_gdrive(folder_url, dest_dir):
    """Download Google Drive folder contents including subfolders"""
    print(f"[Automation] Checking Google Drive: {folder_url}")
    os.makedirs(dest_dir, exist_ok=True)
    try:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        gdown.download_folder(folder_url, output=dest_dir, quiet=False, use_cookies=False, verify=False)
    except Exception as e:
        print(f"[Automation] gdown warning: {e}")

def get_media_in_dir(directory):
    valid_exts = (".mp4", ".mov", ".webm", ".jpg", ".jpeg", ".png", ".webp")
    files = []
    if os.path.exists(directory):
        for f in os.listdir(directory):
            full_path = os.path.join(directory, f)
            if os.path.isfile(full_path) and f.lower().endswith(valid_exts):
                files.append(full_path)
    # Sort files naturally by filename (e.g. 1_みおち.jpg, 2_みなみ.jpg, ...)
    files.sort(key=lambda x: os.path.basename(x))
    return files

def parse_folder_titles(folder_name):
    """
    Extract title & subtitle from folder name.
    Examples:
      - "1029_誰が1番好き？_オパオパダンス4選" -> ("誰が1番好き？", "オパオパダンス4選")
      - "1029_オパオパダンス4選" -> ("誰が1番好き？", "オパオパダンス4選")
      - "20261029" -> ("誰が1番好き？", "2026年10月29日 比較動画")
    """
    today_str = datetime.date.today().strftime("%Y年%m月%d日")
    default_title = "誰が1番好き？"
    default_subtitle = f"{today_str} 比較動画"

    parts = [p.strip() for p in re.split(r'[_\s]+', folder_name) if p.strip()]

    # If first part looks like a date (e.g. 20261029, 1029, 2026-10-29), remove it from title parts
    if parts and re.match(r'^(20\d\d[-_]?)?\d{2}[-_]?\d{2}$', parts[0]):
        parts = parts[1:]

    if len(parts) >= 2:
        return parts[0], parts[1]
    elif len(parts) == 1:
        return default_title, parts[0]
    else:
        return default_title, default_subtitle

def find_target_folder_and_files(base_dir):
    """
    Find today's date folder (e.g. 1029, 1029_ダンス選, 2026-10-29_タイトル, etc.)
    """
    now = datetime.date.today()
    date_patterns = [
        now.strftime("%Y-%m-%d"),
        now.strftime("%Y%m%d"),
        now.strftime("%m-%d"),
        now.strftime("%m%d"),
        f"{now.month}_{now.day}",
        f"{now.month}月{now.day}日",
    ]

    subdirs = []
    if os.path.exists(base_dir):
        for item in os.listdir(base_dir):
            p = os.path.join(base_dir, item)
            if os.path.isdir(p):
                subdirs.append((item, p))

    # 1. Match today's folder
    for name, p in subdirs:
        for pat in date_patterns:
            if pat in name:
                print(f"[Automation] Matched date folder: {name}")
                media = get_media_in_dir(p)
                if media:
                    return name, media

    # 2. Latest folder fallback
    if subdirs:
        subdirs.sort(key=lambda x: x[0], reverse=True)
        for name, p in subdirs:
            media = get_media_in_dir(p)
            if media:
                print(f"[Automation] Using latest folder: {name}")
                return name, media

    # 3. Root fallback
    root_media = get_media_in_dir(base_dir)
    if root_media:
        return "root", root_media

    fallback_dir = os.path.join(PROJECT_DIR, "public", "videos")
    return "default", get_media_in_dir(fallback_dir)

def clean_person_name(filename, default_name):
    """
    Extract person name from filename:
    '1_みおち.mp4' -> 'みおち'
    '02-みなみ.png' -> 'みなみ'
    '金丸紗希.jpg' -> '金丸紗希'
    """
    raw = os.path.splitext(filename)[0]
    # Remove leading numbering like "01_", "1-", "1. ", etc.
    cleaned = re.sub(r'^[0-9]+[_\-\.\s]*', '', raw).strip()
    return cleaned if cleaned else default_name

def render_single_video(config, media_group, output_path, title, subtitle, part_index=1):
    public_videos_dir = os.path.join(PROJECT_DIR, "public", "videos")
    os.makedirs(public_videos_dir, exist_ok=True)

    items = []
    default_names = config.get("default_names", ["みおち", "みなみ", "金丸紗希", "もえ"])

    for i in range(4):
        src_file = media_group[i] if i < len(media_group) else media_group[0]
        filename = os.path.basename(src_file)
        ext = os.path.splitext(filename)[1].lower()
        
        # Save as clean safe filename to avoid OS encoding issues with Remotion staticFile
        safe_filename = f"auto_slot_{part_index}_{i}{ext}"
        dst_path = os.path.join(public_videos_dir, safe_filename)
        shutil.copy2(src_file, dst_path)

        def_name = default_names[i] if i < len(default_names) else f"No.{i+1}"
        name = clean_person_name(filename, def_name)

        items.append({
            "name": name,
            "videoSrc": f"videos/{safe_filename}",
            "startOffset": 0
        })

    # User's chosen fixed styles
    props = {
        "title": title,
        "subtitle": subtitle,
        "titleDuration": 1.5,
        "titleColor": "#ffffff",
        "titleStrokeColor": "#ff2d78",
        "fontFamily": "'Mochiy Pop One', sans-serif",
        "titleFontSize": 1.1,
        "titleStrokeWidth": 11,
        "nameColor": "#ffffff",
        "nameStrokeColor": "#d6006e",
        "nameFontFamily": "'M PLUS Rounded 1c', sans-serif",
        "nameFontSize": 1.0,
        "nameStrokeWidth": 8,
        "audioIndex": 0,
        "durationInSeconds": float(config.get("duration_seconds", 7.0)),
        "items": items
    }

    temp_props_path = os.path.join(PROJECT_DIR, f"_auto_props_{part_index}.json")
    with open(temp_props_path, "w", encoding="utf-8") as f:
        json.dump(props, f, ensure_ascii=False, indent=2)

    print(f"[Automation] Rendering: '{title}' / '{subtitle}'")
    print(f"[Automation] Members: {[it['name'] for it in items]}")
    
    env = os.environ.copy()
    env["NODE_TLS_REJECT_UNAUTHORIZED"] = "0"

    if sys.platform == "win32":
        cmd = [
            "npx.cmd", "remotion", "render",
            "src/index.ts", "CompareVideo",
            output_path,
            f"--props={temp_props_path}"
        ]
        ret = subprocess.run(cmd, cwd=PROJECT_DIR, env=env, shell=True)
    else:
        cmd = [
            "npx", "remotion", "render",
            "src/index.ts", "CompareVideo",
            output_path,
            f"--props={temp_props_path}"
        ]
        ret = subprocess.run(cmd, cwd=PROJECT_DIR, env=env)

    if os.path.exists(temp_props_path):
        os.remove(temp_props_path)

    if ret.returncode != 0:
        raise RuntimeError(f"Remotion render failed for {output_path}")

    print(f"[Automation] Render finished: {output_path}")
    return output_path

def send_to_discord(webhook_url, video_path, message_text):
    if not webhook_url or "YOUR_DISCORD_WEBHOOK" in webhook_url:
        print("[Automation] ERROR: Discord Webhook URL is missing.")
        return False

    print(f"[Automation] Uploading {video_path} to Discord Webhook...")
    filename = os.path.basename(video_path)
    
    with open(video_path, "rb") as f:
        files = {"file": (filename, f, "video/mp4")}
        payload = {"content": message_text}
        res = requests.post(webhook_url, data=payload, files=files, verify=False)

    if res.status_code in (200, 204):
        print("[Automation] Discord delivery successful! (Status 200/204)")
        return True
    else:
        print(f"[Automation] Failed to send to Discord: {res.status_code} - {res.text}")
        return False

def main():
    print("=" * 60)
    print(" TikTok Compare Video Daily Automation (Dynamic Title & Names)")
    print(f" Execution Time: {datetime.datetime.now()}")
    print("=" * 60)

    config = load_config()

    # 1. Download from Google Drive
    gdrive_dir = os.path.join(PROJECT_DIR, "_gdrive_download")
    gdrive_url = config.get("gdrive_folder_url")
    if gdrive_url:
        download_from_gdrive(gdrive_url, gdrive_dir)

    # 2. Target folder selection
    local_drive = config.get("drive_folder_path")
    search_base = gdrive_dir
    if not os.path.exists(search_base) or not os.listdir(search_base):
        if local_drive and os.path.exists(local_drive):
            search_base = local_drive

    folder_name, media_files = find_target_folder_and_files(search_base)
    print(f"[Automation] Target Folder: '{folder_name}', Found {len(media_files)} files")

    if not media_files:
        raise RuntimeError("No media files found to generate video.")

    # 3. Parse title & subtitle from folder name
    base_title, base_subtitle = parse_folder_titles(folder_name)
    print(f"[Automation] Title line 1: '{base_title}'")
    print(f"[Automation] Title line 2: '{base_subtitle}'")

    # 4. Chunk files into groups of 4
    chunk_size = 4
    media_chunks = [media_files[i:i + chunk_size] for i in range(0, len(media_files), chunk_size)]
    total_parts = len(media_chunks)
    print(f"[Automation] Generating {total_parts} video(s)...")

    today_str = datetime.date.today().strftime("%Y-%m-%d")
    out_dir = os.path.join(PROJECT_DIR, "out")
    os.makedirs(out_dir, exist_ok=True)
    webhook_url = config.get("discord_webhook_url")
    today_jp = datetime.date.today().strftime("%Y年%m月%d日")

    for idx, chunk in enumerate(media_chunks, 1):
        while len(chunk) < 4:
            chunk.append(chunk[0])

        current_subtitle = f"{base_subtitle} #{idx}" if total_parts > 1 else base_subtitle
        out_video_name = f"compare_{today_str}_part{idx}.mp4" if total_parts > 1 else f"compare_{today_str}.mp4"
        out_video_path = os.path.join(out_dir, out_video_name)

        # Render
        render_single_video(config, chunk, out_video_path, title=base_title, subtitle=current_subtitle, part_index=idx)

        # Deliver to Discord
        if total_parts > 1:
            msg = f"🌅 **【朝の自動納品】{base_title} - {current_subtitle} ({idx}/{total_parts})**\n（日付: {today_jp} / フォルダ: `{folder_name}`）"
        else:
            msg = f"🌅 **【朝の自動納品】{base_title} - {current_subtitle}**\n本日もよろしくお願いします！（日付: {today_jp}）"

        send_to_discord(webhook_url, out_video_path, msg)

    print("=" * 60)
    print(f"[Automation] Successfully created & delivered {total_parts} video(s)!")
    print("=" * 60)

if __name__ == "__main__":
    main()
