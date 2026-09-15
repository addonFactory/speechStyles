# Copyright (C) 2026 Beka Gozalishvili <beqaprogger@gmail.com>
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

import os.path
import sys

import addonHandler
import gui
import wx

addon = addonHandler.getCodeAddon()
addonSummary = addon.manifest["summary"]

donateDir = os.path.abspath(os.path.join(os.path.dirname(__file__), "globalPlugins", "speechStyles"))
sys.path.append(donateDir)
from donate import requestDonations  # noqa: E402

sys.path.remove(donateDir)

addonHandler.initTranslation()


def onInstall():
    gui.mainFrame.prePopup()
    wx.CallAfter(requestDonations, addonSummary, gui.mainFrame)
    gui.mainFrame.postPopup()
