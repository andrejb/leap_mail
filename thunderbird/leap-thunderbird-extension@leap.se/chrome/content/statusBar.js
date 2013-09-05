/**
 * statusBar.js
 * Copyright (C) 2013 LEAP
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along
 */


Components.utils.import("resource:///modules/mailServices.js");

var accountNotConfigured = getStringBundle(
    "chrome://leap/locale/statusBar.properties")
        .GetStringFromName("account_not_configured");
var accountConfigured = getStringBundle(
    "chrome://leap/locale/statusBar.properties")
        .GetStringFromName("account_configured");


/*****************************************************************************
 * Schedule initialization and update functions.
 ****************************************************************************/

// run startUp() once when window loads
window.addEventListener("load", function(e) { 
	starUp(); 
}, false);

// run updatePanel() periodically
window.setInterval(
	function() {
		updatePanel(); 
	}, 10000); // update every ten seconds


/*****************************************************************************
 * GUI maintenance functions.
 ****************************************************************************/

function starUp() {
    updatePanel();
    if (!isLeapAccountConfigured()) {
        launchAccountWizard();
    }
}

/**
 * Update the status bar panel with information about LEAP accounts.
 */
function updatePanel() {
    var statusBarPanel = document.getElementById("leap-status-bar");
    if (isLeapAccountConfigured())
        statusBarPanel.label = accountConfigured;
    else
        statusBarPanel.label = accountNotConfigured;
}

/**
 * Handle a click on the status bar panel. For now, just launch the new
 * account wizard if there's no account configured.
 */
function handleStatusBarClick() {
    if (!isLeapAccountConfigured())
        launchAccountWizard();
}


/*****************************************************************************
 * Account management functions
 ****************************************************************************/

/**
 * Return true if there exists an account with incoming server hostname equal
 * to IMAP_HOST and port equal to IMAP_PORT.
 *
 * TODO: also verify for SMTP configuration?
 */
function isLeapAccountConfigured() {
    var accountManager = Cc["@mozilla.org/messenger/account-manager;1"]
                         .getService(Ci.nsIMsgAccountManager);
    var existing = accountManager.findRealServer(
        "", IMAP_HOST, "imap", IMAP_PORT);
    return !!existing;
}


/*****************************************************************************
 * Wizard functions.
 ****************************************************************************/

/**
 * Launch the wizard to configure a new LEAP account.
 */
function launchAccountWizard()
{
  msgNewMailAccount(MailServices.mailSession.topmostMsgWindow, null, null);
}

/**
 * Open the New Mail Account Wizard, or focus it if it's already open.
 *
 * @param msgWindow a msgWindow for us to use to verify the accounts.
 * @param okCallback an optional callback for us to call back to if
 *                   everything's okay.
 * @param extraData an optional param that allows us to pass data in and
 *                  out.  Used in the upcoming AccountProvisioner add-on.
 * @see msgOpenAccountWizard below for the previous implementation.
 */
function msgNewMailAccount(msgWindow, okCallback, extraData)
{
  if (!msgWindow)
    throw new Error("msgNewMailAccount must be given a msgWindow.");
  let wm = Components.classes["@mozilla.org/appshell/window-mediator;1"]
                     .getService()
                     .QueryInterface(Components.interfaces.nsIWindowMediator);
  let existingWindow = wm.getMostRecentWindow("mail:leapautoconfig");
  if (existingWindow)
    existingWindow.focus();
  else
    // disabling modal for the time being, see 688273 REMOVEME
    window.openDialog("chrome://leap/content/accountWizard.xul",
                      "AccountSetup", "chrome,titlebar,centerscreen",
                      {msgWindow:msgWindow,
                       okCallback:function () { updatePanel(); },
                       extraData:extraData});

}
