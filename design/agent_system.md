# Crescent Compass: the agent system, cross-referenced

This document reconciles three sources: the ten-page proposal (October 2026, "A friendly atlas for families, neighbours and newcomers"), Kim's brief (the eight-week, $10,000 proposal with 40 verified listings), and the original starter kit (`CLAUDE.md`, `integrations/agent_messaging_future.md`, `research/`, `phoenix_selected/`). Where they differ, Kim's brief is the contractual baseline and the kit's rules are binding; the proposal supplies the human experience and the staged growth path.

## 1. What each source asks for

| Theme | Proposal (10 pages) | Kim's brief | Starter kit | Built now |
|---|---|---|---|---|
| Assistant scope | Discover, coordinate, belong; ask → check → act → record; read / prepare / act-with-authority tiers (p.6, p.8) | Conversational agent is out of scope by default; directory first | Read-only first, feature flag, allow-listed tools, decision records | Read tier live; **prepare** tier live as moderated drafts; act-with-authority not built |
| Onboarding | Five voluntary stages: arrive, orient, settle, contribute, steward; choices not scores; browse without an account (p.2, p.7) | Contributor role with moderated forms; two admins | Rule 8: optional personal settings, anonymous browsing | Join gently: skippable three-step welcome; stages shown as rights held; anonymous browsing untouched |
| Children | Parent-facing only; no child accounts, routes or profiles (p.7) | Caregivers 0–18 | Rule 5 and docs/02: no child locations or profiles | Age *bands* as adult choices; adult confirmation at sign-up; no child fields anywhere |
| Quiet | Quiet is a real choice; mute, decline, leave (p.9) | Not specified | Rule 8: mute/abstain; abstain is a valid action | Dosage few/standard/all; notifications off by default; "forget that"; Compass abstains and says so |
| Honesty | Tell the truth: sources, uncertainty, corrections (p.9) | Last-verified date on every listing | Rule 1, provenance types, decision records | Every answer cites records, shows check dates, writes the eleven-field record |
| Messaging | WhatsApp Business, email, in-app; duplicate-aware ledger (p.4, p.8) | Not in base scope | `agent_messaging_future.md`: separate optional project | Not built; email summaries exist only as an opt-in flag with no sender yet |
| Governance | Monthly listen → review → decide → change → report; eight commitments (p.3, p.9) | Moderation workflow; written acceptance | docs/02 governance loop; hash-chained audit | Audit chain, moderation workflow, About page commitments; monthly report generator still to do |
| Pilot scale | 20 daily users, ~6,000 requests/month, $80–$350/month | $500–$1,000/year operating allowance | Premium services need approval | Daily request cap (200) and LLM off by default keep the pilot inside Kim's allowance; the proposal's monthly range exceeds it and needs written approval before any model spend |

## 2. How the assistant acts (ask → check → act → record)

1. **Ask.** The question is parsed into an intent (age, budget, access need, community, kind of place, events). Saved preferences fill gaps only if the person has allowed Compass to use them, and the answer says which settings were used.
2. **Check.** Four allow-listed, read-only tools run over the published projection only. Hard constraints (age band, verified accessibility) are filters and never relaxed; soft ones (kind, community, cost) may be relaxed one at a time, and the answer says so. The Bayes show test (recommend only when P(current) > 0.75 under the published utilities) separates "recommend" from "listed but not re-verified recently".
3. **Act.** Tier *read*: compose the answer from records, optionally rephrase with Claude, validate every sentence against the records. Tier *prepare*: when a signed-in person says "suggest …" or "correct …", Compass drafts a moderated Submission and reports its number; nothing publishes. Tier *act with authority* (sending messages, writing records): not built; when it is, it follows the proposal's four steps with explicit consent and the kit's server-side permission checks.
4. **Record.** Every answer and every draft writes the eleven provenance fields into the hash-chained audit log, visible on each answer and in the admin.

## 3. What changes on each person's screen (proposal p.7)

| Person | Sees | Does not see |
|---|---|---|
| Visitor | The whole map and directory, events, Compass answers at standard dosage | Saved places, preferences, drafting |
| Joined, oriented | Saved places, chosen dosage, settings-aware Compass, suggestion drafts | Other people's data of any kind |
| Contributor (granted by a steward) | Their own submissions' status; Wagtail access to draft listings if an admin grants it | Publishing |
| Steward / moderator | Review queue, claims, audit log, hazard settings | The AI never grants or expands any of this |

## 4. Memory, honestly

Compass has no long-term memory of people. Its working memory is per session, bounded to six turns, holds record ids and parsed preferences only, is rebuilt when the published projection changes, and is cleared on "forget that". Saved preferences are the person's own explicit choices, editable and deletable from My atlas. The published projection and the audit chain are the only durable memory, and both are governed by humans.

## 5. Open items the owner decides

- Whether the pilot's model spend (proposal: $80–$350/month) is authorised, and at what cap. Until then the LLM stays off and the deterministic composer answers.
- Whether contributor rights are granted by request review (built) or also by invitation.
- When to open the "act with authority" tier (email dispatch first; WhatsApp Business only as a separately approved project per the kit).
- The organisation's visit and contact details for the footer, and photographs for the nine placeholder slots.
