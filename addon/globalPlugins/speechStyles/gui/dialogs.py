# Copyright (C) 2026 Beka Gozalishvili <beqaprogger@gmail.com>
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

import addonHandler
import gui
import wx
from gui import guiHelper
from logHandler import log
from wx.lib import scrolledpanel

addonHandler.initTranslation()

MAX_SCREEN_FRACTION = 0.9


def groupParent(parent, sHelper):
    sizer = sHelper.sizer
    return sizer.GetStaticBox() if isinstance(sizer, wx.StaticBoxSizer) else parent


def showError(parent, message):
    # Translators: The title of a message about a problem, for example with the values in a dialog.
    gui.messageBox(message, _("Speech Styles"), wx.OK | wx.ICON_ERROR, parent)


class Dialog(wx.Dialog):
    initialFocus = None

    def __init__(self, parent, title):
        super().__init__(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        self.content = scrolledpanel.ScrolledPanel(self, style=wx.TAB_TRAVERSAL)
        self.content.SetMinSize((1, 1))
        contentSizer = wx.BoxSizer(wx.VERTICAL)
        sHelper = guiHelper.BoxSizerHelper(self.content, orientation=wx.VERTICAL)
        self.makeContent(sHelper)
        contentSizer.Add(sHelper.sizer, border=guiHelper.BORDER_FOR_DIALOGS, flag=wx.ALL | wx.EXPAND)
        self.content.SetSizer(contentSizer)
        mainSizer.Add(self.content, proportion=1, flag=wx.EXPAND)
        mainSizer.Add(
            wx.StaticLine(self), flag=wx.EXPAND | wx.TOP, border=guiHelper.SPACE_BETWEEN_VERTICAL_DIALOG_ITEMS
        )
        mainSizer.Add(
            self.CreateButtonSizer(wx.OK | wx.CANCEL),
            flag=wx.ALIGN_RIGHT | wx.ALL,
            border=guiHelper.BORDER_FOR_DIALOGS,
        )
        self.Bind(wx.EVT_BUTTON, self.onOk, id=wx.ID_OK)
        self.SetSizer(mainSizer)
        mainSizer.Fit(self)
        self._fitOnScreen()
        self.Layout()
        self.content.SetupScrolling()
        self.CentreOnScreen()
        if self.initialFocus is not None:
            self.initialFocus.SetFocus()

    def _fitOnScreen(self):
        try:
            index = wx.Display.GetFromWindow(self)
            area = wx.Display(max(index, 0)).GetClientArea()
            width, height = self.GetSize()
            maximum = (
                int(area.width * MAX_SCREEN_FRACTION),
                int(area.height * MAX_SCREEN_FRACTION),
            )
            if width > maximum[0] or height > maximum[1]:
                self.SetSize(min(width, maximum[0]), min(height, maximum[1]))
        except Exception:  # noqa: BLE001 - never fail to open a dialog over its size
            log.debugWarning("Could not fit the dialog to the screen", exc_info=True)

    def makeContent(self, sHelper):
        raise NotImplementedError

    def validate(self):
        return True

    def onOk(self, event):
        if self.validate():
            event.Skip()

    def addButton(self, buttonHelper, label, handler):
        button = buttonHelper.addButton(self.content, label=label)
        button.Bind(wx.EVT_BUTTON, handler)
        return button

    def showError(self, message, focus=None):
        showError(self, message)
        if focus is not None:
            focus.SetFocus()
