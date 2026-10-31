import os
import sys
import re
import glob
import json
import shutil
import datetime
import subprocess
import argparse
import requests
import gdown

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(PROJECT_DIR, "automation_config.json")

def get_jst_today():
    """Return today's date in Japan Standard Time (JST = UTC+9)"""
    jst = datetime.timezone(datetime.timedelta(hours=9))
    return datetime.datetime.now(jst).date()

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
    files.sort(key=lambda x: os.path.basename(x))
    return files

def parse_folder_titles(folder_name):
    today_str = get_jst_today().strftime("%Y年%m月%d日")
    default_title = "誰が1番好き？"
    default_subtitle = f"{today_str} 比較動画"

    parts = [p.strip() for p in re.split(r'[_\s]+', folder_name) if p.strip()]

    # If first part looks like a date (e.g. 20261029, 1029, 2026-10-29), remove it from title
    if parts and re.match(r'^(20\d\d[-_]?)?\d{2}[-_]?\d{2}$', parts[0]):
        parts = parts[1:]

    if len(parts) >= 2:
        return parts[0], parts[1]
    elif len(parts) == 1:
        return default_title, parts[0]
    else:
        return default_title, default_subtitle

def find_all_target_folders_and_files(base_dir, target_date=None, process_all=False):
    """
    Find ONLY folders matching target_date (or all if process_all is True).
    Never fall back to older unrelated folders!
    """
    if target_date is None:
        target_date = get_jst_today()

    date_patterns = [
        target_date.strftime("%Y-%m-%d"),
        target_date.strftime("%Y%m%d"),
        target_date.strftime("%m-%d"),
        target_date.strftime("%m%d"),
        f"{target_date.month}_{target_date.day}",
        f"{target_date.month:02d}_{target_date.day:02d}",
        f"{target_date.month}月{target_date.day}日",
    ]

    matched_folders = []
    all_subdirs = []

    if os.path.exists(base_dir):
        for item in os.listdir(base_dir):
            p = os.path.join(base_dir, item)
            if os.path.isdir(p):
                all_subdirs.append((item, p))

    if process_all:
        print("[Automation] Mode: Processing ALL subfolders (--all specified)")
        for name, p in all_subdirs:
            media = get_media_in_dir(p)
            if media:
                matched_folders.append((name, media))
        matched_folders.sort(key=lambda x: x[0])
        return matched_folders

    # Strict match: ONLY folders containing target date patterns
    print(f"[Automation] Searching folders strictly matching date: {target_date} (patterns: {date_patterns})")
    for name, p in all_subdirs:
        for pat in date_patterns:
            if pat in name:
                media = get_media_in_dir(p)
                if media:
                    matched_folders.append((name, media))
                break

    matched_folders.sort(key=lambda x: x[0])
    return matched_folders

def clean_person_name(filename, default_name):
    raw = os.path.splitext(filename)[0]
    cleaned = re.sub(r'^[0-9]+[_\-\.\s]*', '', raw).strip()
    return cleaned if cleaned else default_name

def find_ffprobe():
    # 1. System ffprobe
    import shutil
    p = shutil.which("ffprobe")
    if p:
        return p
    # 2. Remotion bundled ffprobe
    candidates = glob.glob(os.path.join(PROJECT_DIR, "node_modules", "@remotion", "*", "ffprobe*"))
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None

def get_audio_bitrate(ffprobe_bin, file_path):
    if not ffprobe_bin or not os.path.exists(file_path):
        return 0
    ext = os.path.splitext(file_path)[1].lower()
    if ext in ('.jpg', '.jpeg', '.png', '.webp'):
        return 0
    try:
        cmd = [
            ffprobe_bin,
            "-v", "error",
            "-select_streams", "a:0",
            "-show_entries", "stream=bit_rate",
            "-of", "json",
            file_path
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(res.stdout)
        streams = data.get("streams", [])
        if streams and "bit_rate" in streams[0]:
            return int(streams[0]["bit_rate"])
    except Exception:
        pass
    return 0

def get_media_duration(ffprobe_bin, file_path):
    """Get duration of a media file in seconds (float)"""
    if not ffprobe_bin or not os.path.exists(file_path):
        return 0.0
    ext = os.path.splitext(file_path)[1].lower()
    if ext in ('.jpg', '.jpeg', '.png', '.webp'):
        return 0.0
    try:
        cmd = [
            ffprobe_bin,
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "json",
            file_path
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(res.stdout)
        dur = float(data.get("format", {}).get("duration", 0.0))
        return dur
    except Exception:
        pass
    return 0.0

def detect_best_audio_index(media_group):
    """Detect which video has the real sound track (bitrate >= 16kbps)"""
    ffprobe_bin = find_ffprobe()
    best_idx = 0
    max_bitrate = 0

    for idx, p in enumerate(media_group):
        br = get_audio_bitrate(ffprobe_bin, p)
        filename = os.path.basename(p)
        print(f"[AudioCheck] [{idx}] '{filename}' -> bitrate: {br} bps")
        if br > max_bitrate and br >= 16000:
            max_bitrate = br
            best_idx = idx

    print(f"[AudioCheck] => Selected audio index: {best_idx} (bitrate: {max_bitrate} bps)")
    return best_idx

def render_single_video(config, media_group, output_path, title, subtitle, render_id=1, layout='4-grid'):
    public_videos_dir = os.path.join(PROJECT_DIR, "public", "videos")
    os.makedirs(public_videos_dir, exist_ok=True)
    ffprobe_bin = find_ffprobe()

    items = []
    default_names = config.get("default_names", ["みおち", "みなみ", "金丸紗希", "もえ"])
    target_count = 2 if layout == '2-split' else 4

    # Automatically detect the best audio source among the target videos
    best_audio_idx = detect_best_audio_index(media_group[:target_count])

    # Determine video duration: full length of the audio source video (do not cut at 7s!)
    audio_file = media_group[best_audio_idx] if best_audio_idx < len(media_group) else media_group[0]
    audio_dur = get_media_duration(ffprobe_bin, audio_file)

    if audio_dur <= 0:
        # Fallback: check maximum duration among all videos
        durations = [get_media_duration(ffprobe_bin, f) for f in media_group[:target_count]]
        audio_dur = max(durations) if durations else 7.0

    # Ensure duration is reasonable (at least 3.0s, rounded to 1 decimal place)
    final_duration = round(max(3.0, audio_dur), 1)
    print(f"[Automation] Video Duration: {final_duration} seconds (full length of audio source)")

    for i in range(target_count):
        src_file = media_group[i] if i < len(media_group) else media_group[0]
        filename = os.path.basename(src_file)
        ext = os.path.splitext(filename)[1].lower()
        
        safe_filename = f"slot_{render_id}_{i}{ext}"
        dst_path = os.path.join(public_videos_dir, safe_filename)
        shutil.copy2(src_file, dst_path)

        def_name = default_names[i] if i < len(default_names) else f"No.{i+1}"
        name = clean_person_name(filename, def_name)

        items.append({
            "name": name,
            "videoSrc": f"videos/{safe_filename}",
            "startOffset": 0
        })

    # Fixed USER STYLES
    props = {
        "title": title,
        "subtitle": subtitle,
        "titleDuration": 1.5,
        "titleColor": "#ffffff",
        "titleStrokeColor": "#ff2d78",
        "fontFamily": "'Mochiy Pop One', sans-serif",
        "titleFontSize": 0.95,
        "titleStrokeWidth": 8,
        "nameColor": "#ffffff",
        "nameStrokeColor": "#d6006e",
        "nameFontFamily": "'M PLUS Rounded 1c', sans-serif",
        "nameFontSize": 1.0,
        "nameStrokeWidth": 8,
        "audioIndex": best_audio_idx,
        "layout": layout,
        "durationInSeconds": final_duration,
        "items": items
    }

    temp_props_path = os.path.join(PROJECT_DIR, f"_auto_props_{render_id}.json")
    with open(temp_props_path, "w", encoding="utf-8") as f:
        json.dump(props, f, ensure_ascii=False, indent=2)

    print(f"[Automation] Rendering ({layout}, {final_duration}s): '{title}' / '{subtitle}'")
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

    if ret.returncode != 0:
        raise RuntimeError(f"Remotion render failed for {output_path}")

    print(f"[Automation] Render finished: {output_path}")

def send_to_discord(webhook_url, video_path, message_text):
    if not webhook_url:
        print("[Automation] Warning: No DISCORD_WEBHOOK_URL specified. Skipping upload.")
        return

    print(f"[Automation] Uploading {video_path} to Discord Webhook...")
    filename = os.path.basename(video_path)
    file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
    print(f"[Automation] File size: {file_size_mb:.2f} MB")

    if file_size_mb > 24.5:
        print("[Automation] Warning: Video file is over Discord 25MB limit. Sending text notice only.")
        payload = {"content": f"{message_text}\n⚠️ 動画ファイルが25MBを超えているためアップロードできませんでした ({file_size_mb:.1f}MB)。"}
        requests.post(webhook_url, json=payload)
        return

    try:
        with open(video_path, "rb") as f:
            files = {"file": (filename, f, "video/mp4")}
            payload = {"content": message_text}
            res = requests.post(webhook_url, data=payload, files=files, timeout=120)
            if res.status_code in (200, 204):
                print("[Automation] Discord delivery successful! (Status 200/204)")
            else:
                print(f"[Automation] Discord delivery failed: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"[Automation] Error uploading to Discord: {e}")

def main():
    parser = argparse.ArgumentParser(description="TikTok Compare Video Daily Automation")
    parser.add_argument("--date", help="Target date in YYYY-MM-DD or MMDD format (default: today JST)")
    parser.add_argument("--all", action="store_true", help="Process all folders found")
    args = parser.parse_args()

    print("=" * 60)
    print(" TikTok Compare Video Daily Automation (Auto 2-Split / 4-Grid)")
    print(f" Execution Time: {datetime.datetime.now()}")
    print("=" * 60)

    config = load_config()

    target_date = get_jst_today()
    if args.date:
        # Parse custom date
        clean_d = args.date.strip()
        if re.match(r'^\d{4}-\d{2}-\d{2}$', clean_d):
            target_date = datetime.datetime.strptime(clean_d, "%Y-%m-%d").date()
        elif re.match(r'^\d{4}$', clean_d):
            # MMDD for current year
            target_date = datetime.date(target_date.year, int(clean_d[:2]), int(clean_d[2:]))
        print(f"[Automation] Custom Target Date specified: {target_date}")

    # 1. Download from Google Drive
    gdrive_dir = os.path.join(PROJECT_DIR, "_gdrive_download")
    gdrive_url = config.get("gdrive_folder_url")
    if gdrive_url:
        download_from_gdrive(gdrive_url, gdrive_dir)

    # 2. Collect target folders
    local_drive = config.get("drive_folder_path")
    search_base = gdrive_dir
    if not os.path.exists(search_base) or not os.listdir(search_base):
        if local_drive and os.path.exists(local_drive):
            search_base = local_drive

    target_folders = find_all_target_folders_and_files(search_base, target_date=target_date, process_all=args.all)
    print(f"[Automation] Found {len(target_folders)} target folder(s) strictly matching date {target_date}.")

    webhook_url = config.get("discord_webhook_url")
    today_jp = target_date.strftime("%Y年%m月%d日")

    if not target_folders:
        msg = f"ℹ️ **【朝の自動納品】本日の動画素材の確認**\n日付: `{today_jp}` に該当するフォルダがGoogleドライブ上に見つかりませんでした。\n（過去の動画を誤って再送しないよう、本日は処理をスキップしました）"
        print(f"[Automation] {msg}")
        if webhook_url:
            try:
                requests.post(webhook_url, json={"content": msg})
            except Exception:
                pass
        print("=" * 60)
        return

    today_str = target_date.strftime("%Y-%m-%d")
    out_dir = os.path.join(PROJECT_DIR, "out")
    os.makedirs(out_dir, exist_ok=True)

    global_video_count = 0

    for f_idx, (folder_name, media_files) in enumerate(target_folders, 1):
        print("-" * 50)
        print(f"[Automation] Processing Folder [{f_idx}/{len(target_folders)}]: '{folder_name}' ({len(media_files)} files)")

        base_title, base_subtitle = parse_folder_titles(folder_name)
        
        # Determine whether this folder should be 2-split or 4-grid:
        # If exactly 2 files OR folder name contains '2分割' / '2選' / 'vs'
        if len(media_files) == 2 or ("2分割" in folder_name or "2選" in folder_name or "vs" in folder_name.lower()):
            chunk_size = 2
            layout = '2-split'
            print(f"[Automation] Mode: 2-Split (Left vs Right)")
        else:
            chunk_size = 4
            layout = '4-grid'
            print(f"[Automation] Mode: 4-Grid (2x2 Quad)")

        chunks = [media_files[i:i + chunk_size] for i in range(0, len(media_files), chunk_size)]

        for c_idx, chunk in enumerate(chunks, 1):
            global_video_count += 1
            while len(chunk) < chunk_size:
                chunk.append(chunk[0])

            current_subtitle = f"{base_subtitle} #{c_idx}" if len(chunks) > 1 else base_subtitle
            out_video_name = f"compare_{today_str}_f{f_idx}_p{c_idx}_{layout}.mp4"
            out_video_path = os.path.join(out_dir, out_video_name)

            # Render
            render_single_video(
                config, chunk, out_video_path,
                title=base_title, subtitle=current_subtitle,
                render_id=global_video_count, layout=layout
            )

            # Deliver to Discord
            layout_label = "縦2分割" if layout == '2-split' else "4分割"
            msg = f"🌅 **【朝の自動納品】{base_title} - {current_subtitle}** ({layout_label})\n（日付: {today_jp} / フォルダ: `{folder_name}` / 計{len(chunk)}素材）"
            send_to_discord(webhook_url, out_video_path, msg)

    print("=" * 60)
    print(f"[Automation] Finished! Total {global_video_count} video(s) created and delivered to Discord.")
    print("=" * 60)

if __name__ == "__main__":
    main()
