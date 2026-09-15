# Copyright (C) 2022-2026 Beka Gozalishvili <beqaprogger@gmail.com>
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

import addonHandler
import wx
from gui import guiHelper, nvdaControls

from .. import model, sounds
from ..model import BeepStep
from .dialogs import Dialog

addonHandler.initTranslation()

STEP_FIELDS = {
    # Translators: The label of a control to choose the pitch of a beep.
    "frequency": (_("Fre&quency (Hz)"), model.MIN_FREQUENCY, model.MAX_FREQUENCY),
    # Translators: The label of a control to choose how long a beep lasts.
    "length": (_("&Length (ms)"), model.MIN_LENGTH, model.MAX_LENGTH),
    # Translators: The label of a control to choose the volume of a beep in the left channel.
    "leftVolume": (_("L&eft volume (%)"), 0, model.MAX_VOLUME),
    # Translators: The label of a control to choose the volume of a beep in the right channel.
    "rightVolume": (_("&Right volume (%)"), 0, model.MAX_VOLUME),
    # Translators: The label of a control to choose the silence following a beep.
    "pause": (_("&Pause after this beep (ms)"), 0, model.MAX_PAUSE),
}


def describeStep(step):
    # Translators: How one beep of a beep pattern is presented in the list of beeps.
    return _(
        "{frequency} Hz, {length} ms, left {leftVolume}%, right {rightVolume}%, pause {pause} ms"
    ).format(
        frequency=step.frequency,
        length=step.length,
        leftVolume=step.leftVolume,
        rightVolume=step.rightVolume,
        pause=step.pause,
    )


class BeepStepDialog(Dialog):
    def __init__(self, parent, step):
        self.initialStep = step
        # Translators: The title of the dialog to add or edit one beep of a beep pattern.
        super().__init__(parent, _("Beep"))

    def makeContent(self, sHelper):
        self.fieldEdits = {}
        for name, (label, minimum, maximum) in STEP_FIELDS.items():
            self.fieldEdits[name] = sHelper.addLabeledControl(
                label,
                nvdaControls.SelectOnFocusSpinCtrl,
                min=minimum,
                max=maximum,
                initial=getattr(self.initialStep, name),
            )
        buttonHelper = guiHelper.ButtonHelper(wx.HORIZONTAL)
        # Translators: The label of a button to hear the beep which is being edited.
        self.addButton(buttonHelper, _("&Test"), lambda event: sounds.playBeeps((self.step,)))
        sHelper.addItem(buttonHelper)
        self.initialFocus = self.fieldEdits["frequency"]

    @property
    def step(self):
        return BeepStep(**{name: edit.GetValue() for name, edit in self.fieldEdits.items()})


class BeepPatternDialog(Dialog):
    def __init__(self, parent, steps):
        self.steps = list(steps)
        # Translators: The title of the dialog to build a pattern of beeps.
        super().__init__(parent, _("Beeps"))

    def makeContent(self, sHelper):
        self.beepList = sHelper.addLabeledControl(
            # Translators: The label of the list of beeps played as a sound.
            _("&Beeps"),
            wx.ListBox,
            choices=[],
        )
        self.beepList.Bind(wx.EVT_LISTBOX, lambda event: self.updateButtons())
        self.beepList.Bind(wx.EVT_LISTBOX_DCLICK, self.onEdit)
        buttonHelper = guiHelper.ButtonHelper(wx.HORIZONTAL)
        # Translators: The label of a button to add a beep to the pattern.
        self.addButton(buttonHelper, _("&Add..."), self.onAdd)
        # Translators: The label of a button to change the selected beep of the pattern.
        self.editButton = self.addButton(buttonHelper, _("&Edit..."), self.onEdit)
        # Translators: The label of a button to delete the selected beep from the pattern.
        self.removeButton = self.addButton(buttonHelper, _("Re&move"), self.onRemove)
        # Translators: The label of a button to play the selected beep earlier in the pattern.
        self.moveUpButton = self.addButton(buttonHelper, _("Move &up"), lambda event: self.onMove(-1))
        # Translators: The label of a button to play the selected beep later in the pattern.
        self.moveDownButton = self.addButton(buttonHelper, _("Move &down"), lambda event: self.onMove(1))
        # Translators: The label of a button to hear the whole beep pattern.
        self.playButton = self.addButton(
            buttonHelper, _("&Play pattern"), lambda event: sounds.playBeeps(tuple(self.steps))
        )
        sHelper.addItem(buttonHelper)
        self.updateList()
        self.initialFocus = self.beepList

    def validate(self):
        if not self.steps:
            # Translators: Reported when trying to save a beep pattern without beeps.
            self.showError(_("Add at least one beep."))
            return False
        return True

    def updateList(self, selection=0):
        self.beepList.Set([describeStep(step) for step in self.steps])
        if self.steps:
            self.beepList.SetSelection(min(selection, len(self.steps) - 1))
        self.updateButtons()

    def updateButtons(self):
        selection = self.beepList.GetSelection()
        hasSelection = selection != wx.NOT_FOUND
        self.editButton.Enable(hasSelection)
        self.removeButton.Enable(hasSelection)
        self.moveUpButton.Enable(hasSelection and selection > 0)
        self.moveDownButton.Enable(hasSelection and selection < len(self.steps) - 1)
        self.playButton.Enable(bool(self.steps))

    def editStep(self, step):
        with BeepStepDialog(self, step) as dialog:
            return dialog.step if dialog.ShowModal() == wx.ID_OK else None

    def onAdd(self, event):
        step = self.editStep(self.steps[-1] if self.steps else BeepStep())
        if step is not None:
            self.steps.append(step)
            self.updateList(len(self.steps) - 1)
        self.beepList.SetFocus()

    def onEdit(self, event):
        selection = self.beepList.GetSelection()
        if selection == wx.NOT_FOUND:
            return
        step = self.editStep(self.steps[selection])
        if step is not None:
            self.steps[selection] = step
            self.updateList(selection)
        self.beepList.SetFocus()

    def onRemove(self, event):
        selection = self.beepList.GetSelection()
        if selection == wx.NOT_FOUND:
            return
        del self.steps[selection]
        self.updateList(selection)
        self.beepList.SetFocus()

    def onMove(self, offset):
        selection = self.beepList.GetSelection()
        target = selection + offset
        if selection == wx.NOT_FOUND or not 0 <= target < len(self.steps):
            return
        self.steps[selection], self.steps[target] = self.steps[target], self.steps[selection]
        self.updateList(target)
        self.beepList.SetFocus()
