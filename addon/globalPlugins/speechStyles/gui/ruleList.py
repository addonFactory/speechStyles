# Copyright (C) 2026 Beka Gozalishvili <beqaprogger@gmail.com>
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

import dataclasses

import addonHandler
import wx
from gui import guiHelper, nvdaControls

from .dialogs import groupParent

addonHandler.initTranslation()


class RuleList:
    def __init__(self, parent, sHelper, label, describe, editRule):
        self.parent = parent
        self.box = groupParent(parent, sHelper)
        self.describe = describe
        self.editRule = editRule
        self.rules = []
        self._enabled = True
        self.listBox = sHelper.addLabeledControl(label, nvdaControls.CustomCheckListBox, choices=[])
        self.listBox.Bind(wx.EVT_LISTBOX, lambda event: self.updateButtons())
        self.listBox.Bind(wx.EVT_LISTBOX_DCLICK, self.onEdit)
        self.listBox.Bind(wx.EVT_CHECKLISTBOX, self.onCheck)
        buttonHelper = guiHelper.ButtonHelper(wx.HORIZONTAL)
        # Translators: The label of a button to add a rule.
        self._addButton(buttonHelper, _("&Add..."), self.onAdd)
        # Translators: The label of a button to change the selected rule.
        self.editButton = self._addButton(buttonHelper, _("Ed&it..."), self.onEdit)
        # Translators: The label of a button to delete the selected rule.
        self.removeButton = self._addButton(buttonHelper, _("Re&move"), self.onRemove)
        # Translators: The label of a button to apply the selected rule before the previous one.
        self.moveUpButton = self._addButton(buttonHelper, _("Move &up"), lambda event: self.onMove(-1))
        # Translators: The label of a button to apply the selected rule after the next one.
        self.moveDownButton = self._addButton(buttonHelper, _("Move &down"), lambda event: self.onMove(1))
        sHelper.addItem(buttonHelper)

    def _addButton(self, buttonHelper, label, handler):
        button = buttonHelper.addButton(self.box, label=label)
        button.Bind(wx.EVT_BUTTON, handler)
        return button

    def setRules(self, rules):
        self.rules = list(rules)
        self.updateList(0)

    def getRules(self):
        return tuple(self.rules)

    def enable(self, enabled):
        self.listBox.Enable(enabled)
        self._enabled = enabled
        self.updateButtons()

    def updateList(self, selection=0):
        self.listBox.Set([self.describe(rule) for rule in self.rules])
        for index, rule in enumerate(self.rules):
            self.listBox.Check(index, rule.enabled)
        if self.rules:
            self.listBox.SetSelection(min(max(selection, 0), len(self.rules) - 1))
        self.updateButtons()

    def updateButtons(self):
        selection = self.listBox.GetSelection()
        hasSelection = self._enabled and selection != wx.NOT_FOUND
        self.editButton.Enable(hasSelection)
        self.removeButton.Enable(hasSelection)
        self.moveUpButton.Enable(hasSelection and selection > 0)
        self.moveDownButton.Enable(hasSelection and selection < len(self.rules) - 1)

    def onCheck(self, event):
        index = event.GetSelection()
        self.rules[index] = dataclasses.replace(self.rules[index], enabled=self.listBox.IsChecked(index))
        event.Skip()

    def onAdd(self, event):
        rule = self.editRule(None)
        if rule is not None:
            self.rules.append(rule)
            self.updateList(len(self.rules) - 1)
        self.listBox.SetFocus()

    def onEdit(self, event):
        selection = self.listBox.GetSelection()
        if selection == wx.NOT_FOUND or not self._enabled:
            return
        rule = self.editRule(self.rules[selection])
        if rule is not None:
            self.rules[selection] = rule
            self.updateList(selection)
        self.listBox.SetFocus()

    def onRemove(self, event):
        selection = self.listBox.GetSelection()
        if selection == wx.NOT_FOUND:
            return
        del self.rules[selection]
        self.updateList(selection)
        self.listBox.SetFocus()

    def onMove(self, offset):
        selection = self.listBox.GetSelection()
        target = selection + offset
        if selection == wx.NOT_FOUND or not 0 <= target < len(self.rules):
            return
        self.rules[selection], self.rules[target] = self.rules[target], self.rules[selection]
        self.updateList(target)
        self.listBox.SetFocus()
