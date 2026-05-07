from rest_framework import serializers
from .models import CpiCollectionItem, FactPrice, CollectorAssignment, AppUser

class CpiCollectionItemSerializer(serializers.ModelSerializer):
    outlet_name = serializers.CharField(source="outlet.outlet_name", read_only=True)
    item_name = serializers.CharField(source="item.item_name", read_only=True)
    unit_name = serializers.CharField(source="unit.unit_name", read_only=True)
    brand_name = serializers.CharField(source="brand.brand_name", read_only=True)
    country_name = serializers.CharField(source="country.country_name", read_only=True)

    class Meta:
        model = CpiCollectionItem
        fields = [
            "collection_item_id",
            "outlet_name",
            "item_name",
            "spec_type",
            "size_value",
            "unit_name",
            "brand_name",
            "country_name",
            "item_status",
            "is_active",
            "last_price",
        ]


class FactPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = FactPrice
        fields = "__all__"


class AssignedOutletSerializer(serializers.ModelSerializer):
    outlet_id = serializers.IntegerField(source="outlet.outlet_id", read_only=True)
    outlet_name = serializers.CharField(source="outlet.outlet_name", read_only=True)
    island_name = serializers.CharField(source="outlet.island.island_name", read_only=True)

    class Meta:
        model = CollectorAssignment
        fields = [
            "assignment_id",
            "outlet_id",
            "outlet_name",
            "island_name",
        ]


class LoginSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="pk", read_only=True)

    class Meta:
        model = AppUser
        fields = ["user_id", "username", "full_name", "role_code"]