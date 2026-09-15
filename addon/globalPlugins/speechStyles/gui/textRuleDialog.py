# Copyright (C) 2026 Beka Gozalishvili <beqaprogger@gmail.com>
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

import dataclasses

import addonHandler
import wx
from gui import guiHelper

from ..model import DelimiterSpeech, SoundPosition, TextCategory, TextKind, TextRule
from .labels import (
    DELIMITER_SPEECH_LABELS,
    DELIMITER_SPEECHES,
    SOUND_POSITION_LABELS,
    SOUND_POSITIONS,
    TEXT_KIND_LABELS,
    TEXT_KINDS,
    categoryTitle,
    ruleName,
    textRuleMatch,
)
from .ruleDialog import RuleDialog

addonHandler.initTranslation()


class TextRuleDialog(RuleDialog):
    def __init__(self, parent, rule, category, store, speakPreview):
        self.category = category
        super().__init__(
            parent,
            rule if rule is not None else TextRule(category=category),
            store,
            speakPreview,
            categoryTitle(category, editing=rule is not None),
        )

    @property
    def isComment(self):
        return self.category == TextCategory.COMMENT

    def makeRuleContent(self, sHelper):
        self.nameText = sHelper.addLabeledControl(
            # Translators: The label of the field holding the name of a rule, shown in the list.
            _("&Name"),
            wx.TextCtrl,
        )
        if self.isComment:
            self.kindChoice = sHelper.addLabeledControl(
                # Translators: The label of the choice of what kind of comment a rule is for.
                _("Comment st&yle"),
                wx.Choice,
                choices=[TEXT_KIND_LABELS[kind] for kind in TEXT_KINDS],
            )
            self.kindChoice.Bind(wx.EVT_CHOICE, lambda event: self.updateEnabled())
        self.startText = sHelper.addLabeledControl(
            # Translators: The label of the field holding the text a rule starts at, such as ( or //.
            _("&Start delimiter"),
            wx.TextCtrl,
        )
        self.endText = sHelper.addLabeledControl(
            # Translators: The label of the field holding the text a rule ends at, such as ) or */.
            _("End de&limiter"),
            wx.TextCtrl,
        )

        # Translators: The label of the group of settings choosing where a rule matches.
        matchSizer = wx.StaticBoxSizer(wx.VERTICAL, self.content, label=_("Where it matches"))
        matchBox = matchSizer.GetStaticBox()
        match = guiHelper.BoxSizerHelper(self.content, sizer=matchSizer)
        sHelper.addItem(match)
        self.boundaryCheckBox = match.addItem(wx.CheckBox(matchBox, label=self._boundaryLabel(TextKind.PAIR)))
        self.lineStartCheckBox = match.addItem(
            wx.CheckBox(
                matchBox,
                # Translators: The label of a check box to match a comment only at the start of a line.
                label=_("Only at the start of a l&ine"),
            )
        )
        self.unclosedCheckBox = match.addItem(
            wx.CheckBox(
                matchBox,
                # Translators: The label of a check box to customize the rest of the text when the
                # closing delimiter is missing.
                label=_("&Customize to the end when the closing delimiter is missing"),
            )
        )

        self.delimiterChoice = sHelper.addLabeledControl(
            # Translators: The label of the choice of how the delimiters themselves are spoken.
            _("S&peak the delimiters"),
            wx.Choice,
            choices=[DELIMITER_SPEECH_LABELS[speech] for speech in DELIMITER_SPEECHES],
        )
        self.positionChoice = sHelper.addLabeledControl(
            # Translators: The label of the choice of when the sound of a rule is played.
            _("Play the so&und"),
            wx.Choice,
            choices=[SOUND_POSITION_LABELS[position] for position in SOUND_POSITIONS],
        )
        self.initialFocus = self.nameText

    @staticmethod
    def _boundaryLabel(kind):
        if kind == TextKind.LINE:
            # Translators: The label of a check box: a line comment must follow a space or start a line.
            return _("Must &be preceded by a space or the start of the line")
        # Translators: The label of a check box: the delimiters must not be inside a word.
        return _("Only match at word &boundaries")

    def showRule(self, rule):
        self.nameText.SetValue(rule.name)
        if self.isComment:
            self.kindChoice.SetSelection(TEXT_KINDS.index(rule.kind))
        self.startText.SetValue(rule.start)
        self.endText.SetValue(rule.end)
        self.boundaryCheckBox.SetValue(rule.requireBoundary)
        self.lineStartCheckBox.SetValue(rule.lineStartOnly)
        self.unclosedCheckBox.SetValue(rule.allowUnclosed)
        self.delimiterChoice.SetSelection(DELIMITER_SPEECHES.index(rule.delimiters))
        self.positionChoice.SetSelection(SOUND_POSITIONS.index(rule.soundPosition))

    def _kind(self):
        if not self.isComment:
            return TextKind.PAIR
        selection = self.kindChoice.GetSelection()
        return TEXT_KINDS[selection] if selection != wx.NOT_FOUND else TextKind.PAIR

    def buildRule(self):
        kind = self._kind()
        delimiterSelection = self.delimiterChoice.GetSelection()
        positionSelection = self.positionChoice.GetSelection()
        rule = dataclasses.replace(
            self.rule,
            category=self.category,
            name=self.nameText.GetValue().strip(),
            kind=kind,
            start=self.startText.GetValue(),
            end=self.endText.GetValue() if kind == TextKind.PAIR else "",
            requireBoundary=self.boundaryCheckBox.GetValue(),
            lineStartOnly=kind == TextKind.LINE and self.lineStartCheckBox.GetValue(),
            allowUnclosed=kind == TextKind.PAIR and self.unclosedCheckBox.GetValue(),
            delimiters=DELIMITER_SPEECHES[delimiterSelection]
            if delimiterSelection != wx.NOT_FOUND
            else DelimiterSpeech.CUSTOMIZED,
            soundPosition=SOUND_POSITIONS[positionSelection]
            if positionSelection != wx.NOT_FOUND
            else SoundPosition.START,
        )
        return dataclasses.replace(rule, name=ruleName(rule, textRuleMatch(rule)))

    def updateEnabled(self):
        isLine = self._kind() == TextKind.LINE
        self.boundaryCheckBox.SetLabel(self._boundaryLabel(self._kind()))
        self.endText.Enable(not isLine)
        self.lineStartCheckBox.Enable(isLine)
        self.unclosedCheckBox.Enable(not isLine)

    def ruleProblem(self, rule):
        if not rule.start:
            # Translators: Reported when saving a rule without the text it starts at.
            return _("Type the text the rule starts at, such as ( or //."), self.startText
        if rule.kind == TextKind.PAIR and not rule.end:
            # Translators: Reported when saving a rule without the text it ends at.
            return _("Type the text the rule ends at, such as ) or */."), self.endText
        return None

    def noEffectMessage(self):
        # Translators: Reported when a rule would change nothing about how the text is spoken.
        return _("Change at least one speech setting, choose a sound, or hide the delimiters.")
