import numpy as np
from moviepy import VideoFileClip

def get_audio(path):
    print(f"Loading {path}")
    with VideoFileClip(path) as video:
        audio = video.audio
        duration = min(video.duration, 600)
        arr = audio.subclipped(0, duration).to_soundarray(fps=8000)
        
        print("Raw max:", np.max(np.abs(arr)))
        print("Raw mean:", np.mean(arr))
        
        if arr.ndim > 1:
            arr = arr.mean(axis=1)
        
        arr = arr - np.mean(arr)
        std = np.std(arr)
        print("Std:", std)
        
        if std > 0:
            arr = arr / std
            
        print("Processed max:", np.max(arr), "min:", np.min(arr), "Has NaN:", np.isnan(arr).any())
        return arr

a1 = get_audio('raw_videos/20260303_150107.mp4')
a2 = get_audio('raw_videos/20260303_150525.mp4')
