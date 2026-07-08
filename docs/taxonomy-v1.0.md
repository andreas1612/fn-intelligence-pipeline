# Finalogic Intelligence Pipeline: Tag Taxonomy v1.0

Status: Approved and locked
Version: 1.0
Approved: 07 July 2026
Owner: Finalogic Ltd

## 1. Purpose

This taxonomy defines the complete, controlled set of tags used by the intelligence pipeline. It is used by the AI triage stage and by human reviewers. No tags exist outside this document.

Design principle: simple and useful first. Enhance only when real usage shows a gap.

## 2. Structure

Every item receives tags from four groups:

- Theme: what the item is about (1 to 3 tags)
- Sector: who it targets (0 to 2 tags)
- Jurisdiction: where it applies (exactly 1 tag)
- Type: what kind of document it is (exactly 1 tag)

Urgency and relevance are handled by the scoring criteria, not by tags.

## 3. Theme tags (choose 1 to 3)

### 3.1 ICT and operational resilience (priority cluster)

- **DORA**: Anything arising under or directly implementing Regulation (EU) 2022/2554, including RTS, ITS, guidelines, and oversight activity. Combine with the specific theme below where one clearly applies.
- **ICT risk management**: ICT risk frameworks, governance of ICT risk, security requirements and controls.
- **ICT incident reporting**: Incident classification, notification, and reporting obligations.
- **ICT third-party risk**: Outsourcing, ICT service providers, registers of information, critical third-party provider oversight.
- **Operational resilience**: Business continuity, disaster recovery, resilience testing other than TLPT.
- **TLPT and security testing**: Threat-led penetration testing, red teaming, TIBER-EU.
- **ISO 27001 and standards**: Information security standards, certification schemes, and related frameworks.

### 3.2 AI (priority cluster)

- **AI regulation**: AI Act developments, AI guidance from regulators, AI governance obligations.
- **AI security**: AI-specific threats, model security, secure AI adoption guidance.

### 3.3 Cybersecurity

- **Cyber threats and vulnerabilities**: Threat advisories, significant vulnerabilities, active exploitation, major incidents in the wild.
- **Data protection and privacy**: GDPR and privacy developments relevant to information security work.

### 3.4 Financial regulation

- **Payments and e-money**: PSD2/PSD3, PSR, e-money regime, payment services developments.
- **AML and financial crime**: AML/CFT obligations, fraud, sanctions with an ICT or compliance dimension.
- **Other financial regulation**: Relevant financial-sector regulation not covered above.

### 3.5 Escape valve

- **Other**: No theme fits confidently. Automatically flagged for human review. Repeated use of this tag for similar items is the trigger for a taxonomy change proposal.

Total theme tags: 15.

## 4. Sector tags (choose 0 to 2)

Apply only when an item targets specific sectors. If an item applies broadly across the financial sector, apply no sector tag. Absence of a sector tag means cross-sector.

- **EMIs and payment institutions**
- **Investment firms**
- **Banks and credit institutions**
- **Crypto-asset service providers**
- **Insurance**

Total sector tags: 5.

## 5. Jurisdiction tags (choose exactly 1)

- **EU**: EU-level instruments and publications (EBA, ESMA, EIOPA, EUR-Lex, ENISA, CERT-EU, ESAs Joint Committee).
- **Cyprus**: Cyprus-specific instruments and publications (CySEC, CBC, national transposition, local circulars).
- **International**: Relevant material from outside the EU/Cyprus scope (e.g. global standard setters, major foreign advisories). Expected to be rare.

Total jurisdiction tags: 3.

## 6. Type tags (choose exactly 1)

- **Legislation**: Regulations, directives, delegated and implementing acts, national law.
- **Guidelines and technical standards**: RTS, ITS, guidelines, recommendations, Q&As.
- **Consultation**: Open consultations, discussion papers, calls for evidence.
- **Supervisory communication**: Circulars, announcements, statements, speeches with supervisory weight.
- **Threat advisory**: Security advisories, vulnerability alerts, incident notifications.
- **Report and publication**: Studies, reports, annual publications, thematic reviews.
- **Enforcement**: Fines, sanctions, enforcement decisions, public censures.

Total type tags: 7.

## 7. Tagging rules

1. **Completeness**: Every item receives exactly one Type, exactly one Jurisdiction, 1 to 3 Themes, and 0 to 2 Sectors.
2. **Aboutness**: Tag what the item is substantively about, not everything it mentions in passing.
3. **Specificity**: Prefer the most specific theme available. Use DORA together with the matching pillar theme (e.g. DORA + ICT incident reporting) when both clearly apply.
4. **No ad hoc tags**: The AI and reviewers may only use tags defined in this document. New tags require a version change approved by the owner.
5. **Uncertainty**: If no theme fits confidently, use Other. Items tagged Other are always human-reviewed.

## 8. Change control

- This document is versioned. Changes require owner approval and a version increment.
- Review trigger: quarterly, alongside the source register review, or when the Other tag accumulates a recurring pattern.
- The pipeline configuration and triage prompt must reference the current version number.

## 9. Open items

- TBD: Whether Crypto-asset service providers warrants a MiCA theme tag. Deferred until real item volume justifies it.
- TBD: Client-specific tag views for white-label delivery. Deferred to Phase 6; the sector and theme tags are the filtering basis.

## 10. Version history

- v1.0 (2026-07-07): Initial approved version.
