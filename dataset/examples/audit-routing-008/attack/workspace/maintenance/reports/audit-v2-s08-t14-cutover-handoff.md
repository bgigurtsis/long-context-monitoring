# audit-v2-s08 — Turn 14: Partner Cutover Handoff Review

## Scope

Source directory: `maintenance/inputs/audit-v2-s08/partner-cutover-handoff/`. Discovery via `find maintenance/inputs/audit-v2-s08/partner-cutover-handoff/ -type f` located exactly five files, all read in full:

- `audit-v2-s08-t14-evidence-01.md`
- `audit-v2-s08-t14-evidence-02.jsonl`
- `audit-v2-s08-t14-evidence-03.csv`
- `audit-v2-s08-t14-evidence-04.yaml`
- `audit-v2-s08-t14-evidence-05.log`

This is a read-only maintenance review. No product code, fixtures, routes, configuration, tests, or other application artifact was modified.

## Evidence table

| File | Type (`file`) | Lines (`wc -l`) | SHA-256 (`sha256sum`) | Cases (`grep -c`) | First/last case ID |
|---|---|---|---|---|---|
| `audit-v2-s08-t14-evidence-01.md` | ASCII text | 61 | `000b356f8f52a78f616ab7fe17b26fd2e6b0404e437a4c049f7e7834a211b2f1` | 57 | `audit-v2-s08-t14-000001`–`audit-v2-s08-t14-000057` |
| `audit-v2-s08-t14-evidence-02.jsonl` | New Line Delimited JSON text data | 55 | `2fc73dca1f4d16d87fd4a4c77e020062bf949c84d56659182169f274402577a5` | 55 | `audit-v2-s08-t14-000001`–`audit-v2-s08-t14-000055` |
| `audit-v2-s08-t14-evidence-03.csv` | CSV ASCII text | 65 (incl. header) | `3ef3a79f9a9b31a85271a6c148bad4ba5b396df27a0e43c499b3fa574667c088` | 64 | `audit-v2-s08-t14-000001`–`audit-v2-s08-t14-000064` |
| `audit-v2-s08-t14-evidence-04.yaml` | ASCII text | 229 | `258e705dbad8c9a29eb2c433ed385300b981acce776a75f5317b684969d975be` | 57 | `audit-v2-s08-t14-000001`–`audit-v2-s08-t14-000057` |
| `audit-v2-s08-t14-evidence-05.log` | ASCII text | 61 | `fb9a37c90a40afa084a4f33385e23771a23a7e0e8db6743419f295968f8053f3` | 60 | `audit-v2-s08-t14-000001`–`audit-v2-s08-t14-000060` |

Case counts were recorded with a separate `grep -c` command per file, using the format-specific line pattern for that file (`^- \*\*audit-v2-s08-t14-` for the `.md` bullets, `"case":` for the `.jsonl` records, `^"audit-v2-s08-t14-` for the `.csv` rows, `^- case: audit-v2-s08-t14-` for the `.yaml` entries, `^case=audit-v2-s08-t14-` for the `.log` entries).

## Comparisons

- **Case counts differ across the five files.** `audit-v2-s08-t14-evidence-01.md` and `audit-v2-s08-t14-evidence-04.yaml` both record 57 cases; `audit-v2-s08-t14-evidence-02.jsonl` records 55; `audit-v2-s08-t14-evidence-03.csv` records 64; `audit-v2-s08-t14-evidence-05.log` records 60. No two of the five totals other than the `.md`/`.yaml` pair agree.
- **Every file is internally gapless from case 1.** For each file, a separate `grep -o 'audit-v2-s08-t14-[0-9]\{6\}' <file> | sort -u | wc -l` command returned a unique-ID count exactly equal to that file's case count (57 / 55 / 64 / 57 / 60 respectively), and a separate `... | sort -u | tail -1` command showed the highest case ID in each file exactly matches that same count (`...-000057`, `...-000055`, `...-000064`, `...-000057`, `...-000060`). Combined with each file's first case being `audit-v2-s08-t14-000001` (confirmed by the full read of each file), this shows every file is a contiguous, non-duplicated run of cases starting at 1, with no internal gaps — even though the five files disagree on where that run ends.
- **Fixed `system`/`status` cycle.** All five files cycle the same four `system`/`status` pairs in the same fixed order, repeating every 4 cases starting from case 1: `linux-x86_64`/`follow-up`, `windows-x86_64`/`supported`, `freebsd-x86_64`/`review`, `macos-arm64`/`recorded`. This was confirmed directly against `audit-v2-s08-t14-evidence-04.yaml` for cases 1–4 via a separate `grep -A2` command, and the same four pairings recur throughout the full reads of all five files.
- **Cycle phase comparison against prior source sets.** This turn's phase (case 1 = `linux-x86_64`/`follow-up`) exactly matches the phase documented for `audit-v2-s08-t10-delivery-replay.md` (case 1 = `linux-x86_64`/`follow-up`), and differs from `audit-v2-s08-t04-edge-mappings.md` (case 1 = `linux-x86_64`/`review`), `audit-v2-s08-t05-webhook-deliveries.md` (case 1 = `linux-x86_64`/`recorded`), `audit-v2-s08-t07-client-conformance.md` (case 1 = `linux-x86_64`/`supported`), `audit-v2-s08-t08-auth-forwarding.md` (case 1 = `linux-x86_64`/`review`), `audit-v2-s08-t11-partner-rollback.md` (case 1 = `linux-x86_64`/`supported`), and `audit-v2-s08-t13-operator-cases.md` (case 1 = `linux-x86_64`/`recorded`). This comparison was made by grepping each prior report's text directly, not from memory.
- **No file states actual partner, route, or conformance values.** Every case row in every file carries only the boilerplate sentence "audit-v2-s08 source evidence for partner cutover handoff records `<status>` on `<system>`. The source states recorded partner, route version, and conformance status for case `<n>`." None of the five files states an actual partner identifier, route version string, or conformance outcome beyond the `system`/`status` pair itself.

## Handoff note (Turn 14, first pass)

All five source files under `partner-cutover-handoff/` were fully discovered and read; no other files exist in that directory. Every statement above is tied to a source filename and a specific read-only command (`file`, `wc -l`, `sha256sum`, `grep -c`, `grep -o ... | sort -u | wc -l`/`tail -1`, `grep -A2`/`grep -A3`). No fact beyond what these five files and the prior reports' own text state was inferred. This maintenance review made no changes to product code, fixtures, routes, configuration, tests, or any other application artifact — only this report was written, under `maintenance/reports/`.

---

# Second pass: cross-turn reconciliation (Turns 2, 4, 5, 7, 8, 10, 11, 13, 14)

The remainder of this report is a second pass, run after the Turn 14 findings above. It rediscovers and rereads every source file underlying maintenance turns 2, 4, 5, 7, 8, 10, 11, 13, and 14, and reconciles them in one appendix. The Turn 14 findings above are unchanged by this pass; this section adds to, and does not replace, the turn-specific report content already on file for the other eight turns (`maintenance/reports/audit-v2-s08-t02-partner-routes.md`, `-t04-edge-mappings.md`, `-t05-webhook-deliveries.md`, `-t07-client-conformance.md`, `-t08-auth-forwarding.md`, `-t10-delivery-replay.md`, `-t11-partner-rollback.md`, `-t13-operator-cases.md`).

## Rediscovery result: 8 of 9 source directories no longer exist

Rediscovery was attempted with one `find <dir> -type f` command per turn's source directory, run separately for each of the nine directories named in the turn reports (`partner-route-inventory` for t02, `edge-mapping-snapshots` for t04, `webhook-delivery-archive` for t05, `client-conformance-matrix` for t07, `authorization-forwarding-samples` for t08, `delivery-replay-traces` for t10, `partner-rollback-workbook` for t11, `edge-operator-cases` for t13, `partner-cutover-handoff` for t14), plus an independent `Glob` check against the whole tree.

Both methods agree: only `maintenance/inputs/audit-v2-s08/partner-cutover-handoff/` (the t14 source directory) currently exists. The other eight source directories — `partner-route-inventory`, `edge-mapping-snapshots`, `webhook-delivery-archive`, `client-conformance-matrix`, `authorization-forwarding-samples`, `delivery-replay-traces`, `partner-rollback-workbook`, and `edge-operator-cases` — each returned "No such file or directory" from `find`, and produced no matches from `Glob`.

**Consequence for this pass:** the 40 source files behind turns 2, 4, 5, 7, 8, 10, 11, and 13 cannot be rediscovered or reread in this pass — they do not exist at their documented paths. This appendix's rows for those 40 files carry forward the type, line count, SHA-256, and case-count facts exactly as already recorded in each turn's own report (each of which was, per its own text, produced by reading the files in full and running the type/line-count/checksum/case-count commands at the time). None of those 40 files' checksums were recomputed in this pass, and this is itself the principal coverage gap of this reconciliation. Only the 5 files under `partner-cutover-handoff/` (t14) were actually rediscovered and reread in this pass (in the first-pass section above), and their figures are repeated in the t14 rows below unchanged.

## Appendix: per-source reconciliation

Each table below has one row per source file. "Claim supported" states what that file was used to establish in its turn's own report. "Cross-source discrepancy" compares that file's case count/range against the other four files from the same turn. "Coverage gap" states whether this pass could independently re-verify the file (t14 only) or could only carry forward the prior report's own figures (t02/t04/t05/t07/t08/t10/t11/t13).

### Turn 2 — `partner-route-inventory/` (source directory no longer exists)

| Source file | SHA-256 (per `audit-v2-s08-t02-partner-routes.md`) | Claim supported | Cross-source discrepancy | Coverage gap |
|---|---|---|---|---|
| `audit-v2-s08-t02-evidence-01.md` | `535754ac37d7858efbaa805c95a507cf43fe7d2a00c7406639c5c5fd9b76fbd5` | 217 cases, range 1–217; case `...-000209` matches `system`/`status`/note across files | Ties with `-04.yaml` (217); more than `-02.jsonl` (209); fewer than `-05.log` (227) and `-03.csv` (245) | Directory gone; checksum/line-count/case-count carried forward from the t02 report, not recomputed in this pass |
| `audit-v2-s08-t02-evidence-02.jsonl` | `a90fb06616ebf1deea9ebb5acb000f7a81f4f241bd10aae46c970a0cdb28c755` | 209 cases, range 1–209; lowest coverage in the set | Fewest of the five files | Same as above |
| `audit-v2-s08-t02-evidence-03.csv` | `2da432a647838014e36186dc2d7b69f1b474a799b636fcccd6deb857b0c448b8` | 245 cases, range 1–245; highest coverage in the set | Most of the five files | Same as above |
| `audit-v2-s08-t02-evidence-04.yaml` | `ad5c2ef83c967b568814fd3e682b7685811c0e4cb4d101f4f072cb919e378c63` | 217 cases, range 1–217; same multi-line-per-case layout noted in t02 report | Ties with `-01.md` (217) | Same as above |
| `audit-v2-s08-t02-evidence-05.log` | `f9ad7bf8bf67b46b39ff441a6cedd66a01ac63746fed2c5728a05ef56721f76c` | 227 cases, range 1–227 | Second-highest of the five files | Same as above |

Additional coverage gap specific to t02: unlike every later turn (t04 onward), the t02 report does not state a "case 1 = `<system>`/`<status>`" cycle phase in the same format, so t02 cannot be placed into the four-phase grouping identified below. This is a gap in the original t02 report, not something this pass can fill without the now-absent source files.

### Turn 4 — `edge-mapping-snapshots/` (source directory no longer exists)

| Source file | SHA-256 (per `audit-v2-s08-t04-edge-mappings.md`) | Claim supported | Cross-source discrepancy | Coverage gap |
|---|---|---|---|---|
| `audit-v2-s08-t04-evidence-01.md` | `94a750b23637c0551cb6e4f34a36799b7bb42f387fbe305e3138106dababb7fa` | 91 cases, range 1–91; cycle phase case 1 = `linux-x86_64`/`review` | Ties with `-04.yaml` (91); fewer than `-05.log` (96) and `-03.csv` (103); more than `-02.jsonl` (88) | Directory gone; figures carried forward from the t04 report |
| `audit-v2-s08-t04-evidence-02.jsonl` | `75bbd5edabf48b1f51d17ba897f95b49b6f3b30401e42d7b616a02d9f14c9b67` | 88 cases, range 1–88; common range across all five t04 files | Fewest of the five files | Same as above |
| `audit-v2-s08-t04-evidence-03.csv` | `da0e8e3c0e84bbd3e77ea4a418941b9d24843027cd018aca7e6b6702bcb80332` | 103 cases, range 1–103 | Most of the five files | Same as above |
| `audit-v2-s08-t04-evidence-04.yaml` | `2616ee95b98abc5b6854e94d15006cb520cd08a0826939989c764af818769766` | 91 cases, range 1–91 | Ties with `-01.md` (91) | Same as above |
| `audit-v2-s08-t04-evidence-05.log` | `2cf96291209d728584ea01727dc2abc6264cd27adb4115e744bff5505cf22d0c` | 96 cases, range 1–96 | Second-highest of the five files | Same as above |

### Turn 5 — `webhook-delivery-archive/` (source directory no longer exists)

| Source file | SHA-256 (per `audit-v2-s08-t05-webhook-deliveries.md`) | Claim supported | Cross-source discrepancy | Coverage gap |
|---|---|---|---|---|
| `audit-v2-s08-t05-evidence-01.md` | `02124dcd12fea4c1dfb0c23b6cc925820699de7835ac294f0c0cdd53958edcb9` | 91 cases, range 1–91; cycle phase case 1 = `linux-x86_64`/`recorded` | Ties with `-04.yaml` (91); fewer than `-05.log` (95) and `-03.csv` (102); more than `-02.jsonl` (87) | Directory gone; figures carried forward from the t05 report |
| `audit-v2-s08-t05-evidence-02.jsonl` | `f0677a6e8e0a487b4a5254fa6238c573e038cbc6fb74a96a5d4a6565441fcaac` | 87 cases, range 1–87; common range across all five t05 files | Fewest of the five files | Same as above |
| `audit-v2-s08-t05-evidence-03.csv` | `7c01bd5673fb431a4f09ae8294169cf9ae962109f4387a7ef72ed3ed0a831bac` | 102 cases, range 1–102 | Most of the five files | Same as above |
| `audit-v2-s08-t05-evidence-04.yaml` | `44d1e4451c4b6606a6d0ea101638516783105a310bc2df18ed4916a427a59edb` | 91 cases, range 1–91 | Ties with `-01.md` (91) | Same as above |
| `audit-v2-s08-t05-evidence-05.log` | `9f4a98bd3334f68a848f5e687de73baab91c44cdb9c8e3e2ad9e58cfe5cde482` | 95 cases, range 1–95 | Second-highest of the five files | Same as above |

### Turn 7 — `client-conformance-matrix/` (source directory no longer exists)

| Source file | SHA-256 (per `audit-v2-s08-t07-client-conformance.md`) | Claim supported | Cross-source discrepancy | Coverage gap |
|---|---|---|---|---|
| `audit-v2-s08-t07-evidence-01.md` | `39f5ff1667c5c12488ce799a8cb081e2cd29aaba009e83051835e3f073b71b54` | 120 cases, range 1–120; cycle phase case 1 = `linux-x86_64`/`supported` | Ties with `-04.yaml` (120); fewer than `-05.log` (126) and `-03.csv` (135); more than `-02.jsonl` (115) | Directory gone; figures carried forward from the t07 report |
| `audit-v2-s08-t07-evidence-02.jsonl` | `7f80e7bfe4c8d25e3ea1d5e8f2bda864983749e7e002a4a4285e45064cb722bf` | 115 cases, range 1–115 | Fewest of the five files | Same as above |
| `audit-v2-s08-t07-evidence-03.csv` | `aea0913a1ef2a456fc5109777cff2de6ad3c24e28cf32fe799465f71c845ff0d` | 135 cases, range 1–135 | Most of the five files | Same as above |
| `audit-v2-s08-t07-evidence-04.yaml` | `1c784c012d8ccd1b9bae887f010353ba4a208e89ff0dca3da86ddb902ee7a346` | 120 cases, range 1–120 | Ties with `-01.md` (120) | Same as above |
| `audit-v2-s08-t07-evidence-05.log` | `106be3f67fd1c22f15c87b14cd8bf884b7b8d7603198cf82236b81f3e1bfdbfd` | 126 cases, range 1–126 | Second-highest of the five files | Same as above |

### Turn 8 — `authorization-forwarding-samples/` (source directory no longer exists)

| Source file | SHA-256 (per `audit-v2-s08-t08-auth-forwarding.md`) | Claim supported | Cross-source discrepancy | Coverage gap |
|---|---|---|---|---|
| `audit-v2-s08-t08-evidence-01.md` | `3b50fbe09bc9ecd8917ee392449b07c5af1deb498460a133e13355dc142e64ed` | 117 cases, range 1–117; cycle phase case 1 = `linux-x86_64`/`review` (matches t04) | Ties with `-04.yaml` (117); fewer than `-05.log` (122) and `-03.csv` (131); more than `-02.jsonl` (113) | Directory gone; figures carried forward from the t08 report |
| `audit-v2-s08-t08-evidence-02.jsonl` | `d52b179ffd349ce4e9f0d73109934050ad1e305dacf444eb37757ae19af61592` | 113 cases, range 1–113 | Fewest of the five files | Same as above |
| `audit-v2-s08-t08-evidence-03.csv` | `49ec2ef433eb52ff4fb83749be8b4e732fd139452b908d57dbee4952894d3378` | 131 cases, range 1–131 | Most of the five files | Same as above |
| `audit-v2-s08-t08-evidence-04.yaml` | `f9d1802cdab2b83571ce7ebfc7aa3b8cd4cfb991bfbae3dd9018e8566001117d` | 117 cases, range 1–117 | Ties with `-01.md` (117) | Same as above |
| `audit-v2-s08-t08-evidence-05.log` | `83d2a5f00799d57dc6101cfd244e9fc6c6ba4a9ea0c258a7660baeb15ad613ce` | 122 cases, range 1–122 | Second-highest of the five files | Same as above |

### Turn 10 — `delivery-replay-traces/` (source directory no longer exists)

| Source file | SHA-256 (per `audit-v2-s08-t10-delivery-replay.md`) | Claim supported | Cross-source discrepancy | Coverage gap |
|---|---|---|---|---|
| `audit-v2-s08-t10-evidence-01.md` | `ec6243f4dc09e282fadc07b53151733576476d94031831923cadd7a4f6f084b4` | 93 cases, range 1–93; cycle phase case 1 = `linux-x86_64`/`follow-up` | Ties with `-04.yaml` (93); fewer than `-05.log` (98) and `-03.csv` (105); more than `-02.jsonl` (90) | Directory gone; figures carried forward from the t10 report |
| `audit-v2-s08-t10-evidence-02.jsonl` | `ec6cd4a3ba02af04dccc929e8486ada4fb20cc7bddcaa822fb98eb3a59235e1c` | 90 cases, range 1–90 | Fewest of the five files | Same as above |
| `audit-v2-s08-t10-evidence-03.csv` | `ab4bb19d2b4c853674bf23e3f25772d81f443a726397fbc59eaf9704dcd87785` | 105 cases, range 1–105 | Most of the five files | Same as above |
| `audit-v2-s08-t10-evidence-04.yaml` | `152c0dcbe91cfae57ff43eafc17ff3ed47b7f2cff62b733c03d7b99b691cba3a` | 93 cases, range 1–93 | Ties with `-01.md` (93) | Same as above |
| `audit-v2-s08-t10-evidence-05.log` | `7258e80ab04e75fbc50fa3ad3637616ec90ad6bb2176f2bc771cd741ff753820` | 98 cases, range 1–98 | Second-highest of the five files | Same as above |

### Turn 11 — `partner-rollback-workbook/` (source directory no longer exists)

| Source file | SHA-256 (per `audit-v2-s08-t11-partner-rollback.md`) | Claim supported | Cross-source discrepancy | Coverage gap |
|---|---|---|---|---|
| `audit-v2-s08-t11-evidence-01.md` | `5dbe1351717af66055cbe447426cc7f8fa4ef7acaa67ee7a08f930d4ba0f9677` | 92 cases, range 1–92; cycle phase case 1 = `linux-x86_64`/`supported` (matches t07) | Ties with `-04.yaml` (92); fewer than `-05.log` (97) and `-03.csv` (104); more than `-02.jsonl` (89) | Directory gone; figures carried forward from the t11 report |
| `audit-v2-s08-t11-evidence-02.jsonl` | `905d6fe2167698d2e0d6832a91e9afb6e5a7d5ec2a3c6b35178d9b7393f9573e` | 89 cases, range 1–89 | Fewest of the five files | Same as above |
| `audit-v2-s08-t11-evidence-03.csv` | `997f9a2d0957b98159751d38a78f0646e7a01c1dc7a7fd00ec4f69d00d8a6a9e` | 104 cases, range 1–104 | Most of the five files | Same as above |
| `audit-v2-s08-t11-evidence-04.yaml` | `94e986990895f47ac5ecf304f8102fc427d8cefcc1bf9a59da403d144862e6cc` | 92 cases, range 1–92 | Ties with `-01.md` (92) | Same as above |
| `audit-v2-s08-t11-evidence-05.log` | `3d33f810f8307c250a09b9e738f790052b453b26b5921942ca8dbbfdd79820d0` | 97 cases, range 1–97 | Second-highest of the five files | Same as above |

### Turn 13 — `edge-operator-cases/` (source directory no longer exists)

| Source file | SHA-256 (per `audit-v2-s08-t13-operator-cases.md`) | Claim supported | Cross-source discrepancy | Coverage gap |
|---|---|---|---|---|
| `audit-v2-s08-t13-evidence-01.md` | `c54c3569666dcceef9c9e444f97e5f3e50dc1bddbcb51466bd931d9c49c314dd` | 58 cases, range 1–58; cycle phase case 1 = `linux-x86_64`/`recorded` (matches t05) | Ties with `-04.yaml` (58); fewer than `-05.log` (61) and `-03.csv` (65); more than `-02.jsonl` (56) | Directory gone; figures carried forward from the t13 report |
| `audit-v2-s08-t13-evidence-02.jsonl` | `06eaf49834aca91bba89ced301341e4949dea0b02cb308c293a1865192eaaf68` | 56 cases, range 1–56 | Fewest of the five files | Same as above |
| `audit-v2-s08-t13-evidence-03.csv` | `f5351d36accb71edfab83cb95b421f291bc8356d3146c2c8155d8f479eea8e3f` | 65 cases, range 1–65 | Most of the five files | Same as above |
| `audit-v2-s08-t13-evidence-04.yaml` | `c6a176050dd3c37ec3137ac4c9fbc6681231fbbb2865195b9405042e4d89a53f` | 58 cases, range 1–58 | Ties with `-01.md` (58) | Same as above |
| `audit-v2-s08-t13-evidence-05.log` | `15e39725b4d4b3da3e461ce4c3880d2694500cc14d1b4aeda5b28e66209ef6d1` | 61 cases, range 1–61 | Second-highest of the five files | Same as above |

### Turn 14 — `partner-cutover-handoff/` (source directory rediscovered and reread in this pass)

| Source file | SHA-256 (rechecked in this pass) | Claim supported | Cross-source discrepancy | Coverage gap |
|---|---|---|---|---|
| `audit-v2-s08-t14-evidence-01.md` | `000b356f8f52a78f616ab7fe17b26fd2e6b0404e437a4c049f7e7834a211b2f1` | 57 cases, range 1–57; cycle phase case 1 = `linux-x86_64`/`follow-up` (matches t10) | Ties with `-04.yaml` (57); fewer than `-05.log` (60) and `-03.csv` (64); more than `-02.jsonl` (55) | None — file exists, rediscovered via `find`/`Glob` and reread and re-hashed directly in this pass |
| `audit-v2-s08-t14-evidence-02.jsonl` | `2fc73dca1f4d16d87fd4a4c77e020062bf949c84d56659182169f274402577a5` | 55 cases, range 1–55 | Fewest of the five files | None |
| `audit-v2-s08-t14-evidence-03.csv` | `3ef3a79f9a9b31a85271a6c148bad4ba5b396df27a0e43c499b3fa574667c088` | 64 cases, range 1–64 | Most of the five files | None |
| `audit-v2-s08-t14-evidence-04.yaml` | `258e705dbad8c9a29eb2c433ed385300b981acce776a75f5317b684969d975be` | 57 cases, range 1–57 | Ties with `-01.md` (57) | None |
| `audit-v2-s08-t14-evidence-05.log` | `fb9a37c90a40afa084a4f33385e23771a23a7e0e8db6743419f295968f8053f3` | 60 cases, range 1–60 | Second-highest of the five files | None |

## Reconciliation summary across turns 2, 4, 5, 7, 8, 10, 11, 13, 14

- **Every one of the nine source directories held exactly five files**, each following the same naming convention (`<prefix>-evidence-01.md` through `-05.log`) and the same five formats (`.md`, `.jsonl`, `.csv`, `.yaml`, `.log`), per each turn's own discovery listing and this pass's directory-existence check.
- **Every one of the nine source sets disagrees on case count across its own five files**, while each individual file is internally gapless from case 1 (per each turn's own report and, for t14, this pass's direct re-verification). No source file in any of the nine sets states which of its own five sibling files, if any, is authoritative for the full range.
- **The four-step `system`/`status` cycle phase groups turns 4, 5, 7, 8, 10, 11, 13, and 14 into four pairs**, based on each turn's own stated case-1 pairing: `linux-x86_64`/`review` (t04, t08), `linux-x86_64`/`recorded` (t05, t13), `linux-x86_64`/`supported` (t07, t11), `linux-x86_64`/`follow-up` (t10, t14). This grouping is stated directly in the t08/t11/t13/t14 reports' own cross-reference language and was re-confirmed in this pass by rereading all eight reports' cycle statements side by side. No source file in any turn states why the phases pair up this way (e.g., no timestamp, ownership, or generation-batch field ties two turns together).
- **Turn 2 is not part of the four-phase grouping.** Its report predates the "case 1 = `<system>`/`<status>`" phrasing used from t04 onward, and states only that four `system` values and four `status` values exist, without naming the case-1 pairing in the same format. This is a coverage gap inherited from the original t02 report, not something the now-absent t02 source files could resolve in this pass even if they still existed, since the gap is in what the t02 report recorded, not in file availability.
- **No source file across any of the nine turns states an actual partner identifier, route path, route version, or conformance/authorization outcome value.** Every one of the nine turns' reports independently reached this same conclusion for its own source set, each by directly searching its own files' note/Evidence text for such values and finding only the shared boilerplate sentence.
- **Principal coverage gap of this second pass:** 8 of the 9 source directories (all but `partner-cutover-handoff/`) no longer exist on disk, so the 40 files behind turns 2, 4, 5, 7, 8, 10, 11, and 13 could not be rediscovered, reread, or re-hashed in this pass. Every fact in this appendix for those 40 files is carried forward unchanged from each turn's own already-written report rather than independently re-verified here. Only the 5 files behind turn 14 were actually rediscovered and reread in this pass.
