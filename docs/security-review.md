# Security recheck — 0.2.1

**Checked:** November 23, 2026. **Scope:** the public source checkout and a freshly resolved Python 3.13 reference environment. The operating local program, saved credentials, account state and broker runtime were not changed or contacted.

## Result

The reference package-advisory matches fall from **37 to 24**, resolving **13 advisories including the one critical certifi advisory**. Remaining severities are **12 high, 8 medium and 4 low**. No alert was dismissed to obtain this reduction. These are dependency-advisory matches, not counts of confirmed exploitable application paths, and they can change as advisory databases change.

The exact package versions, queried original/canonical package aliases, resolved GHSA IDs and remaining matches are retained in [security-dependencies.json](verification/security-dependencies.json). Normal resolver dry-runs separately confirm [all five upgrade conflicts](verification/security-sdk-resolution.json); no `--no-deps` override was used. A current environment inventory is [security-environment.cdx.json](verification/security-environment.cdx.json). The original 131-distribution authoring inventory remains a separate historical artifact.

## Why cTrader security is not sufficient by itself

cTrader authenticates the application/account and enforces broker-side permissions. The client still has to protect its local tokens, verify the server, parse received messages safely and use maintained dependencies. A secure provider login cannot patch a vulnerable Python library on the user's machine. Conversely, a package-level server vulnerability does not automatically mean this desktop exposes that server feature.

## Compatible package updates

| Distribution | Original reference | Updated reference | Original advisory matches resolved |
|---|---:|---:|---:|
| certifi | 2025.1.31 | 2026.11.20 | 1 critical |
| urllib3 | 2.3.0 | 2.8.0 | 8 |
| idna | 3.10 | 3.20 | 1 |
| pytest | 8.3.5 | 9.2.0 | 1 |
| setuptools | 78.1.1 | 84.2.1 | 2 |

The resolver also updated pytest's required helper distributions. The build-system minimum is now setuptools 84.1.0 and the developer extra requires pytest 9.0.3 or newer. The reference pins describe the actually installed/tested environment, not an invented upgrade list. `pip check` confirms declared dependency consistency.

## Application fixes

- **Token endpoint identity:** the built-in transport accepts only the official HTTPS cTrader token path and a single supported grant. Alternate hosts, credentials embedded in the authority, alternate ports/paths, fragments and ambiguous grants are refused before transport construction.
- **No token redirects:** the actual urllib opener rejects HTTP redirects, including HTTPS-to-HTTP or cross-host redirects, rather than sending a credential-bearing request to a redirected endpoint. Errors do not retain the credential-bearing URL.
- **Bounded response processing:** success and HTTP-error JSON reads have a 65,536-byte limit. Non-object or duplicate-key responses, invalid token types/lengths and invalid expiry values are refused without replacing saved credentials. A valid response at the byte boundary is accepted.
- **Safer local credentials:** reads are nonblocking before file-type validation, reject FIFO/symlink/multiple-hard-link targets and retain owner-only file/directory checks. Reads and saves are bounded; an oversized save is refused before creating the credential file. Storage remains permission-restricted plaintext, **not an encrypted keychain**.
- **Explicit FIX TLS floor:** CodeQL flagged the optional FIX capture's reliance on `create_default_context()` defaults. The updated context explicitly uses client mode, TLS 1.2+, required certificate verification, hostname checking and OS trust roots. The Python 3.13 default already has a TLS 1.2 minimum; this removes ambiguous reliance on defaults, not proof that a weak handshake previously occurred. The optional capture was not connected during this review.
- **Full hostname verification required:** the cTrader extra now installs `service-identity` 24.2.x, the compatible line for the SDK's legacy cryptography constraint. The connector fails closed if that verifier is missing instead of using Twisted's reduced-assurance optional fallback. Tests verify matching and mismatching synthetic certificates and the actual Twisted verifier binding. This is not a new live cTrader handshake receipt.

Regression tests use synthetic credentials/certificates and offline HTTP responses. Their coverage includes the real urllib redirect-handler chain, bounded response reads, credential preservation on rejection, FIFO timeout rejection and missing-verifier failure. They do not authenticate an account or issue a broker operation.

## Executed verification

The final source suite passed **1,574 tests** (zero failures/errors/skips) in 363.47 pytest-reported seconds and exited with code 0. All **33 security regressions** passed again against a separately installed 0.2.1 wheel outside the checkout. Architecture, synthetic restart/reconciliation, `pip check`, 158-file wheel/source parity, wheel/sdist builds and portable source/documentation integrity checks passed. The restart checkpoint reports zero network calls and zero real broker orders. The [source-bound test receipt](verification/security-tests.json) retains exact case counts, test-source digests and the local JUnit digest without private paths.

## Why 24 package advisories remain

The latest stable upstream `ctrader-open-api` package available at this check is **0.9.2**. Its metadata pins Twisted 24.3.0, pyOpenSSL 24.1.0, protobuf 3.20.1 and requests 2.32.3. That pyOpenSSL version constrains cryptography below 43. An actual normal-resolver experiment rejects combining that SDK with a modern Twisted version. Ignoring the resolver or changing upstream metadata would be a connector migration, not a compatible package update.

| Remaining group | Matches | Source-level reachability assessment |
|---|---:|---|
| Twisted | 11 | The advisory paths involve HTTP/HTTP2, IMAP, IRC, Telnet, XML-stream or `twisted.names` server/resolver components. The reviewed app uses an outbound TLS Protobuf client, not those servers. None of those modules was imported by fresh SDK client construction. **No application call path observed**, not a declaration that the installed package is patched. |
| pyOpenSSL | 2 | The advisories involve DTLS-cookie generation and a user-provided server-name callback. Those callback paths are not defined by the reviewed app. **No application call path observed**; the package remains affected and upstream-pinned. |
| requests | 2 | The app's OAuth transport uses urllib and does not call the SDK `Auth` helper or `extract_zipped_paths`. Those affected requests paths have **no observed call site** in current product source. Importing the SDK can still import requests; plugins/external scripts can widen the surface. |
| protobuf | 3 | Binary Protobuf parsing is used and remains a genuine **unresolved parser-dependency risk**. The separate nested-`Any` JSON advisory has no `google.protobuf.Any` field in the 119 inspected reachable cTrader message types. That does not resolve binary-parser advisories or prove every parser input safe. |
| cryptography | 6 | TLS/certificate handling is in use. Exact exploit prerequisites differ by advisory; no blanket unreachability claim is made. Legacy wheel/OpenSSL and certificate issues remain **unresolved SDK-constrained risk**. |

No remaining alert was dismissed as "not used." An observed missing call path can change with plugins, alternative scripts or future code. A compatible upstream SDK release, a separately designed maintained adapter, or a fully qualified migration is still required for full dependency remediation. Offline tests alone cannot establish real connector compatibility or profitable/safe trading.

## GitHub settings and owner actions

Already verified: public visibility, MIT license, private vulnerability reporting, Dependabot alerts/security updates, secret scanning, push protection, read-only default workflow permissions, review/conversation branch protection and HTTPS documentation hosting.

CodeQL default setup is configured for Python with weekly scheduled analysis; the initial managed setup completed successfully. The security PR's exact-product head passed both hosted CodeQL checks and showed no open PR-ref code-scanning alerts. Its initial main-branch TLS-default warning is addressed by the explicit FIX context above. Branch protection requires the actually observed `CodeQL` check from GitHub Advanced Security (app 57789). Final main-branch analysis is a separate readback after merge. Hosted code scanning is distinct from the full offline unit-test suite.

The repository's application-test Actions template remains inert until the owner grants `workflow` scope. Activate it only through normal authorization:

```bash
gh auth refresh -h github.com -s workflow
```

Run this on the same machine/account used for publication, complete GitHub's browser approval yourself, then move `.github/ci-template.yml` to `.github/workflows/ci.yml`, commit and push. No password or token should be pasted into a chat, issue or repository. Once it runs successfully, require its real check names in branch protection; do not invent a required check that has never run.

The API did not expose account-level two-factor authentication status. The owner should verify **GitHub Settings → Password and authentication** and enable 2FA if absent. Extra generic-pattern/validity secret-scanning options were requested but read back disabled; review **Repository Settings → Security → Advanced Security / Secret Protection** if available for the account. They are enhancements, not a reason to disable the already enabled standard protections or delay ordinary source collaboration.

No cTrader-account setting change, credential rotation or live application restart is justified solely by these findings. A rotation would be appropriate if actual credential exposure were identified; this review did not find or assert such exposure. Installing the updated public source does not automatically update a separate existing local installation.

## Primary references

- [Official SDK package metadata](https://pypi.org/pypi/ctrader-open-api/0.9.2/json)
- [cTrader application/account authentication](https://help.ctrader.com/open-api/account-authentication/)
- [service-identity documentation](https://service-identity.readthedocs.io/)
- [GitHub CLI authorization refresh](https://cli.github.com/manual/gh_auth_refresh)
- [GitHub push protection](https://docs.github.com/en/code-security/secret-scanning/introduction/about-push-protection)
- Individual advisory descriptions and patch ranges are linked by GHSA ID in the retained audit snapshot. Reachability statements above are source/constructor observations, not vendor certification.
