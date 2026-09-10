import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cpi_admin.settings")
django.setup()

from basket_matcher import BasketMatcher

matcher = BasketMatcher()

tests = [
    ("Sugar", "Type: Sugar - White"),
    ("Tea", "Type: Tea bags"),
]

for product_name, product_specification in tests:

    result = matcher.find_basket(
        product_name=product_name,
        product_specification=product_specification
    )

    print("INPUT:", product_name)
    print("SPEC:", product_specification)

    if result:
        print(
            "MATCH:",
            result["basket_code"],
            result["basket_name"],
            result["confidence"],
            result["match_type"]
        )
    else:
        print("MATCH: None")

    print("-" * 50)