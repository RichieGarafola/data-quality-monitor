"""
Generate a government procurement reporting dataset with injected quality issues.
Run once: python scripts/generate_sample_data.py
"""

import csv
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(99)
OUTPUT = Path(__file__).parent.parent / "data" / "sample" / "sample_procurement.csv"
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

VENDORS = [
    "Booz Allen Hamilton", "Leidos", "SAIC", "General Dynamics IT",
    "Peraton", "ManTech International", "CACI International",
    "Accenture Federal", "Deloitte Consulting", "DXC Technology",
    "Engility Corporation", "Parsons Corporation", "L3Harris Technologies",
    "Maximus Federal", "ICF International", "Noblis", "Unison",
    "PAE Government Services", "Telos Corporation", "Intelligent Systems",
]
AGENCIES = [
    "Department of Defense", "Department of Homeland Security",
    "Department of Energy", "Department of Veterans Affairs",
    "Health and Human Services", "Department of Justice",
    "Department of Transportation", "Department of State",
    "General Services Administration", "NASA",
    "Social Security Administration", "Department of Education",
    "Department of Labor", "Department of Commerce",
]
NAICS_VALID = [
    "541511", "541512", "541513", "541519",
    "541611", "541618", "541690",
    "541330", "541380", "541620",
    "611710", "611420",
    "518210", "517110",
]
SET_ASIDES = [
    "Small Business", "8(a)", "HUBZone", "WOSB", "SDVOSB",
    "Unrestricted", "VOSB", "Total Small Business",
]
STATES = [
    "VA", "MD", "DC", "CA", "TX", "NY", "FL", "GA", "IL", "OH",
    "PA", "NC", "AZ", "CO", "WA", "MA", "MN", "OR", "NJ", "SC",
]
DOMAINS = ["mail.gov", "agency.gov", "fedmail.gov", "govmail.net", "contractor.com"]


def rand_date(start, end):
    d = start + timedelta(days=random.randint(0, (end - start).days))
    fmt = random.choice(["%Y-%m-%d", "%m/%d/%Y", "%Y-%m-%d", "%Y-%m-%d"])
    return d.strftime(fmt)


def rand_phone():
    choice = random.random()
    if choice < 0.72:
        return f"({random.randint(200, 999)}) {random.randint(200, 999)}-{random.randint(1000, 9999)}"
    if choice < 0.82:
        return f"{random.randint(2000000000, 9999999999)}"
    if choice < 0.90:
        return f"555-{random.randint(1000, 9999)}"
    return ""


def rand_email(vendor_slug, corrupt=False):
    if corrupt:
        return random.choice([
            f"{vendor_slug}",
            f"@{random.choice(DOMAINS)}",
            f"{vendor_slug}..contracts@{random.choice(DOMAINS)}",
            "",
        ])
    return f"{vendor_slug}.contracts@{random.choice(DOMAINS)}"


def rand_naics(corrupt=False):
    if corrupt:
        return random.choice([
            str(random.randint(10000, 99999)),
            str(random.randint(1000000, 9999999)),
            "NAICS-" + str(random.randint(1000, 9999)),
            "",
        ])
    return random.choice(NAICS_VALID)


rows = []
for i in range(1, 121):
    vendor = random.choice(VENDORS)
    vendor_slug = vendor.split()[0].lower()
    agency = random.choice(AGENCIES)

    contract_value = random.choice([
        random.randint(50_000, 2_500_000),
        random.randint(50_000, 2_500_000),
        random.randint(50_000, 2_500_000),
        random.randint(10_000_000, 50_000_000),
        -random.randint(5_000, 50_000),
    ])

    obligation_amount = random.choice([
        random.randint(25_000, 1_500_000),
        random.randint(25_000, 1_500_000),
        random.randint(25_000, 1_500_000),
        random.randint(8_000_000, 40_000_000),
        -random.randint(1_000, 20_000),
    ])

    corrupt_email = random.random() < 0.12
    corrupt_naics = random.random() < 0.06

    award = date(2022, 1, 1) + timedelta(days=random.randint(0, 1200))
    period_end = award + timedelta(days=random.randint(180, 1095))

    rows.append({
        "contract_id":       f"CON-{award.year}{award.month:02d}-{i:04d}" if random.random() > 0.03 else "",
        "vendor_name":       vendor if random.random() > 0.04 else "",
        "agency_name":       agency if random.random() > 0.05 else "",
        "naics_code":        rand_naics(corrupt=corrupt_naics),
        "contract_value":    contract_value if random.random() > 0.04 else "",
        "award_date":        rand_date(date(2022, 1, 1), date(2025, 6, 1)),
        "period_end_date":   period_end.strftime(random.choice(["%Y-%m-%d", "%m/%d/%Y"])),
        "set_aside_type":    random.choice(SET_ASIDES) if random.random() > 0.04 else "Unknown",
        "vendor_email":      rand_email(vendor_slug, corrupt=corrupt_email),
        "vendor_phone":      rand_phone(),
        "state_code":        random.choice(STATES) if random.random() > 0.04 else "ZZ",
        "obligation_amount": obligation_amount if random.random() > 0.04 else "",
    })

# Inject duplicates
for _ in range(8):
    rows.append(random.choice(rows[:80]))

random.shuffle(rows)

FIELDS = [
    "contract_id", "vendor_name", "agency_name", "naics_code",
    "contract_value", "award_date", "period_end_date", "set_aside_type",
    "vendor_email", "vendor_phone", "state_code", "obligation_amount",
]

with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=FIELDS)
    writer.writeheader()
    writer.writerows(rows)

print(f"Generated {len(rows)} rows -> {OUTPUT}")
