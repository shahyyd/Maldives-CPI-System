from django import forms
from django.contrib import admin
from .models import *
from django.db import transaction

from .models import CollectorAssignment, DimOutlet, DimIsland


@admin.register(DimRegion)
class DimRegionAdmin(admin.ModelAdmin):
    list_display = ("region_code", "region_name")
    search_fields = ("region_code", "region_name")


@admin.register(DimAtoll)
class DimAtollAdmin(admin.ModelAdmin):
    list_display = ("atoll_code", "atoll_name", "region")
    search_fields = ("atoll_code", "atoll_name")
    list_filter = ("region",)


@admin.register(DimIsland)
class DimIslandAdmin(admin.ModelAdmin):
    list_display = ("island_code", "island_name", "atoll")
    search_fields = ("island_code", "island_name")
    list_filter = ("atoll",)


@admin.register(DimOutlet)
class DimOutletAdmin(admin.ModelAdmin):
    list_display = ("outlet_code", "outlet_name", "island", "is_active")
    search_fields = ("outlet_code", "outlet_name", "island__island_name")
    list_filter = ("is_active", "island")


@admin.register(DimItem)
class DimItemAdmin(admin.ModelAdmin):
    list_display = ("item_code", "item_name", "coicop_code", "item_group", "is_active")
    search_fields = ("item_code", "item_name", "coicop_code")
    list_filter = ("item_group", "is_active")


@admin.register(DimUnit)
class DimUnitAdmin(admin.ModelAdmin):
    list_display = ("unit_code", "unit_name")
    search_fields = ("unit_code", "unit_name")


@admin.register(DimBrand)
class DimBrandAdmin(admin.ModelAdmin):
    list_display = ("brand_name",)
    search_fields = ("brand_name",)


@admin.register(DimCountry)
class DimCountryAdmin(admin.ModelAdmin):
    list_display = ("iso_code", "country_name")
    search_fields = ("iso_code", "country_name")


@admin.register(CpiRound)
class CpiRoundAdmin(admin.ModelAdmin):
    list_display = ("survey_year", "survey_month", "round_status", "collection_start_date", "collection_end_date")
    list_filter = ("survey_year", "survey_month", "round_status")


@admin.register(CpiVisit)
class CpiVisitAdmin(admin.ModelAdmin):
    list_display = ("visit_id", "round", "outlet", "collector_user", "visit_status", "sync_status", "start_time")
    search_fields = ("outlet__outlet_name", "collector_user__full_name")
    list_filter = ("visit_status", "sync_status", "round")


@admin.register(FactPrice)
class FactPriceAdmin(admin.ModelAdmin):
    list_display = (
        "price_id",
        "collection_item",
        "spec_type",
        "brand_name",
        "country_name",
        "observed_price",
        "last_month_price",
        "availability",
        "quote_status",
        "is_outlier",
        "last_modified_at",
        "remarks",
    )

    search_fields = (
        "collection_item__item__item_name",
        "collection_item__outlet__outlet_name",
        "collection_item__spec_type",
        "collection_item__brand__brand_name",
        "collection_item__country__country_name",
    )

    list_filter = (
        "availability",
        "quote_status",
        "is_outlier",
        "collection_item__brand",
        "collection_item__country",
    )

    list_select_related = (
        "collection_item",
        "collection_item__item",
        "collection_item__outlet",
        "collection_item__brand",
        "collection_item__country",
    )

    def spec_type(self, obj):
        return obj.collection_item.spec_type or "-"

    spec_type.short_description = "Type"

    def brand_name(self, obj):
        return obj.collection_item.brand.brand_name if obj.collection_item.brand else "-"

    brand_name.short_description = "Brand"

    def country_name(self, obj):
        return obj.collection_item.country.country_name if obj.collection_item.country else "-"

    country_name.short_description = "Country"


@admin.register(CpiReplacement)
class CpiReplacementAdmin(admin.ModelAdmin):
    list_display = ("replacement_id", "old_collection_item", "new_name", "new_price", "replacement_status")
    search_fields = ("new_name", "old_collection_item__item__item_name")
    list_filter = ("replacement_status",)


@admin.register(CpiPhoto)
class CpiPhotoAdmin(admin.ModelAdmin):
    list_display = ("photo_id", "photo_type", "file_name", "taken_at", "sync_status")
    search_fields = ("file_name",)
    list_filter = ("photo_type", "sync_status")


@admin.register(AppUser)
class AppUserAdmin(admin.ModelAdmin):
    list_display = ("username", "full_name", "role_code", "phone_number", "is_active")
    search_fields = ("username", "full_name")
    list_filter = ("role_code", "is_active")


@admin.register(AppDevice)
class AppDeviceAdmin(admin.ModelAdmin):
    list_display = ("device_uuid", "device_name", "assigned_user", "is_active", "last_sync_at")
    search_fields = ("device_name", "assigned_user__full_name")
    list_filter = ("is_active",)


@admin.register(SyncBatch)
class SyncBatchAdmin(admin.ModelAdmin):
    list_display = ("sync_batch_id", "device", "user", "sync_status", "sync_started_at", "sync_completed_at")
    list_filter = ("sync_status",)


@admin.register(SyncConflictLog)
class SyncConflictLogAdmin(admin.ModelAdmin):
    list_display = ("conflict_id", "table_name", "record_id", "device", "conflict_type", "created_at")
    search_fields = ("table_name", "conflict_type")
    list_filter = ("conflict_type",)


@admin.register(CpiAuditLog)
class CpiAuditLogAdmin(admin.ModelAdmin):
    list_display = ("entity_name", "entity_id", "action_code", "changed_by", "changed_at")
    search_fields = ("entity_name", "action_code")
    list_filter = ("action_code",)


@admin.register(CpiCollectionItem)
class CpiCollectionItemAdmin(admin.ModelAdmin):
    list_display = (
        "outlet",
        "item",
        "spec_type",
        "size_value",
        "unit",
        "brand",
        "country",
        "item_status",
        "is_active",
    )

    list_filter = ("outlet", "brand", "country")

    search_fields = ("item__item_name", "outlet__outlet_name")




class CollectorAssignmentAdminForm(forms.ModelForm):
    island = forms.ModelChoiceField(
        queryset=DimIsland.objects.filter(
            dimoutlet__is_active=True
        ).distinct().order_by("island_name"),
        required=True,
        widget=forms.Select(attrs={
            "onchange": "const c=document.getElementById('id_collector').value; window.location.href='?island=' + this.value + '&collector=' + c;"
        })
    )

    outlets = forms.ModelMultipleChoiceField(
        queryset=DimOutlet.objects.filter(is_active=True).order_by("outlet_name"),
        required=True,
        widget=admin.widgets.FilteredSelectMultiple("Outlets", is_stacked=False)
    )

    class Meta:
        model = CollectorAssignment
        fields = ["collector", "island", "outlets", "is_active"]


@admin.register(CollectorAssignment)

class CollectorAssignmentAdmin(admin.ModelAdmin):
    form = CollectorAssignmentAdminForm

    list_display = ("assignment_id", "collector", "outlet", "is_active", "assigned_at")
    list_filter = ("collector", "outlet__island", "is_active")

    search_fields = (
        "collector__username",
        "collector__full_name",
        "outlet__outlet_name",
        "outlet__outlet_code",
        "outlet__island__island_name",
    )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        island_id = request.GET.get("island")
        collector_id = request.GET.get("collector")

        # 👇 Keep collector selected after reload
        if collector_id:
            form.base_fields["collector"].initial = collector_id

        if island_id:
            form.base_fields["outlets"].queryset = (
                DimOutlet.objects
                .filter(is_active=True, island_id=island_id)
                .order_by("outlet_name")
            )
        else:
            form.base_fields["outlets"].queryset = DimOutlet.objects.none()

        return form
    
    def save_form(self, request, form, change):
        obj = form.save(commit=False)

        outlets = form.cleaned_data.get("outlets")
        if outlets:
            obj.outlet = outlets.first()

        return obj


    def save_model(self, request, obj, form, change):
        collector = form.cleaned_data["collector"]
        outlets = form.cleaned_data["outlets"]
        is_active = form.cleaned_data["is_active"]

        with transaction.atomic():
            for outlet in outlets:
                CollectorAssignment.objects.update_or_create(
                    collector=collector,
                    outlet=outlet,
                    defaults={"is_active": is_active}
                )
