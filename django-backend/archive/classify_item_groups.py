import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cpi_admin.settings")
django.setup()

from cpi.models import DimItem, DimItemGroup

food_group = DimItemGroup.objects.get(group_code="FOOD")
nonfood_group = DimItemGroup.objects.get(group_code="NONFOOD")
service_group = DimItemGroup.objects.get(group_code="SERVICE")

food_keywords = [
    "rice", "flour", "bread", "fish", "tuna", "chicken",
    "beef", "milk", "egg", "oil", "sugar", "tea", "coffee"
]

service_keywords = [
    "rent", "fee", "charge", "service", "internet",
    "electricity", "telephone", "hotel", "restaurant",
    "haircut", "repair", "doctor", "hospital"
]

food_count = 0
service_count = 0
nonfood_count = 0

for item in DimItem.objects.all():
    name = (item.item_name or "").lower()

    if any(k in name for k in food_keywords):
        item.item_group = food_group
        food_count += 1

    elif any(k in name for k in service_keywords):
        item.item_group = service_group
        service_count += 1

    else:
        item.item_group = nonfood_group
        nonfood_count += 1

    item.save(update_fields=["item_group"])

print(f"FOOD: {food_count}")
print(f"SERVICE: {service_count}")
print(f"NONFOOD: {nonfood_count}")
print("Completed.")