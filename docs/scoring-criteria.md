# Finalogic Intelligence Pipeline: Scoring Criteria v1.3

Status: Approved and locked
Version: 1.3
Approved: 07 July 2026 (v1.0), 09 July 2026 (v1.1, v1.2), 10 July 2026 (v1.3)
Owner: Finalogic Ltd

## 1. Purpose

This document defines how items are scored for relevance and urgency. The rules are used verbatim in the AI triage prompt and by human reviewers. The AI score is advisory. Human reviewers may override any score at the review gate, and overrides are recorded.

Companion document: `taxonomy-v1.0.md`. Scoring happens after tagging.

## 2. Scoring scale

Every item that passes auto-discard receives exactly one level:

| Level | Meaning | Handling |
|---|---|---|
| Urgent | Requires attention before the next weekly digest | Immediate alert, plus inclusion in the digest |
| High | Significant development for Finalogic or its clients | Leads the weekly digest |
| Standard | Relevant, worth knowing | Included in the weekly digest |
| Low | Marginal relevance, kept for the record | Archived and searchable, not distributed |

## 3. Auto-discard (before scoring)

Discard without scoring only when an item is clearly out of scope. All discards are logged with the rule applied.

- **AD-1**: Duplicate of an item already in the system (content hash match).
- **AD-2**: No connection to financial-sector regulation, cybersecurity, information security, or AI. Examples: monetary policy statistics, staff appointments, event photography, consumer-only content with no institutional angle.
- **AD-3**: Administrative page changes with no substantive content (page moved, format reissued without change).

Rule of caution: if in doubt, do not discard. Score Low instead.

## 4. Urgent (narrow by design)

Urgent protects the credibility of the alert channel. An item is Urgent only if at least one of the following applies:

- **U-1**: A vulnerability that is critical, actively exploited or with public exploit code, AND in systems widely used by Finalogic or its client base. Both clauses must hold. If the supplied text establishes the vulnerability is critical and exploited but does not evidence that the affected system is widely used by Finalogic or its client base, U-1 does not apply: the item is not finalised as Urgent. It then takes the level it would hold absent any Urgent test (in most cases High via H-4, since these are broad-impact cybersecurity items short of the Urgent tests) and is flagged F-2 for human review. The provisional level is this cascaded level, not Urgent. This clause is unfillable from source text alone until the client-systems reference list exists (section 12); until then, U-1 without evidenced client-base relevance always routes to human review rather than auto-firing the alert channel.
- **U-2**: A threat advisory or incident notification that requires same-week action by Finalogic or its clients.
- **U-3**: A regulatory instrument or supervisory communication with immediate effect or a compliance deadline within 30 days.
- **U-4**: An enforcement action or supervisory statement directly affecting an active client obligation.

If none of U-1 to U-4 applies, the item is not Urgent, regardless of media attention.

## 5. High

An item is High if it is not Urgent and at least one of the following applies:

- **H-1**: New or materially changed obligations under a priority cluster theme (ICT and operational resilience cluster, or AI cluster, per taxonomy sections 3.1 and 3.2).
- **H-2**: A Cyprus-jurisdiction item from CySEC or CBC that affects regulated entities' obligations or supervision.
- **H-3**: An open consultation where a response could matter to Finalogic or its clients.
- **H-4**: A cybersecurity development with credible, broad impact on the financial sector, short of the Urgent tests.
- **H-5**: Final adoption or entry into force of legislation previously tracked.

## 6. Standard

- **S-1**: An item is Standard if it is relevant to Finalogic's scope but meets no High or Urgent test. Typical examples: reports and thematic reviews, speeches with supervisory weight, guidance clarifications, non-critical advisories, early-stage legislative developments.

## 7. Low

- **L-1**: An item is Low if relevance is marginal but the item is worth keeping for the archive. Typical examples: tangential publications, minor updates to tracked material, international items with weak EU or Cyprus linkage.

## 8. Theme weighting rules

- **W-1**: Priority cluster themes (sections 3.1 and 3.2 of the taxonomy) default one level higher than the same content would score under a general theme, capped by the Urgent tests. Urgent is never reached by weighting alone.
- **W-2**: Cyprus jurisdiction items default one level higher than equivalent EU items, for the same reason: they are closest to client obligations.
- **W-3**: Weighting rules never lower a score.

## 9. Confidence and flagging

The AI must flag an item for human review, instead of finalising the score, when any of the following applies:

- **F-1**: The item was tagged Other (taxonomy rule 5).
- **F-2**: The AI cannot determine whether an Urgent test applies from the supplied text. This includes the mandatory case in U-1: if the client-base relevance clause cannot be evidenced from the supplied text, the item must be flagged F-2 rather than finalised as Urgent.
- **F-3**: The supplied text is truncated, paywalled, or otherwise insufficient to score.
- **F-4**: Two levels appear equally applicable and no rule resolves the tie.

Flagged items enter the review queue with the AI's provisional level and its stated reason for uncertainty. The AI never resolves uncertainty by guessing upward or downward.

## 10. Review gate

- All Urgent items are human-verified before an alert is sent. No exceptions.
- Human overrides of AI scores are recorded (original level, final level, reason). Override patterns feed threshold tuning in Phase 5.

## 11. Change control

- Versioned with owner approval, same regime as the taxonomy.
- Review trigger: quarterly, or when override patterns show systematic mis-scoring.

## 12. Open items

- TBD: Urgent alert delivery channel (see DECISIONS.md open items).
- TBD: Whether U-1 should reference a maintained list of "systems widely used by the client base". Deferred; reviewer judgement applies in v1.0.

## 13. Version history

- v1.3 (2026-07-10): Resolved an ambiguity in the v1.2 U-1 wording. "Its provisional level" is now defined: when U-1's client-base clause cannot be evidenced, the item takes the level it would hold absent any Urgent test (High via H-4 in most cases), not Urgent, and is flagged F-2. Fixes the split in the first v1.2 run where ten items cascaded to High and three held Urgent on the same rule. Logged as D-021.
- v1.2 (2026-07-09): U-1 second clause (client-base relevance) made a mandatory flag condition. An item meeting the critical-exploited clause but lacking evidenced client-base relevance in the supplied text is flagged F-2 for human review, not finalised as Urgent. Fixes over-firing found in the first full triage run (13 of 35 items scored Urgent, 11 asserting U-1 while unable to test its second clause). No new rule IDs. Logged as D-020.
- v1.1 (2026-07-09): Added rule IDs S-1 (Standard) and L-1 (Low) to sections 6 and 7, so all four levels are citable in rules_applied per D-016. No change to scoring behaviour; the level definitions and examples are unchanged. Logged as D-019.
- v1.0 (2026-07-07): Initial approved version.
