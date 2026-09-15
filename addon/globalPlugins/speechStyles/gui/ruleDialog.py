# Copyright (C) 2026 Beka Gozalishvili <beqaprogger@gmail.com>
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

import dataclasses

import addonHandler
import wx
from gui import guiHelper

from .dialogs import Dialog
from .profileControls import ProfileControls
from .soundControls import SoundControls

addonHandler.initTranslation()

Problem = tuple[str, wx.Window | None]


class RuleDialog(Dialog):
    def __init__(self, parent, rule, store, speakPreview, title):
        self.rule = rule
        self.store = store
        self.speakPreview = speakPreview
        super().__init__(parent, title)

    def makeRuleContent(self, sHelper: guiHelper.BoxSizerHelper):
        raise NotImplementedError

    def showRule(self, rule):
        raise NotImplementedError

    def buildRule(self):
        raise NotImplementedError

    def makeExtraContent(self, sHelper: guiHelper.BoxSizerHelper):
        pass

    def updateEnabled(self):
        pass

    def ruleProblem(self, rule):
        return None

    def noEffectMessage(self):
        # Translators: Reported when a rule would change nothing about the speech.
        return _("Change at least one speech setting, or choose a sound.")

    def previewSample(self):
        return ""

    def makeContent(self, sHelper):
        self.makeRuleContent(sHelper)
        # Translators: The label of the group of settings choosing how something is spoken.
        self.profileControls = ProfileControls(self.content, sHelper, _("Speech"))
        self.soundControls = SoundControls(self.content, sHelper, self.store)
        self.makeExtraContent(sHelper)
        buttonHelper = guiHelper.ButtonHelper(wx.HORIZONTAL)
        # Translators: The label of a button to hear a sample of what a rule does.
        self.addButton(buttonHelper, _("&Test"), self._onTest)
        sHelper.addItem(buttonHelper)
        self._showRule(self.rule)

    def _showRule(self, rule):
        self.showRule(rule)
        self.profileControls.setProfile(rule.profile)
        self.soundControls.setSound(rule.sound)
        self.updateEnabled()

    def getRule(self):
        return dataclasses.replace(
            self.buildRule(),
            profile=self.profileControls.getProfile(),
            sound=self.soundControls.getSound(),
        )

    def validate(self):
        rule = self.getRule()
        problem = self.ruleProblem(rule)
        if problem is not None:
            self.showError(*problem)
            return False
        if not self.soundControls.validate():
            return False
        if not rule.hasEffect:
            self.showError(self.noEffectMessage())
            return False
        return True

    def _onTest(self, event):
        if self.validate():
            self.speakPreview(self.getRule(), self.previewSample())
