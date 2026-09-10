import os
import re
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cpi_admin.settings")
django.setup()

from django.db import transaction
from cpi.models import CpiCollectionItem, DimCountry


def clean(value):
    return str(value).strip() if value else ""


def normalize_label(label):
    return clean(label).lower().replace(" ", "").replace("_", "")


def split_inline_labels(text):
    labels = [
        "Type", "Name", "Number of units", "Number of unit",
        "Size of units", "Size of unit", "Size/Dimension", "Size",
        "Unit of Measure", "Unit of measure",
        "Material", "Other specification", "Product Description",
        "Package type", "Brand", "Made in", "Imported from",
        "Imported form", "Code", "Model no", "Subject", "Level",
        "Fiber contant", "Fiber content"
    ]

    for label in labels:
        text = re.sub(
            rf"\s+({re.escape(label)}\s*:)",
            r"\n\1",
            text,
            flags=re.IGNORECASE
        )

    return text


def find_country(name):
    name = clean(name)

    if not name:
        return None

    key = name.lower().replace(".", "").strip()
    key = " ".join(key.split())

    # Remove code text accidentally captured with country
    key = re.sub(r"\s+code.*$", "", key).strip()
    key = re.sub(r"\s+#.*$", "", key).strip()

    ignore_country_values = [
        "-", "--", "?", "??", "",
        "code", "code #", "imported", "local", "ported",
        "product of ….", "product of ....",
        "bottle", "unilever", "sotudex",
        "ink investment", "ink investmnt", "omar",
        "ink investmnt",
        "ink investment",
        "imported",
        "local",
        "ported",
        "bottle",
        "unilever",
        "sotudex",
        "omar",

        "bottle",
        "imported",
        "ink investment",
        "ink investmnt",
        "local",
        "omar",
        "ported",
        "product of ….",
        "sotudex",
        "unilever",

        "bottle",
        "imported",
        "local",
        "ported",
        "unilever",
        "sotudex",
        "ink investment",
        "ink investmnt",
        "omar",
        "product of ….",
        "product of ....",
    ]

    if key in ignore_country_values or key.startswith("code"):
        return None

    fixes = {
        "dubai": "United Arab Emirates",
        "dubai uae": "United Arab Emirates",
        "uae": "United Arab Emirates",
        "uk": "United Kingdom",
        "us": "United States",
        "usa": "United States",

        "prc": "China",
        "p r c (china)": "China",
        "p r c china": "China",
        "p.r.c (china)": "China",
        "chaina": "China",

        "inidia": "India",
        "mumbai india": "India",

        "indonasia": "Indonesia",

        "ausralia": "Australia",
        "austarlia": "Australia",
        "australis": "Australia",
        "autralia": "Australia",

        "newzealand": "New Zealand",
        "newzeland": "New Zealand",

        "malasiya": "Malaysia",
        "malyasia": "Malaysia",
        "malysia": "Malaysia",
        "mlaaysia": "Malaysia",

        "philipines": "Philippines",
        "phillippines": "Philippines",
        "phillipines": "Philippines",
        "phillipina": "Philippines",
        "phillipnes": "Philippines",

        "srilanka": "Sri Lanka",
        "sri lanka": "Sri Lanka",
        "sli lanka": "Sri Lanka",
        "sr ilanka": "Sri Lanka",
        "ceylon": "Sri Lanka",
        "lanka": "Sri Lanka",

        "-thailand": "Thailand",
        "thai;and": "Thailand",

        "-thaiwan": "Taiwan",
        "thaiwan": "Taiwan",

        "saudhi arabia": "Saudi Arabia",
        "saudia arabia": "Saudi Arabia",

        "singaore": "Singapore",
        "singapor": "Singapore",
        "malaysia / singapore": "Singapore",

        "swirzerland": "Switzerland",
        "swiserland": "Switzerland",

        "turkiye": "Turkey",
        "turky": "Turkey",

        "vietname": "Vietnam",

        "bangladhesh": "Bangladesh",

        "brunai": "Brunei",

        "polland": "Poland",

        "madives": "Maldives",
        "madlives": "Maldives",
        "mladives": "Maldives",

        "holland": "Netherlands",
        "korea": "South Korea",
        "russia": "Russia",
        "vietnam": "Vietnam",

        "bangkok": "Thailand",
        "colombo": "Sri Lanka",
        "istanbul": "Turkey",
        "london": "United Kingdom",
        "minneapolis": "United States",
        "minneaplis": "United States",
        "minnepolis": "United States",
        "minnesota": "United States",

        "-thaiwan": "Taiwan",
        "p.r.c (china)": "China",
        "p r c (china)": "China",
        "brunai": "Brunei",
        "vietname": "Vietnam",
        "uk": "United Kingdom",
        "us": "United States",
        "usa": "United States",

        "-thaiwan": "Taiwan",
        "brunai": "Brunei",
        "korea": "South Korea",
        "london": "United Kingdom",
        "minneapolis": "United States",
        "minneaplis": "United States",
        "minnepolis": "United States",
        "minnesota": "United States",
        "p.r.c (china)": "China",
        "russia": "Russia",
        "uk": "United Kingdom",
        "us": "United States",
        "usa": "United States",
        "vietnam": "Vietnam",
        "vietname": "Vietnam",
        "malta (eu)": "Malta",
        "mata (eu)": "Malta",   # likely typo
        "kandoodhoo": "Maldives",
        "london": "United Kingdom",
        "colombo": "Sri Lanka",
        "bangkok": "Thailand",
        "istanbul": "Turkey",

        "brunai": "Brunei Darussalam",
        "brunei": "Brunei Darussalam",

        "korea": "Korea, Republic of",

        "russia": "Russian Federation",

        "taiwan": "Taiwan, Province of China",
        "-thaiwan": "Taiwan, Province of China",
        "thaiwan": "Taiwan, Province of China",

        "uk": "United Kingdom of Great Britain and Northern Ireland",

        "us": "United States of America",
        "usa": "United States of America",

        "vietnam": "Viet Nam",
        "vietname": "Viet Nam",

        "malta (eu)": "Malta",
        "mata (eu)": "Malta",

        "london": "United Kingdom of Great Britain and Northern Ireland",
        "minneapolis": "United States of America",
        "minneaplis": "United States of America",
        "minnepolis": "United States of America",
        "minnesota": "United States of America",
        "bangkok": "Thailand",
        "colombo": "Sri Lanka",
        "istanbul": "Turkey",
        "kandoodhoo": "Maldives",






    }

    fixed = fixes.get(key, key)

    return DimCountry.objects.filter(country_name__iexact=fixed).first()

def parse_spec(spec):
    spec = split_inline_labels(spec or "")

    data = {
        "spec_type": "",
        "material": "",
        "brand": "",
        "made_in": "",
        "imported_from": "",
        "other_lines": [],
    }

    size_text = ""
    unit_text = ""

    for raw_line in spec.splitlines():
        line = clean(raw_line)
        if not line:
            continue

        if ":" in line:
            label, value = line.split(":", 1)
            label_key = normalize_label(label)
            value = clean(value)

            # Split cases like Brand: Sakura Code: 11114
            if label_key == "brand" and re.search(r"\bCode\s*:", value, re.IGNORECASE):
                parts = re.split(r"\bCode\s*:", value, maxsplit=1, flags=re.IGNORECASE)
                value = clean(parts[0])
                code_value = clean(parts[1]) if len(parts) > 1 else ""
                if code_value:
                    data["other_lines"].append(f"Code: {code_value}")

            if label_key in ["type", "name"]:
                if value:
                    data["spec_type"] = value

            elif label_key in ["sizeofunits", "sizeofunit", "size", "sizedimension"]:
                if value:
                    size_text = value

            elif label_key in ["unitofmeasure", "unit"]:
                if value:
                    unit_text = value

            elif label_key == "material":
                if value:
                    data["material"] = value

            elif label_key == "brand":
                data["brand"] = value

            elif label_key == "madein":
                data["made_in"] = value

            elif label_key in ["importedfrom", "importedform"]:
                data["imported_from"] = value

            else:
                data["other_lines"].append(f"{clean(label)}: {value}")

        else:
            lower = line.lower()

            if lower.startswith("made in"):
                data["made_in"] = clean(line[7:])

            elif lower.startswith("imported from"):
                data["imported_from"] = clean(line[13:])

            elif lower.startswith("imported form"):
                data["imported_from"] = clean(line[13:])

            else:
                data["other_lines"].append(line)

    if size_text or unit_text:
        if unit_text and size_text.lower().endswith(unit_text.lower()):
            size_unit = size_text
        else:
            size_unit = " ".join([x for x in [size_text, unit_text] if x])

        data["other_lines"].insert(0, f"Size/Unit: {size_unit}")

    data["other_spec"] = "\n".join(data["other_lines"])

    return data


updated = 0
country_missing = []
imported_country_missing = []

with transaction.atomic():
    items = CpiCollectionItem.objects.exclude(product_specification__isnull=True).exclude(product_specification="")

    for item in items:
        parsed = parse_spec(item.product_specification)

        made_country = find_country(parsed["made_in"])
        imported_country = find_country(parsed["imported_from"])

        if parsed["made_in"] and not made_country:
            country_missing.append(parsed["made_in"])

        if parsed["imported_from"] and not imported_country:
            imported_country_missing.append(parsed["imported_from"])

        item.spec_type = parsed["spec_type"] or None
        item.material = parsed["material"] or None
        item.brand = parsed["brand"] or None
        item.country = made_country
        item.imported_country = imported_country
        item.other_spec = parsed["other_spec"] or None

        item.save()
        updated += 1


print("ATTRIBUTE UPDATE COMPLETED")
print(f"Updated items: {updated}")

if country_missing:
    print("\nMade-in countries not matched:")
    for x in sorted(set(country_missing)):
        print("-", x)

if imported_country_missing:
    print("\nImported-from countries not matched:")
    for x in sorted(set(imported_country_missing)):
        print("-", x)