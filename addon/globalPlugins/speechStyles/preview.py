# Copyright (C) 2026 Beka Gozalishvili <beqaprogger@gmail.com>
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

import dataclasses

import addonHandler

from .markers import ScopeEnd, ScopeStart, TaggedText
from .model import ElementPart, ElementRule, PatternRule, RulesDocument, Scope, TextKind
from .ruleSet import Flags, RuleSet
from .targets import targetValueLabel

addonHandler.initTranslation()


def elementRuleSequence(rule):
    target = (rule.target.type, rule.target.value)
    label = TaggedText(targetValueLabel(rule.target), ElementPart.ROLE, target)
    element = [
        # Translators: The name of the element in the sample spoken by the Test button of a rule.
        TaggedText(_("Sample"), ElementPart.NAME),
        label,
    ]
    if rule.scope == Scope.CONTENT:
        # Translators: The content of the element in the sample spoken by the Test button of a rule.
        element.append(_("its text content"))
    if rule.scope != Scope.LABEL:
        element = [ScopeStart(rule.id), *element, ScopeEnd(rule.id)]
    return [
        # Translators: Spoken before the sample of the Test button of a rule.
        _("Before"),
        *element,
        # Translators: Spoken after the sample of the Test button of a rule.
        _("after"),
    ]


def textRuleSequence(rule):
    # Translators: The text inside the delimiters in the sample spoken by the Test button of a rule.
    inside = _("text inside")
    if rule.kind == TextKind.LINE:
        # Translators: A sample of a line comment. {start} is the comment marker, e.g. "//".
        return [_("code before {start} {inside}").format(start=rule.start, inside=inside)]
    # Translators: A sample of enclosed text. {start} and {end} are the delimiters, e.g. "(" and ")".
    return [
        _("text before {start}{inside}{end} text after").format(start=rule.start, inside=inside, end=rule.end)
    ]


def patternRuleSequence(rule, sample):
    return [sample]


def previewRuleSet(rule):
    flags = Flags(enabled=True, elementRules=True, enclosedText=True, comments=True, patterns=True)
    rule = dataclasses.replace(rule, enabled=True)
    if isinstance(rule, ElementRule):
        return RuleSet(RulesDocument(elementRules=(rule,)), flags)
    if isinstance(rule, PatternRule):
        return RuleSet(RulesDocument(patternRules=(rule,)), flags)
    return RuleSet(RulesDocument(textRules=(rule,)), flags)


def sequenceFor(rule, sample=""):
    if isinstance(rule, ElementRule):
        return elementRuleSequence(rule)
    if isinstance(rule, PatternRule):
        return patternRuleSequence(rule, sample)
    return textRuleSequence(rule)
