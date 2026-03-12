import numpy as np
from scipy import signal
from moviepy import VideoFileClip

def get_audio(path):
    with VideoFileClip(path) as video:
        audio = video.audio
        duration = min(video.duration, 600)
        audio_subclip = audio.subclipped(0, duration)
        arr = audio_subclip.to_soundarray(fps=8000)
        if arr.ndim > 1:
            arr = arr.mean(axis=1)
        arr = arr - np.mean(arr)
        std = np.std(arr)
        if std > 0:
            arr = arr / std
        return arr

a1 = get_audio('raw_videos/20260303_150107.mp4')
a2 = get_audio('raw_videos/20260303_150525.mp4')

print("a1:", a1.shape, "a2:", a2.shape)

corr = signal.correlate(a1, a2, mode='full', method='fft')
peaks = np.argsort(corr)[-5:]

for p in peaks:
    lag = p
    delay_samples = lag - (len(a2) - 1)
    delay_s = delay_samples / 8000.0
    print(f"Peak at index {p}: {corr[p]}, delay_s: {delay_s}")
