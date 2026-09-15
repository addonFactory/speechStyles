# Copyright (C) 2026 Beka Gozalishvili <beqaprogger@gmail.com>
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

import config
import queueHandler
import synthDriverHandler
from logHandler import log
from speech.extensions import speechCanceled

from .markers import VoiceStateCommand


class VoiceController:
    def __init__(self):
        self._applied = None
        self._synth = None

    def register(self):
        synthDriverHandler.pre_synthSpeak.register(self._onPreSynthSpeak)
        synthDriverHandler.synthDoneSpeaking.register(self._onDoneSpeaking)
        synthDriverHandler.synthChanged.register(self._onSynthChanged)
        speechCanceled.register(self.restore)
        config.post_configProfileSwitch.register(self.restore)

    def unregister(self):
        config.post_configProfileSwitch.unregister(self.restore)
        speechCanceled.unregister(self.restore)
        synthDriverHandler.synthChanged.unregister(self._onSynthChanged)
        synthDriverHandler.synthDoneSpeaking.unregister(self._onDoneSpeaking)
        synthDriverHandler.pre_synthSpeak.unregister(self._onPreSynthSpeak)
        self.restore()

    def _onPreSynthSpeak(self, speechSequence):
        state = None
        for index in range(len(speechSequence) - 1, -1, -1):
            item = speechSequence[index]
            if isinstance(item, VoiceStateCommand):
                state = item.state
                del speechSequence[index]
        self.apply(state)

    def apply(self, state):
        synth = synthDriverHandler.getSynth()
        if synth is None or (state == self._applied and synth is self._synth):
            return
        if state is None and self._applied is None:
            return
        try:
            self._give(synth, state)
        except Exception:
            log.error(f"Could not apply {state!r}", exc_info=True)
        self._applied = state
        self._synth = synth if state is not None else None

    def restore(self):
        if self._applied is not None:
            self.apply(None)

    def _give(self, synth, state):
        conf = config.conf["speech"][synth.name]
        voice = (state.voice if state else None) or conf.get("voice")
        if voice and synth.isSupported("voice") and synth.voice != voice:
            if voice in synth.availableVoices:
                synth.voice = voice
                self._reapplySettings(synth, conf)
            else:
                log.debugWarning(f"The voice {voice!r} is not available in {synth.name}")
        if synth.isSupported("inflection"):
            default = conf["inflection"]
            wanted = state.inflection.resolve(default) if state and state.inflection else default
            if synth.inflection != wanted:
                synth.inflection = wanted

    @staticmethod
    def _reapplySettings(synth, conf):
        for setting in synth.supportedSettings:
            if not setting.useConfig or setting.id == "voice":
                continue
            value = conf.get(setting.id)
            if value is not None:
                setattr(synth, setting.id, value)

    def _onDoneSpeaking(self, synth=None):
        if self._applied is not None:
            queueHandler.queueFunction(queueHandler.eventQueue, self._restoreIfIdle)

    def _restoreIfIdle(self):
        import speech.speech

        manager = getattr(speech.speech, "_manager", None)
        hasNoMoreSpeech = getattr(manager, "_hasNoMoreSpeech", None)
        if hasNoMoreSpeech is None or hasNoMoreSpeech():
            self.restore()

    def _onSynthChanged(self, synth=None, **kwargs):
        self._applied = None
        self._synth = None
