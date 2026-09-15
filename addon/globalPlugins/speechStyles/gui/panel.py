# Copyright (C) 2026 Beka Gozalishvili <beqaprogger@gmail.com>
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

import dataclasses
from collections.abc import Callable
from typing import NamedTuple

import addonHandler
import config
import wx
from gui import guiHelper
from gui.settingsDialogs import SettingsPanel
from logHandler import log

from ..donate import requestDonations
from ..model import RulesDocument, TextCategory
from ..storage import CONFIG_SECTION
from .elementRuleDialog import ElementRuleDialog
from .labels import describeElementRule, describePatternRule, describeTextRule
from .patternRuleDialog import PatternRuleDialog
from .ruleList import RuleList
from .textRuleDialog import TextRuleDialog
from .transfer import exportRules, importRules

addonHandler.initTranslation()


def addonSummary():
    try:
        return addonHandler.getCodeAddon().manifest["summary"]
    except Exception:  # noqa: BLE001 - the name is cosmetic; never fail the dialog over it
        log.debugWarning("Could not read the add-on summary", exc_info=True)
        return SpeechStylesPanel.title


class Tab(NamedTuple):
    title: str
    switch: str
    switchLabel: str
    listLabel: str
    describe: Callable[[object], str]
    rulesOf: Callable[[RulesDocument], tuple]
    field: str
    editor: Callable[["SpeechStylesPanel", object], object]
    option: tuple[str, str] | None = None


def tabs():
    return (
        Tab(
            # Translators: The label of the tab holding the role and state rules.
            title=_("Roles and states"),
            switch="elementRules",
            # Translators: The label of a check box to turn role and state rules on or off.
            switchLabel=_("Customize &roles and states"),
            # Translators: The label of the list of role and state rules.
            listLabel=_("Ru&les"),
            describe=describeElementRule,
            rulesOf=lambda document: document.elementRules,
            field="elementRules",
            editor=lambda panel, rule: ElementRuleDialog(panel, rule, panel.store, panel.speakPreview),
        ),
        Tab(
            # Translators: The label of the tab holding the rules for text in quotes and brackets.
            title=_("Enclosed text"),
            switch="enclosedText",
            # Translators: The label of a check box to turn customization of enclosed text on or off.
            switchLabel=_("Customize enclosed te&xt"),
            # Translators: The label of the list of delimiters such as quotes and brackets.
            listLabel=_("Delimiter&s"),
            describe=describeTextRule,
            rulesOf=lambda document: document.textRulesOf(TextCategory.ENCLOSED),
            field="textRules",
            editor=lambda panel, rule: TextRuleDialog(
                panel, rule, TextCategory.ENCLOSED, panel.store, panel.speakPreview
            ),
            option=(
                "allowNesting",
                # Translators: The label of a check box to customize enclosed text inside enclosed text.
                _("Customize &nested enclosed text"),
            ),
        ),
        Tab(
            # Translators: The label of the tab holding the rules for comments in source code.
            title=_("Comments"),
            switch="comments",
            # Translators: The label of a check box to turn customization of comments on or off.
            switchLabel=_("Customize c&omments"),
            # Translators: The label of the list of comment types.
            listLabel=_("Comment t&ypes"),
            describe=describeTextRule,
            rulesOf=lambda document: document.textRulesOf(TextCategory.COMMENT),
            field="textRules",
            editor=lambda panel, rule: TextRuleDialog(
                panel, rule, TextCategory.COMMENT, panel.store, panel.speakPreview
            ),
            option=(
                "enclosedInComments",
                # Translators: The label of a check box to customize quotes and brackets inside comments.
                _("&Customize enclosed text inside comments"),
            ),
        ),
        Tab(
            # Translators: The label of the tab holding the rules for text matching a pattern.
            title=_("Advanced"),
            switch="patterns",
            # Translators: The label of a check box to turn the rules for text patterns on or off.
            switchLabel=_("Customize text pa&tterns"),
            # Translators: The label of the list of text patterns, such as emoji or a word.
            listLabel=_("Patterns"),
            describe=describePatternRule,
            rulesOf=lambda document: document.patternRules,
            field="patternRules",
            editor=lambda panel, rule: PatternRuleDialog(panel, rule, panel.store, panel.speakPreview),
        ),
    )


class SpeechStylesPanel(SettingsPanel):
    # Translators: The title of this add-on's category in NVDA's Settings dialog.
    title = _("Speech Styles")

    plugin = None

    def makeSettings(self, settingsSizer):
        sHelper = guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
        self.enabledCheckBox = sHelper.addItem(
            wx.CheckBox(
                self,
                # Translators: The label of a check box to turn the whole add-on on or off.
                label=_("&Enable Speech Styles"),
            )
        )
        self.enabledCheckBox.Bind(wx.EVT_CHECKBOX, lambda event: self._updateEnabled())

        self.notebook = sHelper.addItem(wx.Notebook(self), flag=wx.EXPAND, proportion=1)
        self.switches = {}
        self.options = {}
        self.lists = {}
        for tab in tabs():
            self._makeTab(tab)

        buttonHelper = guiHelper.ButtonHelper(wx.HORIZONTAL)
        for label, handler in (
            # Translators: The label of a button to save all rules to a file.
            (_("Sa&ve rules to a file..."), self._onExport),
            # Translators: The label of a button to load rules from a file saved earlier.
            (_("Load rules &from a file..."), self._onImport),
            # Translators: The label of a button to support the author of the add-on with a donation.
            (_("Su&pport the author..."), self._onSupportAuthor),
        ):
            button = buttonHelper.addButton(self, label=label)
            button.Bind(wx.EVT_BUTTON, handler)
        sHelper.addItem(buttonHelper)

        self._showDocument(self.plugin.document if self.plugin is not None else RulesDocument())
        self._showSwitches()

    def _makeTab(self, tab):
        window = wx.Panel(self.notebook)
        sizer = wx.BoxSizer(wx.VERTICAL)
        helper = guiHelper.BoxSizerHelper(window, sizer=sizer)
        window.SetSizer(sizer)
        self.notebook.AddPage(window, tab.title)
        self.switches[tab.switch] = self._checkBox(window, helper, tab.switchLabel)
        if tab.option is not None:
            name, label = tab.option
            self.options[name] = (self._checkBox(window, helper, label), tab.switch)
        self.lists[tab.switch] = RuleList(
            window,
            helper,
            tab.listLabel,
            tab.describe,
            lambda rule, tab=tab: self._editRule(rule, tab),
        )

    def _checkBox(self, window, helper, label):
        checkBox = helper.addItem(wx.CheckBox(window, label=label))
        checkBox.Bind(wx.EVT_CHECKBOX, lambda event: self._updateEnabled())
        return checkBox

    def _showDocument(self, document):
        for tab in tabs():
            self.lists[tab.switch].setRules(tab.rulesOf(document))

    def currentDocument(self):
        document = self.plugin.document if self.plugin is not None else RulesDocument()
        rules = {}
        for tab in tabs():
            rules[tab.field] = rules.get(tab.field, ()) + self.lists[tab.switch].getRules()
        return dataclasses.replace(document, **rules)

    def _showSwitches(self):
        section = config.conf[CONFIG_SECTION]
        self.enabledCheckBox.SetValue(section["enabled"])
        for name, checkBox in self.switches.items():
            checkBox.SetValue(section[name])
        for name, (checkBox, _switch) in self.options.items():
            checkBox.SetValue(section[name])
        self._updateEnabled()

    def _updateEnabled(self):
        enabled = self.enabledCheckBox.GetValue()
        for name, checkBox in self.switches.items():
            checkBox.Enable(enabled)
            self.lists[name].enable(enabled and checkBox.GetValue())
        for checkBox, switch in self.options.values():
            checkBox.Enable(enabled and self.switches[switch].GetValue())

    @property
    def store(self):
        return self.plugin.store if self.plugin is not None else None

    def _editRule(self, rule, tab):
        with tab.editor(self, rule) as dialog:
            return dialog.getRule() if dialog.ShowModal() == wx.ID_OK else None

    def speakPreview(self, rule, sample=""):
        if self.plugin is not None:
            self.plugin.speakPreview(rule, sample)

    def _onExport(self, event):
        if self.store is not None:
            exportRules(self, self.store, self.currentDocument())

    def _onImport(self, event):
        if self.store is None:
            return
        document = importRules(self, self.store, self.currentDocument())
        if document is not None:
            self._showDocument(document)

    def _onSupportAuthor(self, event):
        requestDonations(addonSummary(), self)

    def onSave(self):
        section = config.conf[CONFIG_SECTION]
        section["enabled"] = self.enabledCheckBox.GetValue()
        for name, checkBox in self.switches.items():
            section[name] = checkBox.GetValue()
        for name, (checkBox, _switch) in self.options.items():
            section[name] = checkBox.GetValue()
        if self.plugin is not None:
            self.plugin.setDocument(self.currentDocument())
