import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cpi_admin.settings")
django.setup()


import pandas as pd
from django.db import transaction
from django.utils import timezone

from cpi.models import (
    DimOutlet,
    DimItem,
    CpiCollectionItem,
)

EXCEL_PATH = r"F:\CPI_CapiApplication\Other_Docs\Male July final 2025\Male price list.xlsx"
SHEET_NAME = "by outlet"

df = pd.read_excel(EXCEL_PATH, sheet_name=SHEET_NAME)
df.columns = [str(c).strip() for c in df.columns]

required_columns = [
    "Product name",
    "Outlet Name",
    "Brand",
    "Unit",
    "Product code",
    "Specification",
]

missing = [c for c in required_columns if c not in df.columns]
if missing:
    raise Exception(f"Missing columns in Excel: {missing}")

created_collection_items = 0
updated_collection_items = 0
missing_outlets = []

with transaction.atomic():

    for sort_order, row in enumerate(df.itertuples(index=False), start=1):

        row_dict = dict(zip(df.columns, row))

        product_name = str(row_dict["Product name"]).strip() if pd.notna(row_dict["Product name"]) else ""
        outlet_name = str(row_dict["Outlet Name"]).strip() if pd.notna(row_dict["Outlet Name"]) else ""
        brand = str(row_dict["Brand"]).strip() if pd.notna(row_dict["Brand"]) else ""
        unit = str(row_dict["Unit"]).strip() if pd.notna(row_dict["Unit"]) else ""
        raw_product_code = str(row_dict["Product code"]).strip() if pd.notna(row_dict["Product code"]) else ""
        product_code = raw_product_code


        specification_value = row_dict["Specification"]

        if pd.notna(specification_value):

            if isinstance(specification_value, (int, float)):
                specification = str(int(specification_value))
            else:
                specification = str(specification_value).strip()

        else:
            specification = ""

        if not product_name or not outlet_name:
            continue

        outlet = DimOutlet.objects.filter(
            outlet_name__iexact=outlet_name
        ).first()

        if not outlet:
            missing_outlets.append(outlet_name)
            continue
        system_island_code = (
        outlet.island.island_code
        if outlet and outlet.island and outlet.island.island_code
        else "000"
        )

        system_outlet_code = (
            outlet.outlet_code
            if outlet and outlet.outlet_code
            else "0000"
        )

        if raw_product_code and "|" in raw_product_code:

            code_parts = raw_product_code.split("|")

            if len(code_parts) >= 4:
                code_parts[0] = str(system_island_code)
                code_parts[1] = str(system_outlet_code)

                product_code = "|".join(code_parts)
        

        temp_item, _ = DimItem.objects.get_or_create(
            item_name=product_name,
            brand=None,
            unit=None,
            defaults={
                "is_active": True,
            }
        )

        collection_item, created = CpiCollectionItem.objects.get_or_create(
            outlet=outlet,
            product_code=product_code,
            defaults={
                "item": temp_item,
                "specification_no": specification,
                "is_active": True,
                "valid_from": timezone.now().date(),
                "item_status": "ACTIVE",
                "product_name": product_name,
                "brand": brand,
                "unit": unit,
                "excel_product_code": raw_product_code,
                "excel_specification": specification,
                "sort_order": sort_order,
            }
        )
        collection_item.item = temp_item
        collection_item.specification_no = specification
        collection_item.product_code = product_code
        collection_item.is_active = True
        collection_item.item_status = "ACTIVE"

        collection_item.product_name = product_name
        collection_item.brand = brand
        collection_item.product_specification  = unit

        collection_item.excel_product_code = raw_product_code
        collection_item.excel_specification = specification

        collection_item.sort_order = sort_order

        collection_item.save()

        if created:
            created_collection_items += 1
        else:
            updated_collection_items += 1

print("IMPORT COMPLETED")
print(f"Created CpiCollectionItem: {created_collection_items}")
print(f"Updated CpiCollectionItem: {updated_collection_items}")

if missing_outlets:
    print("\nMissing outlets:")
    for outlet_name in sorted(set(missing_outlets)):
        print("-", outlet_name)