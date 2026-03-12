import numpy as np
from moviepy import VideoFileClip

def get_audio(path):
    print(f"Loading {path}")
    with VideoFileClip(path) as video:
        audio = video.audio
        duration = min(video.duration, 600)
        arr = audio.subclipped(0, duration).to_soundarray(fps=8000)
        
        if arr.ndim > 1:
            arr = arr.mean(axis=1)
            
        print("dtype:", arr.dtype)
        print("First 10 before:", arr[:10])
        
        mean_val = np.mean(arr)
        arr = arr - mean_val
        std = np.std(arr)
        print("Std:", std)
        
        print("First 10 after:", arr[:10])
        
        if std > 0:
            arr = arr / std
            
        return arr

a1 = get_audio('raw_videos/20260303_150107.mp4')
