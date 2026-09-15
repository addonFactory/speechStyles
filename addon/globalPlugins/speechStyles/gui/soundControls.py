# Copyright (C) 2026 Beka Gozalishvili <beqaprogger@gmail.com>
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

import dataclasses
import os

import addonHandler
import wx
from gui import guiHelper, nvdaControls
from logHandler import log

from .. import sounds
from ..model import MAX_VOLUME, Sound, SoundType
from ..storage import StorageError
from .beepPatternDialog import BeepPatternDialog
from .dialogs import groupParent, showError
from .labels import SOUND_TYPE_LABELS, SOUND_TYPES

addonHandler.initTranslation()


class SoundControls:
    def __init__(self, parent, sHelper, store):
        self.parent = parent
        self.window = wx.GetTopLevelParent(parent)
        self.store = store
        self._sound = Sound()
        self._enabled = True
        # Translators: The label of the group of settings choosing a sound.
        sizer = wx.StaticBoxSizer(wx.VERTICAL, parent, label=_("Sound"))
        group = guiHelper.BoxSizerHelper(parent, sizer=sizer)
        sHelper.addItem(group)
        self.box = box = groupParent(parent, group)
        self.typeChoice = group.addLabeledControl(
            # Translators: The label of the choice of what sound a rule plays.
            _("Soun&d"),
            wx.Choice,
            choices=[SOUND_TYPE_LABELS[soundType] for soundType in SOUND_TYPES],
        )
        self.typeChoice.Bind(wx.EVT_CHOICE, lambda event: self._onTypeChange())
        self.panCheckBox = group.addItem(
            wx.CheckBox(
                box,
                # Translators: The label of a check box to play beeps from the direction of the element.
                label=_("Pan by the hori&zontal position of the element"),
            )
        )
        self.fileText = group.addLabeledControl(
            # Translators: The label of the field showing the chosen wave file.
            _("&Wave file"),
            wx.TextCtrl,
            style=wx.TE_READONLY,
        )
        self.volumeSpin = group.addLabeledControl(
            # Translators: The label of a control to choose how loud a wave file is played.
            _("Wave file volu&me (%)"),
            nvdaControls.SelectOnFocusSpinCtrl,
            min=0,
            max=MAX_VOLUME,
            initial=100,
        )
        buttonHelper = guiHelper.ButtonHelper(wx.HORIZONTAL)
        self.beepsButton = self._addButton(
            buttonHelper,
            # Translators: The label of a button opening the dialog to build the beeps of a sound.
            _("Confi&gure beeps..."),
            self._onConfigureBeeps,
        )
        self.browseButton = self._addButton(
            buttonHelper,
            # Translators: The label of a button to choose the wave file a rule plays.
            _("Choos&e file..."),
            self._onBrowse,
        )
        self.testButton = self._addButton(
            buttonHelper,
            # Translators: The label of a button to hear the sound of a rule.
            _("Chec&k the sound"),
            lambda event: sounds.play(self.getSound()),
        )
        group.addItem(buttonHelper)
        self.setSound(self._sound)

    def _addButton(self, buttonHelper, label, handler):
        button = buttonHelper.addButton(self.box, label=label)
        button.Bind(wx.EVT_BUTTON, handler)
        return button

    def setSound(self, sound):
        self._sound = sound
        self.typeChoice.SetSelection(SOUND_TYPES.index(sound.type))
        self.panCheckBox.SetValue(sound.panByPosition)
        self.fileText.SetValue(sound.waveFile)
        self.volumeSpin.SetValue(sound.waveVolume)
        self._updateEnabled()

    def getSound(self):
        selection = self.typeChoice.GetSelection()
        soundType = SOUND_TYPES[selection] if selection != wx.NOT_FOUND else SoundType.NONE
        return dataclasses.replace(
            self._sound,
            type=soundType,
            panByPosition=self.panCheckBox.GetValue(),
            waveFile=self.fileText.GetValue(),
            waveVolume=self.volumeSpin.GetValue(),
        )

    def enable(self, enabled):
        self._enabled = enabled
        self._updateEnabled()

    def validate(self):
        sound = self.getSound()
        if sound.type == SoundType.WAVE and not sound.waveFile:
            # Translators: Reported when a rule plays a wave file but none was chosen.
            showError(self.window, _("Choose a wave file, or choose another sound."))
            self.browseButton.SetFocus()
            return False
        return True

    def _soundType(self):
        selection = self.typeChoice.GetSelection()
        return SOUND_TYPES[selection] if selection != wx.NOT_FOUND else SoundType.NONE

    def _onTypeChange(self):
        self._updateEnabled()

    def _updateEnabled(self):
        soundType = self._soundType()
        isBeeps = self._enabled and soundType == SoundType.BEEPS
        isWave = self._enabled and soundType == SoundType.WAVE
        self.typeChoice.Enable(self._enabled)
        self.panCheckBox.Enable(isBeeps)
        self.beepsButton.Enable(isBeeps)
        self.fileText.Enable(isWave)
        self.volumeSpin.Enable(isWave)
        self.browseButton.Enable(isWave)
        self.testButton.Enable(self._enabled and not self.getSound().isSilent)

    def _onConfigureBeeps(self, event):
        with BeepPatternDialog(self.window, self._sound.beeps) as dialog:
            if dialog.ShowModal() == wx.ID_OK:
                self._sound = dataclasses.replace(self._sound, beeps=tuple(dialog.steps))
                self._updateEnabled()

    def _onBrowse(self, event):
        current = self.store.soundPath(self.fileText.GetValue()) or ""
        with wx.FileDialog(
            self.window,
            # Translators: The title of the dialog to choose the wave file a rule plays.
            message=_("Choose a wave file"),
            # Translators: The filter of the dialog to choose a wave file.
            wildcard=_("Wave files") + " (*.wav)|*.wav",
            defaultDir=os.path.dirname(current),
            defaultFile=os.path.basename(current),
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return
            path = dialog.GetPath()
        try:
            name = self.store.addSound(path)
        except StorageError:
            log.error(f"Could not copy the sound {path!r}", exc_info=True)
            # Translators: Reported when a chosen wave file cannot be copied. {file} is its path.
            showError(self.window, _("Could not read {file}.").format(file=path))
            return
        self.fileText.SetValue(name)
        self._updateEnabled()
