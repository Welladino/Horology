/* Run applyDecisions on a timer, and straight after a person edits the Decision Register. */

function installTriggers() {
  stopTriggers();
  ScriptApp.newTrigger('applyDecisions').timeBased().everyMinutes(DECISIONS_CONFIG.CHECK_EVERY_MINUTES).create();
  // Edit triggers fire for people's edits only, not for API or script writes; the timer covers those.
  ScriptApp.newTrigger('applyDecisions').forSpreadsheet(DECISIONS_CONFIG.DECISIONS_SHEET_ID).onEdit().create();
  console.log('Installed: every ' + DECISIONS_CONFIG.CHECK_EVERY_MINUTES + ' minutes, and on Decision Register edits.');
}

function stopTriggers() {
  ScriptApp.getProjectTriggers().filter(t => t.getHandlerFunction() === 'applyDecisions').forEach(t => ScriptApp.deleteTrigger(t));
}
