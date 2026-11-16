# Refactor backlog

Cleanup to do once the client questions are nearly all answered and the build reflects the answers.
Until then, answers keep changing the same flows and rules, so refactoring now would mean doing it
twice. Add new items here as they come up; don't start them early unless a change forces it.

Review taken 12 Nov 2026 from the repo only (no org queries or measured limits).

## When to start

- The LSBC Client Questions doc has no open questions that change flows, rules or the data model
  (open ones about reference data or policy wording are fine).
- Part A of [LSBC_Handoff_Automation_And_UAT.md](LSBC_Handoff_Automation_And_UAT.md) is built.
- UAT has had one full run, so every refactor can be re-tested against known results.

Each refactor still follows CLAUDE.md: propose names first, update the Deployment Manifest and
`package.xml`, and re-run the affected UAT scripts.

## Items, most important first

### 1. Portal form flows have no working generator

The 9 portal form flows (`ScreenFlowIndividualApplication*` for Reciprocity, Renewal, Affidavit,
Retake, Threading Permit, Temporary Permit; `ScreenFlowBusinessLicenseApplication*` for Shop,
Facility, School) are the largest metadata in the repo (40–88 KB each), stored as single-line XML.
They were written by `flowkit.py`, which is not in the repo, then patched by
`scripts/generators/staffintake.py`. Nobody can regenerate them, and git diffs of them can't be
reviewed.

**Do:** look for `flowkit.py` in earlier session transcripts; if found, commit it. Otherwise make
Flow Builder the source of truth: retrieve the 9 flows so they are pretty-printed, and from then on
edit them in the org and retrieve.

**Do now, without waiting:** pretty-print on the next change to any of these flows, so each later
change has a readable diff.

### 2. Decide when the generators stop being the source

Record pages (`pagegen.py`) and the Phase 6 staff flows (`scripts/generators/*.py`) are generated.
If LSBC's admin edits one in Flow Builder or Lightning App Builder, the next generator run silently
overwrites it.

**Do:** keep generating through UAT, then retire the generators before handoff: run each one last
time, retrieve, mark the README "historical", and say in the admin guide that the org is the source.

### 3. Fewer queries in the stop code sync

`SubflowStopCodeSync` runs 35 queries per holder, and it runs after every save of a licence, exam,
fee, bond, payment or relationship (the 100-query limit was already hit once). It has no queries
inside loops, but several lookups repeat the same pattern:

- 5 `Get <Type>Type` lookups (Cosmetologist, Esthetician, two instructor types, Booth Rental
  Permit), each followed by a `Get <Type>License` lookup. Replace with one lookup of the holder's
  current licences with the type name, then collection filters.
- `GetOperatorTypes` + `GetCurrentOperatorLicense`: same, from that one lookup.
- The 4 exam attempt lookups (national, practical, failed practical station, state) and the 3 hours
  lookups: one lookup each, then filter and sort in the flow.

Target is roughly 15–20 queries.

**Waits on:** the booth renter rule (code 6, which licences count) and the manager hold (code 16,
manual or automatic). Both change which licences the sync reads and the `StopCodePerson` and
`StopCodeEstablishment` inputs.

### 4. Shared start-of-form subflow for drafts

All 9 portal forms carry the same copy of the draft handling (`LoopThroughEarlierDrafts` with
`GetEarlierSavedForm` and `DiscardAbandonedDraft`, and `LoopThroughSavedDrafts`). Move it into one
subflow (proposed `Subflow: Preliminary Application Start`) and call it from each form. Do it with
item 1, since it touches the same 9 files.

### 5. Less doc upkeep per change

A deployable change can touch up to 9 places (Deployment Manifest, `package.xml`, Data Model, admin
guide, UAT scripts, client questions, field mapping, design doc change log, CLAUDE.md).

- Generate the Data Model ER diagrams from `force-app` with a script, as `field_coverage.py` reads
  the metadata today.
- Fill the Deployment Manifest change log from `git log`.
- Update the narrative docs (admin guide, Data Model, UAT) per batch or phase; keep only
  `package.xml` and the manifest per commit.

This one doesn't have to wait: it can start whenever doc upkeep gets in the way.

### 6. Split CLAUDE.md

CLAUDE.md is about 280 lines; much of it is the test-record inventory and org quirks (BRE
workarounds, Flow null handling, portal mechanics). Move those to `docs/OrgNotes.md` and
`docs/TestData.md` and keep CLAUDE.md to rules and pointers. The org notes become handoff material
for LSBC's admin.

### 7. Production rule changes leave a gap

An active expression set version can't be redeployed here: it is deactivated, deployed and
reactivated, and every flow that calls it fails meanwhile. Before go-live, add to the Deployment
Manifest's post-deployment steps that rule changes in production run outside portal hours, and
check whether production allows new expression set versions (this sandbox doesn't).

### 8. Housekeeping

- Delete `scripts/apex/hello.apex` and the root `dm_rows.tmp.json`.
- Keep one of `docs/LSBC_Phase1_Stories.xlsx` and `docs/LSBC_Phase1_Stories_Updated.xlsx`.
- Delete the `StopCodeTest` and other test records before UAT data goes in (list in CLAUDE.md).

## Checked and fine as is

- 65 flows, one record-triggered flow per object, 4 Apex classes: proportionate to the scope.
- Rules live in BRE; the flows mostly fetch and save records.
- The renewal form creates an application, fee and checklist per licence inside a loop. A person
  holds 1–3 licences, so it stays well inside limits.
