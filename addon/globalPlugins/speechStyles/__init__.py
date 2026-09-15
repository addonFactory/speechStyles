# Copyright (C) 2026 Beka Gozalishvili <beqaprogger@gmail.com>
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

import os
from contextlib import suppress

import addonHandler
import config
import globalPluginHandler
import globalVars
import gui
import ui
import wx
from gui.settingsDialogs import NVDASettingsDialog
from logHandler import log
from scriptHandler import script

from . import preview, sounds
from .gui.panel import SpeechStylesPanel
from .hooks import SpeechHooks
from .ruleSet import EMPTY_RULE_SET, Flags, RuleSet
from .storage import CONFIG_SECTION, CONFIG_SPEC, RulesStore
from .voiceController import VoiceController

addonHandler.initTranslation()

config.conf.spec[CONFIG_SECTION] = CONFIG_SPEC


def readFlags():
    section = config.conf[CONFIG_SECTION]
    return Flags(**{name: section[name] for name in CONFIG_SPEC})


# Translators: The name of this add-on's category in NVDA's Input Gestures dialog.
SCRIPT_CATEGORY = _("Speech Styles")

SWITCH_NAMES = {
    # Translators: Reported when the whole add-on is turned on or off.
    "enabled": _("Speech Styles"),
    # Translators: Reported when role and state rules are turned on or off.
    "elementRules": _("Roles and states"),
    # Translators: Reported when customization of enclosed text is turned on or off.
    "enclosedText": _("Enclosed text"),
    # Translators: Reported when customization of comments is turned on or off.
    "comments": _("Comments"),
}


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    def __init__(self):
        super().__init__()
        self.ruleSet = EMPTY_RULE_SET
        self.store = RulesStore(os.path.join(globalVars.appArgs.configPath, CONFIG_SECTION), _)
        self.document = self.store.load()
        self.rebuildRuleSet()
        sounds.resolveSoundPath = self.store.soundPath
        self.voiceController = VoiceController()
        self.voiceController.register()
        self.hooks = SpeechHooks(lambda: self.ruleSet)
        self.hooks.install()
        config.post_configProfileSwitch.register(self.rebuildRuleSet)
        SpeechStylesPanel.plugin = self
        NVDASettingsDialog.categoryClasses.append(SpeechStylesPanel)

    def terminate(self):
        with suppress(ValueError):
            NVDASettingsDialog.categoryClasses.remove(SpeechStylesPanel)
        SpeechStylesPanel.plugin = None
        config.post_configProfileSwitch.unregister(self.rebuildRuleSet)
        self.hooks.uninstall()
        self.voiceController.unregister()
        super().terminate()

    def rebuildRuleSet(self):
        try:
            self.ruleSet = RuleSet(self.document, readFlags())
        except Exception:
            log.error("Could not build the Speech Styles rules", exc_info=True)
            self.ruleSet = EMPTY_RULE_SET

    def setDocument(self, document):
        try:
            self.store.save(document)
        except OSError:
            log.error("Could not save the Speech Styles rules", exc_info=True)
        self.document = document
        self.rebuildRuleSet()

    def toggle(self, switch):
        section = config.conf[CONFIG_SECTION]
        section[switch] = value = not section[switch]
        self.rebuildRuleSet()
        name = SWITCH_NAMES[switch]
        ui.message(
            # Translators: Reported when a part of the add-on is turned on. {name} is its name.
            _("{name} on").format(name=name)
            if value
            # Translators: Reported when a part of the add-on is turned off. {name} is its name.
            else _("{name} off").format(name=name)
        )

    @script(
        # Translators: The description of a command, shown in NVDA's Input Gestures dialog.
        description=_("Turns Speech Styles on or off"),
        category=SCRIPT_CATEGORY,
    )
    def script_toggleAddon(self, gesture):
        self.toggle("enabled")

    @script(
        # Translators: The description of a command, shown in NVDA's Input Gestures dialog.
        description=_("Turns the rules for roles and states on or off"),
        category=SCRIPT_CATEGORY,
    )
    def script_toggleElementRules(self, gesture):
        self.toggle("elementRules")

    @script(
        # Translators: The description of a command, shown in NVDA's Input Gestures dialog.
        description=_("Turns customization of enclosed text on or off"),
        category=SCRIPT_CATEGORY,
    )
    def script_toggleEnclosedText(self, gesture):
        self.toggle("enclosedText")

    @script(
        # Translators: The description of a command, shown in NVDA's Input Gestures dialog.
        description=_("Turns customization of comments on or off"),
        category=SCRIPT_CATEGORY,
    )
    def script_toggleComments(self, gesture):
        self.toggle("comments")

    @script(
        # Translators: The description of a command, shown in NVDA's Input Gestures dialog.
        description=_("Opens the Speech Styles settings"),
        category=SCRIPT_CATEGORY,
    )
    def script_openSettings(self, gesture):
        wx.CallAfter(gui.mainFrame.popupSettingsDialog, NVDASettingsDialog, SpeechStylesPanel)

    def speakPreview(self, rule, sample=""):
        try:
            self.hooks.speakPreview(preview.sequenceFor(rule, sample), preview.previewRuleSet(rule))
        except Exception:
            log.error("Could not speak the sample", exc_info=True)
