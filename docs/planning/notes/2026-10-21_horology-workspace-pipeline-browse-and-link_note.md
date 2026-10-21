# Horology workspace Pipeline browsing and menu link

The founder's screenshots showed a wide focus outline crossing the decision option cards. The Extensions menu also opened a generic Apps Script URL that failed for the founder, while the `welladino.com` domain-scoped URL worked. The founder wanted all Pipeline rows visible in the web app.

The form CSS now sizes radio buttons independently and uses a subtle underline for text fields and dropdowns. The Extensions menu link uses the founder's working domain-scoped URL. A read-only Pipeline view reads every Master row with an ID and offers cards, rows, search and a detail page with a direct Sheet row link. The cached view is cleared after saving a decision or adding an item.

The Pipeline and Decision Register remain the source records. No Sheets tab or Cloud Run change is needed. Offline verification covers the Pipeline read and confirms that it makes no writes; the page script passes a syntax check. Browser inspection requires the founder's permission and was not performed.

After the founder renewed `clasp` login, the existing web app deployment was updated to version 3 at the same URL. `clasp deployments` confirmed that version. No commit or PR was made.
