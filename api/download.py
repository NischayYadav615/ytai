from yt_dlp import YoutubeDL
import os
from flask import Flask, jsonify, request, send_file
import subprocess

app = Flask(__name__)

DOWNLOAD_FOLDER = "/tmp"

def combine_video_audio(video_path, audio_path, output_path):
    """Combine video and audio using FFmpeg."""
    command = [
        "ffmpeg", "-i", video_path, "-i", audio_path,
        "-c:v", "copy", "-c:a", "aac", "-strict", "experimental", output_path
    ]
    subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

@app.route('/api/get_formats', methods=['POST'])
def get_formats():
    """Fetch all available formats for a given video."""
    try:
        url = request.json.get('url')
        if not url:
            return jsonify({"status": "error", "message": "No URL provided."}), 400

        with YoutubeDL() as ydl:
            info = ydl.extract_info(url, download=False)
            formats = info.get('formats', [])
            available_formats = [
                {"format_id": fmt['format_id'], "format_note": fmt['format_note'], "ext": fmt['ext']}
                for fmt in formats if fmt['vcodec'] != 'none'
            ]
            return jsonify({"status": "success", "formats": available_formats})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/api/download', methods=['POST'])
def download_video():
    """Download video and handle cases with no audio."""
    try:
        url = request.json.get('url')
        quality = request.json.get('quality')  # Specific format ID

        if not url:
            return jsonify({"status": "error", "message": "No URL provided."}), 400

        video_path = os.path.join(DOWNLOAD_FOLDER, "video.mp4")
        audio_path = os.path.join(DOWNLOAD_FOLDER, "audio.mp4")
        output_path = os.path.join(DOWNLOAD_FOLDER, "final_output.mp4")

        # Download the video
        ydl_opts = {
            'format': quality or 'bestvideo',
            'outtmpl': video_path
        }

        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            has_audio = any(f['acodec'] != 'none' for f in info_dict.get('formats', []))
            ydl.download([url])

        if not has_audio:
            # Download the best audio separately
            ydl_opts_audio = {
                'format': 'bestaudio',
                'outtmpl': audio_path
            }
            with YoutubeDL(ydl_opts_audio) as ydl:
                ydl.download([url])

            # Combine video and audio
            combine_video_audio(video_path, audio_path, output_path)
            download_file = output_path
        else:
            download_file = video_path  # Video already includes audio

        return jsonify({
            "status": "success",
            "message": "Download completed!",
            "download_link": f"/api/download_file?file_path={download_file}"
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/api/download_file', methods=['GET'])
def download_file():
    """Serve the final output file."""
    file_path = request.args.get('file_path')
    if not file_path or not os.path.exists(file_path):
        return jsonify({"status": "error", "message": "File not found."}), 404

    return send_file(file_path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
                        
