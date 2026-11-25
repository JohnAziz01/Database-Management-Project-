# Validation results

| Check | Sample | Full |
|---|---:|---:|
| Policies, holders, vehicles, and Liability links (each) | 200 | 678,013 |
| Matched severity rows mapped to claims and payments (each) | 111 | 26,444 |
| Imported payment amount | 250,131.89 | 59,909,216.50 |
| France parent and source regions | 22 | 22 |
| Current imported Liability rates | 21 | 21 |

The original cleaning validator passed. The frequency data retains 36,102 reported claims. All 26,639 severity rows reconcile to 26,444 matched and 195 quarantined rows. Raw severity totals 60,697,930.68, of which 788,714.18 belongs to quarantined rows.

Both exports loaded alongside the team seed into a SQLite translation of the archived PostgreSQL DDL. Checks passed for keys, foreign keys, schema checks supported by SQLite, policy/vehicle owner consistency, claim dates, payment ordering and amounts, premiums, and a current Liability rate in each imported region. The two active demo policies and two team accounts were present after each load.

The actual PostgreSQL `load.sql`, repeat-run behavior, and live API calls still need a scratch PostgreSQL run. PostgreSQL tools were unavailable, Docker's engine was offline, and WSL was inaccessible. The schema on GitHub at commit 715aa37 matched the archived schema after newline normalization. Use the commands in README.md to complete that integration check.

