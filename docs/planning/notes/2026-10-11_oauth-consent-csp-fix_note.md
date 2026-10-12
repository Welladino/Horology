# OAuth consent redirect CSP fix

The operator reported Chrome blocking consent submission with `form-action 'self'`, followed by Consent rejected on a later attempt. The restrictive consent-page header did not allow the form's final 303 redirect to Codex's loopback callback. Chrome can apply form-action to redirects after a POST; the server consumes consent and clears its cookie before the browser follows that redirect, so reusing the page is invalid.

The consent page now permits its own origin and only the SDK-validated callback origin for that authorization request, including the actual callback port. Other CSP restrictions remain. Client registration rejects network-authority characters that could inject CSP directives. The existing test exercises the consent flow and asserts the exact CSP header; an additional registration case rejects a directive-shaped host.

Validation: the full required tests/ plus gateway tests ran with 67 passed and 10 skipped (disposable Postgres stopped; unchanged database tests were previously validated). Container image built successfully. Final browser verification requires a fresh single Codex login after deployment; used consent pages cannot be retried.

Source: [MDN form-action](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/form-action).

Browser verification completed on 2026-10-12: operator saw Authentication complete and Codex CLI confirmed successful Horology login. The single-tab consent flow now completes.
