"""Build the AutoRisk import CSVs from the validated freMTPL2 intermediates."""
import argparse
from pathlib import Path

import pandas as pd


def export(source, out, sample):
    out.mkdir(parents=True, exist_ok=True)
    p = pd.read_csv(source / "policies_enriched.csv")
    c = pd.read_csv(source / "claims_clean.csv", dtype={"claim_amount": "string"})
    orphan = pd.read_csv(source / "orphan_claims.csv", dtype={"claim_amount": "string"})
    assert p.policy_id.is_unique and c.claim_id.is_unique
    assert c.policy_id.isin(p.policy_id).all()
    assert not orphan.policy_id.isin(p.policy_id).any()
    if sample:
        # Include claims from every region that has matched severity records.
        example_claims = c.merge(p[["policy_id", "region"]], on="policy_id")
        ids = example_claims.groupby("region").head(5).policy_id
        p = p[p.policy_id.isin(ids) | p.policy_id.isin(p.groupby("region").head(5).policy_id)]
        c = c[c.policy_id.isin(p.policy_id)]

    def save(table_name, **columns):
        pd.DataFrame(columns).to_csv(out / (table_name + ".csv"), index=False, lineterminator="\n")

    region_map = {name: -i for i, name in enumerate(sorted(p.region.unique()), 2)}
    save("region", region_id=[-1, *region_map.values()], name=["France", *region_map],
         region_type=["Country", *(["Region"] * len(region_map))],
         parent_region_id=["", *([-1] * len(region_map))], base_risk_factor="1.00")

    ids = -p.policy_id
    start = pd.to_datetime(p.effective_date)
    end = pd.to_datetime(p.expiry_date)
    birth_year = start.dt.year - p.driver_age
    premium = p.annual_premium.round(2)
    assert (end > start).all()
    assert p.vehicle_power.between(4, 15).all()
    save("policyholder", policyholder_id=ids, first_name="Demo", last_name="Driver " + p.policy_id.astype(str),
         date_of_birth=birth_year.astype(str) + "-01-01",
         license_number="FMTPL-" + p.policy_id.astype(str),
         license_issue_date=(birth_year + 18).astype(str) + "-01-01",
         email="fmtpl-" + p.policy_id.astype(str) + "@example.invalid",
         region_id=p.region.map(region_map))
    save("vehicle", vehicle_id=ids, policyholder_id=ids, make=p.vehicle_brand, model="Unknown",
         manufacture_year=start.dt.year - p.vehicle_age,
         engine_power_kw=40 + (p.vehicle_power - 4) * 10, usage_type="Other")
    save("policy", policy_id=ids, policyholder_id=ids, vehicle_id=ids,
         start_date=p.effective_date, end_date=p.expiry_date, status="Expired",
         bonus_malus_coefficient=(p.bonus_malus / 50).round(2), total_premium=premium)
    save("policy_coverage", policy_id=ids, coverage_limit="100000.00",
         deductible="0.00", coverage_premium=premium)
    claim_dates = c.policy_id.map(pd.Series(start.array, index=p.policy_id)) + pd.Timedelta(days=1)
    assert claim_dates.lt(c.policy_id.map(pd.Series(end.array, index=p.policy_id))).all()
    claim_ids = -c.claim_id
    save("claim", claim_id=claim_ids, policy_id=-c.policy_id,
         claim_date=claim_dates.dt.strftime("%Y-%m-%d"),
         claim_type="Liability", status="Paid",
         reported_at=claim_dates.dt.strftime("%Y-%m-%d 00:00:00"))
    save("claim_payment", claim_id=claim_ids, payment_seq=1,
         payment_date=(claim_dates + pd.Timedelta(days=30)).dt.strftime("%Y-%m-%d"),
         amount=c.claim_amount, payment_method="Unknown", status="Paid")
    save("rate_table", rate_table_id=list(region_map.values()), region_id=list(region_map.values()),
         effective_date="2026-01-01", base_rate="450.00", age_factor_young="1.35",
         age_factor_senior="1.20", vehicle_power_factor="1.05", bonus_malus_step="1.00")
    analytics = pd.read_csv(source / "policies_clean.csv")
    analytics = analytics[analytics.policy_id.isin(p.policy_id)].copy()
    analytics.insert(1, "autorisk_policy_id", -analytics.policy_id)
    analytics.to_csv(out / "policy_analytics.csv", index=False, lineterminator="\n")
    orphan.to_csv(out / "orphan_claims.csv", index=False, lineterminator="\n")

    from decimal import Decimal
    total = sum(map(Decimal, c.claim_amount))
    if not sample:
        assert (len(p), len(c), len(orphan), total) == (678013, 26444, 195, Decimal("59909216.50"))
        assert analytics.reported_claim_count.sum() == 36102
    print(f"{out}: {len(p):,} policies, {len(c):,} claims, {total:,.2f} payments, {len(orphan)} quarantined")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Original data/processed directory")
    parser.add_argument("output", type=Path)
    parser.add_argument("--sample", action="store_true")
    args = parser.parse_args()
    export(args.source, args.output, args.sample)

