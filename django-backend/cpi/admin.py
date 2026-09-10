from django import forms
from django.contrib import admin, messages
from django.contrib import messages
from django.db import transaction
from django.http import HttpResponseRedirect
from .models import *
from django.db import transaction, models
from django.db import IntegrityError
from .models import CollectorAssignment, DimOutlet, DimIsland
from django.http import HttpResponseRedirect
from .models import CollectorItemAssignment
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.db.models import Count
from .models import CollectorWorkloadSummary
from django.db.models import ProtectedError
from django.db import IntegrityError, transaction
from django.shortcuts import redirect
from django.utils import timezone
from decimal import Decimal
from .models import (CollectorItemAssignment,AppUser,DimIsland,DimOutlet,CpiCollectionItem,)
from django.utils.html import format_html
from django.urls import path, reverse
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.contrib import admin, messages

def handle_fk_delete_error(admin_obj, request, error):
    error_text = str(error)

    FK_ERROR_MESSAGES = {

        "fact_price_visit_id_fkey":
            "This visit cannot be deleted because Fact Price records are linked to it. "
            "Please delete Fact Price records first.",

        "cpi_visit_collector_user_id_fkey":
            "This user cannot be deleted because CPI Visit records are linked to this user. "
            "Please delete CPI Visit records first or deactivate the user instead.",

        "app_device_assigned_user_id_fkey":
            "This user cannot be deleted because a device is assigned to this user. "
            "Please unassign or delete the device first.",

        "cpi_replacement_price_id_fkey":
            "This Fact Price cannot be deleted because Replacement records are linked to it. "
            "Please delete Replacement records first.",

        "collector_assignment_collector_id_fkey":
            "This user cannot be deleted because Collector Assignments are linked to this user. "
            "Please delete Collector Assignments first.",

        "collector_assignment_outlet_id_fkey":
            "This outlet cannot be deleted because Collector Assignments are linked to it. "
            "Please delete Collector Assignments first.",

        "cpi_collection_item_outlet_id_fkey":
            "This outlet cannot be deleted because Collection Items are linked to it. "
            "Please delete Collection Items first.",

        "fact_price_collection_item_id_fkey":
            "This Collection Item cannot be deleted because Fact Price records are linked to it. "
            "Please delete Fact Price records first.",

    }

    for constraint_name, message in FK_ERROR_MESSAGES.items():
        if constraint_name in error_text:
            admin_obj.message_user(
                request,
                message,
                level=messages.ERROR
            )
            return

    admin_obj.message_user(
        request,
        f"Delete failed because related records exist.\n\n{error_text}",
        level=messages.ERROR
    )


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

    def delete_model(self, request, obj):
        try:
            obj.delete()
        except IntegrityError as e:
            handle_fk_delete_error(self, request, e)

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            try:
                obj.delete()
            except IntegrityError as e:
                handle_fk_delete_error(self, request, e)


@admin.register(DimUnit)
class DimUnitAdmin(admin.ModelAdmin):
    list_display = ("unit_code", "unit_name")
    search_fields = ("unit_code", "unit_name")
    exclude = ("unit_code",)



@admin.register(DimBrand)
class DimBrandAdmin(admin.ModelAdmin):
    list_display = (
        "brand_id",
        "brand_name",
    )

    search_fields = (
        "brand_name",
    )

    def delete_model(self, request, obj):
        try:
            with transaction.atomic():
                obj.delete()
            self.message_user(
                request,
                "Brand deleted successfully.",
                messages.SUCCESS
            )

        except IntegrityError:
            self.message_user(
                request,
                "Cannot delete this brand because it is already used in CPI Collection Items. "
                "First remove or change this brand from related collection items, then delete the brand.",
                messages.ERROR
            )

    def delete_queryset(self, request, queryset):
        deleted_count = 0
        blocked_count = 0

        for obj in queryset:
            try:
                with transaction.atomic():
                    obj.delete()
                deleted_count += 1

            except IntegrityError:
                blocked_count += 1

        if deleted_count:
            self.message_user(
                request,
                f"{deleted_count} brand(s) deleted successfully.",
                messages.SUCCESS
            )

        if blocked_count:
            self.message_user(
                request,
                f"{blocked_count} brand(s) could not be deleted because they are used in CPI Collection Items.",
                messages.ERROR
            )


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


    def delete_model(self, request, obj):
        try:
            obj.delete()

        except IntegrityError as e:
            handle_fk_delete_error(self, request, e)

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            try:
                obj.delete()

            except IntegrityError as e:
                handle_fk_delete_error(self, request, e)


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
        "collection_item__basket_item__basket_item_name",
        "collection_item__outlet__outlet_name",
        "collection_item__product_specification",
        "collection_item__brand",
        "collection_item__brand_fk__brand_name",
        "collection_item__country__country_name",
    )

    list_filter = (
        "availability",
        "quote_status",
        "is_outlier",
        "collection_item__brand_fk",
        "collection_item__country",
    )

    list_select_related = (
        "collection_item",
        "collection_item__basket_item",
        "collection_item__outlet",
        "collection_item__brand_fk",
        "collection_item__country",
    )

    def spec_type(self, obj):
        return obj.collection_item.spec_type or "-"

    spec_type.short_description = "Type"

    def brand_name(self, obj):
        if obj.collection_item.brand_fk:
            return obj.collection_item.brand_fk.brand_name

        return obj.collection_item.brand or "-"

    brand_name.short_description = "Brand"

    def country_name(self, obj):
        if obj.collection_item.country:
            return obj.collection_item.country.country_name

        return "-"

    country_name.short_description = "Country"

    def delete_model(self, request, obj):
        try:
            obj.delete()
        except IntegrityError as e:
            handle_fk_delete_error(self, request, e)

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            try:
                obj.delete()
            except IntegrityError as e:
                handle_fk_delete_error(self, request, e)



class CollectorItemAssignmentAdminForm(forms.ModelForm):

    island = forms.ModelChoiceField(
        queryset=DimIsland.objects.filter(
            dimoutlet__is_active=True
        ).distinct().order_by("island_name"),
        required=True,
        label="Island",
        widget=forms.Select(attrs={
            "onchange": "const c=document.getElementById('id_collector').value; window.location.href='?island=' + this.value + '&collector=' + c;"
        })
    )

    outlet = forms.ModelChoiceField(
        queryset=DimOutlet.objects.none(),
        required=True,
        label="Outlet",
        widget=forms.Select(attrs={
            "onchange": "const c=document.getElementById('id_collector').value; const i=document.getElementById('id_island').value; window.location.href='?island=' + i + '&collector=' + c + '&outlet=' + this.value + '&part=1;'"
        })
    )

    item_split = forms.ChoiceField(
        choices=(
            ("1", "First half"),
            ("2", "Second half"),
        ),
        required=True,
        label="Item split",
        initial="1",
        widget=forms.Select(attrs={
            "onchange": "const c=document.getElementById('id_collector').value; const i=document.getElementById('id_island').value; const o=document.getElementById('id_outlet').value; window.location.href='?island=' + i + '&collector=' + c + '&outlet=' + o + '&part=' + this.value;"
        })
    )


    items = forms.ModelMultipleChoiceField(
        queryset=CpiCollectionItem.objects.none(),
        required=True,
        widget=FilteredSelectMultiple("Items", is_stacked=False),
        label="Items"
    )

    class Meta:
        model = CollectorItemAssignment
        fields = ("collector", "island", "outlet", "item_split", "items", "is_active")


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["collector"].queryset = AppUser.objects.all().order_by("full_name")
        self.fields["is_active"].initial = True





@admin.register(CollectorItemAssignment)
class CollectorItemAssignmentAdmin(admin.ModelAdmin):
    form = CollectorItemAssignmentAdminForm

    list_display = (
        "collector",
        "island_name",
        "outlet_name",
        "item_split",
        "assigned_item_count",
        "is_active",
        "assigned_at",
    )

    list_filter = (
        "collector",
        "is_active",
        "collection_item__outlet",
        "collection_item__outlet__island",
    )

    search_fields = (
        "collector__full_name",
        "collection_item__basket_item__basket_item_name",
        "collection_item__outlet__outlet_name",
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        return (
            qs.select_related(
                "collector",
                "collection_item",
                "collection_item__outlet",
                "collection_item__outlet__island",
            )
            .order_by(
                "collector_id",
                "collection_item__outlet_id",
                "item_split",
                "assignment_id",
            )
            .distinct(
                "collector_id",
                "collection_item__outlet_id",
                "item_split",
            )
        )

    def save_form(self, request, form, change):
        obj = form.save(commit=False)

        items = form.cleaned_data.get("items")
        if items:
            obj.collection_item = items.first()

        return obj

    def save_model(self, request, obj, form, change):

        if change:
            obj.save()
            return

        collector = form.cleaned_data.get("collector")
        items = form.cleaned_data.get("items")
        is_active = form.cleaned_data.get("is_active")
        item_split_value = form.cleaned_data.get("item_split")

        if item_split_value == "1":
            item_split = "First half"
        elif item_split_value == "2":
            item_split = "Second half"
        else:
            item_split = None

        if not collector or not items:
            return
        
        outlet = items.first().outlet

        existing_assignment = CollectorItemAssignment.objects.filter(
            collection_item__outlet=outlet,
            item_split=item_split,
            is_active=True
        ).exclude(
            collector=collector
        ).select_related("collector").first()

        if existing_assignment:

            existing_collector = existing_assignment.collector.full_name

            messages.error(
                request,
                f"The {item_split} items of {outlet.outlet_name} are already assigned to {existing_collector}."
            )
            return

        already_assigned_items = []
        newly_assigned_items = []

        with transaction.atomic():

            for collection_item in items:

                exists = CollectorItemAssignment.objects.filter(
                    collector=collector,
                    collection_item=collection_item
                ).exists()

                item_name = collection_item.item.item_name

                if exists:
                    already_assigned_items.append(item_name)
                    continue

                CollectorItemAssignment.objects.create(
                    collector=collector,
                    collection_item=collection_item,
                    is_active=is_active,
                    item_split=item_split
                )

                newly_assigned_items.append(item_name)

        if newly_assigned_items:
            outlet_name = items.first().outlet.outlet_name

            messages.success(
                request,
                f"The {item_split.lower()} items of {outlet_name} are assigned to {collector.full_name}."
            )

        if already_assigned_items:
            messages.warning(
                request,
                "These item(s) are already assigned to this collector: "
                f"{', '.join(already_assigned_items)}"
            )

    def response_add(self, request, obj, post_url_continue=None):
        return HttpResponseRedirect("../")
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        island_id = request.GET.get("island")
        collector_id = request.GET.get("collector")
        outlet_id = request.GET.get("outlet")

        if collector_id:
            form.base_fields["collector"].initial = collector_id

        if island_id:
            form.base_fields["island"].initial = island_id
            form.base_fields["outlet"].queryset = (
                DimOutlet.objects
                .filter(is_active=True, island_id=island_id)
                .annotate(
                    item_count=Count(
                        "cpicollectionitem",
                        filter=models.Q(cpicollectionitem__is_active=True)
                    )
                )
                .filter(item_count__gt=60)
                .order_by("outlet_name")
            )
        else:
            form.base_fields["outlet"].queryset = DimOutlet.objects.none()

        if outlet_id:
            form.base_fields["outlet"].initial = outlet_id

            all_items = list(
                CpiCollectionItem.objects
                .filter(is_active=True, outlet_id=outlet_id)
                .select_related("item", "outlet")
                .order_by("sort_order", "product_name")
            )

            half = (len(all_items) + 1) // 2
            part = request.GET.get("part", "1")
            form.base_fields["item_split"].initial = part

            if part == "2":
                selected_items = all_items[half:]
            else:
                selected_items = all_items[:half]

            form.base_fields["items"].queryset = (
                CpiCollectionItem.objects
                .filter(collection_item_id__in=[
                    x.collection_item_id for x in selected_items
                ])
                .select_related("item", "outlet")
                .order_by("sort_order", "product_name")
            )
        else:
            form.base_fields["items"].queryset = CpiCollectionItem.objects.none()

        return form
    
    def island_name(self, obj):
        return obj.collection_item.outlet.island.island_name
    island_name.short_description = "Island"

    def outlet_name(self, obj):
        return obj.collection_item.outlet.outlet_name
    outlet_name.short_description = "Outlet"

    def assigned_item_count(self, obj):
        return CollectorItemAssignment.objects.filter(
            collector=obj.collector,
            collection_item__outlet=obj.collection_item.outlet,
            item_split=obj.item_split,
            is_active=obj.is_active,
        ).count()
    assigned_item_count.short_description = "Assigned items"


    def delete_model(self, request, obj):
        CollectorItemAssignment.objects.filter(
            collector=obj.collector,
            collection_item__outlet=obj.collection_item.outlet,
            item_split=obj.item_split,
        ).delete()

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            CollectorItemAssignment.objects.filter(
                collector=obj.collector,
                collection_item__outlet=obj.collection_item.outlet,
                item_split=obj.item_split,
            ).delete()

  

@admin.register(CpiReplacement)
class CpiReplacementAdmin(admin.ModelAdmin):

    list_display = (
        "replacement_id",
        "old_collection_item",
        "new_name",
        "new_brand",
        "new_made_in",
        "new_price",
        "replacement_status",
        "assignment_status",
        "action_buttons",
        "created_at",
    )

    list_filter = (
        "replacement_status",
        "created_at",
    )

    search_fields = (
        "new_name",
        "new_brand",
        "new_made_in",
        "old_collection_item__outlet__outlet_name",
        "old_collection_item__item__item_name",
    )

    readonly_fields = (
        "approved_collection_item",
        "assignment_status",
        "reviewed_at",
        "reviewed_by",
    )

    fields = (
        "old_collection_item",

        "new_name",
        "new_type",
        "new_size",
        "new_unit",

        "new_brand",

        "new_made_in",
        "new_item_group",
        "new_coicop_code",

        "new_price",
        "reason",
        "replacement_status",

        "reviewed_at",
        "reviewed_by",

        "approved_collection_item",
        "assignment_status",
    )

    def assignment_status(self, obj):

        if obj.replacement_status == "REJECTED":
            return format_html(
                '<span style="color: {}; font-weight: bold;">{}</span>',
                "red",
                "Rejected"
            )

        if obj.approved_collection_item:
            return format_html(
                '<span style="color: {}; font-weight: bold;">{}</span>',
                "green",
                "Assigned to outlet"
            )

        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            "orange",
            "Not assigned yet"
        )

    actions = (
        "approve_replacement",
        "reject_replacement",
        "delete_selected_replacements",
    )

    def get_actions(self, request):
        actions = super().get_actions(request)

        if "delete_selected" in actions:
            del actions["delete_selected"]

        return actions

    def action_buttons(self, obj):

        edit_url = reverse(
            "admin:cpi_cpireplacement_change",
            args=[obj.pk]
        )

        approve_url = reverse(
            "admin:cpi_cpireplacement_approve",
            args=[obj.pk]
        )

        reject_url = reverse(
            "admin:cpi_cpireplacement_reject",
            args=[obj.pk]
        )

        if obj.replacement_status == "APPROVED":
            return format_html(
                '<a class="button" href="{}">Edit</a>',
                edit_url
            )

        return format_html(
            '<a href="{}" style="background:#0d6efd;color:white;padding:4px 8px;border-radius:4px;text-decoration:none;margin-right:4px;">Edit</a>'
            '<a href="{}" style="background:#198754;color:white;padding:4px 8px;border-radius:4px;text-decoration:none;margin-right:4px;">Approve</a>'
            '<a href="{}" style="background:#dc3545;color:white;padding:4px 8px;border-radius:4px;text-decoration:none;">Reject</a>',
            edit_url,
            approve_url,
            reject_url
        )

    action_buttons.short_description = "Actions"



    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        for field in [
            "new_name",
            "new_brand",
            "new_made_in",
            "new_type",
            "new_size",
            "new_unit",
        ]:
            if field in form.base_fields:
                form.base_fields[field].widget = forms.TextInput(
                    attrs={"style": "width:400px;"}
                )

        return form

    def delete_selected_replacements(self, request, queryset):

        deleted_count = 0
        blocked_count = 0

        for replacement in queryset:

            linked_photos = CpiPhoto.objects.filter(
                replacement_id=replacement.replacement_id
            ).exists()

            if linked_photos:
                blocked_count += 1
                continue

            replacement.delete()
            deleted_count += 1

        if blocked_count > 0:
            self.message_user(
                request,
                f"{blocked_count} replacement(s) were not deleted because related photos exist.",
                level=messages.ERROR
            )

        if deleted_count > 0:
            self.message_user(
                request,
                f"{deleted_count} replacement(s) deleted successfully.",
                level=messages.SUCCESS
            )

    delete_selected_replacements.short_description = "Delete selected replacements"
    
    
    def delete_model(self, request, obj):

        linked_photos = CpiPhoto.objects.filter(
            replacement_id=obj.replacement_id
        ).exists()

        if linked_photos:
            self.message_user(
                request,
                (
                    f"Replacement {obj.replacement_id} cannot be deleted "
                    "because one or more photos are linked to it. "
                    "Delete the related photos first."
                ),
                level=messages.ERROR
            )
            return

        super().delete_model(request, obj)

    

        
    def get_urls(self):
        urls = super().get_urls()

        custom_urls = [
            path(
                "<int:replacement_id>/approve/",
                self.admin_site.admin_view(self.approve_single_replacement),
                name="cpi_cpireplacement_approve",
            ),
            path(
                "<int:replacement_id>/reject/",
                self.admin_site.admin_view(self.reject_single_replacement),
                name="cpi_cpireplacement_reject",
            ),
        ]

        return custom_urls + urls
    

    def approve_single_replacement(self, request, replacement_id):

        replacement = get_object_or_404(CpiReplacement, pk=replacement_id)

        self.approve_replacement(request, CpiReplacement.objects.filter(pk=replacement_id))

        return redirect("admin:cpi_cpireplacement_changelist")


    def reject_single_replacement(self, request, replacement_id):

        replacement = get_object_or_404(CpiReplacement, pk=replacement_id)

        if request.method == "POST":

            rejection_comment = request.POST.get("rejection_comment", "").strip()

            if not rejection_comment:
                self.message_user(
                    request,
                    "Rejection reason is required.",
                    messages.ERROR
                )
                return redirect("admin:cpi_cpireplacement_reject", replacement_id)

            replacement.replacement_status = "REJECTED"
            replacement.rejection_comment = rejection_comment
            replacement.reviewed_at = timezone.now()
            replacement.reviewed_by = None
            replacement.last_modified_at = timezone.now()
            replacement.save(
                update_fields=[
                    "replacement_status",
                    "rejection_comment",
                    "reviewed_at",
                    "reviewed_by",
                    "last_modified_at",
                ]
            )

            self.message_user(
                request,
                "Replacement rejected successfully.",
                messages.WARNING
            )

            return redirect("admin:cpi_cpireplacement_changelist")

        context = {
            **self.admin_site.each_context(request),
            "replacement": replacement,
        }

        return TemplateResponse(
            request,
            "admin/reject_replacement.html",
            context
        )



    @admin.action(description="Approve selected replacement(s) and create collection item")
    def approve_replacement(self, request, queryset):

        approved_count = 0
        skipped_count = 0

        for replacement in queryset:

            if replacement.replacement_status == "APPROVED":
                skipped_count += 1
                continue

            if replacement.approved_collection_item:
                skipped_count += 1
                continue

            old_collection_item = replacement.old_collection_item
            basket_item = old_collection_item.basket_item
            outlet = old_collection_item.outlet

            with transaction.atomic():

                brand_obj = replacement.new_brand_fk
                country_obj = replacement.new_made_in_fk

                if not brand_obj and replacement.new_brand:
                    brand_obj, _ = DimBrand.objects.get_or_create(
                        brand_name=replacement.new_brand.strip()
                    )

                if not country_obj and replacement.new_made_in:
                    country_obj, _ = DimCountry.objects.get_or_create(
                        country_name=replacement.new_made_in.strip()
                    )

                specification_parts = []

                if replacement.new_type:
                    specification_parts.append(
                        f"Type: {replacement.new_type.strip()}"
                    )

                if replacement.new_size:
                    specification_parts.append(
                        f"Size: {replacement.new_size.strip()}"
                    )

                if replacement.new_unit:
                    specification_parts.append(
                        f"Unit of Measure: {replacement.new_unit.strip()}"
                    )

                if replacement.new_brand:
                    specification_parts.append(
                        f"Brand: {replacement.new_brand.strip()}"
                    )

                if replacement.new_made_in:
                    specification_parts.append(
                        f"Made in: {replacement.new_made_in.strip()}"
                    )

                product_specification = "\n".join(specification_parts)

                if not product_specification:
                    product_specification = (
                        old_collection_item.product_specification
                    )

                new_collection_item = CpiCollectionItem.objects.create(
                    outlet=outlet,
                    basket_item=basket_item,
                    matched_basket_name=(
                        old_collection_item.matched_basket_name
                        or (
                            basket_item.basket_item_name
                            if basket_item
                            else None
                        )
                    ),
                    product_name=(
                        replacement.new_name
                        or old_collection_item.product_name
                    ),
                    brand=(
                        brand_obj.brand_name
                        if brand_obj
                        else (
                            replacement.new_brand
                            or old_collection_item.brand
                        )
                    ),
                    brand_fk=brand_obj,
                    country=country_obj,
                    imported_country=country_obj,
                    product_specification=product_specification,
                    sort_order=old_collection_item.sort_order,
                    is_active=True,
                    valid_from=timezone.now().date(),
                    item_status="ACTIVE",
                    last_price=replacement.new_price,
                )

                old_collection_item.is_active = False
                old_collection_item.valid_to = timezone.now().date()
                old_collection_item.item_status = "REPLACED"
                old_collection_item.save()

                replacement.replacement_status = "APPROVED"
                replacement.approved_collection_item = new_collection_item
                replacement.last_modified_at = timezone.now()
                replacement.save()

                approved_count += 1

        self.message_user(
            request,
            f"{approved_count} replacement(s) approved and assigned to outlet. "
            f"{skipped_count} skipped.",
            messages.SUCCESS
        )

    @admin.action(description="Reject selected replacement(s)")
    def reject_replacement(self, request, queryset):

        updated = queryset.exclude(
            replacement_status="APPROVED"
        ).update(
            replacement_status="REJECTED",
            last_modified_at=timezone.now()
        )

        self.message_user(
            request,
            f"{updated} replacement(s) rejected.",
            messages.WARNING
        )


@admin.register(CpiPhoto)
class CpiPhotoAdmin(admin.ModelAdmin):

    list_display = (
        "photo_id",
        "collection_item",
        "replacement",
        "photo_type",
        "file_name",
        "taken_at",
        "sync_status",
    )

    search_fields = (
        "file_name",
        "collection_item__basket_item__basket_item_name",
        "collection_item__outlet__outlet_name",
    )

    list_filter = (
        "photo_type",
        "sync_status",
    )


@admin.register(AppUser)
class AppUserAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "django_username",
        "role",
        "phone_number",
        "is_active",
    )

    list_filter = (
        "role",
        "is_active",
    )

    search_fields = (
        "full_name",
        "django_user__username",
        "django_user__email",
        "phone_number",
    )

    ordering = (
        "full_name",
    )

    @admin.display(description="Username")
    def django_username(self, obj):
        return obj.django_user.username


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
        "collection_item_id",
        "outlet",
        "island_code_display",
        "outlet_code_display",
        "item_code_display",

        "product_name",
        "brand",
        "spec_type",
        "material",

        "country",
        "imported_country",

        "product_specification",
        "other_spec",

        "specification_no",
        "product_code",

        "excel_subgroup",

        "sort_order",
        "last_price",
        "is_active",
    )

    ordering = (
        "outlet__outlet_name",
        "sort_order",
    )


    list_filter = (
        "outlet",
        "brand",
        "is_active",
    )

    exclude = (
    "specification_no",
    "product_code",
    "valid_to",
    "item_status",
    )

    search_fields = ("item__item_name", "outlet__outlet_name")

    fields = (
    "outlet",
    "item",
    "last_price",
    "last_price_month",
    "valid_from",
    "is_active",
    )

    exclude = (
    "specification_no",
    "product_code",
    "valid_to",
    "item_status",
    )

    def delete_model(self, request, obj):
        try:
            obj.delete()
        except IntegrityError as e:
            handle_fk_delete_error(self, request, e)

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            try:
                obj.delete()
            except IntegrityError as e:
                handle_fk_delete_error(self, request, e)

    def item_size(self, obj):
        return obj.item.size_value
    item_size.short_description = "Size"

    def item_unit(self, obj):
        return obj.item.unit
    item_unit.short_description = "Unit"

    def item_brand(self, obj):
        return obj.item.brand
    item_brand.short_description = "Brand"

    def item_country(self, obj):
        return obj.item.country
    item_country.short_description = "Country"

    def island_code_display(self, obj):
        if obj.outlet and obj.outlet.island:
            return obj.outlet.island.island_code
        return "-"

    island_code_display.short_description = "Island Code"


    def outlet_code_display(self, obj):
        if obj.outlet:
            return obj.outlet.outlet_code
        return "-"

    outlet_code_display.short_description = "Outlet Code"


    def item_code_display(self, obj):
        if obj.basket_item:
            return obj.basket_item.basket_code
        return "-"

    item_code_display.short_description = "Item Code"






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





@admin.action(description="Revoke selected outlet assignments")
def revoke_assignments(modeladmin, request, queryset):
    queryset.update(is_active=False)

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
    list_editable = ("is_active",)
    actions = [revoke_assignments]

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
                .annotate(
                    item_count=Count(
                        "cpicollectionitem",
                        filter=models.Q(cpicollectionitem__is_active=True)
                    )
                )
                .filter(item_count__lte=60)
                .order_by("outlet_name")
            )
        else:
            form.base_fields["outlets"].queryset = DimOutlet.objects.none()

        return form
    def response_add(self, request, obj, post_url_continue=None):
        return HttpResponseRedirect("../")
    
       
    def save_form(self, request, form, change):
        obj = form.save(commit=False)

        outlets = form.cleaned_data.get("outlets")
        if outlets:
            obj.outlet = outlets.first()

        return obj



    def save_model(self, request, obj, form, change):

        # Normal edit
        if change:
            obj.save()
            return

        collector = form.cleaned_data.get("collector")
        outlets = form.cleaned_data.get("outlets")
        is_active = form.cleaned_data.get("is_active")

        if not collector or not outlets:
            return

        already_assigned_outlets = []
        newly_assigned_outlets = []

        with transaction.atomic():

            for outlet in outlets:

                existing_assignment = CollectorAssignment.objects.filter(
                    outlet=outlet,
                    is_active=True
                ).select_related("collector").first()

                if existing_assignment:
                    already_assigned_outlets.append(
                        f"{outlet.outlet_name} is already assigned to {existing_assignment.collector.full_name}"
                    )
                    continue

                CollectorAssignment.objects.create(
                    collector=collector,
                    outlet=outlet,
                    is_active=is_active
                )

                newly_assigned_outlets.append(outlet.outlet_name)

        if newly_assigned_outlets and not already_assigned_outlets:

            if len(newly_assigned_outlets) == 1:

                messages.success(
                    request,
                    f"{newly_assigned_outlets[0]} "
                    f"was successfully assigned to {collector.full_name}."
                )

            else:

                messages.success(
                    request,
                    f"These outlets were successfully assigned to "
                    f"{collector.full_name}: "
                    f"{', '.join(newly_assigned_outlets)}"
                )

        elif already_assigned_outlets and not newly_assigned_outlets:

            messages.warning(
                request,
                "; ".join(already_assigned_outlets) + "."
            )

        elif newly_assigned_outlets and already_assigned_outlets:

            messages.success(
                request,
                f"These outlets were successfully assigned to "
                f"{collector.full_name}: "
                f"{', '.join(newly_assigned_outlets)}"
            )

            messages.warning(
                request,
                "; ".join(already_assigned_outlets) + "."
            )


    def delete_model(self, request, obj):
        try:
            obj.delete()
        except IntegrityError as e:
            handle_fk_delete_error(self, request, e)

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            try:
                obj.delete()
            except IntegrityError as e:
                handle_fk_delete_error(self, request, e)


@admin.register(CollectorWorkloadSummary)
class CollectorWorkloadSummaryAdmin(admin.ModelAdmin):
    list_display = (
        "island_name",
        "outlet_name",
        "total_items",
        "assignment_type",
        "item_split",
        "collector_name",
        "assigned_items",
        "is_active",
        "assigned_date",
    )

    list_filter = (
        "island_name",
        "assignment_type",
        "item_split",
        "is_active",
        "collector_name",
    )

    search_fields = (
        "island_name",
        "outlet_name",
        "collector_name",
    )

    ordering = (
        "island_name",
        "outlet_name",
        "assignment_type",
        "collector_name",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
