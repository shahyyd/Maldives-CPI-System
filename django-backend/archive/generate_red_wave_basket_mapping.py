import os
import sys
import re
import django
from difflib import SequenceMatcher
from openpyxl import Workbook

print("Current folder:", os.getcwd())
print("Python path:", sys.path[0])

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cpi_admin.settings")
django.setup()

from cpi.models import CpiCollectionItem, CpiBasket, CpiMethodology


OUTLET_ID = 31
METHODOLOGY_CODE = "CPI2022"
OUTPUT_FILE = r"F:\Maldives-CPI-System\docs\RED_WAVE_Basket_Mapping.xlsx"


def clean_text(value):
    if not value:
        return ""
    value = str(value).lower().strip()
    value = re.sub(r"^type\s*:\s*", "", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def similarity(a, b):
    return SequenceMatcher(None, clean_text(a), clean_text(b)).ratio()


def best_match(collection_item, basket_items):
    product_name = clean_text(collection_item.product_name)
    specification = clean_text(collection_item.product_specification)

    # 1. Exact product_name match
    for basket in basket_items:
        if product_name and product_name == clean_text(basket.basket_name):
            return basket, 100.0, "Exact product_name"

    # 2. Exact product_specification match
    for basket in basket_items:
        if specification and specification == clean_text(basket.basket_name):
            return basket, 100.0, "Exact product_specification"

    # 3. Fuzzy match
    best_basket = None
    best_score = 0

    for basket in basket_items:
        basket_name = basket.basket_name

        score = max(
            similarity(collection_item.product_name, basket_name),
            similarity(collection_item.product_specification, basket_name),
        )

        if score > best_score:
            best_score = score
            best_basket = basket

    return best_basket, round(best_score * 100, 2), "Fuzzy match"


def main():
    methodology = CpiMethodology.objects.get(methodology_code=METHODOLOGY_CODE)

    basket_items = list(
        CpiBasket.objects.filter(
            methodology=methodology,
            is_basket_item=True,
            is_active=True
        ).order_by("display_order")
    )

    collection_items = (
        CpiCollectionItem.objects
        .filter(outlet_id=OUTLET_ID, is_active=True)
        .select_related("outlet", "basket")
        .order_by("sort_order", "collection_item_id")
    )

    wb = Workbook()
    ws = wb.active
    ws.title = "RED WAVE Mapping"

    ws.append([
        "collection_item_id",
        "outlet_id",
        "outlet_name",
        "product_name",
        "brand",
        "product_specification",
        "excel_subgroup",
        "suggested_basket_id",
        "suggested_basket_name",
        "confidence",
        "match_type",
        "approved_basket_id",
        "approved_basket_name",
        "review_status",
        "remarks",
    ])

    for item in collection_items:
        basket, confidence, match_type = best_match(item, basket_items)

        review_status = "AUTO_OK" if confidence >= 95 else "REVIEW"

        ws.append([
            item.collection_item_id,
            item.outlet_id,
            item.outlet.outlet_name if item.outlet else "",
            item.product_name,
            item.brand,
            item.product_specification,
            item.excel_subgroup,
            basket.basket_id if basket else "",
            basket.basket_name if basket else "",
            confidence,
            match_type,
            basket.basket_id if basket else "",
            basket.basket_name if basket else "",
            review_status,
            "",
        ])

    wb.save(OUTPUT_FILE)

    print("Mapping file created:")
    print(OUTPUT_FILE)
    print(f"Collection items exported: {collection_items.count()}")


if __name__ == "__main__":
    main()