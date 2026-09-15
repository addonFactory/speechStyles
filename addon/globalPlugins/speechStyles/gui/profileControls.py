# Copyright (C) 2026 Beka Gozalishvili <beqaprogger@gmail.com>
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

import dataclasses

import addonHandler
import config
import synthDriverHandler
import wx
from gui import guiHelper, nvdaControls
from logHandler import log

from ..model import (
    PARAM_MAX,
    PARAM_MIN,
    RELATIVE_MAX,
    RELATIVE_MIN,
    ParamMode,
    ParamSetting,
    VoiceProfile,
    clamp,
)
from ..profiles import SETTINGS
from .labels import PARAM_MODE_LABELS, PARAM_MODES, SETTING_LABELS

addonHandler.initTranslation()


class ProfileControls:
    def __init__(self, parent, sHelper, label):
        self.synth = synthDriverHandler.getSynth()
        self.synthName = self.synth.name if self.synth is not None else ""
        self._profile = VoiceProfile()
        self._enabled = True
        sizer = wx.StaticBoxSizer(wx.VERTICAL, parent, label=label)
        group = guiHelper.BoxSizerHelper(parent, sizer=sizer)
        sHelper.addItem(group)
        self.modeChoices = {}
        self.valueSpins = {}
        for setting in SETTINGS:
            settingLabel = SETTING_LABELS[setting]
            if not self._supports(setting):
                # Translators: A speech setting the current synthesizer lacks. {setting} is its name.
                settingLabel = _("{setting} (not supported by the current synthesizer)").format(
                    setting=settingLabel
                )
            choice = group.addLabeledControl(
                settingLabel,
                wx.Choice,
                choices=[PARAM_MODE_LABELS[mode] for mode in PARAM_MODES],
            )
            choice.Bind(wx.EVT_CHOICE, lambda event, setting=setting: self._onModeChange(setting))
            spin = group.addLabeledControl(
                # Translators: The label of the number of a speech setting. {setting} is its name, e.g. Pitch.
                _("{setting} value").format(setting=SETTING_LABELS[setting].replace("&", "")),
                nvdaControls.SelectOnFocusSpinCtrl,
                min=RELATIVE_MIN,
                max=RELATIVE_MAX,
            )
            self.modeChoices[setting] = choice
            self.valueSpins[setting] = spin
        self.voiceIds = [None]
        voiceLabels = [
            # Translators: A choice of voice: the voice is not changed.
            _("Unchanged"),
        ]
        for voiceId, voiceInfo in self._availableVoices():
            self.voiceIds.append(voiceId)
            voiceLabels.append(voiceInfo.displayName)
        self.voiceChoice = group.addLabeledControl(
            # Translators: The label of the choice of voice for customized speech.
            _("V&oice"),
            wx.Choice,
            choices=voiceLabels,
        )
        self.setProfile(self._profile)

    def _supports(self, setting):
        return self.synth is not None and self.synth.isSupported(setting)

    def _availableVoices(self):
        if not self._supports("voice"):
            return []
        try:
            return list(self.synth.availableVoices.items())
        except Exception:
            log.error("Could not list the voices of the synthesizer", exc_info=True)
            return []

    def _configuredValue(self, setting):
        try:
            return int(config.conf["speech"][self.synthName][setting])
        except (KeyError, TypeError, ValueError):
            return 50

    def setProfile(self, profile):
        self._profile = profile
        for setting in SETTINGS:
            param = getattr(profile, setting)
            self.modeChoices[setting].SetSelection(PARAM_MODES.index(param.mode))
            self._setRange(setting, param.mode)
            self.valueSpins[setting].SetValue(param.value)
        voiceId = profile.voiceFor(self.synthName)
        if voiceId is not None and voiceId not in self.voiceIds:
            self.voiceIds.append(voiceId)
            # Translators: A voice chosen earlier which the synthesizer no longer has.
            # {voice} is the identifier of that voice.
            self.voiceChoice.Append(_("{voice} (not available)").format(voice=voiceId))
        self.voiceChoice.SetSelection(self.voiceIds.index(voiceId))
        self._updateEnabled()

    def getProfile(self):
        settings = {
            setting: ParamSetting(self._mode(setting), self.valueSpins[setting].GetValue())
            for setting in SETTINGS
        }
        profile = dataclasses.replace(self._profile, **settings)
        selection = self.voiceChoice.GetSelection()
        voiceId = self.voiceIds[selection] if selection != wx.NOT_FOUND else None
        return profile.withVoice(self.synthName, voiceId)

    def enable(self, enabled):
        self._enabled = enabled
        self._updateEnabled()

    def _mode(self, setting):
        selection = self.modeChoices[setting].GetSelection()
        return PARAM_MODES[selection] if selection != wx.NOT_FOUND else ParamMode.UNCHANGED

    def _setRange(self, setting, mode):
        spin = self.valueSpins[setting]
        if mode == ParamMode.RELATIVE:
            spin.SetRange(RELATIVE_MIN, RELATIVE_MAX)
        else:
            spin.SetRange(PARAM_MIN, PARAM_MAX)

    def _onModeChange(self, setting):
        mode = self._mode(setting)
        self._setRange(setting, mode)
        spin = self.valueSpins[setting]
        if mode == ParamMode.ABSOLUTE:
            spin.SetValue(clamp(self._configuredValue(setting), PARAM_MIN, PARAM_MAX))
        elif mode == ParamMode.RELATIVE:
            spin.SetValue(0)
        self._updateEnabled()

    def _updateEnabled(self):
        for setting in SETTINGS:
            self.modeChoices[setting].Enable(self._enabled)
            self.valueSpins[setting].Enable(self._enabled and self._mode(setting) != ParamMode.UNCHANGED)
        self.voiceChoice.Enable(self._enabled and len(self.voiceIds) > 1)
