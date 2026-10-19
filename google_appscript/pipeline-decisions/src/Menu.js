/* The Extensions menu, so a copy of the workbook can be set up without opening the editor. */

function onOpen() {
  SpreadsheetApp.getUi().createAddonMenu()
    .addItem('Preview decisions', 'previewFromMenu')
    .addItem('Apply decisions now', 'applyFromMenu')
    .addSeparator()
    .addItem('Install triggers', 'installFromMenu')
    .addItem('Stop triggers', 'stopFromMenu')
    .addToUi();
}

function previewFromMenu() { report('Preview: nothing was written', previewDecisions()); }

function applyFromMenu() { report('Decisions applied', applyDecisions()); }

function installFromMenu() {
  installTriggers();
  SpreadsheetApp.getUi().alert('Decisions are now applied every ' + DECISIONS_CONFIG.CHECK_EVERY_MINUTES +
    ' minutes, and after each edit of the Decision Register.');
}

function stopFromMenu() {
  stopTriggers();
  SpreadsheetApp.getUi().alert('Triggers removed. Decisions are no longer applied automatically.');
}

function report(title, out) {
  const lines = out.map(o => 'Item ' + o.pipelineId + ': ' + (o.error ? o.error : o.decision + ' → ' + JSON.stringify(o.set)));
  SpreadsheetApp.getUi().alert(title, lines.length ? lines.join('\n') : 'Nothing to apply.', SpreadsheetApp.getUi().ButtonSet.OK);
}
