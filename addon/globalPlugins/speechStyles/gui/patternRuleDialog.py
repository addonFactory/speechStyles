# Copyright (C) 2026 Beka Gozalishvili <beqaprogger@gmail.com>
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

import dataclasses

import addonHandler
import wx

from .. import patterns
from ..model import PatternKind, PatternRule, SoundPosition
from .labels import (
    PATTERN_KIND_LABELS,
    PATTERN_KINDS,
    SOUND_POSITION_LABELS,
    SOUND_POSITIONS,
    patternRuleMatch,
    ruleName,
)
from .ruleDialog import RuleDialog

addonHandler.initTranslation()

EMOJI_SAMPLE = "Hello \U0001f600 world"


class PatternRuleDialog(RuleDialog):
    def __init__(self, parent, rule, store, speakPreview):
        title = (
            # Translators: The title of the dialog to change a pattern rule.
            _("Edit pattern")
            if rule is not None
            # Translators: The title of the dialog to add a pattern rule.
            else _("Add pattern")
        )
        super().__init__(parent, rule if rule is not None else PatternRule(), store, speakPreview, title)

    def makeRuleContent(self, sHelper):
        self.nameText = sHelper.addLabeledControl(
            # Translators: The label of the field holding the name of a rule, shown in the list.
            _("&Name"),
            wx.TextCtrl,
        )
        self.kindChoice = sHelper.addLabeledControl(
            # Translators: The label of the choice of how a pattern rule matches text.
            _("&Search for"),
            wx.Choice,
            choices=[PATTERN_KIND_LABELS[kind] for kind in PATTERN_KINDS],
        )
        self.kindChoice.Bind(wx.EVT_CHOICE, lambda event: self._onKindChange())
        self.patternText = sHelper.addLabeledControl(
            # Translators: The label of the field holding the text or expression which is matched.
            _("&Pattern"),
            wx.TextCtrl,
        )
        self.caseCheckBox = sHelper.addItem(
            wx.CheckBox(
                self.content,
                # Translators: The label of a check box to match capital and small letters exactly.
                label=_("Match &upper and lower case exactly"),
            )
        )
        self.hideCheckBox = sHelper.addItem(
            wx.CheckBox(
                self.content,
                # Translators: The label of a check box to leave the matched text unspoken.
                label=_("Skip the matched te&xt"),
            )
        )
        self.positionChoice = sHelper.addLabeledControl(
            # Translators: The label of the choice of when the sound of a rule is played.
            _("P&lay the sound"),
            wx.Choice,
            choices=[SOUND_POSITION_LABELS[position] for position in SOUND_POSITIONS],
        )
        self.initialFocus = self.nameText

    def makeExtraContent(self, sHelper):
        self.sampleText = sHelper.addLabeledControl(
            # Translators: The label of the field holding the text the Test button speaks.
            _("Sample text to tr&y"),
            wx.TextCtrl,
        )

    def showRule(self, rule):
        self.nameText.SetValue(rule.name)
        self.kindChoice.SetSelection(PATTERN_KINDS.index(rule.kind))
        self.patternText.SetValue(rule.pattern)
        self.caseCheckBox.SetValue(rule.caseSensitive)
        self.hideCheckBox.SetValue(rule.hideText)
        self.positionChoice.SetSelection(SOUND_POSITIONS.index(rule.soundPosition))
        self.sampleText.SetValue(self._sample(rule))

    @staticmethod
    def _sample(rule):
        if rule.kind == PatternKind.EMOJI:
            return EMOJI_SAMPLE
        if rule.kind in (PatternKind.TEXT, PatternKind.WORD) and rule.pattern:
            # Translators: The sample the Test button speaks. {text} is what the rule matches.
            return _("text before {text} text after").format(text=rule.pattern)
        return ""

    def _kind(self):
        selection = self.kindChoice.GetSelection()
        return PATTERN_KINDS[selection] if selection != wx.NOT_FOUND else PatternKind.TEXT

    def buildRule(self):
        selection = self.positionChoice.GetSelection()
        rule = dataclasses.replace(
            self.rule,
            name=self.nameText.GetValue().strip(),
            kind=self._kind(),
            pattern=self.patternText.GetValue(),
            caseSensitive=self.caseCheckBox.GetValue(),
            hideText=self.hideCheckBox.GetValue(),
            soundPosition=SOUND_POSITIONS[selection] if selection != wx.NOT_FOUND else SoundPosition.START,
        )
        return dataclasses.replace(rule, name=ruleName(rule, patternRuleMatch(rule)))

    def _onKindChange(self):
        self.updateEnabled()
        if not self.sampleText.GetValue().strip():
            self.sampleText.SetValue(self._sample(self.getRule()))

    def updateEnabled(self):
        needsPattern = self._kind() != PatternKind.EMOJI
        self.patternText.Enable(needsPattern)
        self.caseCheckBox.Enable(needsPattern)
        self.profileControls.enable(not self.hideCheckBox.GetValue())

    def ruleProblem(self, rule):
        if rule.needsPattern and not rule.pattern:
            # Translators: Reported when saving a pattern rule without the text it matches.
            return _("Type the text or the expression to search for."), self.patternText
        error = patterns.patternError(rule)
        if error:
            return (
                # Translators: Reported when a regular expression cannot be used. {reason} is why.
                _("This regular expression cannot be used: {reason}").format(reason=error),
                self.patternText,
            )
        return None

    def noEffectMessage(self):
        # Translators: Reported when a pattern rule would change nothing about the speech.
        return _("Change at least one speech setting, choose a sound, or skip the matched text.")

    def previewSample(self):
        return self.sampleText.GetValue()

    def _onTest(self, event):
        if not self.validate():
            return
        sample = self.sampleText.GetValue()
        if not sample.strip():
            # Translators: Reported when the Test button is pressed without a sample to speak.
            self.showError(_("Type the text to try the pattern on."), self.sampleText)
            return
        expression = patterns.compiled(self.getRule())
        if expression is not None and not expression.search(sample):
            # Translators: Reported when the sample of the Test button has nothing the rule matches.
            self.showError(_("The pattern matches nothing in this text."), self.sampleText)
            return
        super()._onTest(event)
