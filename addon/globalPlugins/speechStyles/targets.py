# Copyright (C) 2026 Beka Gozalishvili <beqaprogger@gmail.com>
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

import addonHandler
import controlTypes
from logHandler import log

from .model import TargetType

addonHandler.initTranslation()

TARGET_TYPE_LABELS = {
    # Translators: A kind of thing a rule applies to: a control type such as link or button.
    TargetType.ROLE: _("Role"),
    # Translators: A kind of thing a rule applies to: a state such as checked or expanded.
    TargetType.STATE: _("State"),
    # Translators: A kind of thing a rule applies to: a state which is absent, such as "not checked".
    TargetType.NEGATIVE_STATE: _("Negative state"),
}


def _hasLabel(member):
    try:
        return member in member._displayStringLabels
    except Exception:  # noqa: BLE001 - a missing or changed private attribute must not break the dialog
        log.debugWarning(f"Cannot tell whether {member!r} has a label", exc_info=True)
        return False


def targetChoices(targetType):
    if targetType == TargetType.ROLE:
        choices = [(role.name, role.displayString) for role in controlTypes.Role if _hasLabel(role)]
    else:
        negative = targetType == TargetType.NEGATIVE_STATE
        choices = [
            (state.name, state.negativeDisplayString if negative else state.displayString)
            for state in controlTypes.State
            if _hasLabel(state)
        ]
    return sorted(choices, key=lambda choice: choice[1].lower())


def targetValueLabel(target):
    enumClass = controlTypes.Role if target.type == TargetType.ROLE else controlTypes.State
    member = getattr(enumClass, target.value, None)
    if member is None or not _hasLabel(member):
        # Translators: Shown for a role or state this version of NVDA doesn't know. {name} is its identifier.
        return _("{name} (unknown)").format(name=target.value)
    if target.type == TargetType.NEGATIVE_STATE:
        return member.negativeDisplayString
    return member.displayString


def describeTarget(target):
    # Translators: How the target of a rule is shown, such as "Role: link".
    return _("{type}: {value}").format(type=TARGET_TYPE_LABELS[target.type], value=targetValueLabel(target))
