import numpy as np
from moviepy import VideoFileClip

path = 'raw_videos/20260303_150525.mp4'
print(f"Loading {path}")
with VideoFileClip(path) as video:
    audio = video.audio
    dur = int(video.duration)
    print(f"Total duration: {dur}s")
    for start_t in range(0, dur, 60):
        end_t = min(start_t + 60, dur)
        arr = audio.subclipped(start_t, end_t).to_soundarray(fps=8000)
        if arr.ndim > 1:
            arr = arr.mean(axis=1)
        print(f"{start_t}s - {end_t}s : std = {np.std(arr):.6f}")
