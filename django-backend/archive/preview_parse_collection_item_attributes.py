import os
import re
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cpi_admin.settings")
django.setup()

from cpi.models import CpiCollectionItem, DimCountry


def clean(value):
    return str(value).strip() if value else ""


def normalize_label(label):
    return clean(label).lower().replace(" ", "").replace("_", "")


def parse_spec(spec):
    data = {}
    other_lines = []

    for raw_line in spec.splitlines():
        line = clean(raw_line)
        if not line:
            continue

        if ":" in line:
            label, value = line.split(":", 1)
            label_key = normalize_label(label)
            value = clean(value)

            if label_key in ["type", "name"]:
                data["spec_type"] = value

            elif label_key in ["sizeofunits", "sizeofunit", "size"]:
                data["size_text"] = value

            elif label_key in ["unitofmeasure", "unit"]:
                data["unit_text"] = value

            elif label_key == "material":
                data["material"] = value

            elif label_key == "brand":
                data["brand"] = value

            elif label_key in ["madein"]:
                data["made_in"] = value

            elif label_key in ["importedfrom", "importedform"]:
                data["imported_from"] = value

            else:
                other_lines.append(f"{label}: {value}")

        else:
            lower = line.lower()

            if lower.startswith("made in"):
                data["made_in"] = clean(line[7:])

            elif lower.startswith("imported from"):
                data["imported_from"] = clean(line[13:])

            elif lower.startswith("imported form"):
                data["imported_from"] = clean(line[13:])

            else:
                other_lines.append(line)

    size_unit = " ".join(
        [x for x in [data.get("size_text"), data.get("unit_text")] if x]
    )

    if size_unit:
        other_lines.insert(0, f"Size/Unit: {size_unit}")

    data["other_spec"] = "\n".join(other_lines)

    return data


def find_country(name):
    name = clean(name)

    if not name:
        return None

    fixes = {
        "indonasia": "Indonesia",
        "indonesia": "Indonesia",
        "dubai": "United Arab Emirates",
        "uae": "United Arab Emirates",
        "u.a.e": "United Arab Emirates",
        "china": "China",
        "india": "India",
        "brazil": "Brazil",
        "germany": "Germany",
    }

    key = name.lower().replace(".", "").strip()
    fixed = fixes.get(key, name)

    return DimCountry.objects.filter(country_name__iexact=fixed).first()


items = CpiCollectionItem.objects.exclude(
    product_specification__isnull=True
).exclude(
    product_specification=""
)[:50]


for item in items:
    parsed = parse_spec(item.product_specification)

    made_country = find_country(parsed.get("made_in"))
    imported_country = find_country(parsed.get("imported_from"))

    print("=" * 100)
    print("PRODUCT:", item.product_name)
    print("SPEC:")
    print(item.product_specification)

    print("\nPARSED:")
    print("spec_type        :", parsed.get("spec_type"))
    print("material         :", parsed.get("material"))
    print("brand            :", parsed.get("brand"))
    print("made_in          :", parsed.get("made_in"), "=>", made_country)
    print("imported_from    :", parsed.get("imported_from"), "=>", imported_country)
    print("other_spec:")
    print(parsed.get("other_spec"))