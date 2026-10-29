"""
TikTok 4分割 比較動画 バッチ一括自動化スクリプト
JSON設定ファイルやリストから、Remotionを使って自動レンダリングを行います。

使い方:
  python batch_render.py
  python batch_render.py --config my_config.json --output out/my_video.mp4
"""

import os
import sys
import json
import subprocess
import argparse

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

def render_video(props: dict, output_path: str):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Save temporary props json
    temp_props_path = os.path.join(PROJECT_DIR, "_temp_props.json")
    with open(temp_props_path, "w", encoding="utf-8") as f:
        json.dump(props, f, ensure_ascii=False, indent=2)

    cmd = [
        "cmd.exe", "/c",
        f"cd /d \"{PROJECT_DIR}\" && "
        f"set NODE_TLS_REJECT_UNAUTHORIZED=0 && "
        f"npx.cmd remotion render src/index.ts CompareVideo \"{output_path}\" --props=\"{temp_props_path}\""
    ]

    print(f"[Batch] Rendering to: {output_path} ...")
    ret = subprocess.run(cmd, cwd=PROJECT_DIR)
    
    if os.path.exists(temp_props_path):
        os.remove(temp_props_path)

    if ret.returncode == 0:
        print(f"[Batch] Success: {output_path}")
        return True
    else:
        print(f"[Batch] Error during render.")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Render comparison video")
    parser.add_argument("--config", help="Path to props JSON file", default=None)
    parser.add_argument("--output", help="Output MP4 file path", default="out/batch_output.mp4")
    args = parser.parse_args()

    if args.config and os.path.exists(args.config):
        with open(args.config, "r", encoding="utf-8") as f:
            props = json.load(f)
    else:
        # Default props from 4 videos
        props = {
            "title": "誰が1番好き？",
            "subtitle": "オパオパダンス4選",
            "titleDuration": 2.2,
            "titleColor": "#ffffff",
            "titleStrokeColor": "#ff2d78",
            "nameColor": "#ffffff",
            "nameStrokeColor": "#d6006e",
            "durationInSeconds": 7.0,
            "audioIndex": 0,
            "items": [
                { "name": "みおち", "videoSrc": "videos/v1c044g50000dbbl47nog65kps1bcong.mp4", "startOffset": 0 },
                { "name": "みなみ", "videoSrc": "videos/v14044g50000datr2knog65gphn6o3c0.mp4", "startOffset": 0 },
                { "name": "金丸紗希", "videoSrc": "videos/v14044g50000davp1v7og65gkm0vl580.mp4", "startOffset": 0 },
                { "name": "もえ", "videoSrc": "videos/v1c044g50000dav3khnog65l82rllud0.mp4", "startOffset": 0 }
            ]
        }

    render_video(props, os.path.abspath(args.output))
