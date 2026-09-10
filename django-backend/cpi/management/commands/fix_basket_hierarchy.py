from django.core.management.base import BaseCommand
from django.db import transaction

from cpi.models import CpiBasket


class Command(BaseCommand):
    help = (
        "Correct basket-item COICOP hierarchy fields using the "
        "existing parent_basket hierarchy."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show proposed changes without updating the database.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        basket_items = (
            CpiBasket.objects
            .filter(is_basket_item=True)
            .select_related("parent_basket")
            .order_by("basket_id")
        )

        checked_count = 0
        changed_count = 0
        incomplete_count = 0
        pending_updates = []

        for item in basket_items:
            checked_count += 1

            hierarchy = self.get_hierarchy(item)

            division = hierarchy.get(2)
            group = hierarchy.get(3)
            class_row = hierarchy.get(4)
            subclass = hierarchy.get(5)

            if not all([division, group, class_row, subclass]):
                incomplete_count += 1

                self.stdout.write(
                    self.style.WARNING(
                        f"Incomplete hierarchy | "
                        f"Basket ID: {item.basket_id} | "
                        f"Item: {item.basket_item_name or item.description}"
                    )
                )
                continue

            new_values = {
                "coicop_division_code": division.coicop_2016,
                "coicop_division_name": division.description,
                "coicop_group_code": group.coicop_2016,
                "coicop_group_name": group.description,
                "coicop_class_code": class_row.coicop_2016,
                "coicop_class_name": class_row.description,
                "coicop_subclass_code": subclass.coicop_2016,
                "coicop_subclass_name": subclass.description,
            }

            changes = {}

            for field_name, new_value in new_values.items():
                old_value = getattr(item, field_name)

                if old_value != new_value:
                    changes[field_name] = {
                        "old": old_value,
                        "new": new_value,
                    }

            if not changes:
                continue

            changed_count += 1

            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(
                    f"Basket ID: {item.basket_id} | "
                    f"Item: {item.basket_item_name or item.description}"
                )
            )

            for field_name, values in changes.items():
                self.stdout.write(
                    f"  {field_name}: "
                    f"{values['old']!r} -> {values['new']!r}"
                )

            for field_name, new_value in new_values.items():
                setattr(item, field_name, new_value)

            pending_updates.append(item)

        if pending_updates and not dry_run:
            with transaction.atomic():
                CpiBasket.objects.bulk_update(
                    pending_updates,
                    fields=[
                        "coicop_division_code",
                        "coicop_division_name",
                        "coicop_group_code",
                        "coicop_group_name",
                        "coicop_class_code",
                        "coicop_class_name",
                        "coicop_subclass_code",
                        "coicop_subclass_name",
                    ],
                    batch_size=500,
                )

        self.stdout.write("")
        self.stdout.write("-" * 60)

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    "Basket hierarchy dry run completed."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    "Basket hierarchy update completed."
                )
            )

        self.stdout.write(
            f"Basket items checked       : {checked_count:,}"
        )
        self.stdout.write(
            f"Basket items to change     : {changed_count:,}"
        )
        self.stdout.write(
            f"Incomplete hierarchies     : {incomplete_count:,}"
        )

    def get_hierarchy(self, basket_item):
        """
        Follow parent_basket links upward and return ancestor rows
        keyed by their hierarchy level.
        """
        hierarchy = {}

        current = basket_item.parent_basket

        while current is not None:
            if current.level is not None:
                hierarchy[current.level] = current

            current = current.parent_basket

        return hierarchy