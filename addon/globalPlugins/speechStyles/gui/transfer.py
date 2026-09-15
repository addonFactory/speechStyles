# Copyright (C) 2026 Beka Gozalishvili <beqaprogger@gmail.com>
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

import os

import addonHandler
import wx
from gui.message import DialogType, MessageDialog, ReturnCode
from logHandler import log

from ..model import ImportMode
from ..storage import StorageError
from .dialogs import showError

addonHandler.initTranslation()

DEFAULT_FILE_NAME = "speechStyles-rules.zip"


def _wildcard():
    # Translators: The kind of file rules are saved to, in the dialog to choose one.
    return _("Speech Styles rules") + " (*.zip)|*.zip"


def exportRules(parent, store, document):
    with wx.FileDialog(
        parent,
        # Translators: The title of the dialog to choose where the rules are saved.
        message=_("Save rules to a file"),
        wildcard=_wildcard(),
        defaultFile=DEFAULT_FILE_NAME,
        style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
    ) as dialog:
        if dialog.ShowModal() != wx.ID_OK:
            return False
        path = dialog.GetPath()
    try:
        store.exportArchive(document, path)
    except (OSError, StorageError):
        log.error(f"Could not save the rules to {path!r}", exc_info=True)
        # Translators: Reported when the rules cannot be saved. {file} is the chosen file.
        showError(parent, _("Could not save the rules to {file}.").format(file=path))
        return False
    return True


def importRules(parent, store, document):
    with wx.FileDialog(
        parent,
        # Translators: The title of the dialog to choose the file rules are loaded from.
        message=_("Load rules from a file"),
        wildcard=_wildcard(),
        style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
    ) as dialog:
        if dialog.ShowModal() != wx.ID_OK:
            return None
        path = dialog.GetPath()
    mode = _askImportMode(parent, os.path.basename(path))
    if mode is None:
        return None
    try:
        return store.importArchive(path, document, mode)
    except (OSError, StorageError):
        log.error(f"Could not load the rules from {path!r}", exc_info=True)
        # Translators: Reported when the rules of a file cannot be read. {file} is the chosen file.
        showError(parent, _("Could not read the rules of {file}.").format(file=path))
        return None


def _askImportMode(parent, fileName):
    dialog = MessageDialog(
        parent,
        # Translators: The question asked when loading rules from a file. {file} is its name.
        _("What should be done with the rules of {file}?").format(file=fileName),
        # Translators: The title of the dialog asking how rules are loaded from a file.
        _("Load rules"),
        dialogType=DialogType.WARNING,
        buttons=None,
    )
    dialog.addButton(
        ReturnCode.CUSTOM_1,
        # Translators: A button to add the rules of a file to the rules you already have.
        label=_("&Add them to my rules"),
        defaultFocus=True,
    )
    dialog.addButton(
        ReturnCode.CUSTOM_2,
        # Translators: A button to replace all your rules by the rules of a file.
        label=_("&Replace all my rules"),
    )
    dialog.addCancelButton(fallbackAction=True)
    answer = dialog.ShowModal()
    if answer == ReturnCode.CUSTOM_1:
        return ImportMode.MERGE
    if answer == ReturnCode.CUSTOM_2:
        return ImportMode.REPLACE
    return None
