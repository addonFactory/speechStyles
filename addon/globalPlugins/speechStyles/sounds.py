# Copyright (C) 2022-2026 Beka Gozalishvili <beqaprogger@gmail.com>
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

import array
import threading
import wave

import nvwave
import tones
import wx
from logHandler import log

from .model import SoundType, pannedSteps

SAMPLE_TYPES = {8: "B", 16: "h", 32: "i"}

resolveSoundPath = lambda name: None  # noqa: E731


def play(sound, position=None):
    if sound.type == SoundType.BEEPS:
        playBeeps(pannedSteps(sound.beeps, position) if sound.panByPosition else sound.beeps)
    elif sound.type == SoundType.WAVE:
        path = resolveSoundPath(sound.waveFile)
        if path is None:
            log.debugWarning(f"The sound {sound.waveFile!r} is missing")
            return
        _wavePlayer.play(path, sound.waveVolume)


def playBeeps(steps):
    delay = 0
    for step in steps:
        if delay:
            wx.CallLater(delay, tones.beep, step.frequency, step.length, step.leftVolume, step.rightVolume)
        else:
            tones.beep(step.frequency, step.length, step.leftVolume, step.rightVolume)
        delay += step.length + step.pause


class _WavePlayer:
    def __init__(self):
        self._lock = threading.Lock()
        self._requested = threading.Event()
        self._request = None
        self._thread = None
        self._player = None
        self._playerFormat = None

    def play(self, path, volume):
        with self._lock:
            self._request = (path, volume)
        if self._player is not None:
            self._player.stop()
        self._requested.set()
        if self._thread is None or not self._thread.is_alive():
            self._thread = threading.Thread(name=f"{__name__}.WavePlayer", target=self._run, daemon=True)
            self._thread.start()

    def _run(self):
        while True:
            self._requested.wait()
            self._requested.clear()
            with self._lock:
                request, self._request = self._request, None
            if request is None:
                continue
            try:
                self._play(*request)
            except Exception:
                log.error(f"Could not play the wave file {request[0]!r}", exc_info=True)

    def _play(self, path, volume):
        with wave.open(path, "r") as waveFile:
            fileFormat = (waveFile.getnchannels(), waveFile.getframerate(), waveFile.getsampwidth() * 8)
            frames = waveFile.readframes(waveFile.getnframes())
        if self._player is None or fileFormat != self._playerFormat:
            channels, samplesPerSec, bitsPerSample = fileFormat
            self._player = nvwave.WavePlayer(
                channels=channels,
                samplesPerSec=samplesPerSec,
                bitsPerSample=bitsPerSample,
                wantDucking=False,
                purpose=nvwave.AudioPurpose.SOUNDS,
            )
            self._playerFormat = fileFormat
        self._player.feed(_atVolume(frames, fileFormat[2], volume))
        self._player.idle()


def _atVolume(frames, bitsPerSample, volume):
    level = min(max(volume, 0), 100) / 100
    if level == 1:
        return frames
    sampleType = SAMPLE_TYPES.get(bitsPerSample)
    if sampleType is None:
        log.debugWarning(f"Cannot change the volume of {bitsPerSample} bit audio")
        return frames
    try:
        samples = array.array(sampleType, frames)
    except ValueError:
        log.debugWarning(f"Cannot change the volume of {len(frames)} bytes of audio", exc_info=True)
        return frames
    if sampleType == "B":
        samples[:] = array.array(sampleType, (round(128 + (sample - 128) * level) for sample in samples))
    else:
        samples[:] = array.array(sampleType, (round(sample * level) for sample in samples))
    return samples.tobytes()


_wavePlayer = _WavePlayer()
