#!/usr/bin/env python3
"""
Troll Video Renderer
====================
Renders a troll MP4 video with a bait image as the first frame,
followed by the troll video content, looped to your desired duration.

Usage:
  python3 render_troll.py --bait image.png --video troll.mp4 --duration 22 --output my_troll.mp4
  python3 render_troll.py --bait image.png --video troll.mp4 --duration 60 --boost 200 --output prank.mp4

Requirements:
  - Python 3
  - FFmpeg installed (ffmpeg command available in PATH)
"""

import argparse
import subprocess
import sys
import os
import random
import string

def random_filename():
    adj = ['funny','epic','crazy','wild','dank','based','rare','ultra','mega','hyper',
           'super','sick','fire','goated','elite','savage','cursed','blessed','spicy','crispy']
    nouns = ['clip','moment','video','footage','edit','reel','cut','take','shot','drop',
             'highlight','play','scene','capture','render','content','recording','montage']
    num = random.randint(1000, 9999)
    return f"{random.choice(adj)}_{random.choice(nouns)}_{random.choice(adj)}_{num}"

def check_ffmpeg():
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False

def render_troll_video(bait_image, troll_video, duration, output, boost=100, bait_duration=0.15):
    """
    Render a troll MP4 with:
    - bait_image as the first frame(s) for bait_duration seconds
    - troll_video looped to fill the remaining duration
    - Audio from troll_video with optional volume boost
    """
    if not os.path.exists(bait_image):
        print(f"Error: Bait image not found: {bait_image}")
        sys.exit(1)
    if not os.path.exists(troll_video):
        print(f"Error: Troll video not found: {troll_video}")
        sys.exit(1)

    print(f"Rendering troll video...")
    print(f"  Bait image:  {bait_image}")
    print(f"  Troll video: {troll_video}")
    print(f"  Duration:    {duration}s")
    print(f"  Boost:       {boost}%")
    print(f"  Output:      {output}")
    print()

    volume_filter = f"volume={boost/100}" if boost != 100 else "anull"

    cmd = [
        'ffmpeg', '-y',
        '-loop', '1', '-t', str(bait_duration), '-framerate', '30', '-i', bait_image,
        '-stream_loop', '-1', '-i', troll_video,
        '-filter_complex',
        f"[0:v]scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2:black,fps=30,setsar=1[bait];"
        f"[1:v]scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2:black,fps=30,setsar=1[troll];"
        f"[bait][troll]concat=n=2:v=1:a=0[vout];"
        f"[1:a]{volume_filter}[aout]",
        '-map', '[vout]', '-map', '[aout]',
        '-c:v', 'libx264', '-preset', 'fast', '-crf', '23', '-pix_fmt', 'yuv420p',
        '-c:a', 'aac', '-b:a', '192k',
        '-t', str(duration),
        '-movflags', '+faststart',
        output
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"FFmpeg error:\n{result.stderr[-500:]}")
            sys.exit(1)
        
        size = os.path.getsize(output)
        print(f"Done! Output: {output} ({size/1024:.0f} KB)")
        print(f"The first frame shows your bait image, then the troll video plays for {duration}s.")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='Render a troll video with a bait image as the first frame')
    parser.add_argument('--bait', '-b', required=True, help='Path to the bait image (PNG, JPG, etc)')
    parser.add_argument('--video', '-v', required=True, help='Path to the troll video (MP4)')
    parser.add_argument('--duration', '-d', type=float, default=15, help='Total video duration in seconds (default: 15)')
    parser.add_argument('--output', '-o', default=None, help='Output filename (default: random name)')
    parser.add_argument('--boost', type=int, default=100, help='Audio volume boost percentage (default: 100)')
    parser.add_argument('--bait-duration', type=float, default=0.15, help='How long to show bait image in seconds (default: 0.15)')
    
    args = parser.parse_args()
    
    if not check_ffmpeg():
        print("Error: FFmpeg is not installed or not in PATH.")
        print("Install it: https://ffmpeg.org/download.html")
        sys.exit(1)
    
    output = args.output or (random_filename() + '.mp4')
    
    render_troll_video(
        bait_image=args.bait,
        troll_video=args.video,
        duration=args.duration,
        output=output,
        boost=args.boost,
        bait_duration=args.bait_duration
    )

if __name__ == '__main__':
    main()
