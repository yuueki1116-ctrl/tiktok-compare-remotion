import os
import sys
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

    # Allow environment variables to override
    if os.environ.get("DISCORD_WEBHOOK_URL"):
        config["discord_webhook_url"] = os.environ["DISCORD_WEBHOOK_URL"]
    if os.environ.get("GDRIVE_FOLDER_URL"):
        config["gdrive_folder_url"] = os.environ["GDRIVE_FOLDER_URL"]
    return config

def download_from_gdrive(folder_url, dest_dir):
    """Download all files from Google Drive shared folder using gdown"""
    print(f"[Automation] Checking Google Drive folder: {folder_url}")
    os.makedirs(dest_dir, exist_ok=True)
    try:
        # Suppress insecure SSL warning on local windows if needed
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # Download folder
        gdown.download_folder(folder_url, output=dest_dir, quiet=False, use_cookies=False, verify=False)
    except Exception as e:
        print(f"[Automation] gdown error (non-fatal): {e}")

def get_media_files(media_dirs):
    valid_exts = (".mp4", ".mov", ".webm", ".jpg", ".jpeg", ".png", ".webp")
    all_files = []
    
    for d in media_dirs:
        if os.path.exists(d):
            for root, _, files in os.walk(d):
                for f in files:
                    if f.lower().endswith(valid_exts):
                        full_path = os.path.join(root, f)
                        all_files.append(full_path)

    # Sort files by name or modification time
    all_files.sort(key=lambda x: os.path.basename(x))
    return all_files

def render_comparison_video(config, media_files, output_path):
    today_str = datetime.date.today().strftime("%Y年%m月%d日")
    subtitle = config.get("subtitle_template", "{date} 比較動画").replace("{date}", today_str)
    title = config.get("title_prefix", "誰が1番好き？")

    public_videos_dir = os.path.join(PROJECT_DIR, "public", "videos")
    os.makedirs(public_videos_dir, exist_ok=True)

    items = []
    default_names = config.get("default_names", ["みおち", "みなみ", "金丸紗希", "もえ"])

    for i in range(4):
        src_file = media_files[i] if i < len(media_files) else media_files[0]
        filename = os.path.basename(src_file)
        dst_path = os.path.join(public_videos_dir, filename)
        if os.path.abspath(src_file) != os.path.abspath(dst_path):
            shutil.copy2(src_file, dst_path)

        # Name extraction: from filename (e.g. "みなみ.jpg" -> "みなみ")
        raw_name = os.path.splitext(filename)[0]
        if any("\u3040" <= c <= "\u30ff" or "\u4e00" <= c <= "\u9fff" for c in raw_name):
            name = raw_name
        else:
            name = default_names[i] if i < len(default_names) else f"Member {i+1}"

        items.append({
            "name": name,
            "videoSrc": f"videos/{filename}",
            "startOffset": 0
        })

    # Fixed props chosen by USER
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

    temp_props_path = os.path.join(PROJECT_DIR, "_auto_props.json")
    with open(temp_props_path, "w", encoding="utf-8") as f:
        json.dump(props, f, ensure_ascii=False, indent=2)

    print(f"[Automation] Rendering video with Remotion (Title: '{subtitle}') ...")
    
    # Detect platform (Windows vs Linux)
    if sys.platform == "win32":
        cmd = [
            "cmd.exe", "/c",
            f"cd /d \"{PROJECT_DIR}\" && set NODE_TLS_REJECT_UNAUTHORIZED=0 && npx.cmd remotion render src/index.ts CompareVideo \"{output_path}\" --props=\"{temp_props_path}\""
        ]
    else:
        cmd = [
            "npx", "remotion", "render", "src/index.ts", "CompareVideo", output_path, f"--props={temp_props_path}"
        ]

    ret = subprocess.run(cmd, cwd=PROJECT_DIR)

    if os.path.exists(temp_props_path):
        os.remove(temp_props_path)

    if ret.returncode != 0:
        raise RuntimeError("Remotion render failed")

    print(f"[Automation] Render complete: {output_path}")
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
    print(" TikTok Compare Video Automation (Daily Run)")
    print(f" Current Time: {datetime.datetime.now()}")
    print("=" * 60)

    config = load_config()

    # 1. Download files from Google Drive
    gdrive_dir = os.path.join(PROJECT_DIR, "_gdrive_download")
    gdrive_url = config.get("gdrive_folder_url")
    if gdrive_url:
        download_from_gdrive(gdrive_url, gdrive_dir)

    # 2. Collect media files
    local_drive = config.get("drive_folder_path")
    search_dirs = [gdrive_dir]
    if local_drive and os.path.exists(local_drive):
        search_dirs.append(local_drive)
    search_dirs.append(os.path.join(PROJECT_DIR, "public", "videos"))

    media_files = get_media_files(search_dirs)
    print(f"[Automation] Found {len(media_files)} candidate media files:")
    for mf in media_files[:4]:
        print(f"  - {os.path.basename(mf)}")

    if not media_files:
        raise RuntimeError("No media files found to generate video.")

    # 3. Render MP4
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    out_dir = os.path.join(PROJECT_DIR, "out")
    os.makedirs(out_dir, exist_ok=True)
    out_video_path = os.path.join(out_dir, f"compare_{today_str}.mp4")

    render_comparison_video(config, media_files, out_video_path)

    # 4. Deliver to Discord
    webhook_url = config.get("discord_webhook_url")
    today_jp = datetime.date.today().strftime("%Y年%m月%d日")
    msg = f"🌅 **【朝の自動納品】{today_jp} 比較動画** が完成しました！\n本日もよろしくお願いします！"
    send_to_discord(webhook_url, out_video_path, msg)

if __name__ == "__main__":
    main()
