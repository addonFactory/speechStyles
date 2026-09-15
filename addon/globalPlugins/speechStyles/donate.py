# Copyright (C) 2022-2026 Beka Gozalishvili <beqaprogger@gmail.com>
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

import webbrowser

import addonHandler
from gui.message import DialogType, MessageDialog, ReturnCode
from logHandler import log

addonHandler.initTranslation()

PAYPAL_URL = "https://paypal.me/gozaltech"
YOOMONEY_URL = "https://yoomoney.ru/to/4100117727255296"


def _openUrl(url):
    try:
        webbrowser.open(url)
    except Exception:
        log.error(f"Could not open {url}", exc_info=True)


class DonationDialog(MessageDialog):
    def __init__(self, parent, title, message):
        super().__init__(parent, message, title, dialogType=DialogType.WARNING, buttons=None)
        self.addButton(
            ReturnCode.CUSTOM_1,
            # Translators: The label of a button on the donation dialog.
            label=_("Donate via &PayPal"),
            callback=lambda payload: _openUrl(PAYPAL_URL),
            defaultFocus=True,
        )
        self.addButton(
            ReturnCode.CUSTOM_2,
            # Translators: The label of a button on the donation dialog.
            label=_("Donate via &Yoomoney"),
            callback=lambda payload: _openUrl(YOOMONEY_URL),
        )
        self.addCancelButton(fallbackAction=True)


def requestDonations(addonSummary, parentWindow):
    return DonationDialog(
        parentWindow,
        # Translators: The title of the donation dialog. {name} is the name of the add-on.
        _("Request for contributions to {name}").format(name=addonSummary),
        # Translators: The message of the donation dialog. {name} is the name of the add-on.
        _(
            "{name} is a free add-on for NVDA.\n"
            "You can make a donation to its author to support further development of this and other "
            "free projects.\n"
            "Do you want to donate now? Choose one of the available payment methods. "
            "You will be redirected to the corresponding website to complete a donation"
        ).format(name=addonSummary),
    ).ShowModal()
