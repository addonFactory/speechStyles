# Copyright (C) 2026 Beka Gozalishvili <beqaprogger@gmail.com>
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

import dataclasses

import addonHandler
import wx
from gui import guiHelper, nvdaControls

from ..model import ElementRule, RuleTarget, Scope, TargetType
from .labels import (
    CONTEXT_LABELS,
    CONTEXTS,
    ELEMENT_PART_LABELS,
    ELEMENT_PARTS,
    SCOPE_LABELS,
    SCOPES,
    TARGET_TYPE_LABELS,
    TARGET_TYPES,
    targetChoices,
)
from .ruleDialog import RuleDialog

addonHandler.initTranslation()


class ElementRuleDialog(RuleDialog):
    def __init__(self, parent, rule, store, speakPreview):
        self._targetValues = []
        title = (
            # Translators: The title of the dialog to change a role or state rule.
            _("Edit rule")
            if rule is not None
            # Translators: The title of the dialog to add a role or state rule.
            else _("Add rule")
        )
        super().__init__(parent, rule if rule is not None else ElementRule(), store, speakPreview, title)

    def makeRuleContent(self, sHelper):
        self.typeChoice = sHelper.addLabeledControl(
            # Translators: The label of the choice of what kind of thing a rule applies to.
            _("App&lies to"),
            wx.Choice,
            choices=[TARGET_TYPE_LABELS[targetType] for targetType in TARGET_TYPES],
        )
        self.typeChoice.Bind(wx.EVT_CHOICE, lambda event: self._onTypeChange())
        self.valueChoice = sHelper.addLabeledControl(
            # Translators: The label of the choice of the role or state a rule applies to.
            _("&Role or state"),
            wx.Choice,
            choices=[],
        )

        # Translators: The label of the group of settings choosing what a rule does.
        actionsSizer = wx.StaticBoxSizer(wx.VERTICAL, self.content, label=_("What the rule does"))
        actionsBox = actionsSizer.GetStaticBox()
        actions = guiHelper.BoxSizerHelper(self.content, sizer=actionsSizer)
        sHelper.addItem(actions)
        self.hideCheckBox = actions.addItem(
            wx.CheckBox(
                actionsBox,
                # Translators: The label of a check box to stop speaking a role or state word.
                label=_("Do&n't speak the label"),
            )
        )
        self.hideCheckBox.Bind(wx.EVT_CHECKBOX, lambda event: self.updateEnabled())
        self.customizeCheckBox = actions.addItem(
            wx.CheckBox(
                actionsBox,
                # Translators: The label of a check box to speak something with customized speech settings.
                label=_("&Customize speech"),
            )
        )
        self.customizeCheckBox.Bind(wx.EVT_CHECKBOX, lambda event: self.updateEnabled())
        self.scopeChoice = actions.addLabeledControl(
            # Translators: The label of the choice of what customized speech applies to.
            _("C&ustomize"),
            wx.Choice,
            choices=[SCOPE_LABELS[scope] for scope in SCOPES],
        )
        self.scopeChoice.Bind(wx.EVT_CHOICE, lambda event: self.updateEnabled())
        self.partsList = actions.addLabeledControl(
            # Translators: The label of the list of the parts of an element which are customized.
            _("&Parts of the element"),
            nvdaControls.CustomCheckListBox,
            choices=[ELEMENT_PART_LABELS[part] for part in ELEMENT_PARTS],
        )
        self.soundCheckBox = actions.addItem(
            wx.CheckBox(
                actionsBox,
                # Translators: The label of a check box to play a sound for a role or state.
                label=_("Play a &sound"),
            )
        )
        self.soundCheckBox.Bind(wx.EVT_CHECKBOX, lambda event: self.updateEnabled())
        self.exitCheckBox = actions.addItem(
            wx.CheckBox(
                actionsBox,
                # Translators: The label of a check box to apply a rule to messages such as "out of list".
                label=_('Also apply to e&xit messages, such as "out of list"'),
            )
        )

        self.contextsList = sHelper.addLabeledControl(
            # Translators: The label of the list of the situations in which a rule applies.
            _("Use &in"),
            nvdaControls.CustomCheckListBox,
            choices=[CONTEXT_LABELS[context] for context in CONTEXTS],
        )

        self.initialFocus = self.typeChoice

    def showRule(self, rule):
        self.typeChoice.SetSelection(TARGET_TYPES.index(rule.target.type))
        self._fillValues(rule.target)
        self.hideCheckBox.SetValue(rule.hideLabel)
        self.customizeCheckBox.SetValue(rule.customizeSpeech)
        self.scopeChoice.SetSelection(SCOPES.index(rule.scope))
        for index, part in enumerate(ELEMENT_PARTS):
            self.partsList.Check(index, part in rule.elementParts)
        self.soundCheckBox.SetValue(rule.playSound)
        self.exitCheckBox.SetValue(rule.applyToExit)
        for index, context in enumerate(CONTEXTS):
            self.contextsList.Check(index, context in rule.contexts)

    def _fillValues(self, target):
        choices = targetChoices(target.type)
        self._targetValues = [value for value, _label in choices]
        labels = [label for _value, label in choices]
        if target.value and target.value not in self._targetValues:
            self._targetValues.append(target.value)
            # Translators: A role or state of a rule which this version of NVDA doesn't know.
            labels.append(_("{name} (unknown)").format(name=target.value))
        self.valueChoice.Set(labels)
        if target.value in self._targetValues:
            self.valueChoice.SetSelection(self._targetValues.index(target.value))
        elif self._targetValues:
            self.valueChoice.SetSelection(0)

    def _targetType(self):
        selection = self.typeChoice.GetSelection()
        return TARGET_TYPES[selection] if selection != wx.NOT_FOUND else TargetType.ROLE

    def _target(self):
        selection = self.valueChoice.GetSelection()
        value = self._targetValues[selection] if selection != wx.NOT_FOUND else ""
        return RuleTarget(self._targetType(), value)

    def _checkedItems(self, listBox, values):
        return frozenset(value for index, value in enumerate(values) if listBox.IsChecked(index))

    def buildRule(self):
        scopeSelection = self.scopeChoice.GetSelection()
        return dataclasses.replace(
            self.rule,
            target=self._target(),
            contexts=self._checkedItems(self.contextsList, CONTEXTS),
            hideLabel=self.hideCheckBox.GetValue(),
            customizeSpeech=self.customizeCheckBox.GetValue(),
            scope=SCOPES[scopeSelection] if scopeSelection != wx.NOT_FOUND else Scope.LABEL,
            elementParts=self._checkedItems(self.partsList, ELEMENT_PARTS),
            playSound=self.soundCheckBox.GetValue(),
            applyToExit=self.exitCheckBox.GetValue(),
        )

    def _onTypeChange(self):
        self._fillValues(RuleTarget(self._targetType(), ""))
        self.updateEnabled()

    def updateEnabled(self):
        customizes = self.customizeCheckBox.GetValue()
        playsSound = self.soundCheckBox.GetValue()
        scopeSelection = self.scopeChoice.GetSelection()
        scope = SCOPES[scopeSelection] if scopeSelection != wx.NOT_FOUND else Scope.LABEL
        self.scopeChoice.Enable(customizes)
        self.partsList.Enable(customizes and scope != Scope.LABEL)
        self.profileControls.enable(customizes)
        self.soundControls.enable(playsSound)
        self.exitCheckBox.Enable(self._targetType() == TargetType.ROLE)

    def ruleProblem(self, rule):
        if not rule.target.value:
            # Translators: Reported when saving a rule without choosing a role or state.
            return _("Choose a role or state."), self.valueChoice
        if not (rule.hideLabel or rule.customizeSpeech or rule.playSound):
            # Translators: Reported when saving a rule which does nothing.
            return _("Choose at least one thing the rule should do."), self.hideCheckBox
        if rule.customizeSpeech and rule.profile.isEmpty:
            # Translators: Reported when a rule customizes speech without changing any setting.
            return _("Change at least one speech setting, or clear the customize speech check box."), None
        if rule.customizeSpeech and rule.scope != Scope.LABEL and not rule.elementParts:
            # Translators: Reported when a rule customizes an element but no part of it is chosen.
            return _("Choose at least one part of the element."), self.partsList
        if not rule.contexts:
            # Translators: Reported when saving a rule which applies in no situation.
            return _("Choose at least one situation to use the rule in."), self.contextsList
        return None
