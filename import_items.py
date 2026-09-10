import re
import pandas as pd
import psycopg

# ============================================================
# Import CPI item details into:
#   1. dim_item
#   2. dim_unit
#   3. dim_brand
#   4. cpi_collection_item
#
# The CSV is expected to contain at least:
#   outletcode
#   item_details
# ============================================================

csv_path = r"F:\CPI_CapiApplication\cpi\Item details.csv"

DB = {
    "dbname": "cpi_test",
    "user": "postgres",
    "password": "Welcome@123",
    "host": "localhost",
    "port": "5432",
}


def clean_text(value):
    """Return clean text or None."""
    if value is None or pd.isna(value):
        return None
    value = str(value).strip()
    return value if value else None


def get_part(text, label):
    """
    Extract values like:
    Type: ... | Size of units: ... | Unit of Measure: ...

    This also handles Brand values followed by '| Made in ...'.
    """
    if not text:
        return None
    pattern = rf"{re.escape(label)}:\s*(.*?)(?=\s*\|\s*[A-Za-z ]+:|$)"
    match = re.search(pattern, text, flags=re.IGNORECASE)
    return match.group(1).strip() if match else None


def get_item_name(text):
    """Get item name before the first pipe symbol."""
    if not text:
        return None
    return text.split("|")[0].strip()


def get_last_price(text):
    """Extract last price month and price from text."""
    if not text:
        return None, None
    match = re.search(
        r"Last Price:\s*([A-Za-z_0-9]+)\s*Price:\s*([0-9]+(?:\.[0-9]+)?)",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return None, None
    return match.group(1), float(match.group(2))


def parse_brand_and_country(item_details):
    """
    Correctly split strings like:
    Brand: Maharani | Made in India

    Returns:
    brand_name = Maharani
    country_text = India
    """
    brand_name = get_part(item_details, "Brand")
    country_text = get_part(item_details, "Made in")

    # If the brand field accidentally captured 'Brand | Made in ...', split it.
    if brand_name and "|" in brand_name:
        parts = [p.strip() for p in brand_name.split("|")]
        brand_name = parts[0] if parts else None
        for part in parts[1:]:
            if part.lower().startswith("made in"):
                country_text = part[7:].strip()

    # Clean cases such as 'Made in India' still appearing in country_text.
    if country_text and country_text.lower().startswith("made in"):
        country_text = country_text[7:].strip()

    # Avoid storing blank country values from text like 'Made in'
    if country_text in ("", None):
        country_text = None

    return clean_text(brand_name), clean_text(country_text)


def normalize_unit(unit_name):
    if not unit_name:
        return None, None
    raw = unit_name.strip()
    low = raw.lower()
    if low in ("kg", "kgs", "kilogram", "kilograms"):
        return "KG", "Kg"
    if low in ("g", "gm", "gram", "grams"):
        return "G", "g"
    if low in ("piece", "pieces", "pcs", "pc"):
        return "PC", "Piece"
    return raw.upper(), raw


def parse_size(size_value_raw):
    if not size_value_raw:
        return None
    match = re.search(r"[0-9]+(?:\.[0-9]+)?", str(size_value_raw))
    return float(match.group(0)) if match else None


# Read CSV
# dtype=str keeps leading zeros in outlet codes if they exist.
df = pd.read_csv(csv_path, dtype=str)
df.columns = df.columns.str.strip().str.lower()

required_columns = {"outletcode", "item_details"}
missing = required_columns - set(df.columns)
if missing:
    raise ValueError(f"Missing required CSV columns: {missing}")

inserted_rows = 0
skipped_rows = 0

conn = psycopg.connect(**DB)

with conn:
    with conn.cursor() as cur:
        for row_no, row in df.iterrows():
            item_details = clean_text(row.get("item_details"))
            outlet_code_raw = clean_text(row.get("outletcode"))

            if not item_details or not outlet_code_raw:
                skipped_rows += 1
                print(f"Skipped row {row_no + 2}: missing outletcode or item_details")
                continue

            outlet_code = outlet_code_raw.zfill(4)

            item_name = get_item_name(item_details)
            spec_type = get_part(item_details, "Type")
            size_value_raw = get_part(item_details, "Size of units")
            unit_name_raw = get_part(item_details, "Unit of Measure")
            material = clean_text(get_part(item_details, "Material"))
            brand_name, country_text = parse_brand_and_country(item_details)
            last_price_month, last_price = get_last_price(item_details)
            size_value = parse_size(size_value_raw)

            if not item_name:
                skipped_rows += 1
                print(f"Skipped row {row_no + 2}: item name not found")
                continue

            # 1. Insert item master
            cur.execute(
                """
                insert into dim_item (item_name, is_active, created_at, updated_at)
                values (%s, true, now(), now())
                on conflict do nothing;
                """,
                (item_name,),
            )
            cur.execute(
                """
                select item_id
                from dim_item
                where lower(trim(item_name)) = lower(trim(%s))
                limit 1;
                """,
                (item_name,),
            )
            item_result = cur.fetchone()
            if not item_result:
                skipped_rows += 1
                print(f"Skipped row {row_no + 2}: item not found/created - {item_name}")
                continue
            item_id = item_result[0]

            # 2. Unit
            unit_id = None
            unit_code, unit_name = normalize_unit(unit_name_raw)
            if unit_name:
                cur.execute(
                    """
                    insert into dim_unit (unit_code, unit_name)
                    values (%s, %s)
                    on conflict do nothing;
                    """,
                    (unit_code, unit_name),
                )
                cur.execute(
                    """
                    select unit_id
                    from dim_unit
                    where lower(trim(unit_name)) = lower(trim(%s))
                       or lower(trim(unit_code)) = lower(trim(%s))
                    limit 1;
                    """,
                    (unit_name, unit_code),
                )
                unit_result = cur.fetchone()
                unit_id = unit_result[0] if unit_result else None

            # 3. Brand
            brand_id = None
            if brand_name:
                cur.execute(
                    """
                    insert into dim_brand (brand_name)
                    values (%s)
                    on conflict do nothing;
                    """,
                    (brand_name,),
                )
                cur.execute(
                    """
                    select brand_id
                    from dim_brand
                    where lower(trim(brand_name)) = lower(trim(%s))
                    limit 1;
                    """,
                    (brand_name,),
                )
                brand_result = cur.fetchone()
                brand_id = brand_result[0] if brand_result else None

            # 4. Country
            country_id = None
            if country_text:
                cur.execute(
                    """
                    select country_id
                    from dim_country
                    where lower(trim(country_name)) = lower(trim(%s))
                    limit 1;
                    """,
                    (country_text,),
                )
                country_result = cur.fetchone()
                country_id = country_result[0] if country_result else None

            # 5. Outlet
            cur.execute(
                """
                select outlet_id
                from dim_outlet
                where outlet_code = %s
                limit 1;
                """,
                (outlet_code,),
            )
            outlet = cur.fetchone()
            if not outlet:
                skipped_rows += 1
                print(f"Skipped row {row_no + 2}: outlet not found - {outlet_code}")
                continue
            outlet_id = outlet[0]

            # 6. Insert collection item
            cur.execute(
                """
                insert into cpi_collection_item (
                    outlet_id,
                    item_id,
                    spec_name,
                    spec_type,
                    size_value,
                    unit_id,
                    brand_id,
                    country_id,
                    material,
                    display_description,
                    last_price_month,
                    last_price,
                    is_active,
                    valid_from,
                    item_status
                )
                values (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    true, current_date, 'ACTIVE'
                )
                on conflict do nothing;
                """,
                (
                    outlet_id,
                    item_id,
                    spec_type,
                    spec_type,
                    size_value,
                    unit_id,
                    brand_id,
                    country_id,
                    material,
                    item_details,
                    last_price_month,
                    last_price,
                ),
            )
            inserted_rows += 1

print(f"Item details import finished. Processed rows: {inserted_rows}. Skipped rows: {skipped_rows}.")
