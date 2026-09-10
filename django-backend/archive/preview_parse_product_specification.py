import os
import re
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cpi_admin.settings")
django.setup()

from cpi.models import CpiCollectionItem


def get_value(spec, label):

    pattern = rf"{label}\s*:\s*(.*?)(?:\n|$)"

    match = re.search(
        pattern,
        spec,
        flags=re.IGNORECASE
    )

    if match:
        return match.group(1).strip()

    return ""


items = CpiCollectionItem.objects.exclude(
    product_specification__isnull=True
).exclude(
    product_specification=""
)[:50]


for item in items:

    spec = item.product_specification or ""

    spec_type = get_value(spec, "Type")
    size = get_value(spec, "Size of units")
    unit = get_value(spec, "Unit of Measure")
    material = get_value(spec, "Material")
    brand = get_value(spec, "Brand")

    made_in = ""

    made_match = re.search(
        r"Made in\s*(.*?)(?:\n|$)",
        spec,
        flags=re.IGNORECASE
    )

    if made_match:
        made_in = made_match.group(1).strip()

    print("=" * 100)

    print("PRODUCT:")
    print(item.product_name)

    print("\nSPECIFICATION:")
    print(spec)

    print("\nEXTRACTED:")

    print("TYPE       :", spec_type)
    print("SIZE       :", size)
    print("UNIT       :", unit)
    print("MATERIAL   :", material)
    print("BRAND      :", brand)
    print("MADE IN    :", made_in)

    print()