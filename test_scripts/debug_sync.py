import numpy as np
from scipy import signal
from moviepy import VideoFileClip
import os

def get_audio(path):
    with VideoFileClip(path) as video:
        audio = video.audio
        duration = min(video.duration, 60)
        audio_subclip = audio.subclipped(0, duration)
        arr = audio_subclip.to_soundarray(fps=8000)
        if arr.ndim > 1:
            arr = arr.mean(axis=1)
        arr = arr - np.mean(arr)
        std = np.std(arr)
        if std > 0:
            arr = arr / std
        return arr

p1 = "raw_videos/20260303_150107.mp4"
p2 = "raw_videos/20260303_150525.mp4"

a1 = get_audio(p1)
a2 = get_audio(p2)

print("a1 shape:", a1.shape, "max:", np.max(a1), "min:", np.min(a1))
print("a2 shape:", a2.shape, "max:", np.max(a2), "min:", np.min(a2))

corr = signal.correlate(a1, a2, mode='full', method='fft')
lag = np.argmax(corr)

print("corr shape:", corr.shape)
print("max corr:", corr[lag], "at lag:", lag)
print("delay samples:", lag - (len(a2) - 1))
