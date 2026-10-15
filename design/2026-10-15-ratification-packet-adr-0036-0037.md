# Ratification packet: Proposed ADRs 0036 and 0037

**decision packet — not a decision.** Non-authoritative; prepared 2026-10-15
against `31f93bb93b6748e4e3f619c0fb0f70d7599f6929`. Both ADRs remain Proposed,
Implementation: None. This packet records no ratification, closes no gap and
authorizes no implementation.

## One-page decision brief

**Decision:** ratify Proposed [0036](../decisions/0036-strict-payload-keys.md)
and Proposed [0037](../decisions/0037-o3-mention-discovery.md), including their
single [V1–V9 bundle](../decisions/0036-strict-payload-keys.md#shared-version-boundary)?
Implementation requires both authority receipts.

| Ratification would commit to | Practical consequence |
|---|---|
| 0036: explicit projector `"4"`, envelope schema `"1"`, lineage `nyx-belief-lineage/4` | Recursively reject decoded duplicate keys before side effects; validate raw text independently at append/read/replay/verifier boundaries. Unique-key noncanonical spelling remains admissible. Canonical hashes authenticate content, not original spelling. |
| Compatibility/adoption | Preserve old text/last-wins interpretation, IDs, exact retries and frozen results. `"4"` inherits `"3"` claim semantics/refusals. Full-log integrity precedes cutoff: frozen replay refuses strict suffixes. Prove every supported old prefix on a distinct working copy. |
| 0037: public, same-database mention index | Explicit `"2"`/`"3"`/`"4"`; exact/prefix search, every mention, complete typed traversal, no scalar winner. Listings order by ID; search by text bytes then mention ID. Pages default/max 100/1,000; lifecycle default all. |
| Joint schema 6/publication | Exact O8 layout plus two amended committed constraints; unchanged schema-4/5 opens, explicit copy migration/backfill. Retained owner enrollment configuration; atomic projection/index/readiness/progress after separate append. Strict writing works with O3 disabled. |
| Query/recovery behavior | Unavailable differs from empty; valid older pages disclose global staleness. Changed publication restarts cursors. History explicitly replays. Strict append makes old O3 unavailable; mixed discovery selects `"4"`. Reads record no usage or repair. |

**Recorded drafting rulings:** Josh selected **C/B** on 2026-10-14, then **“all
recommended”**: strict **Yes / Permissive / Yes / Yes / Yes**; O3 **Yes / Text /
Yes / All / Label / Yes (100/1,000) / Yes**. The proposals reconcile all 31 original
worksheet answers, including O3 search order/version changes. Those follow-up
answers authorize drafting, not ratification or other proposals.

**Audit history:** Dot's [PR #23](https://github.com/axendo79/ProjectNyx/pull/23)
audit at `194076d`: **no findings** in contracts/design records.
[PR #24](https://github.com/axendo79/ProjectNyx/pull/24) contract review at
`31f93bb`: **no findings** in the plan, gap wording or acceptance traceability;
same tree as `11f92fe`. Both were **UNVERIFIED source-only**: no execution,
checker or test behavior verified; neither ratifies or proves implementation.

**Risks:** lost raw text; retry/readiness ordering; lost enrollment obligations;
structurally valid incomplete indexes; migration/concurrency/crash boundaries;
text-bearing cursor/backup copies; repeated pagination restarts. Independent
witnesses are required. Numeric/resource/private-codec, erasure, report correction,
merge/split and usage blockers remain. Specialized report API guards stay frozen.

**First three slices unlocked:** (1) joint authority receipts/explicit selectors;
(2) final schema-6 layout/constraints; (3) frozen schema-4/5 opens and unavailability
without mutation. These prepare later parser, migration and query work.

**Josh's yes/no checklist** (blank means unanswered; this packet selects none):

- [ ] Yes / No: ratify S1–S8/O1–O12/V1–V9 as written?
- [ ] Yes / No: accept historical/mixed-log limits and working-copy adoption?
- [ ] Yes / No: accept public copies, stale pages, restarts and explicit enrollment?
- [ ] Yes / No: require T1–T10/A1–A12, independent completeness and actual crash evidence?
- [ ] Yes / No: make both authority commits, then separately authorize implementation?

A No requires revised authority. No drafting answer is missing in this scope.

## Josh-only authority-commit steps

Run later in an **isolated authority worktree**, not the pinned `D:\ProjectNyx`
checkout. These commands are instructions for Josh; none was executed by this
documentation task. Start from a clean index. Ratify each ADR separately in
dependency order; do not mix implementation files into either commit.

1. In `decisions/0036-strict-payload-keys.md`, explicitly record Josh's acceptance
   date and ratification of S1–S8/V1–V9/T1–T10, including the dependency on 0037.
   Reconcile prospective status/supersession wording with that acceptance; keep
   Implementation: None. Stage and inspect only that authority record, then commit:

```powershell
git add -- decisions/0036-strict-payload-keys.md
git status --short
git diff --cached --check
git diff --cached
$env:NYX_AUTHORITY_COMMIT = '1' # Josh alone
try {
    git commit -m 'authority: ratify ADR 0036 strict payload keys'
    if ($LASTEXITCODE -ne 0) { throw 'Commit failed; stop here.' }
}
finally { Remove-Item Env:NYX_AUTHORITY_COMMIT }
git show --stat --oneline HEAD
```

2. In `decisions/0037-o3-mention-discovery.md`, explicitly record Josh's
   acceptance date and ratification of O1–O12/A1–A12 and the same referenced
   V1–V9 bundle. Reconcile prospective wording; keep Implementation: None. Then:

```powershell
git add -- decisions/0037-o3-mention-discovery.md
git status --short
git diff --cached --check
git diff --cached
$env:NYX_AUTHORITY_COMMIT = '1' # Josh alone
try {
    git commit -m 'authority: ratify ADR 0037 public mention discovery'
    if ($LASTEXITCODE -ne 0) { throw 'Commit failed; stop here.' }
}
finally { Remove-Item Env:NYX_AUTHORITY_COMMIT }
git show --stat --oneline HEAD
```

Inspect each displayed status/diff before proceeding. Any failed check or commit
stops this sequence; never bypass the hook. If the accepted contract requires
additional authority amendments, review and stage those explicitly with the
corresponding ADR, never invent them during implementation. Supply both resulting
hashes and confirmation before activation. Implement one ADR per commit in
dependency order; after each implementation commit, separately stage its one-line
Implementation marker citing that hash for Josh's authority commit. Those
markers are not part of the implementation commits or this packet.

## Evidence and navigation

The [25-slice preparation plan](2026-10-14-adr-0036-0037-implementation-plan.md)
maps prospective acceptance families to dependencies. Its 81 local `.pending`
functions / 654 planned cases are planning counts, not collected/passing tests;
the ignored artifacts are not present in this fresh worktree. No acceptance
draft is activated by this packet. See also the
[blocked-gap worksheets](2026-10-15-blocked-gaps-worksheets.md) and
[authority protocol](../AGENTS.md#adr-commit-protocol).

Audit evidence read locally: `D:\eTPSDotty\2026-10-14-projectnyx-pr23-194076d-audit-4e5facdf426a.md`
and `D:\eTPSDotty\2026-10-15-projectnyx-31f93bb-contract-review.md`. The PR #22
worksheet audit (`2026-10-14-projectnyx-pr22-165363d-audit-da2bb398fcf6.md`)
also reported no findings, source-only; its earlier worksheets supply the format,
not authority. Current execution evidence is recorded separately in this
worktree's ignored `scratch/EVIDENCE.md`, with raw logs and the final commit hash.

Exact reviewed heads: PR #23 `194076da8b2e8b5fdf29b57c72a399d53b344c17`;
contract review `31f93bb93b6748e4e3f619c0fb0f70d7599f6929`; prior content head
`11f92fe1219f471462f1bcf4b9bcaaa773bedfc5`. Historical Proposed 0027/0028
allocations require reconciliation when those proposals are revised; neither
this packet nor the 0036/0037 drafting rulings approve their implementation.
