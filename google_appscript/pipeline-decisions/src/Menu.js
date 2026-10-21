/* The workbook keeps one entry point into the web workspace. */

function onOpen() {
  SpreadsheetApp.getUi().createAddonMenu()
    .addItem('Open Horology workspace', 'openHorologyWorkspace')
    .addToUi();
}

function openHorologyWorkspace() {
  const page = HtmlService.createHtmlOutput(
    '<div style="font:15px Arial,sans-serif;padding:18px;color:#1b3037">' +
    '<p>Review decisions, Pipeline items, and folders in the Horology workspace.</p>' +
    '<p><a href="' + DECISIONS_CONFIG.WEB_APP_URL +
    '" target="_blank" rel="noopener noreferrer" style="display:inline-block;padding:11px 16px;' +
    'background:#151819;color:white;border-radius:8px;text-decoration:none">Open workspace ↗</a></p>' +
    '</div>').setWidth(390).setHeight(150);
  SpreadsheetApp.getUi().showModalDialog(page, 'Open Horology workspace');
}
