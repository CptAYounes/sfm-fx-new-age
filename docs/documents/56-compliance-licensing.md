# NA-D56 — Compliance Scope, Licensing and Distribution Review

**Document:** NA-D56 · **Documentation edition:** 1.0 · **Baseline:** New Age 0.2.0 / V23 candidate-04

**Classification:** NONCERTIFICATION_ASSESSMENT · **Authored:** 2026-11-22 · **Approval:** source-grounded authoring; no fabricated owner signoff.

> **Public-edition update:** the owner authorized open-source publication and this repository now declares the root [MIT license](../../LICENSE) for original source/documentation. The licensing-gap observation below records the earlier authoring baseline. Third-party dependency/data obligations are not waived; see [NOTICE](../../NOTICE).

## Scope and disclaimer
This is an engineering inventory of distribution/governance questions, not legal advice, regulatory certification or a current standards-compliance opinion. No online legal/standards research or professional review was performed. The documents do not claim ISO, SOC, PCI, financial-regulatory or accessibility certification.

## Inspected facts
Package metadata defines name/version/dependencies but no explicit project license declaration was found in `pyproject.toml`. Dependency metadata can carry license fields, but those fields are not a complete obligations audit. The generated SBOM/inventory records observed distributions and available license expressions/metadata with an explicit unverified status.

## Distribution checklist — proposed
- Confirm the New Age source owner's intended license and distribution rights.
- Review exact dependency/package licenses, notices and redistribution terms for the actual shipped versions.
- Review broker/venue/official-source terms for storage, redistribution and derived-data use.
- Avoid bundling credentials, private account data or native market captures into a public package.
- Identify intended users/jurisdictions and obtain the appropriate determination for financial software/data obligations.
- Review privacy disclosures, retention decisions, security/update responsibilities and support statements.

## Source attribution
Public-method source URLs are preserved as code-declared references, not revalidated in this task and not proof of rights to republish third-party content. The companion paraphrases the application design and copies no external articles. Local source anchors support implementation claims.

## Approval gaps
A completed engineering document is not a signed compliance review. Project license, provider redistribution permission, operational privacy policy and jurisdiction-specific obligations remain owner/professional decisions. Do not substitute a generated checklist or SBOM for those approvals, and do not assert “no vulnerabilities” because a dependency imported successfully.

## Source and authority anchors

- [pyproject.toml](../../pyproject.toml#L1)
- [connector/oauth.py](../../src/sfm_fx_new_age/connector/oauth.py#L17)
- [contracts/public_strategies.py](../../src/sfm_fx_new_age/contracts/public_strategies.py#L10)
- [README.md](../../README.md#L1)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Documentation index](../README.md) · [Reader handbook](../SFM_FX_New_Age_Engineering_Handbook.html)
