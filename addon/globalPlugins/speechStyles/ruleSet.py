# Copyright (C) 2026 Beka Gozalishvili <beqaprogger@gmail.com>
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

from dataclasses import dataclass

from .model import RulesDocument, Scope, TargetType, TextCategory


@dataclass(frozen=True)
class Flags:
    enabled: bool = True
    elementRules: bool = True
    enclosedText: bool = False
    comments: bool = False
    patterns: bool = False
    allowNesting: bool = True
    enclosedInComments: bool = False


class RuleSet:
    def __init__(self, document, flags):
        self.flags = flags
        elementRules = ()
        if flags.enabled and flags.elementRules:
            elementRules = tuple(rule for rule in document.elementRules if rule.enabled and rule.hasEffect)
        self.elementRules = elementRules
        byTarget = {}
        for rule in elementRules:
            byTarget.setdefault((rule.target.type, rule.target.value), []).append(rule)
        self._byTarget = {key: tuple(rules) for key, rules in byTarget.items()}
        self._byId = {rule.id: rule for rule in elementRules}
        types = {rule.target.type for rule in elementRules}
        self.hasRoleRules = TargetType.ROLE in types
        self.hasStateRules = bool(types & {TargetType.STATE, TargetType.NEGATIVE_STATE})
        self.hasContentRules = any(
            rule.scope == Scope.CONTENT and rule.customizesSpeech for rule in elementRules
        )

        categories = set()
        if flags.enabled and flags.enclosedText:
            categories.add(TextCategory.ENCLOSED)
        if flags.enabled and flags.comments:
            categories.add(TextCategory.COMMENT)
        self.textRules = tuple(
            rule
            for rule in document.textRules
            if rule.category in categories and rule.enabled and rule.isValid and rule.hasEffect
        )
        patternRules = ()
        if flags.enabled and flags.patterns:
            patternRules = tuple(
                rule for rule in document.patternRules if rule.enabled and rule.isValid and rule.hasEffect
            )
        self.patternRules = patternRules

    @property
    def hasElementRules(self):
        return bool(self.elementRules)

    @property
    def hasTextRules(self):
        return bool(self.textRules)

    @property
    def hasPatternRules(self):
        return bool(self.patternRules)

    @property
    def hasSpanRules(self):
        return bool(self.textRules or self.patternRules)

    @property
    def isEmpty(self):
        return not self.elementRules and not self.textRules and not self.patternRules

    def rulesFor(self, targetType, value):
        return self._byTarget.get((targetType, value), ())

    def ruleById(self, ruleId):
        return self._byId.get(ruleId)


EMPTY_RULE_SET = RuleSet(RulesDocument(), Flags(enabled=False))
