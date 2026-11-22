# Security policy

## Supported scope

The current `main` branch and latest public 0.2.x release are the maintenance targets. This is a community project, not an audited or certified trading system; there is no guaranteed response or patch SLA.

## Known dependency advisories

At initial publication on November 22, 2026, GitHub identified **37 open package advisories: 1 critical, 18 high, 13 medium and 5 low** in the preserved reference environment. This is not an exploitability determination, and the counts may change as GitHub updates its database or dependencies change. The critical advisory affects the pinned certifi reference version. Several other legacy packages are constrained by the current upstream optional cTrader SDK (0.9.2).

Track triage and compatible remediation in [issue #14](https://github.com/CptAYounes/sfm-fx-new-age/issues/14). Do not use this initial edition with real accounts or exposed network services as if it were security-cleared. Do not force incompatible dependency versions or merge bot upgrade PRs without resolver, offline regression and explicitly authorized native-compatibility evidence. Secret scanning and passing tests do not resolve these advisories.

## Report vulnerabilities privately

Use [GitHub private vulnerability reporting](https://github.com/CptAYounes/sfm-fx-new-age/security/advisories/new). Do not open a public issue with exploit details, credentials, account information or raw state exports. If private reporting is temporarily unavailable, wait until it is restored rather than posting secrets publicly.

Include the affected commit/version, minimal reproduction with synthetic data, impact and suggested mitigation. Send no real broker credentials, tokens, personal/account records or native market captures. Agree disclosure timing with the maintainer before publishing an exploit.

## Local security boundaries

- Local credential storage uses owner-restricted files; it is not an encrypted OS keychain. Protect the host, backups and file permissions.
- A normal saved session can reconnect when its owner enabled that preference. Use a new `--state-dir` for isolated work.
- Disconnect is not revocation and sign-out is not broker-order cancellation. Revoke compromised grants through the provider.
- Review every plugin and dependency before running it; in-process plugins are not a security sandbox.
- Never bypass Issue/preflight, source identity, unknown-order reconciliation, or freshness checks to make a connection work.

The supplied CI template performs offline application verification, not a live broker audit; it is not activated in the initial public edition. Secret scanning reduces accidental exposure but cannot prove an absence of every secret or vulnerability.
