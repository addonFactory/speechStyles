# Copyright (C) 2026 Beka Gozalishvili <beqaprogger@gmail.com>
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

from dataclasses import dataclass

from .model import DelimiterSpeech, TextCategory, TextKind, TextRule

MAX_PASSES = 16

LINE_BREAKS = "\r\n"


@dataclass(frozen=True, slots=True)
class Span:
    rule: object
    start: int
    contentStart: int
    contentEnd: int
    end: int
    delimiters: DelimiterSpeech = DelimiterSpeech.CUSTOMIZED
    hidden: bool = False


@dataclass(slots=True)
class _Open:
    rule: TextRule
    start: int
    contentStart: int


def findSpans(text, rules, allowNesting=True, enclosedInComments=False):
    rules = [rule for rule in rules if rule.isValid]
    if not text or not rules:
        return []
    scanner = _Scanner(text, rules, allowNesting, enclosedInComments)
    spans = []
    for _ in range(MAX_PASSES):
        spans, unmatched = scanner.scan()
        if not unmatched:
            break
        scanner.ignored |= unmatched
    return sorted(spans, key=lambda span: (span.start, -span.end))


def _span(rule, start, contentStart, contentEnd, end):
    return Span(rule, start, contentStart, contentEnd, end, delimiters=rule.delimiters)


def _isWordCharacter(character):
    return character.isalnum() or character == "_"


class _Scanner:
    def __init__(self, text, rules, allowNesting, enclosedInComments):
        self.text = text
        self.openers = sorted(rules, key=lambda rule: len(rule.start), reverse=True)
        self.firstCharacters = frozenset(rule.start[0] for rule in rules)
        self.allowNesting = allowNesting
        self.enclosedInComments = enclosedInComments
        self.ignored = set()

    def scan(self):
        text = self.text
        length = len(text)
        stack = []
        spans = []
        unmatched = set()
        position = 0
        while position < length:
            character = text[position]
            if character in LINE_BREAKS and stack:
                lineIndex = self._innermostLineComment(stack)
                if lineIndex is not None:
                    for entry in stack[lineIndex + 1 :]:
                        self._cutOff(entry, position, spans, unmatched)
                    entry = stack[lineIndex]
                    spans.append(_span(entry.rule, entry.start, entry.contentStart, position, position))
                    del stack[lineIndex:]
                    continue
            if stack and self._closes(stack[-1], position):
                entry = stack.pop()
                end = position + len(entry.rule.end)
                spans.append(_span(entry.rule, entry.start, entry.contentStart, position, end))
                position = end
                continue
            if character in self.firstCharacters:
                rule = self._opener(position, stack)
                if rule is not None:
                    stack.append(_Open(rule, position, position + len(rule.start)))
                    position += len(rule.start)
                    continue
            position += 1
        for entry in stack:
            if entry.rule.kind == TextKind.LINE:
                spans.append(_span(entry.rule, entry.start, entry.contentStart, length, length))
            else:
                self._cutOff(entry, length, spans, unmatched)
        return spans, unmatched

    @staticmethod
    def _innermostLineComment(stack):
        for index in range(len(stack) - 1, -1, -1):
            if stack[index].rule.kind == TextKind.LINE:
                return index
        return None

    @staticmethod
    def _cutOff(entry, position, spans, unmatched: set[tuple[int, str]]):
        if entry.rule.allowUnclosed:
            spans.append(_span(entry.rule, entry.start, entry.contentStart, position, position))
        else:
            unmatched.add((entry.start, entry.rule.id))

    def _closes(self, entry, position):
        rule = entry.rule
        text = self.text
        if rule.kind != TextKind.PAIR or not text.startswith(rule.end, position):
            return False
        if not rule.requireBoundary:
            return True
        after = position + len(rule.end)
        if after < len(text) and _isWordCharacter(text[after]):
            return False
        return not (rule.isSymmetric and position > entry.contentStart and text[position - 1].isspace())

    def _opener(self, position, stack):
        text = self.text
        for rule in self.openers:
            if (
                text.startswith(rule.start, position)
                and (position, rule.id) not in self.ignored
                and self._mayNest(rule, stack)
                and self._opens(rule, position)
            ):
                return rule
        return None

    def _mayNest(self, rule, stack):
        isComment = rule.category == TextCategory.COMMENT
        for entry in stack:
            openRule = entry.rule
            if openRule.category == TextCategory.COMMENT:
                if isComment or not self.enclosedInComments:
                    return False
            elif isComment:
                if openRule.isSymmetric:
                    return False
            elif not self.allowNesting or (rule.isSymmetric and openRule.id == rule.id):
                return False
        return True

    def _opens(self, rule, position):
        text = self.text
        before = text[position - 1] if position > 0 else ""
        if rule.kind == TextKind.LINE:
            if rule.requireBoundary and before and not before.isspace():
                return False
            if rule.lineStartOnly:
                lineStart = max(text.rfind("\n", 0, position), text.rfind("\r", 0, position)) + 1
                if text[lineStart:position].strip():
                    return False
            return True
        if not rule.requireBoundary:
            return True
        if before and _isWordCharacter(before):
            return False
        if rule.isSymmetric:
            after = position + len(rule.start)
            if after >= len(text) or text[after].isspace():
                return False
        return True
