# AutoRisk data handoff

This package targets the team’s PostgreSQL schema in the October 9 local GitHub snapshot. The current team schema has the same normalized SHA-256 as the archived schema. This handoff adds files only under autorisk-app/data-handoff. See [ERD.md](ERD.md) for the data team's updated export diagram.

Download and extract AutoRisk-data.zip to use the full CSV export. The sample and import scripts are also available directly in this directory.

## Load a sample or the full data

Use a new PostgreSQL scratch database named `autorisk_import_test`. Run these commands from the package folder in PowerShell after setting `$app` to the absolute path to the team's `autorisk-app` folder. Change `postgres` to your PostgreSQL user if necessary. Compare the current team schema with the archived revision first. `schema.sha256` contains the SHA-256 of the archived SQL with LF newlines.

```powershell
createdb -U postgres autorisk_import_test
psql -X -U postgres -d autorisk_import_test -v ON_ERROR_STOP=1 -f "$app/db/schema.sql"
psql -X -U postgres -d autorisk_import_test -v ON_ERROR_STOP=1 -f "$app/db/seed.sql"
Push-Location sample
psql -X -U postgres -d autorisk_import_test -f ../load.sql
psql -X -U postgres -d autorisk_import_test -f ../load.sql
Pop-Location
Push-Location full
psql -X -U postgres -d autorisk_import_test -f ../load.sql
Pop-Location
```

Stop at any failed command. The team schema script drops existing app tables, so use it only on a disposable database. For a database that already has the matching schema and seed, run only the loader from the desired CSV directory. The loader uses a transaction and stable negative IDs, so source rows and the team’s positive serial IDs can coexist. Identical rows can be loaded again. A conflicting existing row aborts the import. The sample uses the full export’s IDs, so it can be followed by the full load. `policy_coverage.csv` and `rate_table.csv` omit `coverage_id` because the loader resolves the database’s seeded Liability ID.

After loading, point the app at the scratch database. Verify the dashboard still shows two active demo policies, check an imported paid claim, and request a Liability quote for Alsace. Imported historical policies are expired. The France parent and other coverage combinations have no imported quote rates. The archived app's paid total sums all claim payments, so the historical import increases that metric substantially.

## Field provenance

- **Observed**: source policy IDs, driver and vehicle age, brand and power codes, exposure, reported frequency count, geographic attributes, and matched severity amounts. `policy_analytics.csv` retains the source fields that the team schema cannot store directly. `orphan_claims.csv` is an audit file. Neither is loaded into the app database.
- **Derived**: one region row per source region under France, birth and manufacture year relative to the generated policy start, and bonus–malus divided by 50 to align with the prior data script's pricing baseline. The import represents one synthetic holder and one vehicle per policy. Claim IDs are negated cleaned severity row IDs.
- **Demo values**: identity, license, birth and license dates, model placeholder, vehicle power in kW (40 + 10 × (source code − 4), an illustrative mapping), policy dates and existing annual premium estimates, coverage terms, claim and payment dates, and current quote rates. Claim dates are one day after policy start. Payment dates are 30 days after claim date. Each matched severity row is represented as one paid claim and one payment for app compatibility. The source does not supply actual settlement status, payment method, claim dates, premiums, or quote rates. The import uses a neutral fault default and region risk factor. Use exposure and reported claim count from the analytics CSV for frequency calculations. Do not infer exposure from synthetic policy dates.

## Regenerate

Run with Python and pandas from the package folder. The source path is your original project's `data/processed` folder.

```powershell
python export_autorisk.py "$source" full
python export_autorisk.py "$source" sample --sample
python validate_export.py "$teamZip" sample full
```

See [VALIDATION.md](VALIDATION.md) for results and the PostgreSQL verification still required.

