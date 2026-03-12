import imageio_ffmpeg
import subprocess
import os
import tempfile
import numpy as np
from scipy.io import wavfile

def extract_audio_ffmpeg(video_path):
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    
    # Create temp wav file
    temp_wav = tempfile.mktemp(suffix=".wav")
    
    # Extract 60 seconds, convert to mono, 8000 Hz
    cmd = [
        ffmpeg_exe,
        "-i", video_path,
        "-t", "60",         # Only first 60 seconds
        "-vn",              # Disable video
        "-ac", "1",         # Mono
        "-ar", "8000",      # Sample rate 8000 Hz
        "-y",               # Overwrite
        temp_wav
    ]
    
    try:
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        sample_rate, data = wavfile.read(temp_wav)
        
        print(f"File: {video_path}")
        print(f"Sample Rate: {sample_rate}")
        print(f"Data Shape: {data.shape}")
        print(f"Max Val: {np.max(data)}")
        print(f"Min Val: {np.min(data)}")
        print(f"Std Dev: {np.std(data)}")
        print(f"First 10: {data[:10]}")
        
    except subprocess.CalledProcessError as e:
        print(f"Error: {e.stderr.decode('utf-8', errors='ignore')}")
    finally:
        if os.path.exists(temp_wav):
            os.remove(temp_wav)

extract_audio_ffmpeg('raw_videos/20260303_150107.mp4')
extract_audio_ffmpeg('raw_videos/20260303_150525.mp4')
