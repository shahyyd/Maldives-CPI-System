import os
import sys
import re
import django
from difflib import SequenceMatcher

print("Current folder:", os.getcwd())
print("Python path:", sys.path[0])

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cpi_admin.settings")
django.setup()

from cpi.models import CpiCollectionItem, CpiBasket, CpiMethodology


OUTLET_ID = 31
METHODOLOGY_CODE = "CPI2022"
AUTO_UPDATE_SCORE = 95.0


def clean_text(value):
    if not value:
        return ""

    value = str(value).lower().strip()
    value = re.sub(r"^type\s*:\s*", "", value)
    value = re.sub(r"\(including.*?\)", "", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()

    return value


def similarity(a, b):
    return SequenceMatcher(None, clean_text(a), clean_text(b)).ratio() * 100


def get_best_match(item, basket_items):
    product_name = clean_text(item.product_name)
    specification = clean_text(item.product_specification)

    # 1. Exact product name
    for basket in basket_items:
        if product_name and product_name == clean_text(basket.basket_name):
            return basket, 100.0, "Exact product_name"

    # 2. Basket name contained in product name
    for basket in basket_items:
        basket_name = clean_text(basket.basket_name)
        if basket_name and basket_name in product_name:
            return basket, 98.0, "Basket name in product_name"

    # 3. Product name contained in basket name
    for basket in basket_items:
        basket_name = clean_text(basket.basket_name)
        if product_name and product_name in basket_name:
            return basket, 98.0, "Product name in basket_name"

    # 4. Exact specification
    for basket in basket_items:
        if specification and specification == clean_text(basket.basket_name):
            return basket, 96.0, "Exact product_specification"

    # 5. Fuzzy fallback
    best_basket = None
    best_score = 0.0

    for basket in basket_items:
        score = max(
            similarity(item.product_name, basket.basket_name),
            similarity(item.product_specification, basket.basket_name),
        )

        if score > best_score:
            best_score = score
            best_basket = basket

    return best_basket, round(best_score, 2), "Fuzzy match"


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
        .filter(
            outlet_id=OUTLET_ID,
            is_active=True,
            basket__isnull=True
        )
        .order_by("sort_order", "collection_item_id")
    )

    updated = 0
    skipped = 0

    print(f"Outlet ID: {OUTLET_ID}")
    print(f"Basket items: {len(basket_items)}")
    print(f"Unmapped collection items: {collection_items.count()}")
    print("")

    for item in collection_items:
        basket, confidence, match_type = get_best_match(item, basket_items)

        if basket and confidence >= AUTO_UPDATE_SCORE:
            item.basket = basket
            item.save(update_fields=["basket"])

            updated += 1

            print(
                f"UPDATED [{confidence:.2f}%] "
                f"{item.collection_item_id} | {item.product_name} "
                f"-> {basket.basket_name} ({match_type})"
            )
        else:
            skipped += 1

            print(
                f"SKIPPED [{confidence:.2f}%] "
                f"{item.collection_item_id} | {item.product_name} "
                f"-> {basket.basket_name if basket else 'No match'} ({match_type})"
            )

    print("")
    print("Basket mapping completed.")
    print(f"Updated: {updated}")
    print(f"Skipped: {skipped}")


if __name__ == "__main__":
    main()