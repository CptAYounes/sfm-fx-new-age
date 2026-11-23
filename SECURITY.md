# Security policy

## Supported scope

The current `main` branch and latest public 0.2.x release are the maintenance targets. This is a community project, not an audited or certified trading system; there is no guaranteed response or patch SLA.

## Known dependency advisories

The November 23, 2026 **0.2.1** recheck resolves **13 of the original 37 advisories, including the critical certifi finding**, through resolver-compatible updates. The current reference environment matches **24 remaining advisories (12 high, 8 medium, 4 low)**, all in packages pinned directly or transitively by the optional cTrader SDK. No alerts were dismissed to produce the reduction. Package matches are not a completed exploitability determination; current observed exposure and remaining parser/TLS risk are documented in the [security review](docs/security-review.md).

Track remaining work in [issue #14](https://github.com/CptAYounes/sfm-fx-new-age/issues/14). Do not treat the reference stack as security-cleared merely because provider authentication and offline tests pass. Do not force incompatible dependency versions or merge bot upgrade PRs without resolver, offline regression and explicitly authorized native-compatibility evidence. Secret scanning and passing tests do not resolve the SDK-constrained advisories.

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
