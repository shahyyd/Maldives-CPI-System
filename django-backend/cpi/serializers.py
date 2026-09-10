from rest_framework import serializers
from .models import (
    CpiCollectionItem,
    FactPrice,
    CollectorAssignment,
    AppUser,
    CpiReplacement,
    CpiPhoto,
)
from django.contrib.auth.models import User
from django.db import transaction

class CpiCollectionItemSerializer(serializers.ModelSerializer):

    outlet_name = serializers.CharField(
        source="outlet.outlet_name",
        read_only=True
    )

    item_name = serializers.CharField(
        source="product_name",
        read_only=True
    )

    unit_name = serializers.CharField(
        source="product_specification",
        read_only=True
    )

    brand_name = serializers.CharField(
        source="brand",
        read_only=True
    )

    basket_id = serializers.IntegerField(
    source="basket_item.basket_id",
    read_only=True
    )

    basket_code = serializers.CharField(
        source="basket_item.basket_code",
        read_only=True
    )

    basket_item_code = serializers.CharField(
        source="basket_item.basket_item_code",
        read_only=True
    )

    basket_item_name = serializers.CharField(
        source="basket_item.basket_item_name",
        read_only=True
    )

    display_name = serializers.SerializerMethodField()
    replacement_status = serializers.SerializerMethodField()
    replacement_rejection_comment = serializers.SerializerMethodField()
    has_item_photo = serializers.SerializerMethodField()
    item_photo_url = serializers.SerializerMethodField()
    photo_status = serializers.SerializerMethodField()
    photo_rejection_reason = serializers.SerializerMethodField()

    def get_replacement_rejection_comment(self, obj):
        replacement = (
            CpiReplacement.objects
            .filter(
                old_collection_item=obj,
                is_deleted=False
            )
            .order_by("-replacement_id")
            .first()
        )

        if replacement and replacement.replacement_status == "REJECTED":
            return replacement.rejection_comment or ""

        return ""

    def get_photo_status(self, obj):
        photo = (
            CpiPhoto.objects
            .filter(
                collection_item=obj,
                photo_type="ITEM",
                is_deleted=False
            )
            .order_by("-photo_id")
            .first()
        )

        if photo:
            return photo.status

        return ""


    def get_photo_rejection_reason(self, obj):
        photo = (
            CpiPhoto.objects
            .filter(
                collection_item=obj,
                photo_type="ITEM",
                is_deleted=False
            )
            .order_by("-photo_id")
            .first()
        )

        if photo:
            return photo.rejection_reason or ""

        return ""

    def get_replacement_status(self, obj):
        replacement = (
            CpiReplacement.objects
            .filter(
                old_collection_item=obj,
                is_deleted=False
            )
            .order_by("-replacement_id")
            .first()
        )

        if replacement:
            return replacement.replacement_status

        return ""

    def get_has_item_photo(self, obj):
        return CpiPhoto.objects.filter(
            collection_item=obj,
            photo_type="REFERENCE_ITEM",
            is_deleted=False
        ).exists()


    def get_item_photo_url(self, obj):
        photo = (
            CpiPhoto.objects
            .filter(
                collection_item=obj,
                photo_type="REFERENCE_ITEM",
                is_deleted=False
            )
            .order_by("-photo_id")
            .first()
        )

        if photo:
            return photo.file_path

        return None

    def get_display_name(self, obj):
        parts = [
            obj.product_name,
            obj.brand,
            obj.product_specification,
        ]
        return " | ".join([p for p in parts if p])

    class Meta:
        model = CpiCollectionItem
        fields = (
            "collection_item_id",
            "outlet",
            "outlet_name",
            "basket_id",
            "basket_code",
            "basket_item_code",
            "basket_item_name",
            "item_name",
            "product_name",
            "brand",
            "brand_name",
            "product_specification",
            "unit_name",
            "display_name",
            "specification_no",
            "product_code",
            "last_price",
            "last_price_month",
            "has_item_photo",
            "item_photo_url",
            "photo_status",
            "photo_rejection_reason",
            "replacement_status",
            "replacement_rejection_comment",
        )


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

    username = serializers.CharField(
        source="django_user.username",
        read_only=True
    )

    class Meta:
        model = AppUser
        fields = [
            "user_id",
            "username",
            "full_name",
            "role",
        ]


class AppUserCreateSerializer(serializers.ModelSerializer):
    username = serializers.CharField(write_only=True)

    password = serializers.CharField(
        write_only=True,
        min_length=8
    )

    class Meta:
        model = AppUser
        fields = [
            "user_id",
            "username",
            "password",
            "full_name",
            "email",
            "phone_number",
            "role",
            "is_active",
        ]

        read_only_fields = ["user_id"]

    def validate_username(self, value):
        username = value.strip()

        if User.objects.filter(username__iexact=username).exists():
            raise serializers.ValidationError(
                "A user with this username already exists."
            )

        return username

    @transaction.atomic
    def create(self, validated_data):
        username = validated_data.pop("username")
        password = validated_data.pop("password")

        email = validated_data.get("email") or ""
        is_active = validated_data.get("is_active", True)

        django_user = User.objects.create_user(
            username=username,
            password=password,
            email=email,
            is_active=is_active,
        )

        app_user = AppUser.objects.create(
            django_user=django_user,
            **validated_data
        )

        return app_user