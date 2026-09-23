# Dual-Track Backlink Prospecting Matrix

English · [简体中文](README.zh-CN.md) · Version 1.1.1 · [MIT License](LICENSE)

This open-source Codex skill suite separates backlink prospecting into two independent tracks: high-volume submission candidates and higher-investment editorial opportunities. A shared source, deduplication, batching, and workbook contract connects both tracks.

The matrix helps acquire, compress, screen, deduplicate, and package prospects. It is not an automated link-blasting tool and does not promise acceptance, link attributes, traffic, or rankings.

## Two tracks

| Track | Primary objective | Screening approach |
|---|---|---|
| Batch submission | Expand the pool of lawful, relevant, executable product-listing prospects | Permissive: login, CAPTCHA, manual review, and `nofollow` are allowed; formal articles, mandatory reciprocal links or badges, and clear deletion risk are excluded |
| Quality editorial | Find opportunities worth content and outreach effort | Balance topic fit, admission difficulty, and expected return; an undisclosed fee is not treated as free |

## Skill matrix

| Skill | Responsibility | Main outputs |
|---|---|---|
| `backlink-expansion-matrix` | Freeze scope, route stages, inspect handoffs, and enforce status boundaries | Project route, stage boundaries, acceptance result |
| `backlink-source-prep` | Prepare organic competitors, Backlink Gap exports, referring domains, and public lists | Source register, consolidated pool, exclusions, priority pool, summary |
| `backlink-batch-expansion` | Screen directories, product listings, startup databases, community profiles, and resource pages | Executable batch pool, reserve pool, exclusions |
| `backlink-quality-expansion` | Screen guest articles, industry publications, expert contributions, and editorial resource pages | Free editorial prospects, paid or fee-unknown prospects, exclusions |
| `backlink-workbook-delivery` | Deduplicate history and tracks, freeze batches, build workbooks, and run QA | Free/paid workbooks, dedup log, QA report |

## Workflow

```text
Target brands and delivery requirements
        │
        ▼
Organic competitors and other reference sources
        │
        ▼
Backlink Gap / referring domains / history / public resources
        │
        ▼
Normalize, consolidate, remove noise, create priority pool
        │
        ├───────────────┐
        ▼               ▼
Batch track        Quality track
        │               │
        └───────┬───────┘
                ▼
 Historical and cross-track deduplication
                │
                ▼
       Free / paid execution workbooks
```

## Why compress before screening

Backlink exports can contain repeated referring domains, repeated target–domain pairs, irrelevant networks, and multiple URLs pointing to the same submission route. Normalize and consolidate the raw files first, then prioritize domains for site-level review. The repository intentionally contains no real brand list, business dataset, account detail, historical submission record, or project-specific threshold.

## Installation

Run from the repository root:

```sh
cp -R 双线外链挖掘矩阵/skills/* ~/.codex/skills/
```

The installed skills can then be invoked directly:

```text
$backlink-expansion-matrix
$backlink-source-prep
$backlink-batch-expansion
$backlink-quality-expansion
$backlink-workbook-delivery
```

## Complete practical tutorial

### Step 0: Freeze the scope

Provide Codex with:

- canonical brand names and websites;
- whether the batch track, quality track, or both are required;
- existing prospect workbooks, historical submissions, and frozen batches;
- whether the target means “top up to N” or “create a new batch of N”;
- batch size;
- whether Semrush browser export is authorized;
- whether subagent parallelism is explicitly authorized;
- final visible columns and output location.

“Top up A existing rows to B” means adding `B-A` rows, not producing another B rows.

Suggested starting prompt:

```text
Use $backlink-expansion-matrix to start a dual-track backlink expansion project.
The target brands are ...; top up the batch track to ... rows and the quality track to ... rows.
Historical submissions are located at ...; each final workbook needs Free and Paid sheets.
Freeze the scope and report missing inputs first. Do not perform real submissions.
```

### Step 1: Create a working directory

A practical layout is:

```text
workspace/
├── 01-source-materials/
│   ├── organic-competitors/
│   ├── semrush-backlink-gap-raw/
│   ├── historical-prospects/
│   └── historical-submissions/
├── 02-candidate-pools/
│   ├── batch-track/
│   └── quality-track/
├── 03-deliverables/
└── 04-process-and-qa/
```

Copy and register source files without overwriting them. Keep intermediate pools, exclusions, QA reports, and final workbooks separate.

### Step 2: Obtain organic competitors

Export the complete Semrush organic-competitor report for every target site. Select reference competitors using a combination of:

- competitor relevance;
- shared keywords;
- organic keywords and estimated organic traffic;
- product and audience fit;
- whether the competitor’s link sources can plausibly inform the target brand.

Do not restrict the entire project to a single comparison batch. Build a broader reference pool first, then split it according to the comparison slots supported by the current product interface.

### Step 3: Export Backlink Gap batches

Use the batch size supported by the current product interface. Record the target, competitors, batch number, and export date. A useful naming convention is:

```text
gap-target-domain-batch01-YYYY-MM-DD.csv
gap-target-domain-batch02-YYYY-MM-DD.csv
```

During browser work:

- use only the account and browser session authorized by the user;
- do not access unrelated pages or change account, security, or subscription settings;
- stop at CAPTCHA or security verification instead of bypassing it;
- register each export immediately to avoid missing or repeating batches.

Organic competitors and competitor backlinks are independent sources. The first answers “who is worth studying”; the second answers “where those competitors obtained links.”

### Step 4: Audit raw exports

Run:

```sh
python3 skills/backlink-source-prep/scripts/audit_semrush_exports.py \
  --input-dir /path/to/semrush-exports \
  --report /path/to/source-audit.json
```

This script inventories CSV count, nonblank rows, empty files, read errors, and header variants. It does not determine whether a domain is a valid submission platform and does not replace business screening.

### Step 5: Consolidate and compress source data

Invoke:

```text
Use $backlink-source-prep to process these Semrush exports.
Preserve source files and provenance, normalize domains, and output a consolidated pool,
an exclusion table, a priority pool, and a statistical report.
Do not describe source candidates as verified submission platforms.
```

Recommended compression order:

1. Remove blank and unparseable records.
2. Merge identical target–referring-domain pairs.
3. Mark owned domains and competitor-owned domains.
4. Exclude obvious shorteners, gambling, malware, mirrors, and spam patterns.
5. Calculate target coverage, competitor coverage, and cross-target unique domains.
6. Prioritize with coverage, authority, traffic, and topic signals.

Include data volume in filenames, for example:

```text
backlink-gap-raw-<rows>-rows-<files>-files/
consolidated-candidates-<rows>-rows.csv
priority-candidates-<rows>-rows.csv
excluded-records-<rows>-rows.csv
```

A high-authority generic site is not automatically a submission platform. A small vertical directory should not be discarded solely because its authority is low.

### Step 6: Screen the batch track

Invoke:

```text
Use $backlink-batch-expansion to expand the batch-submission track from the priority pool.
Favor scale. Allow registration, login, CAPTCHA, manual review, and nofollow.
Exclude opportunities requiring a formal article, mandatory reciprocal link or badge,
or carrying a clear deletion risk. Output executable, reserve, and excluded pools.
Do not build the final workbook yet.
```

If an explicit entry cannot be found but the domain remains useful, place it in the reserve pool instead of inventing `/submit`. Different real submission objects on the same domain may be retained; paths resolving to the same form should be consolidated.

Validate the pool:

```sh
python3 skills/backlink-batch-expansion/scripts/validate_candidate_pool.py \
  --input /path/to/candidate-pool.csv \
  --report /path/to/candidate-pool-qa.json
```

### Step 7: Screen the quality track

Invoke:

```text
Use $backlink-quality-expansion to expand the editorial quality track.
Evaluate topic fit, admission difficulty, and expected return separately.
Prefer official contribution guidelines and editorial policies as evidence.
Output free, paid or fee-unknown, reserve, and excluded pools.
Do not write the article, contact editors, or pay.
```

If the same publication offers both free editorial contribution and paid branded content, both can be retained as separate opportunities with separate URLs, conditions, and fees. An unknown fee must not be classified as free.

### Step 8: Deduplicate history and freeze batches

Invoke:

```text
Use $backlink-workbook-delivery to deduplicate both tracks against historical submissions,
cross-track entries, and frozen exported batches. If the historical file has no brand field,
state that only platform-level deduplication is possible; do not claim a specific brand was submitted.
Keep exported batches frozen.
```

Deduplication has three layers:

1. normalized URL;
2. entry-level judgment within the same platform domain;
3. historical submissions, earlier batches, and cross-track conflicts.

The same entry cannot appear in both tracks. A real tool-submission route and a separate editorial-contribution route on the same domain may both remain.

### Step 9: Build execution workbooks

The default is one workbook per track with `Free` and `Paid` sheets. Visible columns are:

```text
Domain | URL | Submission conditions | Suitable brand websites
```

Confirmed-free routes go to `Free`. Confirmed-paid routes go to `Paid`. Fee-unknown routes also go to `Paid`, with “fee to be confirmed” stated in the conditions and counted separately in QA. Provenance, evidence, status, and internal IDs remain in the internal candidate pool.

Validate the delivery CSV before creating XLSX:

```sh
python3 skills/backlink-workbook-delivery/scripts/validate_delivery_csv.py \
  --input /path/to/delivery.csv \
  --report /path/to/delivery-qa.json
```

After creating XLSX, reimport it to check sheet names, columns, row counts, and formula errors. Visually inspect the top, bottom, and newly appended region of every sheet. Visual inspection does not replace data validation.

### Step 10: Feed execution results into the next batch

After real execution begins, collect a user-approved feedback sample from the first batch. Record:

- whether the route still works;
- actual free or paid status;
- login or CAPTCHA requirements;
- mandatory reciprocal-link or badge requirements;
- brand fit;
- submitted, awaiting review, published, rejected, or outcome unknown.

If route failure, forced payment, or brand mismatch rises materially, adjust ordering and screening before generating the next batch. Candidate count, actual submissions, and public placements must remain separate metrics.

## Common invocation patterns

### Source preparation only

```text
Use $backlink-source-prep to inventory and prepare these exports. Deliver only the source register,
consolidated pool, exclusions, priority pool, and statistical report. Stop before site screening.
```

### Top up the batch track

```text
Use $backlink-batch-expansion to top up the existing batch workbook from A to B rows.
Add only B-A rows and preserve existing batch membership.
```

### Create a new quality batch

```text
Use $backlink-quality-expansion to create N new editorial prospects.
Balance topic fit, admission difficulty, and expected return. Do not classify unknown fees as free.
```

### Deduplication and workbook delivery only

```text
Use $backlink-workbook-delivery with the screened pools and historical submissions.
Only deduplicate, freeze batches, split Free/Paid sheets, and run QA. Do not research new sites.
```

## Acceptance checklist

- Source files were not overwritten.
- Every prospect retains traceable provenance.
- Batch and quality tracks did not use the same screening threshold.
- Fee-unknown prospects were not reported as free.
- Normalized URLs, platform domains, historical files, and frozen batches were checked.
- Exported batches were not reassigned.
- Workbooks expose only requested columns.
- Workbooks were reimported and visually inspected.
- Deliverables are labeled as execution candidates.
- A reachable page, existing form, or HTTP 200 was not reported as a completed submission or placement.

## Data and execution boundaries

- The repository contains only generic workflows, rules, templates, and validators. It contains no proprietary brand configuration, business dataset, project statistics, submission history, or account information.
- Semrush, competitor backlinks, and public lists are prospect sources, not proof of eligibility.
- Without separate authorization, the skills do not register, log in, pay, submit, or contact site owners.
- CAPTCHA and security verification must be completed through the site’s native flow or by the user, never bypassed.

## Directory structure

```text
双线外链挖掘矩阵/
├── README.md
├── README.zh-CN.md
├── LICENSE
├── matrix.yaml
└── skills/
    ├── backlink-expansion-matrix/
    ├── backlink-source-prep/
    ├── backlink-batch-expansion/
    ├── backlink-quality-expansion/
    └── backlink-workbook-delivery/
```

## License

[MIT](LICENSE)
