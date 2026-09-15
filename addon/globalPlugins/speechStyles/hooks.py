# Copyright (C) 2026 Beka Gozalishvili <beqaprogger@gmail.com>
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

import functools
import inspect

import api
import config
import controlTypes
import NVDAObjects
import speech
import speech.speech
import synthDriverHandler
from controlTypes import OutputReason, Role, State
from logHandler import log
from speech.extensions import filter_speechSequence

from .markers import ScopeEnd, ScopeStart, TaggedText
from .model import ContextGroup, ElementPart, Scope, TargetType
from .profiles import SETTINGS, SynthContext
from .transform import contextMatches, stripMarkers, takeSoundsWithoutSpeech, transform

_CONTEXT_REASON_NAMES = {
    ContextGroup.FOCUS: ("FOCUS", "FOCUSENTERED"),
    ContextGroup.NAVIGATION: ("CARET", "QUICKNAV"),
    ContextGroup.SAY_ALL: ("SAYALL",),
    ContextGroup.OBJECT_NAVIGATION: ("QUERY", "EXPLORE", "MOUSE"),
    ContextGroup.CHANGES: ("CHANGE",),
}
CONTEXTS = {
    reason: group
    for group, names in _CONTEXT_REASON_NAMES.items()
    for name in names
    if (reason := getattr(OutputReason, name, None)) is not None
}

_PROPERTY_PARTS = {
    "name": ElementPart.NAME,
    "value": ElementPart.VALUE,
    "description": ElementPart.DESCRIPTION,
    "placeholder": ElementPart.OTHER,
    "errorMessage": ElementPart.OTHER,
}

_START_FIELD_PREFIX = "start_"
_END_FIELD_PREFIX = "end_"
#: Field types whose speech is added even when empty without affecting blank line reporting.
_CONTENT_START_FIELD_TYPES = ("start_relative",)
_CONTENT_END_FIELD_TYPES = ("end_relative", "end_removedFromControlFieldStack")


def contextFor(reason):
    return CONTEXTS.get(reason)


_TEXT_INFO_REASON_INDEX = 3


def _reasonOf(args, kwargs):
    if "reason" in kwargs:
        return kwargs["reason"]
    if len(args) > _TEXT_INFO_REASON_INDEX:
        return args[_TEXT_INFO_REASON_INDEX]
    return OutputReason.QUERY


def objectPosition(obj):
    try:
        location = obj.location
        desktop = api.getDesktopObject().location
        if not location or not desktop or not desktop.width:
            return None
        centre = location.left + location.width / 2 - desktop.left
        return min(max(centre / desktop.width, 0.0), 1.0)
    except Exception:  # noqa: BLE001 - a location is a nicety; never fail speech for it
        log.debugWarning("Could not find the position of an object", exc_info=True)
        return None


def _enumMember(enumClass, value):
    if value is None:
        return None
    try:
        return enumClass(value)
    except ValueError:
        return None


def currentSynthContext():
    synth = synthDriverHandler.getSynth()
    if synth is None:
        return SynthContext()
    conf = config.conf["speech"][synth.name]
    defaults = {}
    for setting in SETTINGS:
        if synth.isSupported(setting):
            value = conf.get(setting)
            if isinstance(value, int):
                defaults[setting] = value
    return SynthContext(synth.name, defaults, synth.isSupported("voice"))


class _Patch:
    def __init__(self, modules, name, makeWrapper):
        self.modules = modules
        self.name = name
        self.makeWrapper = makeWrapper
        self.original = None
        self.wrapper = None
        self.patched = []

    def install(self):
        self.original = getattr(self.modules[0], self.name)
        self.wrapper = functools.wraps(self.original)(self.makeWrapper(self.original))
        for module in self.modules:
            if getattr(module, self.name, None) is self.original:
                setattr(module, self.name, self.wrapper)
                self.patched.append(module)

    def uninstall(self):
        for module in self.patched:
            if getattr(module, self.name, None) is self.wrapper:
                setattr(module, self.name, self.original)
            else:
                log.warning(f"{module.__name__}.{self.name} was replaced by someone else; leaving it")
        self.patched = []


class SpeechHooks:
    def __init__(self, getRuleSet):
        self.getRuleSet = getRuleSet
        self.bypass = False
        self._controlFieldDepth = 0
        self._object = None
        self._patches = [
            _Patch([speech.speech, speech], "getPropertiesSpeech", self._wrapGetPropertiesSpeech),
            _Patch([speech.speech, speech], "getControlFieldSpeech", self._wrapGetControlFieldSpeech),
            _Patch([speech.speech, speech], "getObjectPropertiesSpeech", self._wrapObjectSpeech),
            _Patch([speech.speech, speech], "getObjectSpeech", self._wrapObjectSpeech),
            _Patch([speech.speech, speech], "getTextInfoSpeech", self._wrapGetTextInfoSpeech),
            _Patch([controlTypes], "processAndLabelStates", self._wrapProcessAndLabelStates),
        ]

    def install(self):
        for patch in self._patches:
            try:
                patch.install()
            except Exception:
                log.error(f"Could not hook {patch.name}", exc_info=True)
        filter_speechSequence.register(self._filterSpeechSequence)

    def uninstall(self):
        filter_speechSequence.unregister(self._filterSpeechSequence)
        for patch in reversed(self._patches):
            patch.uninstall()

    def speakPreview(self, sequence, ruleSet):
        result = transform(sequence, ruleSet, currentSynthContext)
        result, sounds = takeSoundsWithoutSpeech(result)
        for sound in sounds:
            sound.run()
        self.bypass = True
        try:
            speech.speak(result)
        finally:
            self.bypass = False

    def _filterSpeechSequence(self, sequence):
        if self.bypass:
            return sequence
        try:
            result = transform(sequence, self.getRuleSet(), currentSynthContext)
        except Exception:
            log.error("Could not customize speech", exc_info=True)
            return stripMarkers(sequence)
        if result is sequence:
            return sequence
        result, sounds = takeSoundsWithoutSpeech(result)
        if sounds and speech.getState().speechMode == speech.SpeechMode.talk:
            for sound in sounds:
                try:
                    sound.run()
                except Exception:
                    log.error("Could not play a sound", exc_info=True)
        return result

    def _position(self, ruleSet, rules):
        if self._object is None or not any(rule.playsSound and rule.sound.panByPosition for rule in rules):
            return None
        return objectPosition(self._object)

    def _wrapObjectSpeech(self, original):
        def getSpeech(obj, *args, **kwargs):
            if not self.getRuleSet().hasElementRules:
                return original(obj, *args, **kwargs)
            previous, self._object = self._object, obj
            try:
                return original(obj, *args, **kwargs)
            finally:
                self._object = previous

        return getSpeech

    def _wrapGetTextInfoSpeech(self, original):
        def getTextInfoSpeech(info, *args, **kwargs):
            rules = ()
            try:
                ruleSet = self.getRuleSet()
                if ruleSet.hasContentRules:
                    rules = self._contentRules(info, ruleSet, _reasonOf(args, kwargs))
            except Exception:
                log.error("Could not find the rules for a text object", exc_info=True)
            generator = original(info, *args, **kwargs)
            if not rules:
                return (yield from generator)
            starts = [ScopeStart(rule.id) for rule in rules]
            ends = [ScopeEnd(rule.id) for rule in reversed(rules)]
            while True:
                try:
                    sequence = next(generator)
                except StopIteration as stop:
                    return stop.value
                yield [*starts, *sequence, *ends] if sequence else sequence

        return getTextInfoSpeech

    @classmethod
    def _contentRules(cls, info, ruleSet, reason):
        obj = getattr(info, "obj", None)
        if not isinstance(obj, NVDAObjects.NVDAObject):
            return []
        rules = cls._elementRules(ruleSet, _enumMember(Role, obj.role), obj.states, contextFor(reason))
        return [rule for rule in rules if rule.customizesSpeech and rule.scope == Scope.CONTENT]

    def _wrapGetPropertiesSpeech(self, original):
        def getPropertiesSpeech(reason=OutputReason.QUERY, **propertyValues):
            ruleSet = self.getRuleSet()
            if not ruleSet.hasElementRules:
                return original(reason, **propertyValues)
            context = contextFor(reason)
            tagged = dict(propertyValues)
            try:
                self._tagPropertyValues(tagged, context)
            except Exception:
                log.error("Could not tag property values", exc_info=True)
                tagged = propertyValues
            sequence = original(reason, **tagged)
            try:
                return self._tagPropertiesSpeech(sequence, propertyValues, context, ruleSet)
            except Exception:
                log.error("Could not tag property speech", exc_info=True)
                return sequence

        return getPropertiesSpeech

    @staticmethod
    def _tagPropertyValues(propertyValues, context):
        for key, part in _PROPERTY_PARTS.items():
            value = propertyValues.get(key)
            if isinstance(value, str) and value and not isinstance(value, TaggedText):
                propertyValues[key] = TaggedText(value, part, context=context)
        role = _enumMember(Role, propertyValues.get("role"))
        roleText = propertyValues.get("roleText")
        if role is not None and isinstance(roleText, str) and roleText:
            propertyValues["roleText"] = TaggedText(
                roleText, ElementPart.ROLE, (TargetType.ROLE, role.name), context
            )

    def _tagPropertiesSpeech(self, sequence, propertyValues, context, ruleSet):
        result = list(sequence)
        role = _enumMember(Role, propertyValues.get("role", propertyValues.get("_role")))
        if "role" in propertyValues and role is not None and not propertyValues.get("roleText"):
            try:
                roleLabel = role.displayString
            except KeyError:
                roleLabel = None
            for index, item in enumerate(result):
                if type(item) is str and item == roleLabel:
                    result[index] = TaggedText(item, ElementPart.ROLE, (TargetType.ROLE, role.name), context)
                    break
        for index, item in enumerate(result):
            if type(item) is str:
                result[index] = TaggedText(item, ElementPart.OTHER, context=context)
        if self._controlFieldDepth or not result:
            return result
        states = propertyValues.get("_states", propertyValues.get("states"))
        rules = self._scopeRules(ruleSet, role, states, result, context)
        position = self._position(ruleSet, self._labelRules(ruleSet, result, context))
        if position is not None:
            result = [
                item.withPosition(position) if isinstance(item, TaggedText) else item for item in result
            ]
        for rule in reversed(rules):
            result = [ScopeStart(rule.id, position), *result, ScopeEnd(rule.id)]
        return result

    @staticmethod
    def _labelRules(ruleSet, sequence, context):
        rules = []
        for item in sequence:
            target = getattr(item, "target", None)
            if target is not None:
                rules.extend(rule for rule in ruleSet.rulesFor(*target) if contextMatches(rule, context))
        return rules

    @staticmethod
    def _elementRules(ruleSet, role, states, context, sequence=()):
        candidates = []
        if role is not None:
            candidates.extend(ruleSet.rulesFor(TargetType.ROLE, role.name))
        if ruleSet.hasStateRules:
            for state in states or ():
                member = _enumMember(State, state)
                if member is not None:
                    candidates.extend(ruleSet.rulesFor(TargetType.STATE, member.name))
            for item in sequence:
                target = getattr(item, "target", None)
                if target is not None and target[0] == TargetType.NEGATIVE_STATE:
                    candidates.extend(ruleSet.rulesFor(*target))
        order = {rule.id: index for index, rule in enumerate(ruleSet.elementRules)}
        matching = {rule.id: rule for rule in candidates if contextMatches(rule, context)}
        return sorted(matching.values(), key=lambda rule: order[rule.id])

    @classmethod
    def _scopeRules(cls, ruleSet, role, states, sequence, context):
        return [
            rule
            for rule in cls._elementRules(ruleSet, role, states, context, sequence)
            if rule.customizesSpeech and rule.scope != Scope.LABEL
        ]

    def _wrapGetControlFieldSpeech(self, original):
        def getControlFieldSpeech(
            attrs, ancestorAttrs, fieldType, formatConfig=None, extraDetail=False, reason=None
        ):
            ruleSet = self.getRuleSet()
            if not ruleSet.hasElementRules:
                return original(attrs, ancestorAttrs, fieldType, formatConfig, extraDetail, reason)
            self._controlFieldDepth += 1
            try:
                sequence = original(attrs, ancestorAttrs, fieldType, formatConfig, extraDetail, reason)
            finally:
                self._controlFieldDepth -= 1
            try:
                return self._tagControlFieldSpeech(sequence, attrs, fieldType, reason, ruleSet)
            except Exception:
                log.error("Could not tag control field speech", exc_info=True)
                return sequence

        return getControlFieldSpeech

    def _tagControlFieldSpeech(self, sequence, attrs, fieldType, reason, ruleSet):
        if attrs.get("isHidden"):
            return sequence
        context = contextFor(reason)
        role = _enumMember(Role, attrs.get("role"))
        isStart = fieldType.startswith(_START_FIELD_PREFIX)
        isEnd = fieldType.startswith(_END_FIELD_PREFIX)
        result = list(sequence)
        roleTarget = (TargetType.ROLE, role.name) if role is not None else None
        roleTexts = self._controlFieldRoleTexts(attrs, role) if isStart else ()
        plainItems = [index for index, item in enumerate(result) if type(item) is str]
        for index in plainItems:
            item = result[index]
            if roleTarget and isEnd and len(result) == 1:
                result[index] = TaggedText(item, ElementPart.ROLE, roleTarget, context, isExit=True)
            elif roleTarget and item in roleTexts:
                result[index] = TaggedText(item, ElementPart.ROLE, roleTarget, context)
            else:
                result[index] = TaggedText(item, ElementPart.OTHER, context=context)
        if not (isStart or isEnd):
            return result
        rules = self._scopeRules(ruleSet, role, attrs.get("states"), result, context)
        for rule in reversed(rules):
            if rule.scope == Scope.ELEMENT:
                if isStart and result:
                    result = [ScopeStart(rule.id), *result, ScopeEnd(rule.id)]
            elif isStart:
                if result or fieldType in _CONTENT_START_FIELD_TYPES:
                    result = [ScopeStart(rule.id), *result]
            elif result or fieldType in _CONTENT_END_FIELD_TYPES:
                result = [*result, ScopeEnd(rule.id)]
        return result

    @staticmethod
    def _controlFieldRoleTexts(attrs, role):
        texts = []
        roleText = attrs.get("roleText")
        if roleText:
            texts.append(roleText)
        landmark = attrs.get("landmark")
        if role == Role.LANDMARK and landmark:
            try:
                import aria

                texts.append(f"{aria.landmarkRoles[landmark]} {Role.LANDMARK.displayString}")
            except (ImportError, KeyError):
                pass
        return tuple(texts)

    def _wrapProcessAndLabelStates(self, original):
        try:
            from controlTypes.processAndLabelStates import _processNegativeStates, _processPositiveStates

            signature = inspect.signature(original)
        except (ImportError, TypeError, ValueError):
            log.warning("Cannot tag state labels in this version of NVDA", exc_info=True)
            return original

        def processAndLabelStates(*args, **kwargs):
            labels = original(*args, **kwargs)
            ruleSet = self.getRuleSet()
            if not ruleSet.hasElementRules or not labels:
                return labels
            try:
                arguments = signature.bind(*args, **kwargs)
                arguments.apply_defaults()
                values = arguments.arguments
                role, states, reason = values["role"], values["states"], values["reason"]
                positive = _processPositiveStates(role, states, reason, values.get("positiveStates"))
                negative = _processNegativeStates(role, states, reason, values.get("negativeStates"))
                ordered = sorted(positive | negative)
                if len(ordered) != len(labels):
                    return labels
                context = contextFor(reason)
                return [
                    TaggedText(
                        label,
                        ElementPart.STATES,
                        (TargetType.STATE if state in positive else TargetType.NEGATIVE_STATE, state.name),
                        context,
                    )
                    for state, label in zip(ordered, labels, strict=True)
                ]
            except Exception:
                log.error("Could not tag state labels", exc_info=True)
                return labels

        return processAndLabelStates
