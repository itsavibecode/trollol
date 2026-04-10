#!/usr/bin/env python3
"""
Troll Video Generator Server
Run: python3 troll_server.py
Then open: http://localhost:8420

Requires: ffmpeg installed, emodeninod-full19_6_new.mp4 in the same folder.
"""

import os, sys, json, base64, subprocess, tempfile, shutil, uuid
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import threading

PORT = 8420
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TROLL_VIDEO = os.path.join(SCRIPT_DIR, "emodeninod-full19_6_new.mp4")
HTML_FILE = os.path.join(SCRIPT_DIR, "troll-video-generator.html")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "rendered")
TROLL_DURATION = 15.418  # seconds

os.makedirs(OUTPUT_DIR, exist_ok=True)


def render_troll_video(bait_image_data, duration, loop, boost_pct, filename):
    """
    Use ffmpeg to create an mp4 with:
    - Bait image as the first ~0.5s
    - Troll video content for the remaining duration (looped if needed)
    - Audio from troll video with optional volume boost
    Returns the path to the rendered mp4.
    """
    work_dir = tempfile.mkdtemp(prefix="troll_")
    
    try:
        # 1. Save bait image
        if bait_image_data.startswith("data:"):
            # Strip data URI prefix
            header, b64data = bait_image_data.split(",", 1)
            ext = "jpg"
            if "png" in header:
                ext = "png"
            elif "webp" in header:
                ext = "webp"
        else:
            b64data = bait_image_data
            ext = "jpg"
        
        bait_path = os.path.join(work_dir, f"bait.{ext}")
        with open(bait_path, "wb") as f:
            f.write(base64.b64decode(b64data))
        
        # Calculate durations
        bait_dur = 0.5  # half second of bait image
        troll_dur = max(0.5, duration - bait_dur)
        
        # 2. Determine how many loops needed
        loops_needed = 0
        if loop and troll_dur > TROLL_DURATION:
            import math
            loops_needed = math.ceil(troll_dur / TROLL_DURATION) - 1
        
        # 3. Create bait clip (image -> video with silent audio, matching troll video specs)
        bait_clip = os.path.join(work_dir, "bait.mp4")
        subprocess.run([
            "ffmpeg", "-y",
            "-loop", "1", "-i", bait_path,
            "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2",
            "-r", "30", "-t", str(bait_dur),
            "-c:a", "aac", "-b:a", "128k", "-shortest",
            bait_clip
        ], capture_output=True, timeout=30)
        
        # 4. Normalize troll video
        troll_norm = os.path.join(work_dir, "troll_norm.mp4")
        volume_filter = f"volume={boost_pct/100:.2f}" if boost_pct != 100 else "anull"
        subprocess.run([
            "ffmpeg", "-y",
            "-i", TROLL_VIDEO,
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2",
            "-r", "30",
            "-c:a", "aac", "-b:a", "128k", "-af", volume_filter,
            troll_norm
        ], capture_output=True, timeout=60)
        
        # 5. Create looped troll clip at exact duration
        troll_looped = os.path.join(work_dir, "troll_looped.mp4")
        loop_arg = str(loops_needed) if loops_needed > 0 else "0"
        subprocess.run([
            "ffmpeg", "-y",
            "-stream_loop", loop_arg,
            "-i", troll_norm,
            "-t", str(troll_dur),
            "-c", "copy",
            troll_looped
        ], capture_output=True, timeout=60)
        
        # 6. Concatenate bait + troll
        concat_file = os.path.join(work_dir, "concat.txt")
        with open(concat_file, "w") as f:
            f.write(f"file '{bait_clip}'\n")
            f.write(f"file '{troll_looped}'\n")
        
        output_path = os.path.join(OUTPUT_DIR, f"{filename}.mp4")
        result = subprocess.run([
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", concat_file,
            "-c", "copy",
            output_path
        ], capture_output=True, timeout=60)
        
        if result.returncode != 0:
            print(f"FFmpeg concat error: {result.stderr.decode()}", file=sys.stderr)
            return None
        
        # Verify output
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            return output_path
        return None
        
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


class TrollHandler(BaseHTTPRequestHandler):
    
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        if path == "/" or path == "/index.html":
            self.serve_file(HTML_FILE, "text/html")
        elif path.endswith(".mp4") and "/rendered/" in path:
            fpath = os.path.join(OUTPUT_DIR, os.path.basename(path))
            if os.path.exists(fpath):
                self.serve_file(fpath, "video/mp4")
            else:
                self.send_error(404)
        elif path.endswith(".mp4"):
            fpath = os.path.join(SCRIPT_DIR, os.path.basename(path))
            if os.path.exists(fpath):
                self.serve_file(fpath, "video/mp4")
            else:
                self.send_error(404)
        else:
            self.send_error(404)
    
    def do_POST(self):
        if self.path == "/api/render":
            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len)
            
            try:
                data = json.loads(body)
                bait_image = data["bait_image"]
                duration = float(data.get("duration", 15))
                loop = bool(data.get("loop", True))
                boost = int(data.get("boost", 100))
                filename = data.get("filename", f"troll_{uuid.uuid4().hex[:8]}")
                
                # Render
                output_path = render_troll_video(bait_image, duration, loop, boost, filename)
                
                if output_path:
                    url = f"/rendered/{os.path.basename(output_path)}"
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"url": url, "filename": os.path.basename(output_path)}).encode())
                else:
                    self.send_response(500)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Render failed"}).encode())
                    
            except Exception as e:
                print(f"Error: {e}", file=sys.stderr)
                import traceback; traceback.print_exc()
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
        else:
            self.send_error(404)
    
    def serve_file(self, filepath, content_type):
        try:
            with open(filepath, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", len(data))
            if content_type == "video/mp4":
                self.send_header("Accept-Ranges", "bytes")
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            self.send_error(500, str(e))
    
    def log_message(self, format, *args):
        print(f"[{self.log_date_time_string()}] {format % args}")


def main():
    if not os.path.exists(TROLL_VIDEO):
        print(f"ERROR: {TROLL_VIDEO} not found!")
        print(f"Place emodeninod-full19_6_new.mp4 in: {SCRIPT_DIR}")
        sys.exit(1)
    
    if not os.path.exists(HTML_FILE):
        print(f"ERROR: {HTML_FILE} not found!")
        sys.exit(1)
    
    server = HTTPServer(("0.0.0.0", PORT), TrollHandler)
    print(f"\n{'='*50}")
    print(f"  TROLL VIDEO GENERATOR")
    print(f"  Open: http://localhost:{PORT}")
    print(f"  Press Ctrl+C to stop")
    print(f"{'='*50}\n")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
