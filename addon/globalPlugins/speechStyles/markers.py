# Copyright (C) 2026 Beka Gozalishvili <beqaprogger@gmail.com>
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

from speech.commands import BaseCallbackCommand, SpeechCommand

from .model import ContextGroup, ElementPart, TargetType

Target = tuple[TargetType, str]


class TaggedText(str):
    part: ElementPart
    target: Target | None
    context: ContextGroup | None
    isExit: bool
    position: float | None

    def __new__(cls, text, part, target=None, context=None, isExit=False, position=None):
        obj = super().__new__(cls, text)
        obj.part = part
        obj.target = target
        obj.context = context
        obj.isExit = isExit
        obj.position = position
        return obj

    def withPosition(self, position):
        return TaggedText(str(self), self.part, self.target, self.context, self.isExit, position)

    def withText(self, text):
        return TaggedText(text, self.part, self.target, self.context, self.isExit, self.position)

    def __repr__(self):
        return f"TaggedText({str.__repr__(self)}, {self.part}, target={self.target})"


class ScopeStart(SpeechCommand):
    def __init__(self, ruleId, position=None):
        self.ruleId = ruleId
        self.position = position

    def __repr__(self):
        return f"ScopeStart({self.ruleId!r})"


class ScopeEnd(SpeechCommand):
    def __init__(self, ruleId):
        self.ruleId = ruleId

    def __repr__(self):
        return f"ScopeEnd({self.ruleId!r})"


class VoiceStateCommand(SpeechCommand):
    def __init__(self, state):
        self.state = state

    def __repr__(self):
        return f"VoiceStateCommand({self.state!r})"

    def __eq__(self, other):
        return type(other) is type(self) and other.state == self.state

    __hash__ = SpeechCommand.__hash__


class SoundCommand(BaseCallbackCommand):
    def __init__(self, sound, position=None):
        self.sound = sound
        self.position = position

    def run(self):
        from . import sounds

        sounds.play(self.sound, self.position)

    def __repr__(self):
        return f"SoundCommand({self.sound.type})"

    def __eq__(self, other):
        return type(other) is type(self) and (other.sound, other.position) == (self.sound, self.position)

    __hash__ = BaseCallbackCommand.__hash__


MARKER_COMMANDS = (ScopeStart, ScopeEnd)
