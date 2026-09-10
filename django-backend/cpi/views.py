import os
from calendar import monthrange
from math import atan2, cos, radians, sin, sqrt

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.files.storage import FileSystemStorage
from django.db import connection, transaction
from django.db.models import Count, Max, Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt

from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.shortcuts import redirect
from .decorators import supervisor_required
from django.views.decorators.http import require_GET, require_POST
from django.db import transaction
from cpi.models import CpiPhoto
from rest_framework.views import APIView
from rest_framework import status
from .models import FactPrice

from .models import AppUser
from .serializers import LoginSerializer



from .models import (
    AppUser,
    CollectorAssignment,
    CollectorItemAssignment,
    CollectorWorkloadSummary,
    CpiBasket,
    CpiCollectionItem,
    CpiPhoto,
    CpiReplacement,
    CpiRound,
    CpiVisit,
    DimBrand,
    DimCountry,
    DimIsland,
    DimOutlet,
    DimOutletType,
    DimUnit,
    FactPrice,
)

from .permissions import IsAdministrator

from .serializers import (
    AppUserCreateSerializer,
    AssignedOutletSerializer,
    CpiCollectionItemSerializer,
    FactPriceSerializer,
    LoginSerializer,
)

from .decorators import (
    admin_required,
    supervisor_required,
    viewer_required,
)

@api_view(["GET"])
def saved_price(request, visit_id, collection_item_id):
    try:
        price = FactPrice.objects.get(
            visit_id=visit_id,
            collection_item_id=collection_item_id,
            is_deleted=False
        )
    except FactPrice.DoesNotExist:
        return Response({"found": False})

    replacement = CpiReplacement.objects.filter(
        price_id=price.price_id,
        old_collection_item_id=collection_item_id,
        is_deleted=False
    ).first()

    return Response({
        "found": True,
        "availability": price.availability,
        "observed_price": str(price.observed_price) if price.observed_price is not None else "",
        "remarks": price.remarks or "",

        "supervisor_comment": price.supervisor_comment or "",
        "review_status": price.review_status or "",

        "new_item_name": replacement.new_name if replacement else "",
        "new_item_type": replacement.new_type if replacement else "",
        "new_item_size": replacement.new_size if replacement else "",
        "new_item_unit": replacement.new_unit if replacement else "",
        "new_item_brand": replacement.new_brand if replacement else "",

        # Use country ID for Android dropdown
        "new_item_country_id": (
            replacement.new_made_in_fk_id
            if replacement and replacement.new_made_in_fk_id
            else ""
        ),

        "new_item_price": str(replacement.new_price) if replacement and replacement.new_price is not None else "",

        # Rejection feedback for Android
        "replacement_status": replacement.replacement_status if replacement else "",
        "rejection_comment": replacement.rejection_comment if replacement else "",
    })



@api_view(["GET"])
def countries_list(request):
    countries = (
        DimCountry.objects
        .all()
        .order_by("country_name")
        .values("country_id", "country_name")
    )

    return Response(list(countries))

@api_view(["GET"])
def item_photo(request, collection_item_id):

    photo = (
        CpiPhoto.objects
        .filter(
            collection_item_id=collection_item_id,
            photo_type="REFERENCE_ITEM",
            is_deleted=False
        )
        .order_by("-photo_id")
        .first()
    )

    if not photo:
        return Response(
            {"found": False},
            status=404
        )



    full_path = os.path.join(
        settings.MEDIA_ROOT,
        "cpi_photos",
        photo.file_name
    )

    if not os.path.exists(full_path):
        return Response(
            {"found": False},
            status=404
        )

    return Response({
        "found": True,
        "file_name": photo.file_name,
        "file_path": photo.file_path,
    })




@api_view(["GET"])
def outlet_items(request, outlet_id):

    collector_id = request.GET.get("collector_id")

    if collector_id:
        assigned_item_ids = (
            CollectorItemAssignment.objects
            .filter(
                collector_id=collector_id,
                collection_item__outlet_id=outlet_id,
                is_active=True
            )
            .values_list("collection_item_id", flat=True)
        )

        # Large outlet split assignment: show only assigned half
        if assigned_item_ids.exists():
            items = (
                CpiCollectionItem.objects
                .filter(
                    collection_item_id__in=assigned_item_ids,
                    is_active=True
                )
                .select_related("outlet", "basket_item")
                .order_by("sort_order", "product_name")
            )

        # Normal outlet assignment: show all items
        else:
            items = (
                CpiCollectionItem.objects
                .filter(outlet_id=outlet_id, is_active=True)
                .select_related("outlet", "basket_item")
                .order_by("sort_order", "product_name")
            )

    else:
        items = (
            CpiCollectionItem.objects
            .filter(outlet_id=outlet_id, is_active=True)
            .select_related("outlet", "basket_item")
            .order_by("sort_order", "product_name")
        )

    serializer = CpiCollectionItemSerializer(items, many=True)

    data = list(serializer.data)

    latest_visit = (
        CpiVisit.objects
        .filter(
            collector_user_id=collector_id,
            outlet_id=outlet_id,
            is_deleted=False,
        )
        .order_by("-visit_id")
        .first()
    )

    price_map = {}

    if latest_visit:

        prices = FactPrice.objects.filter(
            visit=latest_visit,
            is_deleted=False,
        )

        if collector_id and assigned_item_ids.exists():
            prices = prices.filter(
                collection_item_id__in=assigned_item_ids
            )

        for price in prices:

            price_map[price.collection_item_id] = {
                "availability": price.availability,

                "observed_price": (
                    str(price.observed_price)
                    if price.observed_price is not None
                    else None
                ),

                "remarks": price.remarks or "",

                "is_outlier": bool(price.is_outlier),

                "outlier_level": price.outlier_level or "NONE",

                "quote_status": price.quote_status or "",

                "review_status": price.review_status or "",

                "supervisor_comment": price.supervisor_comment or "",
            }


    for item in data:

        response_data = price_map.get(
            item["collection_item_id"]
        )

        item["is_collected"] = response_data is not None

        item["collected_response"] = response_data


    return Response(data)

@api_view(["GET"])
def collector_outlets(request, collector_id):

    normal_outlet_ids = (
        CollectorAssignment.objects
        .filter(
            collector_id=collector_id,
            is_active=True
        )
        .values_list("outlet_id", flat=True)
    )

    split_outlet_ids = (
        CollectorItemAssignment.objects
        .filter(
            collector_id=collector_id,
            is_active=True
        )
        .values_list("collection_item__outlet_id", flat=True)
    )

    outlet_ids = list(set(list(normal_outlet_ids) + list(split_outlet_ids)))

    outlets = (
        DimOutlet.objects
        .filter(
            outlet_id__in=outlet_ids,
            is_active=True
        )
        .select_related("island")
        .distinct()
        .order_by("island__island_name", "outlet_name")
    )

    data = []

    for outlet in outlets:

        assigned_item_ids = (
            CollectorItemAssignment.objects
            .filter(
                collector_id=collector_id,
                collection_item__outlet=outlet,
                is_active=True
            )
            .values_list("collection_item_id", flat=True)
        )
        is_split_assignment = assigned_item_ids.exists()

        if assigned_item_ids.exists():
            total_items = CpiCollectionItem.objects.filter(
                collection_item_id__in=assigned_item_ids,
                is_active=True
            ).count()
        else:
            total_items = CpiCollectionItem.objects.filter(
                outlet=outlet,
                is_active=True
            ).count()

        latest_visit = CpiVisit.objects.filter(
            collector_user_id=collector_id,
            outlet=outlet,
            is_deleted=False
        ).order_by("-visit_id").first()

        # A completed outlet must not be downloaded
        # to the collector's tablet again.
        if (
            latest_visit
            and latest_visit.visit_status in (
                "COMPLETED",
                "CORRECTED_PENDING_REVIEW",
            )
            and latest_visit.review_status != "REJECTED"
        ):
            continue

        visit_status = None
        collected_items = 0

        if latest_visit:

            visit_status = latest_visit.visit_status

            if assigned_item_ids.exists():

                collected_items = FactPrice.objects.filter(
                    visit=latest_visit,
                    collection_item_id__in=assigned_item_ids,
                    quote_status="SUBMITTED"
                ).values("collection_item").distinct().count()

            else:

                collected_items = FactPrice.objects.filter(
                    visit=latest_visit,
                    collection_item__outlet=outlet,
                    quote_status="SUBMITTED"
                ).values("collection_item").distinct().count()

       
            if assigned_item_ids.exists():
                collected_items = FactPrice.objects.filter(
                    visit=latest_visit,
                    collection_item_id__in=assigned_item_ids,
                    quote_status="SUBMITTED"
                ).values("collection_item").distinct().count()
            else:
                collected_items = FactPrice.objects.filter(
                    visit=latest_visit,
                    collection_item__outlet=outlet,
                    quote_status="SUBMITTED"
                ).values("collection_item").distinct().count()

        correction_count = 0

        corrections = []

        if latest_visit:
            correction_prices = FactPrice.objects.filter(
                visit=latest_visit,
                review_status="CORRECTION_REQUIRED",
                is_deleted=False
            ).select_related("collection_item")

            if assigned_item_ids.exists():
                correction_prices = correction_prices.filter(
                    collection_item_id__in=assigned_item_ids
                )

            corrections = [
                {
                    "collection_item_id": price.collection_item_id,
                    "supervisor_comment": price.supervisor_comment,
                }
                for price in correction_prices
            ]

        if latest_visit:
            correction_qs = FactPrice.objects.filter(
                visit=latest_visit,
                review_status="CORRECTION_REQUIRED",
                is_deleted=False
            )

            if assigned_item_ids.exists():
                correction_qs = correction_qs.filter(
                    collection_item_id__in=assigned_item_ids
                )

            correction_count = correction_qs.count()       

        data.append({
            "outlet_id": outlet.outlet_id,
            "outlet_name": outlet.outlet_name,
            "island_name": outlet.island.island_name,
            "total_items": total_items,
            "collected_items": collected_items,
            "visit_status": visit_status,
            "is_split_assignment": is_split_assignment,
            "correction_count": correction_count,
            "corrections": corrections,

            "outlet_rejected": (
                latest_visit is not None
                and latest_visit.review_status == "REJECTED"
            ),

            "outlet_rejection_comment": (
                latest_visit.remarks
                if latest_visit
                and latest_visit.review_status == "REJECTED"
                else None
            ),

            "visit_id": (
                latest_visit.visit_id
                if latest_visit and latest_visit.review_status == "REJECTED"
                else None
            ),

            "local_uuid": (
                str(latest_visit.local_uuid)
                if latest_visit
                and latest_visit.review_status == "REJECTED"
                and latest_visit.local_uuid
                else None
            ),

            "start_time": (
                latest_visit.start_time.isoformat()
                if latest_visit
                and latest_visit.review_status == "REJECTED"
                and latest_visit.start_time
                else None
            ),

            "end_time": (
                latest_visit.end_time.isoformat()
                if latest_visit
                and latest_visit.review_status == "REJECTED"
                and latest_visit.end_time
                else None
            ),

            "gps_lat": (
                float(latest_visit.gps_lat)
                if latest_visit
                and latest_visit.review_status == "REJECTED"
                and latest_visit.gps_lat is not None
                else None
            ),

            "gps_lon": (
                float(latest_visit.gps_lon)
                if latest_visit
                and latest_visit.review_status == "REJECTED"
                and latest_visit.gps_lon is not None
                else None
            ),

            "gps_accuracy_m": (
                float(latest_visit.gps_accuracy_m)
                if latest_visit
                and latest_visit.review_status == "REJECTED"
                and latest_visit.gps_accuracy_m is not None
                else None
            ),

            "gps_distance_meters": (
                float(latest_visit.gps_distance_meters)
                if latest_visit
                and latest_visit.review_status == "REJECTED"
                and latest_visit.gps_distance_meters is not None
                else None
            ),

            "gps_within_range": (
                latest_visit.gps_within_range
                if latest_visit and latest_visit.review_status == "REJECTED"
                else None
            ),

            "gps_recorded_at": (
                latest_visit.gps_recorded_at.isoformat()
                if latest_visit
                and latest_visit.review_status == "REJECTED"
                and latest_visit.gps_recorded_at
                else None
            ),
        })

    return Response(data)







@csrf_exempt
@api_view(["POST"])
def start_visit(request):

    collector_id = request.data.get("collector_id")
    outlet_id = request.data.get("outlet_id")
    local_uuid = request.data.get("local_uuid")

    if not collector_id or not outlet_id or not local_uuid:
        return Response(
            {
                "error":
                "collector_id, outlet_id and local_uuid are required"
            },
            status=400
        )
    
    open_round = CpiRound.objects.filter(round_status="OPEN").first()

    if not open_round:
        return Response(
            {"error": "No open CPI round. Please contact supervisor."},
            status=400
        )

    existing_local_visit = CpiVisit.objects.filter(
        local_uuid=local_uuid,
        is_deleted=False
    ).first()

    if existing_local_visit:
        return Response(
            {
                "visit_id": existing_local_visit.visit_id,
                "local_uuid": str(existing_local_visit.local_uuid),
                "reused": True,
            },
            status=200
        )

    existing_visit = CpiVisit.objects.filter(
        collector_user_id=collector_id,
        outlet_id=outlet_id,
        round=open_round,
        is_deleted=False
    ).order_by("-visit_id").first()

    if existing_visit:
        return Response({
            "visit_id": existing_visit.visit_id,
            "reused": True
        }, status=200)

    visit = CpiVisit.objects.create(
        collector_user_id=collector_id,
        outlet_id=outlet_id,
        round=open_round,
        local_uuid=local_uuid,
        visit_status="IN_PROGRESS",
        sync_status="SYNCED",
        created_on_device=True,
        is_deleted=False,
        created_at=timezone.now(),
        last_modified_at=timezone.now(),
    )

    return Response(
        {
            "visit_id": visit.visit_id,
            "local_uuid": str(visit.local_uuid),
            "reused": False,
        },
        status=201
    )


@csrf_exempt
@api_view(["POST"])
def record_start_time(request):
    visit_id = request.data.get("visit_id")
    start_time = request.data.get("start_time")

    print("START TIME REQUEST:", request.data)

    if not visit_id:
        return Response({"error": "visit_id is required"}, status=400)

    if not start_time:
        return Response({"error": "start_time is required"}, status=400)

    parsed_time = parse_datetime(start_time)

    if not parsed_time:
        return Response({"error": "Invalid datetime format", "value": start_time}, status=400)

    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE cpi_visit
            SET start_time = %s,
                last_modified_at = NOW()
            WHERE visit_id = %s
            """,
            [parsed_time, visit_id]
        )

    print("RAW SQL SAVED START TIME:", parsed_time)

    return Response({"message": "Start time saved"}, status=200)

@csrf_exempt
@api_view(["POST"])
def record_end_time(request):
    visit_id = request.data.get("visit_id")
    end_time = request.data.get("end_time")
    incomplete_reason = request.data.get("incomplete_reason")

    if not visit_id:
        return Response({"error": "visit_id is required"}, status=400)

    if not end_time:
        return Response({"error": "end_time is required"}, status=400)

    parsed_time = parse_datetime(end_time)

    if not parsed_time:
        return Response(
            {"error": "Invalid datetime format", "value": end_time},
            status=400
        )

    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE cpi_visit
            SET end_time = %s,
                visit_status = 'COMPLETED',
                incomplete_reason = %s,

                review_status = CASE
                    WHEN review_status = 'REJECTED'
                    THEN 'CORRECTED_PENDING_REVIEW'
                    ELSE review_status
                END,

                reviewed_at = CASE
                    WHEN review_status = 'REJECTED'
                    THEN NULL
                    ELSE reviewed_at
                END,

                last_modified_at = NOW()

            WHERE visit_id = %s
            """,
            [parsed_time, incomplete_reason, visit_id]
        )

    return Response({"message": "End time saved"}, status=200)



@csrf_exempt
@api_view(["POST"])
def submit_price(request):
    collection_item_id = request.data.get("collection_item")
    observed_price = request.data.get("observed_price")
    availability = request.data.get("availability")
    remarks = request.data.get("remarks", "")
    visit_id = request.data.get("visit_id")

    existing_price = FactPrice.objects.filter(
        visit_id=visit_id,
        collection_item_id=collection_item_id,
        is_deleted=False
    ).first()

    if existing_price and existing_price.review_status == "CORRECTION_REQUIRED":
        if not remarks or not remarks.strip():
            return Response(
                {"error": "Please add a response in remarks before saving this corrected item."},
                status=400
            )

    if not collection_item_id:
        return Response({"error": "collection_item is required"}, status=400)

    if not visit_id:
        return Response({"error": "visit_id is required"}, status=400)

    current_visit = CpiVisit.objects.get(visit_id=visit_id)

    previous_price = (
        FactPrice.objects
        .filter(
            collection_item_id=collection_item_id,
            visit__round_id=current_visit.round_id - 1,
            is_deleted=False
        )
        .order_by("-created_at")
        .first()
    )
    
    collection_item = CpiCollectionItem.objects.get(
        collection_item_id=collection_item_id
    )

    last_month_price = collection_item.last_price

    # Calculate outlier
    is_outlier = False
    outlier_level = "NONE"
    change_percent = 0

    if observed_price and last_month_price:
        try:
            observed = float(observed_price)
            previous = float(last_month_price)

            if previous > 0:
                change_percent = round(
                    abs(observed - previous) / previous * 100,
                    1
                )

                if change_percent > 20:
                    outlier_level = "HIGH"
                    is_outlier = True

                elif change_percent > 10:
                    outlier_level = "MEDIUM"

                elif change_percent > 5:
                    outlier_level = "LOW"

        except:
            is_outlier = False
            outlier_level = "NONE"
            change_percent = 0


    # ✅ ADD THIS BLOCK HERE
    if is_outlier and not remarks:
        return Response(
            {"error": "Remarks required for outlier"},
            status=400
        )

    existing_price = FactPrice.objects.filter(
        visit_id=visit_id,
        collection_item_id=collection_item_id,
        is_deleted=False
    ).first()

    new_review_status = "PENDING_REVIEW"
    new_supervisor_comment = None

    price, created = FactPrice.objects.update_or_create(
        visit_id=visit_id,
        collection_item_id=collection_item_id,
        defaults={
            "observed_price": observed_price,
            "last_month_price": last_month_price,
            "availability": availability or "AVAILABLE",
            "is_outlier": is_outlier,
            "outlier_level": outlier_level,
            "remarks": remarks,

            "review_status": new_review_status,
            "supervisor_comment": new_supervisor_comment,
            "reviewed_at": None,

            "quote_status": "SUBMITTED",
            "sync_status": "SYNCED",
            "created_on_device": False,
            "is_deleted": False,
            "created_at": timezone.now(),
            "updated_at": timezone.now(),
            "last_modified_at": timezone.now(),
        }
    )

    if existing_price and existing_price.review_status == "CORRECTION_REQUIRED":
        current_visit.review_status = "CORRECTED_PENDING_REVIEW"
        current_visit.reviewed_at = None
        current_visit.save(update_fields=["review_status", "reviewed_at"])



    if availability == "PERMANENT":
        print("REQUEST DATA:", request.data)

        replacement = (
            CpiReplacement.objects
            .filter(
                price_id=price.price_id,
                old_collection_item_id=collection_item_id
            )
            .order_by("-replacement_id")
            .first()
        )
        country_id = request.data.get("new_item_country_id")

        country_obj = None
        country_name = ""

        if country_id:
            country_obj = DimCountry.objects.filter(
                country_id=country_id
            ).first()

            if country_obj:
                country_name = country_obj.country_name
        if replacement:
            replacement.new_name = request.data.get("new_item_name")
            replacement.new_type = request.data.get("new_item_type")
            replacement.new_size = request.data.get("new_item_size")
            replacement.new_unit = request.data.get("new_item_unit")
            replacement.new_brand = request.data.get("new_item_brand")
            replacement.new_made_in = country_name
            replacement.new_made_in_fk = country_obj
            replacement.new_price = request.data.get("new_item_price")
            replacement.reason = remarks
            replacement.replacement_status = "PENDING"
            replacement.sync_status = "SYNCED"
            replacement.is_deleted = False
            replacement.server_received_at = timezone.now()
            replacement.last_modified_at = timezone.now()
            replacement.save()
        else:
            CpiReplacement.objects.create(
                price_id=price.price_id,
                old_collection_item_id=collection_item_id,
                new_name=request.data.get("new_item_name"),
                new_type=request.data.get("new_item_type"),
                new_size=request.data.get("new_item_size"),
                new_unit=request.data.get("new_item_unit"),
                new_brand=request.data.get("new_item_brand"),
                new_made_in=country_name,
                new_made_in_fk=country_obj,
                new_price=request.data.get("new_item_price"),
                reason=remarks,
                replacement_status="PENDING",
                sync_status="SYNCED",
                created_on_device=False,
                is_deleted=False,
                created_at=timezone.now(),
                server_received_at=timezone.now(),
                last_modified_at=timezone.now(),
            )

    else:
        CpiReplacement.objects.filter(
            price_id=price.price_id,
            old_collection_item_id=collection_item_id
        ).delete()

    return Response(
        {
            "message": "Price saved",
            "price_id": price.price_id,
            "created": created,
            "is_outlier": is_outlier,
            "replacement_id": replacement.replacement_id if availability == "PERMANENT" and replacement else None
        },
        status=201
    )



@api_view(["POST"])
def collector_login(request):
    username = request.data.get("username")
    password = request.data.get("password")

    if not username or not password:
        return Response(
            {"error": "Username and password are required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    django_user = authenticate(
        request,
        username=username,
        password=password
    )

    if django_user is None:
        return Response(
            {"error": "Invalid username or password"},
            status=status.HTTP_401_UNAUTHORIZED
        )

    if not django_user.is_active:
        return Response(
            {"error": "This account is inactive"},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        app_user = django_user.cpi_profile
    except AppUser.DoesNotExist:
        return Response(
            {"error": "CPI user profile not found"},
            status=status.HTTP_403_FORBIDDEN
        )

    if not app_user.is_active:
        return Response(
            {"error": "This CPI user account is inactive"},
            status=status.HTTP_403_FORBIDDEN
        )

    if not app_user.is_collector:
        return Response(
            {"error": "Only collectors can log in to the Android application"},
            status=status.HTTP_403_FORBIDDEN
        )

    serializer = LoginSerializer(app_user)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["POST"])
def record_gps(request):
    visit_id = request.data.get("visit_id")
    latitude = request.data.get("latitude")
    longitude = request.data.get("longitude")
    accuracy = request.data.get("accuracy")

    try:
        visit = CpiVisit.objects.select_related("outlet").get(visit_id=visit_id)
    except CpiVisit.DoesNotExist:
        return Response({"error": "Visit not found"}, status=404)

    visit.gps_lat = latitude
    visit.gps_lon = longitude
    visit.gps_accuracy_m = accuracy
    visit.gps_recorded_at = timezone.now()

    outlet = visit.outlet

    distance_meters = None
    within_range = None
    message = "GPS recorded"

    if outlet.latitude is not None and outlet.longitude is not None:
        lat1 = radians(float(outlet.latitude))
        lon1 = radians(float(outlet.longitude))
        lat2 = radians(float(latitude))
        lon2 = radians(float(longitude))

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        distance_meters = 6371000 * c
        within_range = distance_meters <= outlet.allowed_radius_meters

        visit.gps_distance_meters = round(distance_meters, 2)
        visit.gps_within_range = within_range

        if within_range:
            message = "GPS recorded"
        else:
            message = "Outside outlet range"

    visit.save()

    return Response({
        "message": message,
        "distance_meters": distance_meters,
        "within_range": within_range
    })

@csrf_exempt
@api_view(["POST"])
def upload_item_photo(request):

    replacement_id = request.data.get("replacement_id")
    visit_id = request.data.get("visit_id")
    collection_item_id = request.data.get("collection_item_id")

    photo = request.FILES.get("photo")
    photo_type = request.data.get("photo_type", "ITEM")

    if not photo:
        return Response(
            {"error": "Photo is required"},
            status=400
        )

    fs = FileSystemStorage(
        location="media/cpi_photos"
    )

    filename = fs.save(photo.name, photo)

    file_path = f"/media/cpi_photos/{filename}"

    replacement = CpiReplacement.objects.filter(
        replacement_id=replacement_id
    ).first()

    visit = CpiVisit.objects.filter(
        visit_id=visit_id
    ).first()

    collection_item = CpiCollectionItem.objects.filter(
        collection_item_id=collection_item_id
    ).first()

    existing_photo_query = CpiPhoto.objects.filter(
        visit=visit,
        collection_item=collection_item,
        photo_type=photo_type,
        is_deleted=False,
    )

    if photo_type == "REPLACEMENT_ITEM":
        existing_photo_query = existing_photo_query.filter(
            replacement=replacement
        )
    else:
        existing_photo_query = existing_photo_query.filter(
            replacement__isnull=True
        )

    existing_photo = existing_photo_query.first()

    if existing_photo:

        old_file_path = fs.path(existing_photo.file_name)

        if os.path.exists(old_file_path):
            os.remove(old_file_path)

        existing_photo.file_name = filename
        existing_photo.file_path = file_path
        existing_photo.replacement = replacement
        existing_photo.status = "PENDING"
        existing_photo.sync_status = "SYNCED"
        existing_photo.is_deleted = False
        existing_photo.server_received_at = timezone.now()

        existing_photo.save(
            update_fields=[
                "file_name",
                "file_path",
                "replacement",
                "status",
                "sync_status",
                "is_deleted",
                "server_received_at",
            ]
        )
        cpi_photo = existing_photo

    else:

        cpi_photo = CpiPhoto.objects.create(
            replacement=replacement,
            visit=visit,
            collection_item=collection_item,
            file_name=filename,
            file_path=file_path,
            photo_type=photo_type,
            status="PENDING",
            sync_status="SYNCED",
            is_deleted=False,
            created_at=timezone.now(),
            server_received_at=timezone.now(),
        )

    return Response({
        "message": "Photo uploaded successfully",
        "photo_id": cpi_photo.photo_id,
        "file_path": file_path
    })

class ApprovePhotoAPIView(APIView):

    def post(self, request):

        photo_id = request.data.get("photo_id")

        if not photo_id:
            return Response(
                {"error": "photo_id is required"},
                status=400
            )

        photo = CpiPhoto.objects.filter(
            photo_id=photo_id,
            is_deleted=False,
            photo_type="ITEM",
            status="PENDING"
        ).first()

        if not photo:
            return Response(
                {"error": "Photo not found"},
                status=404
            )

        CpiPhoto.objects.filter(
            collection_item=photo.collection_item,
            photo_type="REFERENCE_ITEM",
            is_deleted=False,
        ).update(
            is_deleted=True,
            status="REPLACED",
        )

        photo.photo_type = "REFERENCE_ITEM"
        photo.status = "APPROVED"
        photo.rejection_reason = ""
        photo.reviewed_at = timezone.now()
        

        photo.save(
            update_fields=[
                "photo_type",
                "status",
                "rejection_reason",
   

            ]
        )

        return Response({
            "message": "Photo approved successfully",
            "photo_id": photo.photo_id,
            "status": photo.status,
        })
    

class RejectPhotoAPIView(APIView):

    def post(self, request):

        photo_id = request.data.get("photo_id")
        rejection_reason = request.data.get("rejection_reason", "").strip()

        if not photo_id:
            return Response(
                {"error": "photo_id is required"},
                status=400
            )

        if not rejection_reason:
            return Response(
                {"error": "Rejection reason is required"},
                status=400
            )

        photo = CpiPhoto.objects.filter(
            photo_id=photo_id,
            is_deleted=False,
            photo_type="ITEM",
            status="PENDING"
        ).first()

        if not photo:
            return Response(
                {"error": "Photo not found"},
                status=404
            )

        photo.status = "REJECTED"
        photo.rejection_reason = rejection_reason
        photo.reviewed_at = timezone.now()


        photo.save(
            update_fields=[
                "status",
                "rejection_reason",
                "reviewed_at",

            ]
        )


        return Response({
            "message": "Photo rejected successfully",
            "photo_id": photo.photo_id,
            "status": photo.status,
            "rejection_reason": photo.rejection_reason,
        })

@require_POST
def supervisor_approve_photo(request, photo_id):

    photo = get_object_or_404(
        CpiPhoto,
        photo_id=photo_id,
        photo_type="ITEM",
        status="PENDING",
        is_deleted=False,
    )

    CpiPhoto.objects.filter(
        collection_item=photo.collection_item,
        photo_type="REFERENCE_ITEM",
        status="APPROVED",
        is_deleted=False,
    ).update(
        status="REPLACED",
        is_deleted=True,
    )

    photo.photo_type = "REFERENCE_ITEM"
    photo.status = "APPROVED"
    photo.save(
        update_fields=[
            "photo_type",
            "status",
        ]
    )

    messages.success(request, "Item photo approved successfully.")

    return redirect(
        "supervisor-review-outlet",
        visit_id=photo.visit_id,
    )


@api_view(["GET"])
def pending_item_photos(request):

    photos = (
        CpiPhoto.objects
        .filter(
            photo_type="ITEM",
            status="PENDING",
            is_deleted=False,
            replacement__isnull=True,
        )
        .select_related(
            "collection_item",
            "collection_item__outlet",
            "visit",
        )
        .order_by("-created_at")
    )

    data = []

    for photo in photos:

        collection_item = photo.collection_item

        if not collection_item:
            continue

        data.append({
            "photo_id": photo.photo_id,
            "collection_item_id": collection_item.collection_item_id,
            "product_code": collection_item.product_code,
            "product_name": collection_item.product_name,
            "brand": collection_item.brand,
            "product_specification": collection_item.product_specification,
            "outlet_name": str(collection_item.outlet),
            "photo_url": request.build_absolute_uri(photo.file_path),
            "uploaded_at": photo.created_at,
            "status": photo.status,
        })

    return Response(data)


def supervisor_login(request):
    if request.user.is_authenticated:
        return redirect("supervisor-dashboard")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(
            request,
            username=username,
            password=password,
        )

        if user is None:
            messages.error(request, "Invalid username or password.")

        elif not user.is_active:
            messages.error(request, "This user account is inactive.")

        else:
            try:
                profile = user.cpi_profile
            except AppUser.DoesNotExist:
                messages.error(
                    request,
                    "This account does not have a CPI user profile.",
                )
            else:
                if not profile.is_active:
                    messages.error(
                        request,
                        "This CPI user account is inactive.",
                    )
                elif profile.role not in [
                    AppUser.ROLE_ADMIN,
                    AppUser.ROLE_SUPERVISOR,
                    AppUser.ROLE_VIEWER,
                ]:
                    messages.error(
                        request,
                        "You do not have permission to access the dashboard.",
                    )
                else:
                    login(request, user)
                    return redirect("supervisor-dashboard")

    return render(
        request,
        "supervisor/login.html",
    )


def supervisor_logout(request):
    logout(request)
    return redirect("supervisor-login")


def supervisor_dashboard(request):
    active_round = CpiRound.objects.filter(round_status="OPEN").first()

    collector_count = AppUser.objects.filter(
        role=AppUser.ROLE_COLLECTOR,
        is_active=True
    ).count()

    outlet_count = DimOutlet.objects.filter(is_active=True).count()
    basket_item_count = (
        CpiBasket.objects
        .filter(
            is_basket_item=True,
            is_active=True,
        )
        .count()
    )

    collection_item_count = (
        CpiCollectionItem.objects
        .filter(is_active=True)
        .count()
    )


    item_count = (
        CollectorItemAssignment.objects
        .filter(
            is_active=True,
            collection_item__is_active=True,
        )
        .values("collection_item_id")
        .distinct()
        .count()
    )

    collected_count = 0

    if active_round:
        collected_count = (
            FactPrice.objects
            .filter(
                visit__round=active_round,
                quote_status="SUBMITTED",
                is_deleted=False,
            )
            .values("collection_item")
            .distinct()
            .count()
        )

    pending_replacements = CpiReplacement.objects.filter(
        replacement_status="PENDING",
        is_deleted=False
    ).count()

    outlier_count = FactPrice.objects.filter(
        is_outlier=True,
        is_deleted=False
    ).count()

    items_by_outlet_type = (
        CpiCollectionItem.objects
        .filter(is_active=True)
        .values("outlet__outlet_type__outlet_type_name")
        .annotate(item_count=Count("collection_item_id"))
        .order_by("-item_count")
    )

    overall_progress_percent = 0

    assigned_outlets = (
        CollectorWorkloadSummary.objects
        .filter(is_active=True)
        .values("island_name", "outlet_name")
        .distinct()
        .count()
    )



    unassigned_outlets = outlet_count - assigned_outlets

    large_outlets = (
        DimOutlet.objects
        .filter(is_active=True)
        .annotate(
            item_count=Count(
                "cpicollectionitem",
                filter=Q(cpicollectionitem__is_active=True),
                distinct=True,
            )
        )
        .filter(item_count__gt=60)
        .count()
    )

    small_outlets = (
        DimOutlet.objects
        .filter(is_active=True)
        .annotate(
            item_count=Count(
                "cpicollectionitem",
                filter=Q(cpicollectionitem__is_active=True),
                distinct=True,
            )
        )
        .filter(item_count__lte=60)
        .count()
    )

    island_status_map = {}

    assignments = (
        CollectorWorkloadSummary.objects
        .filter(is_active=True)
        .order_by("island_name", "outlet_name")
    )

    for assignment in assignments:
        island_name = assignment.island_name or "Unknown"
        outlet_name = assignment.outlet_name

        if island_name not in island_status_map:
            island_status_map[island_name] = {
                "island_name": island_name,
                "outlets": {},
            }

        if outlet_name not in island_status_map[island_name]["outlets"]:
            island_status_map[island_name]["outlets"][outlet_name] = {
                "assigned_count": 1,
                "completed_parts": 0,
                "total_parts": 0,
                "started_parts": 0,
            }

        outlet_row = island_status_map[island_name]["outlets"][outlet_name]
        outlet_row["total_parts"] += 1

        outlet = DimOutlet.objects.filter(
            outlet_name=assignment.outlet_name,
            island__island_name=assignment.island_name
        ).first()

        collector = AppUser.objects.filter(
            full_name=assignment.collector_name
        ).first()

        if not collector:
            collector = AppUser.objects.filter(
                django_user__username=assignment.collector_name
            ).first()

        if outlet and collector and active_round:
            visit = (
                CpiVisit.objects
                .filter(
                    round=active_round,
                    outlet=outlet,
                    collector_user=collector,
                    is_deleted=False
                )
                .order_by("-visit_id")
                .first()
            )

            if visit:
                outlet_row["started_parts"] += 1

                assigned_item_ids = list(
                    CollectorItemAssignment.objects
                    .filter(
                        collector=collector,
                        collection_item__outlet=outlet,
                        is_active=True
                    )
                    .values_list("collection_item_id", flat=True)
                )

                if assigned_item_ids:
                    total_items_for_assignment = len(assigned_item_ids)
                    collected_items_for_assignment = (
                        FactPrice.objects
                        .filter(
                            visit=visit,
                            collection_item_id__in=assigned_item_ids,
                            is_deleted=False
                        )
                        .values("collection_item")
                        .distinct()
                        .count()
                    )
                else:
                    total_items_for_assignment = CpiCollectionItem.objects.filter(
                        outlet=outlet,
                        is_active=True
                    ).count()

                    collected_items_for_assignment = (
                        FactPrice.objects
                        .filter(
                            visit=visit,
                            is_deleted=False
                        )
                        .values("collection_item")
                        .distinct()
                        .count()
                    )

                if (
                    total_items_for_assignment > 0 and
                    collected_items_for_assignment >= total_items_for_assignment
                ):
                    outlet_row["completed_parts"] += 1

    island_status = []

    for island_name, island_data in island_status_map.items():
        assigned_outlets_count = len(island_data["outlets"])
        completed_outlets_count = 0
        in_progress_outlets_count = 0
        not_started_outlets_count = 0

        for outlet_name, outlet_data in island_data["outlets"].items():
            total_parts = outlet_data["total_parts"]
            started_parts = outlet_data["started_parts"]
            completed_parts = outlet_data["completed_parts"]

            if completed_parts == total_parts and total_parts > 0:
                completed_outlets_count += 1
            elif started_parts > 0:
                in_progress_outlets_count += 1
            else:
                not_started_outlets_count += 1

        progress = 0
        if assigned_outlets_count > 0:
            progress = round((completed_outlets_count / assigned_outlets_count) * 100, 1)

        island_status.append({
            "island_name": island_name,
            "assigned_outlets": assigned_outlets_count,
            "completed_outlets": completed_outlets_count,
            "in_progress_outlets": in_progress_outlets_count,
            "not_started_outlets": not_started_outlets_count,
            "progress_percent": progress,
        })

    island_status = sorted(island_status, key=lambda x: x["island_name"])   

    dashboard_outlets = []

    assignments = (
        CollectorWorkloadSummary.objects
        .filter(is_active=True)
        .order_by(
            "island_name",
            "outlet_name",
            "item_split",
            "collector_name"
        )
    )

    for assignment in assignments:

        outlet = DimOutlet.objects.filter(
            outlet_name=assignment.outlet_name,
            island__island_name=assignment.island_name
        ).first()

        collector = AppUser.objects.filter(
            full_name=assignment.collector_name
        ).first()

        if not collector:
            collector = AppUser.objects.filter(
                django_user__username=assignment.collector_name
            ).first()

        if not outlet or not collector:
            continue

        visit = None

        if active_round:
            visit = (
                CpiVisit.objects
                .filter(
                    round=active_round,
                    outlet=outlet,
                    collector_user=collector,
                    is_deleted=False
                )
                .order_by("-visit_id")
                .first()
            )

        assigned_item_ids = list(
            CollectorItemAssignment.objects
            .filter(
                collector=collector,
                collection_item__outlet=outlet,
                is_active=True
            )
            .values_list("collection_item_id", flat=True)
        )

        if assigned_item_ids:
            total_items = len(assigned_item_ids)

            collected_items = (
                FactPrice.objects
                .filter(
                    visit=visit,
                    collection_item_id__in=assigned_item_ids,
                    is_deleted=False
                )
                .values("collection_item")
                .distinct()
                .count()
            ) if visit else 0

        else:
            total_items = CpiCollectionItem.objects.filter(
                outlet=outlet,
                is_active=True
            ).count()

            collected_items = (
                FactPrice.objects
                .filter(
                    visit=visit,
                    is_deleted=False
                )
                .values("collection_item")
                .distinct()
                .count()
            ) if visit else 0

        if collected_items == 0:
            status = "Not Started"
        elif collected_items >= total_items:
            status = "Completed"
        else:
            status = "In Progress"

        progress_percent = 0
        if total_items > 0:
            progress_percent = round((collected_items / total_items) * 100, 1)

        review_status = "Not Submitted"

        if visit:
            if visit.review_status == "APPROVED":
                review_status = "Approved"
            elif visit.review_status == "CORRECTION_REQUIRED":
                review_status = "Correction Required"
            elif visit.review_status == "CORRECTED_PENDING_REVIEW":
                review_status = "Corrected - Pending Review"
            elif collected_items >= total_items:
                review_status = "Pending Review"

        dashboard_outlets.append({
            "island_name": assignment.island_name,
            "outlet_name": assignment.outlet_name,
            "collector_name": assignment.collector_name,
            "item_split": assignment.item_split or "All items",
            "total_items": total_items,
            "collected_items": collected_items,
            "status": status,
            "progress_percent": progress_percent,
            "review_status": review_status,
            "visit_id": visit.visit_id if visit else None,
        })

    dashboard_total_items = sum(
        row["total_items"]
        for row in dashboard_outlets
    )

    dashboard_collected_items = sum(
        row["collected_items"]
        for row in dashboard_outlets
    )

    if dashboard_total_items > 0:
        overall_progress_percent = round(
            (
                dashboard_collected_items
                / dashboard_total_items
            ) * 100,
            1,
        )

    pending_reviews = 0

    for row in dashboard_outlets:
        if row["review_status"] in [
            "Pending Review",
            "Corrected - Pending Review"
        ]:
            pending_reviews += 1




    return render(request, "supervisor/dashboard.html", {
        "active_round": active_round,
        "collector_count": collector_count,
        "outlet_count": outlet_count,
        "item_count": item_count,
        "basket_item_count": basket_item_count,
        "collection_item_count": collection_item_count,
        "collected_count": collected_count,
        "pending_replacements": pending_replacements,
        "outlier_count": outlier_count,
        "progress_percent": overall_progress_percent,
        "items_by_outlet_type": items_by_outlet_type,

        "assigned_outlets": assigned_outlets,
        "unassigned_outlets": unassigned_outlets,
        "large_outlets": large_outlets,
        "small_outlets": small_outlets,
        "island_status": island_status,
        "dashboard_outlets": dashboard_outlets,
        "pending_reviews": pending_reviews,
    })

@supervisor_required
@require_GET
def supervisor_rounds(request):
    rounds = CpiRound.objects.all().order_by("-survey_year", "-survey_month")

    return render(request, "supervisor/rounds.html", {
        "rounds": rounds,
    })

@supervisor_required
@require_POST
def supervisor_round_create(request):
    today = timezone.now().date()

    year = today.year
    month = today.month

    start_date = today.replace(day=1)
    end_date = today.replace(day=monthrange(year, month)[1])

    if CpiRound.objects.filter(
        survey_year=year,
        survey_month=month
    ).exists():
        messages.warning(request, "Current month CPI round already exists.")
        return redirect("supervisor-rounds")

    CpiRound.objects.create(
        survey_year=year,
        survey_month=month,
        round_status="DRAFT",
        collection_start_date=start_date,
        collection_end_date=end_date,
        created_at=timezone.now(),
    )

    messages.success(request, "Current month CPI round created successfully.")
    return redirect("supervisor-rounds")

@supervisor_required
@require_POST
def supervisor_round_open(request, round_id):
    round_obj = get_object_or_404(CpiRound, round_id=round_id)

    if round_obj.round_status != "PREPARED":
        messages.error(request, "Only PREPARED rounds can be opened.")
        return redirect("supervisor-rounds")

    if CpiRound.objects.filter(round_status="OPEN").exclude(round_id=round_id).exists():
        messages.error(request, "Another CPI round is already OPEN. Close it first.")
        return redirect("supervisor-rounds")

    round_obj.round_status = "OPEN"
    round_obj.save(update_fields=["round_status"])

    messages.success(request, "CPI round opened.")
    return redirect("supervisor-rounds")



@supervisor_required
@require_POST
def supervisor_round_close(request, round_id):
    round_obj = get_object_or_404(CpiRound, round_id=round_id)

    if round_obj.round_status == "LOCKED":
        messages.error(request, "Locked rounds cannot be closed.")
        return redirect("supervisor-rounds")

    round_obj.round_status = "CLOSED"
    round_obj.save(update_fields=["round_status"])

    messages.success(request, "CPI round closed.")
    return redirect("supervisor-rounds")

@supervisor_required
@require_POST
def supervisor_round_reopen(request, round_id):
    round_obj = get_object_or_404(CpiRound, round_id=round_id)

    if round_obj.round_status != "CLOSED":
        messages.error(request, "Only CLOSED rounds can be reopened.")
        return redirect("supervisor-rounds")

    if CpiRound.objects.filter(round_status="OPEN").exclude(round_id=round_id).exists():
        messages.error(request, "Another CPI round is already OPEN. Close it first.")
        return redirect("supervisor-rounds")

    round_obj.round_status = "OPEN"
    round_obj.save(update_fields=["round_status"])

    messages.success(request, "CPI round reopened.")
    return redirect("supervisor-rounds")


@supervisor_required
@require_POST
def supervisor_round_lock(request, round_id):
    round_obj = get_object_or_404(CpiRound, round_id=round_id)

    if round_obj.round_status == "OPEN":
        messages.error(request, "Open rounds must be closed before locking.")
        return redirect("supervisor-rounds")

    round_obj.round_status = "LOCKED"
    round_obj.save(update_fields=["round_status"])

    messages.success(request, "CPI round locked.")
    return redirect("supervisor-rounds")

@supervisor_required
@require_POST
def supervisor_round_unlock(request, round_id):
    round_obj = get_object_or_404(CpiRound, round_id=round_id)

    if round_obj.round_status != "LOCKED":
        messages.error(request, "Only locked rounds can be unlocked.")
        return redirect("supervisor-rounds")

    round_obj.round_status = "CLOSED"
    round_obj.save(update_fields=["round_status"])

    messages.success(request, "CPI round unlocked.")
    return redirect("supervisor-rounds")

@supervisor_required
@require_GET
def supervisor_outlets(request):
    search = request.GET.get("search", "")
    island_id = request.GET.get("island", "")
    outlet_type_id = request.GET.get("outlet_type", "")

    outlets = (
        DimOutlet.objects
        .filter(is_active=True)
        .select_related("island", "outlet_type")
        .annotate(
            item_count=Count(
                "cpicollectionitem",
                filter=Q(cpicollectionitem__is_active=True),
                distinct=True,
            )
        )
    )
    if search:
        outlets = outlets.filter(
            Q(outlet_name__icontains=search) |
            Q(outlet_code__icontains=search) |
            Q(island__island_name__icontains=search)
        )

    if island_id:
        outlets = outlets.filter(island_id=island_id)

    if outlet_type_id:
        outlets = outlets.filter(outlet_type_id=outlet_type_id)

    outlets = outlets.order_by("-created_at")

    islands = (DimIsland.objects.filter(dimoutlet__is_active=True).distinct().order_by("island_name"))
    outlet_types = DimOutletType.objects.all().order_by("sort_order")

    return render(request, "supervisor/outlets.html", {
        "outlets": outlets,
        "islands": islands,
        "outlet_types": outlet_types,
        "search": search,
        "selected_island": island_id,
        "selected_outlet_type": outlet_type_id,
    })

@supervisor_required
@require_POST
def supervisor_outlet_delete(request, outlet_id):
    outlet = get_object_or_404(DimOutlet, outlet_id=outlet_id)

    if request.method == "POST":
        has_items = CpiCollectionItem.objects.filter(outlet=outlet).exists()
        has_visits = CpiVisit.objects.filter(outlet=outlet).exists()
        has_assignments = CollectorAssignment.objects.filter(outlet=outlet).exists()

        if has_items or has_visits or has_assignments:
            outlet.is_active = False
            outlet.save(update_fields=["is_active"])
            messages.warning(request, "Outlet has linked records, so it was deactivated instead of deleted.")
        else:
            outlet.delete()
            messages.success(request, "Outlet deleted successfully.")

        return redirect("supervisor-outlets")

    return redirect("supervisor-outlets")

@supervisor_required
@require_POST
def supervisor_outlet_detail(request, outlet_id):
    outlet = get_object_or_404(
        DimOutlet.objects.select_related("island", "outlet_type"),
        outlet_id=outlet_id
    )

    items = (
        CpiCollectionItem.objects
        .filter(outlet=outlet)
        .order_by("sort_order", "product_name")
    )

    return render(request, "supervisor/outlet_detail.html", {
        "outlet": outlet,
        "items": items,
    })

@supervisor_required
@require_POST
def supervisor_outlet_add_item(request, outlet_id):
    outlet = get_object_or_404(
        DimOutlet.objects.select_related(
            "island",
            "outlet_type",
        ),
        outlet_id=outlet_id,
    )

    basket_items = (
        CpiBasket.objects
        .filter(
            is_basket_item=True,
            is_active=True,
        )
        .order_by(
            "display_order",
            "basket_item_name",
        )
    )

    if request.method == "POST":
        basket_id = request.POST.get("basket_item")
        product_name = request.POST.get(
            "product_name",
            "",
        ).strip()
        brand = request.POST.get(
            "brand",
            "",
        ).strip()
        product_specification = request.POST.get(
            "product_specification",
            "",
        ).strip()

        basket_item = get_object_or_404(
            CpiBasket,
            basket_id=basket_id,
            is_basket_item=True,
            is_active=True,
        )

        if not product_name:
            messages.error(
                request,
                "Product name is required.",
            )

            return render(
                request,
                "supervisor/outlet_add_item.html",
                {
                    "outlet": outlet,
                    "basket_items": basket_items,
                },
            )

        if not product_specification:
            messages.error(
                request,
                "Product specification is required.",
            )

            return render(
                request,
                "supervisor/outlet_add_item.html",
                {
                    "outlet": outlet,
                    "basket_items": basket_items,
                },
            )

        last_sort_order = (
            CpiCollectionItem.objects
            .filter(outlet=outlet)
            .order_by("-sort_order")
            .values_list(
                "sort_order",
                flat=True,
            )
            .first()
        )

        if last_sort_order is None:
            next_sort_order = 1
        else:
            next_sort_order = last_sort_order + 1

        new_collection_item = CpiCollectionItem.objects.create(
            outlet=outlet,
            basket_item=basket_item,
            matched_basket_name=basket_item.basket_item_name,
            product_name=product_name,
            brand=brand or None,
            product_specification=product_specification,
            sort_order=next_sort_order,
            is_active=True,
            valid_from=timezone.now().date(),
            item_status="ACTIVE",
        )

        messages.success(
            request,
            (
                f"Collection item "
                f"'{new_collection_item.product_name}' "
                f"added to {outlet.outlet_name}."
            ),
        )

        return redirect(
            "supervisor-outlet-detail",
            outlet_id=outlet.outlet_id,
        )

    return render(
        request,
        "supervisor/outlet_add_item.html",
        {
            "outlet": outlet,
            "basket_items": basket_items,
        },
    )
@supervisor_required
@require_POST
def supervisor_outlet_create(request):
    islands = DimIsland.objects.all().order_by("island_name")
    outlet_types = DimOutletType.objects.all().order_by("sort_order")

    if request.method == "POST":
        outlet_name = request.POST.get("outlet_name")
        island_id = request.POST.get("island")
        outlet_type_id = request.POST.get("outlet_type")
        address_text = request.POST.get("address_text")
        contact_person = request.POST.get("contact_person")
        contact_no = request.POST.get("contact_no")

        island = DimIsland.objects.get(island_id=island_id)

        last_outlet = (
            DimOutlet.objects
            .exclude(outlet_code__isnull=True)
            .exclude(outlet_code="")
            .order_by("-outlet_code")
            .first()
        )

        if last_outlet:
            next_seq = int(last_outlet.outlet_code) + 1
        else:
            next_seq = 1

        outlet_code = str(next_seq).zfill(3)

        DimOutlet.objects.create(
            outlet_code=outlet_code,
            outlet_name=outlet_name,
            island_id=island_id,
            outlet_type_id=outlet_type_id,
            address_text=address_text,
            contact_person=contact_person,
            contact_no=contact_no,
            allowed_radius_meters=100,
            is_active=True,
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )

        messages.success(
            request,
            f"Outlet added successfully. Outlet code: {outlet_code}"
        )
        return redirect("supervisor-outlets")

    return render(request, "supervisor/outlet_form.html", {
        "islands": islands,
        "outlet_types": outlet_types,
        "mode": "create",
    })

@supervisor_required
@require_GET
def supervisor_products(request):
    search = request.GET.get("search", "").strip()
    group_code = request.GET.get("group", "").strip()
    status = request.GET.get("status", "").strip()

    products = (
        CpiBasket.objects
        .filter(is_basket_item=True)
        .select_related(
            "methodology",
            "parent_basket",
        )
        .annotate(
            collection_item_count=Count(
                "collection_items",
                filter=Q(collection_items__is_active=True),
                distinct=True,
            )
        )
    )

    if search:
        products = products.filter(
            Q(basket_code__icontains=search)
            | Q(basket_item_code__icontains=search)
            | Q(basket_item_name__icontains=search)
            | Q(description__icontains=search)
            | Q(coicop_2016__icontains=search)
            | Q(coicop_division_name__icontains=search)
            | Q(coicop_group_name__icontains=search)
            | Q(coicop_class_name__icontains=search)
            | Q(coicop_subclass_name__icontains=search)
        )

    if group_code:
        products = products.filter(
            coicop_division_code=group_code
        )

    if status == "active":
        products = products.filter(is_active=True)

    elif status == "inactive":
        products = products.filter(is_active=False)

    products = products.order_by(
        "display_order",
        "basket_item_name",
        "basket_code",
    )

    division_rows = (
        CpiBasket.objects
        .filter(is_basket_item=True)
        .exclude(coicop_division_code__isnull=True)
        .exclude(coicop_division_code="")
        .values(
            "coicop_division_code",
            "coicop_division_name",
        )
        .distinct()
        .order_by("coicop_division_code")
    )

    # Keep group_code and group_name keys so the current template
    # can be adjusted with minimal changes.
    groups = [
        {
            "group_code": row["coicop_division_code"],
            "group_name": (
                row["coicop_division_name"]
                or row["coicop_division_code"]
            ),
        }
        for row in division_rows
    ]

    return render(
        request,
        "supervisor/products.html",
        {
            "products": products,
            "groups": groups,
            "search": search,
            "selected_group": group_code,
            "selected_status": status,
        },
    )

@supervisor_required
@require_POST
def supervisor_product_detail(request, item_id):

    product = get_object_or_404(
        CpiBasket.objects.select_related(
            "methodology",
            "parent_basket",
        ),
        basket_id=item_id,
        is_basket_item=True,
    )

    collection_items = (
        CpiCollectionItem.objects
        .filter(basket_item_id=item_id)
        .select_related(
            "outlet",
            "outlet__island",
            "brand_fk",
            "country",
        )
        .order_by(
            "outlet__outlet_name",
            "specification_no",
        )
    )

    return render(
        request,
        "supervisor/product_detail.html",
        {
            "product": product,
            "collection_items": collection_items,
        },
    )

@supervisor_required
@require_POST
def supervisor_product_edit(request, item_id):
    product = get_object_or_404(
        CpiBasket,
        basket_id=item_id,
        is_basket_item=True,
    )

    if request.method == "POST":
        product.basket_item_name = (
            request.POST.get("basket_item_name", "").strip()
            or None
        )

        product.description = (
            request.POST.get("description", "").strip()
        )

        product.basket_item_code = (
            request.POST.get("basket_item_code", "").strip()
            or None
        )

        product.coicop_2016 = (
            request.POST.get("coicop_2016", "").strip()
            or None
        )

        division_code = (
            request.POST.get(
                "coicop_division_code",
                "",
            ).strip()
            or None
        )

        division = None

        if division_code:
            division = (
                CpiBasket.objects
                .filter(
                    is_basket_item=True,
                    coicop_division_code=division_code,
                )
                .exclude(coicop_division_name__isnull=True)
                .exclude(coicop_division_name="")
                .first()
            )

        product.coicop_division_code = division_code

        product.coicop_division_name = (
            division.coicop_division_name
            if division
            else None
        )

        group_code = (
            request.POST.get(
                "coicop_group_code",
                "",
            ).strip()
            or None
        )

        group = None

        if group_code:
            group = (
                CpiBasket.objects
                .filter(
                    is_basket_item=True,
                    coicop_division_code=division_code,
                    coicop_group_code=group_code,
                )
                .exclude(coicop_group_name__isnull=True)
                .exclude(coicop_group_name="")
                .first()
            )

        if group_code and not group:
            messages.error(
                request,
                "The selected Group does not belong to the selected Division.",
            )
            return redirect(
                "supervisor-product-edit",
                item_id=product.basket_id,
            )

        product.coicop_group_code = group_code

        product.coicop_group_name = (
            group.coicop_group_name
            if group
            else None
        )

        class_code = (
            request.POST.get(
                "coicop_class_code",
                "",
            ).strip()
            or None
        )

        class_item = None

        if class_code:
            class_item = (
                CpiBasket.objects
                .filter(
                    is_basket_item=True,
                    coicop_division_code=division_code,
                    coicop_group_code=group_code,
                    coicop_class_code=class_code,
                )
                .exclude(coicop_class_name__isnull=True)
                .exclude(coicop_class_name="")
                .first()
            )

        if class_code and not class_item:
            messages.error(
                request,
                "The selected Class does not belong to the selected Group.",
            )
            return redirect(
                "supervisor-product-edit",
                item_id=product.basket_id,
            )

        product.coicop_class_code = class_code

        product.coicop_class_name = (
            class_item.coicop_class_name
            if class_item
            else None
        )

        subclass_code = (
            request.POST.get(
                "coicop_subclass_code",
                "",
            ).strip()
            or None
        )

        subclass = None

        if subclass_code:
            subclass = (
                CpiBasket.objects
                .filter(
                    is_basket_item=True,
                    coicop_division_code=division_code,
                    coicop_group_code=group_code,
                    coicop_class_code=class_code,
                    coicop_subclass_code=subclass_code,
                )
                .exclude(coicop_subclass_name__isnull=True)
                .exclude(coicop_subclass_name="")
                .first()
            )
        if subclass_code and not subclass:
            messages.error(
                request,
                "The selected Subclass does not belong to the selected Class.",
            )
            return redirect(
                "supervisor-product-edit",
                item_id=product.basket_id,
            )

        product.coicop_subclass_code = subclass_code

        product.coicop_subclass_name = (
            subclass.coicop_subclass_name
            if subclass
            else None
        )

        display_order = request.POST.get(
            "display_order",
            "",
        ).strip()

        product.display_order = (
            int(display_order)
            if display_order
            else None
        )

        product.is_active = (
            request.POST.get("is_active") == "on"
        )

        product.save()

        messages.success(
            request,
            "Basket item updated successfully.",
        )

        return redirect("supervisor-products")
    
    divisions = (
        CpiBasket.objects
        .filter(is_basket_item=True)
        .exclude(coicop_division_code__isnull=True)
        .exclude(coicop_division_code="")
        .values(
            "coicop_division_code",
            "coicop_division_name",
        )
        .distinct()
        .order_by("coicop_division_code")
    )

    groups = (
        CpiBasket.objects
        .filter(
            is_basket_item=True,
            coicop_division_code=product.coicop_division_code,
        )
        .exclude(coicop_group_code__isnull=True)
        .exclude(coicop_group_code="")
        .values(
            "coicop_group_code",
            "coicop_group_name",
        )
        .distinct()
        .order_by("coicop_group_code")
    )

    classes = (
        CpiBasket.objects
        .filter(
            is_basket_item=True,
            coicop_group_code=product.coicop_group_code,
        )
        .exclude(coicop_class_code__isnull=True)
        .exclude(coicop_class_code="")
        .values(
            "coicop_class_code",
            "coicop_class_name",
        )
        .distinct()
        .order_by("coicop_class_code")
    )

    subclasses = (
        CpiBasket.objects
        .filter(
            is_basket_item=True,
            coicop_class_code=product.coicop_class_code,
        )
        .exclude(coicop_subclass_code__isnull=True)
        .exclude(coicop_subclass_code="")
        .values(
            "coicop_subclass_code",
            "coicop_subclass_name",
        )
        .distinct()
        .order_by("coicop_subclass_code")
    )

    hierarchy_rows = list(
        CpiBasket.objects
        .filter(is_basket_item=True)
        .exclude(coicop_division_code__isnull=True)
        .exclude(coicop_group_code__isnull=True)
        .exclude(coicop_class_code__isnull=True)
        .exclude(coicop_subclass_code__isnull=True)
        .values(
            "coicop_division_code",
            "coicop_division_name",
            "coicop_group_code",
            "coicop_group_name",
            "coicop_class_code",
            "coicop_class_name",
            "coicop_subclass_code",
            "coicop_subclass_name",
        )
        .distinct()
        .order_by(
            "coicop_division_code",
            "coicop_group_code",
            "coicop_class_code",
            "coicop_subclass_code",
        )
    )

    return render(
        request,
        "supervisor/product_edit.html",
        {
            "product": product,
            "divisions": divisions,
            "groups": groups,
            "classes": classes,
            "subclasses": subclasses,
            "hierarchy_rows": hierarchy_rows,
        },
    )
@supervisor_required
@require_POST
def supervisor_product_delete(request, item_id):
    product = get_object_or_404(
        CpiBasket,
        basket_id=item_id,
        is_basket_item=True,
    )

    if request.method == "POST":
        usage_count = CpiCollectionItem.objects.filter(
            basket_item_id=item_id
        ).count()

        if usage_count > 0:
            messages.error(
                request,
                (
                    "This basket item cannot be deleted because it is "
                    f"linked to {usage_count} collection item(s). "
                    "Deactivate it instead."
                ),
            )

            return redirect("supervisor-products")

        product.delete()

        messages.success(
            request,
            "Basket item deleted successfully.",
        )

    return redirect("supervisor-products")



def build_target_item_name(item):
    name = item.product_name or ""

    spec = item.product_specification or ""

    item_type = ""
    size = ""

    if "Type:" in spec:
        item_type = spec.split("Type:", 1)[1].split("Size", 1)[0].strip()

    if "Size of unit:" in spec:
        size = spec.split("Size of unit:", 1)[1].split("Other specification", 1)[0].strip()
    elif "Size of units:" in spec:
        size = spec.split("Size of units:", 1)[1].split("Unit of Measure", 1)[0].strip()

    parts = [name]

    if item_type:
        parts.append(item_type)

    if size:
        parts.append(size)

    return " - ".join(parts)



class OutletEditForm(forms.ModelForm):
    class Meta:
        model = DimOutlet
        fields = [
            "outlet_name",
            "island",
            "outlet_type",
            "address_text",
            "contact_person",
            "contact_no",
            "allowed_radius_meters",
            "is_active",
        ]

        widgets = {
            "outlet_name": forms.TextInput(attrs={"class": "form-control"}),
            "island": forms.Select(attrs={"class": "form-select"}),
            "outlet_type": forms.Select(attrs={"class": "form-select"}),
            "address_text": forms.TextInput(attrs={"class": "form-control"}),
            "contact_person": forms.TextInput(attrs={"class": "form-control"}),
            "contact_no": forms.TextInput(attrs={"class": "form-control"}),
            "allowed_radius_meters": forms.NumberInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

def supervisor_outlet_edit(request, outlet_id):
    outlet = get_object_or_404(DimOutlet, outlet_id=outlet_id)

    if request.method == "POST":
        form = OutletEditForm(request.POST, instance=outlet)

        if form.is_valid():
            form.save()
            messages.success(request, "Outlet updated successfully.")
            return redirect("supervisor-outlet-detail", outlet_id=outlet.outlet_id)
    else:
        form = OutletEditForm(instance=outlet)

    return render(request, "supervisor/outlet_edit.html", {
        "form": form,
        "outlet": outlet,
    })


def supervisor_collection_items(request):

    search_query = request.GET.get("q", "").strip()
    selected_outlet = request.GET.get("outlet", "").strip()
    selected_island = request.GET.get("island", "").strip()
    selected_outlet_type = request.GET.get(
        "outlet_type",
        "",
    ).strip()
    selected_status = request.GET.get("status", "").strip()
    selected_specification = request.GET.get(
        "specification",
        "",
    ).strip()

    items = (
        CpiCollectionItem.objects
        .select_related(
            "outlet",
            "outlet__island",
            "outlet__outlet_type",
            "basket_item",
        )
        .order_by(
            "outlet__outlet_name",
            "sort_order",
            "product_name",
        )
    )

    if search_query:
        items = items.filter(
            Q(product_name__icontains=search_query)
            | Q(product_code__icontains=search_query)
            | Q(product_specification__icontains=search_query)
            | Q(basket_item__basket_item_name__icontains=search_query)
            | Q(basket_item__basket_item_code__icontains=search_query)
        )

    if selected_island:
        items = items.filter(
            outlet__island_id=selected_island
        )

    if selected_outlet_type:
        items = items.filter(
            outlet__outlet_type_id=selected_outlet_type
        )

    if selected_outlet:
        items = items.filter(
            outlet_id=selected_outlet
        )

    if selected_status == "active":
        items = items.filter(is_active=True)

    elif selected_status == "inactive":
        items = items.filter(is_active=False)

    if selected_specification == "missing":
        items = items.filter(
            Q(product_specification__isnull=True)
            | Q(product_specification__exact="")
        )

    elif selected_specification == "available":
        items = (
            items
            .exclude(product_specification__isnull=True)
            .exclude(product_specification__exact="")
        )

    islands = (
        DimIsland.objects
        .filter(
            dimoutlet__is_active=True
        )
        .distinct()
        .order_by("island_name")
    )

    outlet_types = (
        DimOutletType.objects
        .filter(
            dimoutlet__is_active=True
        )
        .distinct()
        .order_by(
            "sort_order",
            "outlet_type_name",
        )
    )

    outlets = (
        DimOutlet.objects
        .filter(is_active=True)
        .select_related(
            "island",
            "outlet_type",
        )
    )

    if selected_island:
        outlets = outlets.filter(
            island_id=selected_island
        )

    if selected_outlet_type:
        outlets = outlets.filter(
            outlet_type_id=selected_outlet_type
        )

    outlets = outlets.order_by("outlet_name")

    return render(
        request,
        "supervisor/collection_items.html",
        {
            "items": items[:500],
            "islands": islands,
            "outlet_types": outlet_types,
            "outlets": outlets,
            "search_query": search_query,
            "selected_island": selected_island,
            "selected_outlet_type": selected_outlet_type,
            "selected_outlet": selected_outlet,
            "selected_status": selected_status,
            "selected_specification": selected_specification,
        },
    )
def supervisor_collection_item_detail(request, collection_item_id):
    item = get_object_or_404(
        CpiCollectionItem.objects.select_related("outlet"),
        collection_item_id=collection_item_id
    )

    return render(request, "supervisor/collection_item_detail.html", {
        "item": item,
    })

class CollectionItemEditForm(forms.ModelForm):
    class Meta:
        model = CpiCollectionItem
        fields = [
            "product_name",
            "brand",
            "spec_type",
            "size_value",
            "unit",
            "material",
            "other_spec",
            "product_specification",
            "last_price",
            "is_active",
        ]

        widgets = {
            "product_name": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "brand": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "spec_type": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "size_value": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.001",
                }
            ),
            "unit": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "material": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "other_spec": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "product_specification": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 6,
                }
            ),
            "last_price": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                }
            ),
            "is_active": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
        }

def supervisor_collection_item_edit(request, collection_item_id):
    item = get_object_or_404(CpiCollectionItem, collection_item_id=collection_item_id)

    if request.method == "POST":
        form = CollectionItemEditForm(request.POST, instance=item)

        if form.is_valid():
            form.save()
            messages.success(request, "Collection item updated successfully.")
            return redirect(
                "supervisor-collection-item-detail",
                collection_item_id=item.collection_item_id
            )
    else:
        form = CollectionItemEditForm(instance=item)

    return render(request, "supervisor/collection_item_edit.html", {
        "form": form,
        "item": item,
    })   



def supervisor_assignments(request):
    active_round = (
        CpiRound.objects
        .filter(round_status="OPEN")
        .order_by(
            "-survey_year",
            "-survey_month",
        )
        .first()
    )

    collectors = (
        AppUser.objects
        .filter(
            role=AppUser.ROLE_COLLECTOR,
            is_active=True,
        )
        .order_by(
            "full_name",
            "django_user__username",
        )
    )

    selected_category = request.GET.get(
        "category",
        "FOOD",
    )

    if selected_category not in (
        "FOOD",
        "NONFOOD",
        "SERVICE",
    ):
        selected_category = "FOOD"

    islands = (
        DimIsland.objects
        .filter(
            dimoutlet__is_active=True,
            dimoutlet__outlet_type__broad_type=selected_category,
        )
        .distinct()
        .order_by("island_name")
    )

    selected_island_id = request.GET.get(
        "island",
        "",
    ).strip()

    selected_collector_id = request.GET.get(
        "collector",
        "",
    ).strip()

    assignments = []
    incomplete_large_outlets = []

    if not active_round:
        messages.warning(
            request,
            "No OPEN CPI round is available.",
        )

        return render(
            request,
            "supervisor/assignments.html",
            {
                "active_round": None,
                "assignments": [],
                "collectors": collectors,
                "total_collectors": 0,
                "assigned_outlets": 0,
                "shared_outlets": 0,
                "incomplete_large_outlets": [],
            },
        )

    small_assignments = (
        CollectorAssignment.objects
        .filter(
            round=active_round,
            is_active=True,
            outlet__outlet_type__broad_type=selected_category,
        )
        .select_related(
            "collector",
            "collector__django_user",
            "outlet",
            "outlet__island",
        )
        .annotate(
            total_items=Count(
                "outlet__cpicollectionitem",
                filter=Q(
                    outlet__cpicollectionitem__is_active=True
                ),
                distinct=True,
            )
        )
        .order_by(
            "outlet__island__island_name",
            "outlet__outlet_name",
        )
    )

    if selected_island_id:
        small_assignments = small_assignments.filter(
            outlet__island_id=selected_island_id
        )

    if selected_collector_id:
        small_assignments = small_assignments.filter(
            collector_id=selected_collector_id
        )

    collector_ids = set()
    assigned_outlet_ids = set()

    for assignment in small_assignments:
        collector_ids.add(
            assignment.collector_id
        )
        assigned_outlet_ids.add(
            assignment.outlet_id
        )

        collector_name = (
            assignment.collector.full_name
            or (
                assignment.collector.django_user.username
                if assignment.collector.django_user
                else assignment.collector.email
            )
        )

        assignments.append({
            "island_name": (
                assignment.outlet.island.island_name
                if assignment.outlet.island
                else "-"
            ),
            "outlet_id": assignment.outlet_id,
            "outlet_name": assignment.outlet.outlet_name,
            "total_items": assignment.total_items,
            "assignment_type": "Outlet assignment",
            "item_split": "All items",
            "collector_id": assignment.collector_id,
            "collector_name": collector_name,
            "display_range": str(
                assignment.total_items
            ),
            "is_active": assignment.is_active,
        })

    large_rows = (
        CollectorItemAssignment.objects
        .filter(
            round=active_round,
            is_active=True,
        )
        .values(
            "collection_item__outlet_id",
            "collection_item__outlet__outlet_name",
            "collection_item__outlet__island__island_name",
            "collector_id",
            "collector__full_name",
           "collector__django_user__username",
            "item_split",
        )
        .annotate(
            assigned_items=Count(
                "collection_item_id",
                distinct=True,
            )
        )
        .order_by(
            "collection_item__outlet__island__island_name",
            "collection_item__outlet__outlet_name",
            "item_split",
        )
    )

    if selected_island_id:
        large_rows = large_rows.filter(
            collection_item__outlet__island_id=selected_island_id
        )

    if selected_collector_id:
        large_rows = large_rows.filter(
            collector_id=selected_collector_id
        )



    large_outlet_ids = {
        row["collection_item__outlet_id"]
        for row in large_rows
    }

    total_items_map = {
        row["outlet_id"]: row["total_items"]
        for row in (
            CpiCollectionItem.objects
            .filter(
                outlet_id__in=large_outlet_ids,
                is_active=True,
            )
            .values("outlet_id")
            .annotate(
                total_items=Count(
                    "collection_item_id"
                )
            )
        )
    }

    assigned_splits = {}

    for row in large_rows:
        outlet_id = (
            row["collection_item__outlet_id"]
        )

        collector_ids.add(
            row["collector_id"]
        )
        assigned_outlet_ids.add(
            outlet_id
        )

        assigned_splits.setdefault(
            outlet_id,
            set(),
        ).add(row["item_split"])

        collector_name = (
            row["collector__full_name"]
            or row["collector__django_user__username"]
        )

        assignments.append({
            "island_name": (
                row[
                    "collection_item__outlet__island__island_name"
                ]
                or "-"
            ),
            "outlet_id": outlet_id,
            "outlet_name": row[
                "collection_item__outlet__outlet_name"
            ],
            "total_items": total_items_map.get(
                outlet_id,
                0,
            ),
            "assignment_type": "Item split assignment",
            "item_split": row["item_split"],
            "collector_id": row["collector_id"],
            "collector_name": collector_name,
            "display_range": (
                f'{row["assigned_items"]} items'
            ),
            "is_active": True,
        })

    outlet_names = {
        row["outlet_id"]: row["outlet_name"]
        for row in assignments
    }

    for outlet_id, splits in assigned_splits.items():
        if splits == {"First half"}:
            incomplete_large_outlets.append({
                "outlet_name": outlet_names.get(
                    outlet_id,
                    "Unknown outlet",
                ),
                "missing_split": "Second half",
            })

        elif splits == {"Second half"}:
            incomplete_large_outlets.append({
                "outlet_name": outlet_names.get(
                    outlet_id,
                    "Unknown outlet",
                ),
                "missing_split": "First half",
            })

    assignments.sort(
        key=lambda row: (
            row["island_name"],
            row["outlet_name"],
            row["item_split"],
        )
    )

    return render(
        request,
        "supervisor/assignments.html",
        {
            "active_round": active_round,
            "assignments": assignments,
            "collectors": collectors,
            "selected_category": selected_category,
            "islands": islands,
            "selected_island_id": selected_island_id,
            "selected_collector_id": selected_collector_id,
            "total_collectors": len(
                collector_ids
            ),
            "assigned_outlets": len(
                assigned_outlet_ids
            ),
            "shared_outlets": len(
                large_outlet_ids
            ),
            "incomplete_large_outlets": (
                incomplete_large_outlets
            ),
        },
    )

def supervisor_round_prepare(request, round_id):

    round_obj = get_object_or_404(
        CpiRound,
        round_id=round_id
    )

    if round_obj.round_status != "DRAFT":
        messages.error(
            request,
            "Only DRAFT rounds can be prepared."
        )
        return redirect("supervisor-rounds")

    updated_count = 0

    items = CpiCollectionItem.objects.filter(
        is_active=True
    )

    for item in items:

        last_price = (
            FactPrice.objects
            .filter(
                collection_item=item,
                quote_status="SUBMITTED",
                is_deleted=False,
                observed_price__isnull=False,
                visit__round__isnull=False,
            )
            .filter(
                Q(
                    visit__round__survey_year__lt=round_obj.survey_year
                )
                |
                Q(
                    visit__round__survey_year=round_obj.survey_year,
                    visit__round__survey_month__lt=round_obj.survey_month,
                )
            )
            .order_by(
                "-visit__round__survey_year",
                "-visit__round__survey_month",
                "-created_at",
            )
            .first()
        )

        if last_price:

            item.last_price = last_price.observed_price

            visit_round = (
                last_price.visit.round
                if last_price.visit
                else None
            )

            if visit_round:
                item.last_price_month = (
                    f"{visit_round.survey_year}-"
                    f"{visit_round.survey_month:02d}"
                )

            item.save()

            updated_count += 1

    round_obj.round_status = "PREPARED"
    round_obj.save()

    messages.success(
        request,
        f"Round prepared successfully. "
        f"{updated_count} last prices updated."
    )

    return redirect("supervisor-rounds")


def build_current_assignment_workload(active_round):
    collectors = (
        AppUser.objects.filter(
            role=AppUser.ROLE_COLLECTOR,
            is_active=True
        )
        .order_by("full_name", "django_user__username")
    )

    assignments = []
    collector_ids = set()
    assigned_outlet_ids = set()
    large_outlet_ids = set()
    incomplete_large_outlets = []

    small_assignments = (
        CollectorAssignment.objects
        .filter(
            round=active_round,
            is_active=True,
        )
        .select_related(
            "collector",
            "collector__django_user",
            "outlet",
            "outlet__island",
        )
        .annotate(
            total_items=Count(
                "outlet__cpicollectionitem",
                filter=Q(
                    outlet__cpicollectionitem__is_active=True
                ),
                distinct=True,
            )
        )
    )

    for assignment in small_assignments:
        collector_ids.add(assignment.collector_id)
        assigned_outlet_ids.add(assignment.outlet_id)

        assignments.append({
            "island_name": (
                assignment.outlet.island.island_name
                if assignment.outlet.island
                else "-"
            ),
            "outlet_id": assignment.outlet_id,
            "outlet_name": assignment.outlet.outlet_name,
            "total_items": assignment.total_items or 0,
            "assignment_type": "Outlet assignment",
            "item_split": "All items",
            "collector_id": assignment.collector_id,
            "collector_name": (
                assignment.collector.full_name
                or assignment.collector.django_user.username
            ),
            "display_range": str(assignment.total_items or 0),
            "is_active": True,
        })

    large_assignments = (
        CollectorItemAssignment.objects
        .filter(
            round=active_round,
            is_active=True,
        )
        .values(
            "collection_item__outlet_id",
            "collection_item__outlet__outlet_name",
            "collection_item__outlet__island__island_name",
            "collector_id",
            "collector__full_name",
            "collector__django_user__username",
            "item_split",
        )
        .annotate(
            assigned_items=Count(
                "collection_item_id",
                distinct=True,
            )
        )
        .order_by(
            "collection_item__outlet__island__island_name",
            "collection_item__outlet__outlet_name",
            "item_split",
        )
    )

    total_items_by_outlet = {
        row["outlet_id"]: row["total_items"]
        for row in (
            CpiCollectionItem.objects
            .filter(
                is_active=True,
                outlet_id__in=[
                    row["collection_item__outlet_id"]
                    for row in large_assignments
                ],
            )
            .values("outlet_id")
            .annotate(
                total_items=Count("collection_item_id")
            )
        )
    }

    assigned_splits_by_outlet = {}
    outlet_names = {}

    for row in large_assignments:
        outlet_id = row["collection_item__outlet_id"]

        collector_ids.add(row["collector_id"])
        assigned_outlet_ids.add(outlet_id)
        large_outlet_ids.add(outlet_id)

        outlet_names[outlet_id] = (
            row["collection_item__outlet__outlet_name"]
        )

        assigned_splits_by_outlet.setdefault(
            outlet_id,
            set(),
        ).add(row["item_split"])

        assignments.append({
            "island_name": (
                row[
                    "collection_item__outlet__island__island_name"
                ]
                or "-"
            ),
            "outlet_id": outlet_id,
            "outlet_name": (
                row[
                    "collection_item__outlet__outlet_name"
                ]
            ),
            "total_items": total_items_by_outlet.get(
                outlet_id,
                0,
            ),
            "assignment_type": "Item split assignment",
            "item_split": row["item_split"],
            "collector_id": row["collector_id"],
            "collector_name": (
                row["collector__full_name"]
                or row["collector__django_user__username"]
            ),
            "display_range": (
                f'{row["assigned_items"]} items'
            ),
            "is_active": True,
        })

    for outlet_id, assigned_splits in assigned_splits_by_outlet.items():
        if assigned_splits == {"First half"}:
            incomplete_large_outlets.append({
                "outlet_name": outlet_names[outlet_id],
                "missing_split": "Second half",
            })

        elif assigned_splits == {"Second half"}:
            incomplete_large_outlets.append({
                "outlet_name": outlet_names[outlet_id],
                "missing_split": "First half",
            })

    assignments.sort(
        key=lambda row: (
            row["island_name"],
            row["outlet_name"],
            row["item_split"],
        )
    )

    return {
        "collectors": collectors,
        "assignments": assignments,
        "total_collectors": len(collector_ids),
        "assigned_outlets": len(assigned_outlet_ids),
        "shared_outlets": len(large_outlet_ids),
        "incomplete_large_outlets": incomplete_large_outlets,
    }


@supervisor_required
def supervisor_small_assignment(request):

    active_round = (
        CpiRound.objects
        .filter(round_status="OPEN")
        .first()
    )

    if request.method == "POST":

        collector_id = request.POST.get("collector")
        outlet_ids = request.POST.getlist("outlet_ids")

        if not collector_id:
            messages.error(
                request,
                "Please select a collector."
            )
            return redirect(
                "supervisor-small-assignment"
            )

        if not outlet_ids:
            messages.error(
                request,
                "Please select at least one outlet."
            )
            return redirect(
                "supervisor-small-assignment"
            )
        assigned_names = []

        for outlet_id in outlet_ids:

            outlet = get_object_or_404(
                DimOutlet,
                outlet_id=outlet_id,
                is_active=True,
            )

            active_item_count = (
                CpiCollectionItem.objects
                .filter(
                    outlet=outlet,
                    is_active=True,
                )
                .count()
            )

            if active_item_count > 60:
                messages.warning(
                    request,
                    f"{outlet.outlet_name} is a large outlet."
                )
                continue

            if (
                CollectorAssignment.objects
                .filter(
                    round=active_round,
                    outlet=outlet,
                    is_active=True,
                )
                .exists()
            ):
                continue

            CollectorAssignment.objects.create(
                round=active_round,
                collector_id=collector_id,
                outlet=outlet,
                is_active=True,
            )

            assigned_names.append(
                outlet.outlet_name
            )

        if assigned_names:
            messages.success(
                request,
                f"{len(assigned_names)} outlet(s) successfully assigned."
            )

        return redirect(
            "supervisor-small-assignment"
        ) 


    selected_category = request.GET.get("category", "FOOD")

    if selected_category not in ("FOOD", "NONFOOD", "SERVICE"):
        selected_category = "FOOD"

    collectors = (
        AppUser.objects
        .filter(
            role=AppUser.ROLE_COLLECTOR,
            is_active=True,
        )
        .select_related("django_user")
        .order_by("full_name")
    )

    islands = (
        DimIsland.objects
        .filter(
            dimoutlet__is_active=True,
            dimoutlet__outlet_type__broad_type=selected_category,
        )
        .distinct()
        .order_by("island_name")
    )

    selected_island_id = request.GET.get("island", "").strip()

    small_outlets = (
        DimOutlet.objects
        .filter(
            is_active=True,
            outlet_type__broad_type=selected_category,
        )
        .annotate(
            item_count=Count(
                "cpicollectionitem",
                filter=Q(
                    cpicollectionitem__is_active=True
                ),
                distinct=True,
            )
        )
        .filter(
            item_count__lte=60
        )
        .select_related(
            "island",
            "outlet_type",
        )
    )

    assigned_small_rows = (
        CollectorAssignment.objects
        .filter(
            round=active_round,
            is_active=True,
            outlet_id__in=small_outlets.values_list(
                "outlet_id",
                flat=True,
            ),
        )
        .values(
            "outlet_id",
            "collector_id",
            "collector__full_name",
            "collector__django_user__username",
        )
    )

    assigned_small = {}

    for row in assigned_small_rows:

        collector_name = (
            row["collector__full_name"]
            or row["collector__django_user__username"]
        )

        assigned_small[row["outlet_id"]] = {
            "collector_id": row["collector_id"],
            "collector_name": collector_name,
        }

    if selected_island_id:
        small_outlets = small_outlets.filter(
            island_id=selected_island_id
        )

    small_outlets = small_outlets.order_by(
        "island__island_name",
        "outlet_name",
    )

    for outlet in small_outlets:

        assignment = assigned_small.get(
            outlet.outlet_id
        )

        outlet.is_assigned = bool(
            assignment
        )

        outlet.assigned_collector = (
            assignment["collector_name"]
            if assignment
            else None
        )

    context = {
        "active_round": active_round,
        "collectors": collectors,
        "islands": islands,
        "selected_category": selected_category,
        "small_outlets": small_outlets,
        "selected_island_id": selected_island_id,

    }

    return render(
        request,
        "supervisor/small_assignment.html",
        context
    )

@supervisor_required
def supervisor_small_assignment_items(request):

    outlet_id = request.GET.get(
        "outlet_id"
    )

    outlet = get_object_or_404(
        DimOutlet,
        outlet_id=outlet_id,
        is_active=True,
    )

    active_items = (
        CpiCollectionItem.objects
        .filter(
            outlet=outlet,
            is_active=True,
        )
        .order_by(
            "sort_order",
            "product_name",
            "collection_item_id",
        )
    )

    items = [
        {
            "collection_item_id": item.collection_item_id,
            "product_name": item.product_name,
            "product_specification": item.product_specification,
        }
        for item in active_items
    ]

    return JsonResponse(
        {
            "success": True,
            "outlet_name": outlet.outlet_name,
            "item_count": len(items),
            "items": items,
        }
    )

@supervisor_required
def supervisor_large_assignment(request):

    active_round = (
        CpiRound.objects
        .filter(round_status="OPEN")
        .order_by(
            "-survey_year",
            "-survey_month",
        )
        .first()
    )

    if request.method == "POST":

        collector_id = request.POST.get(
            "collector",
            "",
        )

        first_half_outlet_ids = request.POST.getlist(
            "first_half_outlet_ids"
        )

        second_half_outlet_ids = request.POST.getlist(
            "second_half_outlet_ids"
        )

        if not collector_id:
            messages.error(
                request,
                "Please select a collector.",
            )
            return redirect(
                "supervisor-large-assignment"
            )

        if (
            not first_half_outlet_ids
            and not second_half_outlet_ids
        ):
            messages.error(
                request,
                "Please select at least one outlet half.",
            )
            return redirect(
                "supervisor-large-assignment"
            )

        assignments_created = 0

        selected_halves = []

        for outlet_id in first_half_outlet_ids:
            selected_halves.append(
                (
                    outlet_id,
                    "First half",
                )
            )

        for outlet_id in second_half_outlet_ids:
            selected_halves.append(
                (
                    outlet_id,
                    "Second half",
                )
            )

        for outlet_id, item_split in selected_halves:

            outlet = get_object_or_404(
                DimOutlet,
                outlet_id=outlet_id,
                is_active=True,
            )

            if (
                CollectorItemAssignment.objects
                .filter(
                    round=active_round,
                    collection_item__outlet=outlet,
                    item_split=item_split,
                    is_active=True,
                )
                .exists()
            ):
                continue

            active_items = list(
                CpiCollectionItem.objects
                .filter(
                    outlet=outlet,
                    is_active=True,
                )
                .order_by(
                    "sort_order",
                    "product_name",
                    "collection_item_id",
                )
            )

            if len(active_items) <= 60:
                continue

            half = (
                len(active_items) + 1
            ) // 2

            if item_split == "First half":
                selected_items = active_items[:half]
            else:
                selected_items = active_items[half:]

            with transaction.atomic():

                for item in selected_items:

                    CollectorItemAssignment.objects.create(
                        round=active_round,
                        collector_id=collector_id,
                        collection_item=item,
                        item_split=item_split,
                        is_active=True,
                    )

            assignments_created += 1

        if assignments_created:
            messages.success(
                request,
                f"{assignments_created} outlet half assignment(s) created successfully.",
            )

        return redirect(
            "supervisor-large-assignment"
        )

    selected_category = request.GET.get(
        "category",
        "FOOD",
    )

    if selected_category not in (
        "FOOD",
        "NONFOOD",
        "SERVICE",
    ):
        selected_category = "FOOD"

    islands = (
        DimIsland.objects
        .filter(
            dimoutlet__is_active=True,
            dimoutlet__outlet_type__broad_type=selected_category,
        )
        .distinct()
        .order_by("island_name")
    )

    selected_island_id = request.GET.get(
        "island",
        "",
    ).strip()

    collectors = (
        AppUser.objects
        .filter(
            role=AppUser.ROLE_COLLECTOR,
            is_active=True,
        )
        .select_related("django_user")
        .order_by(
            "full_name",
            "django_user__username",
        )
    )

    large_outlets = (
        DimOutlet.objects
        .filter(
            is_active=True,
            outlet_type__broad_type=selected_category,
        )
        .annotate(
            item_count=Count(
                "cpicollectionitem",
                filter=Q(
                    cpicollectionitem__is_active=True
                ),
                distinct=True,
            )
        )
        .filter(
            item_count__gt=60
        )
        .select_related(
            "island",
            "outlet_type",
        )
        .order_by(
            "island__island_name",
            "outlet_name",
        )
    )
    if selected_island_id:
        large_outlets = large_outlets.filter(
            island_id=selected_island_id
        )
    assigned_split_rows = (
        CollectorItemAssignment.objects
        .filter(
            round=active_round,
            is_active=True,
            collection_item__outlet_id__in=large_outlets.values_list(
                "outlet_id",
                flat=True,
            ),
        )
        .values(
            "collection_item__outlet_id",
            "item_split",
            "collector_id",
            "collector__full_name",
            "collector__django_user__username",
        )
        .distinct()
    )

    assigned_splits = {}

    for row in assigned_split_rows:

        outlet_id = row[
            "collection_item__outlet_id"
        ]

        collector_name = (
            row["collector__full_name"]
            or row["collector__django_user__username"]
        )

        assigned_splits.setdefault(
            outlet_id,
            {},
        )[row["item_split"]] = {
            "collector_id": row["collector_id"],
            "collector_name": collector_name,
        }

    # fully_assigned_outlet_ids = [
    #     outlet_id
    #     for outlet_id, splits in assigned_splits.items()
    #     if "First half" in splits
    #     and "Second half" in splits
    # ]

    # large_outlets = large_outlets.exclude(
    #     outlet_id__in=fully_assigned_outlet_ids
    # )

    for outlet in large_outlets:

        total_items = outlet.item_count or 0

        outlet.first_half_count = (
            total_items + 1
        ) // 2

        outlet.second_half_count = (
            total_items
            - outlet.first_half_count
        )

        outlet.first_half_range = (
            f"1-{outlet.first_half_count}"
        )

        outlet.second_half_range = (
            f"{outlet.first_half_count + 1}-{total_items}"
        )

        split_details = assigned_splits.get(
            outlet.outlet_id,
            {},
        )

        first_assignment = split_details.get(
            "First half"
        )

        second_assignment = split_details.get(
            "Second half"
        )

        outlet.first_half_assigned = bool(
            first_assignment
        )

        outlet.second_half_assigned = bool(
            second_assignment
        )

        outlet.first_half_collector = (
            first_assignment["collector_name"]
            if first_assignment
            else None
        )

        outlet.second_half_collector = (
            second_assignment["collector_name"]
            if second_assignment
            else None
        )
    return render(
        request,
        "supervisor/large_assignment.html",
        {
            "active_round": active_round,
            "selected_category": selected_category,
            "islands": islands,
            "selected_island_id": selected_island_id,
            "collectors": collectors,
            "large_outlets": large_outlets,
        }
    )


@supervisor_required
def supervisor_large_assignment_half_items(request):

    outlet_id = request.GET.get(
        "outlet_id"
    )

    item_split = request.GET.get(
        "item_split"
    )

    if item_split not in (
        "First half",
        "Second half",
    ):
        return JsonResponse(
            {
                "success": False,
                "message": "Invalid item split.",
            },
            status=400,
        )

    outlet = get_object_or_404(
        DimOutlet,
        outlet_id=outlet_id,
        is_active=True,
    )

    active_items = list(
        CpiCollectionItem.objects
        .filter(
            outlet=outlet,
            is_active=True,
        )
        .order_by(
            "sort_order",
            "product_name",
            "collection_item_id",
        )
    )

    half = (
        len(active_items) + 1
    ) // 2

    if item_split == "First half":
        selected_items = active_items[:half]
    else:
        selected_items = active_items[half:]

    items = [
        {
            "collection_item_id": item.collection_item_id,
            "product_name": item.product_name,
            "product_specification": item.product_specification,
        }
        for item in selected_items
    ]

    return JsonResponse(
        {
            "success": True,
            "outlet_name": outlet.outlet_name,
            "item_split": item_split,
            "first_half_count": half,
            "items": items,
        }
    )


def supervisor_assignments_clear(request):
    if request.method == "POST":
        CollectorItemAssignment.objects.all().delete()
        CollectorAssignment.objects.all().delete()

        messages.success(request, "All collector assignments have been deleted.")
        return redirect("supervisor-assignments")

    return redirect("supervisor-assignments")


def supervisor_assignment_remove(request):
    if request.method != "POST":
        return redirect("supervisor-assignments")

    active_round = get_object_or_404(
        CpiRound,
        round_status="OPEN",
    )

    outlet_id = request.POST.get(
        "outlet_id"
    )

    collector_id = request.POST.get(
        "collector_id"
    )

    assignment_type = request.POST.get(
        "assignment_type"
    )

    item_split = request.POST.get(
        "item_split",
        "",
    )

    outlet = get_object_or_404(
        DimOutlet,
        outlet_id=outlet_id,
    )

    if assignment_type == "Outlet assignment":
        updated = (
            CollectorAssignment.objects
            .filter(
                round=active_round,
                outlet=outlet,
                collector_id=collector_id,
                is_active=True,
            )
            .update(is_active=False)
        )

        description = outlet.outlet_name

    else:
        updated = (
            CollectorItemAssignment.objects
            .filter(
                round=active_round,
                collection_item__outlet=outlet,
                collector_id=collector_id,
                item_split=item_split,
                is_active=True,
            )
            .update(is_active=False)
        )

        description = (
            f"{item_split} of "
            f"{outlet.outlet_name}"
        )

    if updated:
        messages.success(
            request,
            f"{description} was revoked.",
        )
    else:
        messages.warning(
            request,
            "No active assignment was found.",
        )

    return redirect("supervisor-assignments")


def supervisor_assignment_reassign(request):
    if request.method != "POST":
        return redirect("supervisor-assignments")

    active_round = get_object_or_404(
        CpiRound,
        round_status="OPEN",
    )

    outlet_id = request.POST.get(
        "outlet_id"
    )

    old_collector_id = request.POST.get(
        "collector_id"
    )

    new_collector_id = request.POST.get(
        "new_collector"
    )

    assignment_type = request.POST.get(
        "assignment_type"
    )

    item_split = request.POST.get(
        "item_split",
        "",
    )

    if not new_collector_id:
        messages.error(
            request,
            "Please select the new collector.",
        )
        return redirect("supervisor-assignments")

    if str(old_collector_id) == str(new_collector_id):
        messages.warning(
            request,
            "The selected collector is already assigned.",
        )
        return redirect("supervisor-assignments")

    outlet = get_object_or_404(
        DimOutlet,
        outlet_id=outlet_id,
    )

    with transaction.atomic():
        if assignment_type == "Outlet assignment":
            old_assignment = get_object_or_404(
                CollectorAssignment,
                round=active_round,
                outlet=outlet,
                collector_id=old_collector_id,
                is_active=True,
            )

            old_assignment.is_active = False
            old_assignment.save(
                update_fields=["is_active"]
            )

            CollectorAssignment.objects.create(
                round=active_round,
                outlet=outlet,
                collector_id=new_collector_id,
                is_active=True,
            )

            description = outlet.outlet_name

        else:
            old_assignments = list(
                CollectorItemAssignment.objects
                .filter(
                    round=active_round,
                    collection_item__outlet=outlet,
                    collector_id=old_collector_id,
                    item_split=item_split,
                    is_active=True,
                )
                .select_related(
                    "collection_item"
                )
            )

            if not old_assignments:
                messages.error(
                    request,
                    "The assignment could not be found.",
                )
                return redirect(
                    "supervisor-assignments"
                )

            CollectorItemAssignment.objects.filter(
                assignment_id__in=[
                    assignment.assignment_id
                    for assignment
                    in old_assignments
                ]
            ).update(is_active=False)

            CollectorItemAssignment.objects.bulk_create([
                CollectorItemAssignment(
                    round=active_round,
                    collector_id=new_collector_id,
                    collection_item=(
                        assignment.collection_item
                    ),
                    item_split=item_split,
                    is_active=True,
                )
                for assignment in old_assignments
            ])

            description = (
                f"{item_split} of "
                f"{outlet.outlet_name}"
            )

    messages.success(
        request,
        f"{description} was reassigned successfully.",
    )

    return redirect("supervisor-assignments")


def supervisor_replacements(request):

    base_queryset = (
        CpiReplacement.objects
        .filter(is_deleted=False)
        .select_related(
            "old_collection_item",
            "old_collection_item__outlet",
            "old_collection_item__basket_item",
            "approved_collection_item",
        )
    )

    pending_replacements = (
        base_queryset
        .filter(
            replacement_status=CpiReplacement.STATUS_PENDING
        )
        .order_by("-created_at")
    )

    active_replacements = (
        base_queryset
        .filter(
            replacement_status=CpiReplacement.STATUS_APPROVED,
            approved_collection_item__is_active=True,
        )
        .order_by("-reviewed_at", "-created_at")
    )

    replacement_history = (
        base_queryset
        .filter(
            replacement_status__in=[
                CpiReplacement.STATUS_APPROVED,
                CpiReplacement.STATUS_REVERTED,
                CpiReplacement.STATUS_REPLACED_AGAIN,
            ]
        )
        .order_by("-reviewed_at", "-created_at")
    )

    rejected_replacements = (
        base_queryset
        .filter(
            replacement_status=CpiReplacement.STATUS_REJECTED
        )
        .order_by("-reviewed_at", "-created_at")
    )

    for r in pending_replacements:

        item_photo = (
            CpiPhoto.objects.filter(
                collection_item=r.old_collection_item,
                photo_type="ITEM",
                is_deleted=False,
            )
            .order_by("-created_at")
            .first()
        )

        replacement_photo = (
            CpiPhoto.objects.filter(
                replacement=r,
                photo_type="REPLACEMENT_ITEM",
                is_deleted=False,
            )
            .order_by("-created_at")
            .first()
        )

        r.item_photo = item_photo
        r.replacement_photo = replacement_photo
    context = {
        "pending_replacements": pending_replacements,
        "active_replacements": active_replacements,
        "replacement_history": replacement_history,
        "rejected_replacements": rejected_replacements,

        "pending_count": pending_replacements.count(),
        "active_count": active_replacements.count(),
        "history_count": replacement_history.count(),
        "rejected_count": rejected_replacements.count(),
    }

    return render(
        request,
        "supervisor/replacements.html",
        context,
    )

@supervisor_required
@require_POST
def supervisor_replacement_approve(request, replacement_id):

    with transaction.atomic():

        replacement = get_object_or_404(
            CpiReplacement.objects.select_for_update(),
            replacement_id=replacement_id,
            is_deleted=False,
        )

        if (
            replacement.replacement_status
            == CpiReplacement.STATUS_APPROVED
            or replacement.approved_collection_item_id
        ):
            messages.warning(
                request,
                "This replacement has already been approved.",
            )
            return redirect("supervisor-replacements")

        if (
            replacement.replacement_status
            != CpiReplacement.STATUS_PENDING
        ):
            messages.error(
                request,
                "Only pending replacement requests can be approved.",
            )
            return redirect("supervisor-replacements")

        old_collection_item = (
            CpiCollectionItem.objects
            .select_for_update(of=("self",))
            .get(
                collection_item_id=replacement.old_collection_item_id
            )
        )

        basket_item = old_collection_item.basket_item
        outlet = old_collection_item.outlet

        active_item = (
            CpiCollectionItem.objects
            .filter(
                outlet=outlet,
                basket_item=basket_item,
                specification_no=old_collection_item.specification_no,
                is_active=True,
            )
            .exclude(
                collection_item_id=old_collection_item.collection_item_id
            )
            .first()
        )

        if active_item:
            messages.error(
                request,
                (
                    f"An active replacement already exists "
                    f"({active_item.product_name}). "
                    f"Deactivate it before approving another replacement."
                ),
            )
            return redirect("supervisor-replacements")

        if not basket_item:
            messages.error(
                request,
                "The previous collection item is not linked to a basket item.",
            )
            return redirect("supervisor-replacements")

        brand_obj = replacement.new_brand_fk
        country_obj = replacement.new_made_in_fk

        if not brand_obj and replacement.new_brand:
            brand_name = replacement.new_brand.strip()

            if brand_name:
                brand_obj, _ = DimBrand.objects.get_or_create(
                    brand_name=brand_name
                )

        if not country_obj and replacement.new_made_in:
            country_name = replacement.new_made_in.strip()

            if country_name:
                country_obj, _ = DimCountry.objects.get_or_create(
                    country_name=country_name
                )

        specification_parts = []

        if replacement.new_type:
            specification_parts.append(
                f"Type: {replacement.new_type.strip()}"
            )

        if replacement.new_size:
            specification_parts.append(
                f"Size of units: {replacement.new_size.strip()}"
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

        product_specification = " | ".join(
            specification_parts
        )

        if not product_specification:
            product_specification = (
                old_collection_item.product_specification
            )

        today = timezone.localdate()

        new_collection_item = CpiCollectionItem.objects.create(
            outlet=outlet,
            basket_item=basket_item,

            matched_basket_name=(
                old_collection_item.matched_basket_name
                or basket_item.basket_item_name
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

            spec_type=(
                replacement.new_type
                or old_collection_item.spec_type
            ),

            unit=(
                replacement.new_unit
                or old_collection_item.unit
            ),

            excel_subgroup=old_collection_item.excel_subgroup,
            sort_order=old_collection_item.sort_order,

            is_active=True,
            valid_from=today,
            valid_to=None,

            item_status=CpiCollectionItem.STATUS_ACTIVE_REPLACEMENT,

            last_price=replacement.new_price,
            last_price_month=None,
        )

        old_collection_item.is_active = False
        old_collection_item.valid_to = today
        old_collection_item.item_status = (
            CpiCollectionItem.STATUS_REPLACED
        )

        old_collection_item.save(
            update_fields=[
                "is_active",
                "valid_to",
                "item_status",
            ]
        )

        replacement.replacement_status = (
            CpiReplacement.STATUS_APPROVED
        )

        replacement.approved_collection_item = (
            new_collection_item
        )

        replacement.reviewed_at = timezone.now()
        replacement.reviewed_by = request.user.cpi_profile
        replacement.last_modified_at = timezone.now()

        replacement.save(
            update_fields=[
                "replacement_status",
                "approved_collection_item",
                "reviewed_at",
                "reviewed_by",
                "last_modified_at",
            ]
        )

    messages.success(
        request,
        (
            f"Replacement '{new_collection_item.product_name}' "
            f"was approved for {outlet.outlet_name}. "
            f"It remains linked to basket item "
            f"{basket_item.basket_code}."
        ),
    )

    return redirect("supervisor-replacements")



@supervisor_required
@require_POST
@transaction.atomic
def supervisor_restore_original(request, replacement_id):
    replacement = get_object_or_404(
        CpiReplacement.objects.select_for_update(),
        pk=replacement_id,
        replacement_status=CpiReplacement.STATUS_APPROVED,
    )

    original_item = replacement.old_collection_item
    replacement_item = replacement.approved_collection_item

    if original_item is None:
        messages.error(
            request,
            "The original collection item could not be found.",
        )
        return redirect("supervisor-replacements")

    if replacement_item is None:
        messages.error(
            request,
            "The approved replacement collection item could not be found.",
        )
        return redirect("supervisor-replacements")

    # Lock both collection-item records separately.
    collection_items = {
        item.pk: item
        for item in CpiCollectionItem.objects.select_for_update().filter(
            pk__in=[original_item.pk, replacement_item.pk]
        )
    }

    if original_item.pk not in collection_items:
        messages.error(
            request,
            "The original collection item could not be found.",
        )
        return redirect("supervisor-replacements")

    if replacement_item.pk not in collection_items:
        messages.error(
            request,
            "The approved replacement collection item could not be found.",
        )
        return redirect("supervisor-replacements")

    original_item = collection_items[original_item.pk]
    replacement_item = collection_items[replacement_item.pk]

    if not replacement_item.is_active:
        messages.warning(
            request,
            "This replacement product is no longer active.",
        )
        return redirect("supervisor-replacements")

    today = timezone.localdate()

    # Deactivate the replacement item.
    replacement_item.is_active = False
    replacement_item.item_status = CpiCollectionItem.STATUS_INACTIVE
    replacement_item.valid_to = today
    replacement_item.save(
        update_fields=[
            "is_active",
            "item_status",
            "valid_to",
        ]
    )

    # Reactivate the original item.
    original_item.is_active = True
    original_item.item_status = CpiCollectionItem.STATUS_ACTIVE
    original_item.valid_to = None
    original_item.save(
        update_fields=[
            "is_active",
            "item_status",
            "valid_to",
        ]
    )

    # Update the replacement history record.
    replacement.replacement_status = CpiReplacement.STATUS_REVERTED
    replacement.reviewed_at = timezone.now()
    replacement.reviewed_by = request.user.cpi_profile
    replacement.save(
        update_fields=[
            "replacement_status",
            "reviewed_at",
            "reviewed_by",
        ]
    )

    messages.success(
        request,
        f'Original product "{original_item.product_name}" restored successfully.',
    )

    return redirect("supervisor-replacements")


def supervisor_replacement_reject(request, replacement_id):
    replacement = get_object_or_404(CpiReplacement, replacement_id=replacement_id)

    if request.method == "POST":
        rejection_comment = request.POST.get("rejection_comment", "").strip()

        if not rejection_comment:
            messages.error(request, "Rejection reason is required.")
            return redirect("supervisor-replacements")

        replacement.replacement_status = "REJECTED"
        replacement.rejection_comment = rejection_comment
        replacement.reviewed_at = timezone.now()
        replacement.reviewed_by = None
        replacement.last_modified_at = timezone.now()
        replacement.save(update_fields=[
            "replacement_status",
            "rejection_comment",
            "reviewed_at",
            "reviewed_by",
            "last_modified_at",
        ])

        messages.warning(request, "Replacement rejected successfully.")
        return redirect("supervisor-replacements")

    return redirect("supervisor-replacements")

def supervisor_reviews(request):
    active_round = CpiRound.objects.filter(round_status="OPEN").first()

    if not active_round:
        messages.warning(request, "No OPEN CPI round found.")
        return render(request, "supervisor/reviews.html", {
            "active_round": None,
        })

    selected_island = request.GET.get("island", "").strip()

    islands = (
        CollectorWorkloadSummary.objects
        .filter(is_active=True)
        .exclude(island_name__isnull=True)
        .exclude(island_name="")
        .values_list("island_name", flat=True)
        .distinct()
        .order_by("island_name")
    )

    assignments = CollectorWorkloadSummary.objects.filter(
        is_active=True
    )

    if selected_island:
        assignments = assignments.filter(
            island_name=selected_island
        )

    assignments = assignments.order_by(
        "island_name",
        "outlet_name",
        "item_split",
        "collector_name"
    )

    review_rows = []

    for assignment in assignments:
        outlet = DimOutlet.objects.filter(
            outlet_name=assignment.outlet_name,
            island__island_name=assignment.island_name
        ).first()

        collector = AppUser.objects.filter(
            full_name=assignment.collector_name
        ).first()

        if not collector:
            collector = AppUser.objects.filter(
                django_user__username=assignment.collector_name
            ).first()

        if not outlet or not collector:
            continue

        visit = (
            CpiVisit.objects
            .filter(
                round=active_round,
                outlet=outlet,
                collector_user=collector,
                is_deleted=False
            )
            .order_by("-visit_id")
            .first()
        )

        assigned_item_ids = list(
            CollectorItemAssignment.objects
            .filter(
                collector=collector,
                collection_item__outlet=outlet,
                is_active=True
            )
            .values_list("collection_item_id", flat=True)
        )

        if assigned_item_ids:
            total_items = len(assigned_item_ids)
        else:
            total_items = CpiCollectionItem.objects.filter(
                outlet=outlet,
                is_active=True
            ).count()

        prices = FactPrice.objects.none()

        if visit:
            if assigned_item_ids:
                prices = FactPrice.objects.filter(
                    visit=visit,
                    collection_item_id__in=assigned_item_ids,
                    is_deleted=False
                )
            else:
                prices = FactPrice.objects.filter(
                    visit=visit,
                    is_deleted=False
                )



        submitted_items = prices.count()
        pending_items = total_items - submitted_items

        progress_percent = 0
        if total_items > 0:
            progress_percent = round((submitted_items / total_items) * 100, 1)
        outlier_items = prices.filter(is_outlier=True).count()
        correction_items = prices.filter(review_status="CORRECTION_REQUIRED").count()
        approved_items = prices.filter(review_status__in=["APPROVED", "OUTLET_APPROVED"]).count()

        pending_review_items = prices.filter(review_status="PENDING_REVIEW").count()
        
        if submitted_items == 0:
            review_status = "Not submitted"
        elif visit and visit.review_status == "APPROVED":
            review_status = "Approved"
        elif visit and visit.review_status == "REJECTED":
            review_status = "Rejected by Supervisor"
        elif visit and visit.review_status == "CORRECTION_REQUIRED":
            review_status = "Correction required"
        elif visit and visit.review_status == "CORRECTED_PENDING_REVIEW":
            review_status = "Corrected - Pending review"
        else:
            review_status = "Pending review"

        review_rows.append({
            "visit": visit,
            "collector_name": collector.full_name or collector.username,
            "island_name": outlet.island.island_name,
            "outlet_name": outlet.outlet_name,
            "item_split": assignment.item_split or "All items",
            "submitted_items": submitted_items,
            "outlier_items": outlier_items,
            "correction_items": correction_items,
            "approved_items": approved_items,
            "review_status": review_status,
            "total_items": total_items,
            "pending_items": pending_items,
            "pending_review_items": pending_review_items,
            "progress_percent": progress_percent,
        })

    return render(request, "supervisor/reviews.html", {
        "active_round": active_round,
        "review_rows": review_rows,
        "islands": islands,
        "selected_island": selected_island,
    })

def supervisor_review_outlet(request, visit_id):
    visit = get_object_or_404(
        CpiVisit.objects.select_related(
            "collector_user",
            "outlet",
            "outlet__island"
        ),
        visit_id=visit_id,
        is_deleted=False
    )

    prices = (
        FactPrice.objects
        .filter(
            visit=visit,
            is_deleted=False
        )
        .select_related("collection_item")
        .order_by(
            "collection_item__sort_order",
            "collection_item__product_name"
        )
    )

    review_items = []

    collection_item_ids = list(
        prices.values_list("collection_item_id", flat=True)
    )

    reference_photos = {
        photo.collection_item_id: photo
        for photo in CpiPhoto.objects.filter(
            collection_item_id__in=collection_item_ids,
            photo_type="REFERENCE_ITEM",
            status="APPROVED",
            is_deleted=False,
        ).order_by("collection_item_id", "-created_at")
    }

    pending_photos = {
        photo.collection_item_id: photo
        for photo in CpiPhoto.objects.filter(
            collection_item_id__in=collection_item_ids,
            visit=visit,
            photo_type="ITEM",
            status="PENDING",
            is_deleted=False,
            replacement__isnull=True,
        ).order_by("collection_item_id", "-created_at")
    }

    for price in prices:
        last_price = price.last_month_price
        current_price = price.observed_price

        change_percent = None
        if last_price and current_price and last_price > 0:
            change_percent = round(((current_price - last_price) / last_price) * 100, 1)

        review_items.append({
            "price": price,
            "item": price.collection_item,
            "change_percent": change_percent,
            "reference_photo": reference_photos.get(
                price.collection_item_id
            ),
            "pending_photo": pending_photos.get(
                price.collection_item_id
            ),
        })

    total_items = CpiCollectionItem.objects.filter(
    outlet=visit.outlet,
    is_active=True
    ).count()

    collected_items = prices.count()
    pending_items = total_items - collected_items

    progress_percent = 0
    if total_items > 0:
        progress_percent = round((collected_items / total_items) * 100, 1)

    return render(request, "supervisor/review_outlet.html", {
        "visit": visit,
        "review_items": review_items,
        "total_items": total_items,
        "collected_items": collected_items,
        "pending_items": pending_items,
        "progress_percent": progress_percent,
    })


def supervisor_price_comment(request, price_id):
    price = get_object_or_404(FactPrice, price_id=price_id, is_deleted=False)

    if request.method == "POST":
        supervisor_comment = request.POST.get("supervisor_comment", "").strip()

        if supervisor_comment:
            price.supervisor_comment = supervisor_comment
            price.review_status = "CORRECTION_REQUIRED"
            price.reviewed_at = timezone.now()
            price.quote_status = "CORRECTION_REQUIRED"
            price.save(update_fields=[
                "supervisor_comment",
                "review_status",
                "reviewed_at",
                "quote_status",
            ])
            visit = price.visit
            visit.review_status = "CORRECTION_REQUIRED"
            visit.reviewed_at = timezone.now()
            visit.save(update_fields=["review_status", "reviewed_at"])

            messages.warning(request, "Correction comment saved for this item.")
        else:
            messages.error(request, "Please enter a correction comment.")

    return redirect("supervisor-review-outlet", visit_id=price.visit_id)


def supervisor_approve_outlet(request, visit_id):
    visit = get_object_or_404(CpiVisit, visit_id=visit_id, is_deleted=False)

    if request.method == "POST":

        total_items = CpiCollectionItem.objects.filter(
            outlet=visit.outlet,
            is_active=True
        ).count()

        collected_items = FactPrice.objects.filter(
            visit=visit,
            is_deleted=False
        ).values("collection_item").distinct().count()

        if collected_items < total_items:
            messages.error(
                request,
                "This outlet cannot be approved because collection is not complete."
            )
            return redirect("supervisor-review-outlet", visit_id=visit.visit_id)

        correction_count = FactPrice.objects.filter(
            visit=visit,
            review_status="CORRECTION_REQUIRED",
            is_deleted=False
        ).count()

        if correction_count > 0:
            messages.error(
                request,
                "This outlet cannot be approved because some items need correction."
            )
            return redirect("supervisor-review-outlet", visit_id=visit.visit_id)

        FactPrice.objects.filter(
            visit=visit,
            is_deleted=False
        ).update(
            review_status="OUTLET_APPROVED",
            quote_status="APPROVED",
            reviewed_at=timezone.now()
        )
        visit.review_status = "APPROVED"
        visit.reviewed_at = timezone.now()
        visit.save(update_fields=["review_status", "reviewed_at"])

        messages.success(request, "Whole outlet approved successfully.")

    return redirect("supervisor-reviews")


def supervisor_reject_outlet(request, visit_id):

    visit = get_object_or_404(
        CpiVisit,
        visit_id=visit_id,
        is_deleted=False
    )

    if request.method == "POST":

        rejection_comment = request.POST.get(
            "rejection_comment",
            ""
        ).strip()

        if not rejection_comment:
            messages.error(
                request,
                "Please enter a reason for rejecting the outlet."
            )
            return redirect(
                "supervisor-review-outlet",
                visit_id=visit.visit_id
            )

        visit.review_status = "REJECTED"
        visit.reviewed_at = timezone.now()
        visit.remarks = rejection_comment

        visit.save(
            update_fields=[
                "review_status",
                "reviewed_at",
                "remarks"
            ]
        )

        messages.warning(
            request,
            "Outlet rejected and returned to the collector for correction."
        )

        return redirect(
            "supervisor-review-outlet",
            visit_id=visit.visit_id
        )

    return redirect(
        "supervisor-review-outlet",
        visit_id=visit.visit_id
    )

def supervisor_progress(request):
    active_round = CpiRound.objects.filter(round_status="OPEN").first()

    if not active_round:
        messages.warning(request, "No OPEN CPI round found.")
        return render(request, "supervisor/progress.html", {
            "active_round": None,
        })

    selected_island = request.GET.get("island", "").strip()

    islands = (
        DimOutlet.objects
        .exclude(island__isnull=True)
        .values_list("island__island_name", flat=True)
        .distinct()
        .order_by("island__island_name")
    )

    total_assigned_outlets = (
        CollectorWorkloadSummary.objects
        .filter(is_active=True)
        .values("island_name", "outlet_name")
        .distinct()
        .count()
    )

    visits_started = CpiVisit.objects.filter(
        round=active_round,
        is_deleted=False
    ).count()

    visits_completed = CpiVisit.objects.filter(
        round=active_round,
        visit_status="COMPLETED",
        is_deleted=False
    ).count()

    total_items = CpiCollectionItem.objects.filter(
        is_active=True
    ).count()

    collected_items = (
        FactPrice.objects
        .filter(
            visit__round=active_round,
            quote_status="SUBMITTED",
            is_deleted=False
        )
        .values("collection_item")
        .distinct()
        .count()
    )

    pending_items = total_items - collected_items

    outlier_items = FactPrice.objects.filter(
        visit__round=active_round,
        is_outlier=True,
        is_deleted=False
    ).count()

    progress_percent = 0
    if total_items > 0:
        progress_percent = round((collected_items / total_items) * 100, 1)

    outlet_progress = []

    assignments = CollectorWorkloadSummary.objects.filter(
        is_active=True
    )

    if selected_island:
        assignments = assignments.filter(
            island_name=selected_island
        )

    assignments = assignments.order_by(
        "island_name",
        "outlet_name",
        "collector_name"
    )

    for assignment in assignments:
        outlet = DimOutlet.objects.filter(
            outlet_name=assignment.outlet_name,
            island__island_name=assignment.island_name
        ).first()

        collector = AppUser.objects.filter(
            full_name=assignment.collector_name
        ).first()

        if not collector:
            collector = AppUser.objects.filter(
                django_user__username=assignment.collector_name
            ).first()

        collected_count = 0
        visit_status = "Not started"

        assigned_item_ids = []

        if outlet and collector:
            assigned_item_ids = list(
                CollectorItemAssignment.objects
                .filter(
                    collector=collector,
                    collection_item__outlet=outlet,
                    is_active=True
                )
                .values_list("collection_item_id", flat=True)
            )

            latest_visit = (
                CpiVisit.objects
                .filter(
                    round=active_round,
                    outlet=outlet,
                    collector_user=collector,
                    is_deleted=False
                )
                .order_by("-visit_id")
                .first()
            )

            if latest_visit:
                visit_status = latest_visit.visit_status

                if assigned_item_ids:
                    collected_count = (
                        FactPrice.objects
                        .filter(
                            visit=latest_visit,
                            collection_item_id__in=assigned_item_ids,
                            quote_status="SUBMITTED",
                            is_deleted=False
                        )
                        .values("collection_item")
                        .distinct()
                        .count()
                    )
                else:
                    collected_count = (
                        FactPrice.objects
                        .filter(
                            visit=latest_visit,
                            collection_item__outlet=outlet,
                            quote_status="SUBMITTED",
                            is_deleted=False
                        )
                        .values("collection_item")
                        .distinct()
                        .count()
                    )

        if assigned_item_ids:
            total = len(assigned_item_ids)
        else:
            total = assignment.total_items or 0

        pending = total - collected_count

        if total > 0 and collected_count >= total:
            visit_status = "COMPLETED"
        elif collected_count > 0:
            visit_status = "IN_PROGRESS"

        percent = 0
        if total > 0:
            percent = round((collected_count / total) * 100, 1)

        outlet_progress.append({
            "collector_name": assignment.collector_name,
            "island_name": assignment.island_name,
            "outlet_name": assignment.outlet_name,
            "item_split": assignment.item_split or "All items",
            "total_items": total,
            "collected_items": collected_count,
            "pending_items": pending,
            "progress_percent": percent,
            "visit_status": visit_status,
        })

    return render(request, "supervisor/progress.html", {
        "active_round": active_round,
        "total_assigned_outlets": total_assigned_outlets,
        "visits_started": visits_started,
        "visits_completed": visits_completed,
        "total_items": total_items,
        "collected_items": collected_items,
        "pending_items": pending_items,
        "outlier_items": outlier_items,
        "progress_percent": progress_percent,
        "outlet_progress": outlet_progress,
        "islands": islands,
        "selected_island": selected_island,
    })

class AppUserCreateAPIView(generics.CreateAPIView):
    serializer_class = AppUserCreateSerializer
    permission_classes = [IsAdministrator]

@admin_required
def supervisor_users(request):
    users = (
        AppUser.objects
        .select_related("django_user")
        .order_by("role", "full_name")
    )

    return render(
        request,
        "supervisor/users.html",
        {
            "users": users,
        },
    )

@admin_required
def supervisor_user_create(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")
        full_name = request.POST.get("full_name", "").strip()
        email = request.POST.get("email", "").strip()
        phone_number = request.POST.get("phone_number", "").strip()
        role_value = request.POST.get("role", "").strip()
        island_id = request.POST.get("assigned_island", "").strip()

        if not username:
            messages.error(request, "Username is required.")
            return redirect("supervisor-user-create")

        if not password:
            messages.error(request, "Password is required.")
            return redirect("supervisor-user-create")

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect("supervisor-user-create")

        if not full_name:
            messages.error(request, "Full name is required.")
            return redirect("supervisor-user-create")

        try:
            role = int(role_value)
        except (TypeError, ValueError):
            messages.error(request, "Please select a valid role.")
            return redirect("supervisor-user-create")

        valid_roles = {choice[0] for choice in AppUser.ROLE_CHOICES}

        if role not in valid_roles:
            messages.error(request, "Please select a valid role.")
            return redirect("supervisor-user-create")

        if User.objects.filter(username__iexact=username).exists():
            messages.error(request, "Username already exists.")
            return redirect("supervisor-user-create")

        assigned_island = None

        if island_id:
            assigned_island = get_object_or_404(
                DimIsland,
                pk=island_id,
            )

        try:
            with transaction.atomic():
                django_user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    is_active=True,
                )

                AppUser.objects.create(
                    django_user=django_user,
                    full_name=full_name,
                    email=email or None,
                    phone_number=phone_number or None,
                    role=role,
                    assigned_island=assigned_island,
                    is_active=True,
                )

        except Exception:
            messages.error(
                request,
                "The user could not be created. Please check the details and try again.",
            )
            return redirect("supervisor-user-create")

        messages.success(request, "User created successfully.")
        return redirect("supervisor-users")

    islands = DimIsland.objects.order_by("island_name")

    return render(
        request,
        "supervisor/user_create.html",
        {
            "islands": islands,
            "role_choices": AppUser.ROLE_CHOICES,
        },
    )

@admin_required
def supervisor_user_edit(request, user_id):

    user = get_object_or_404(
        AppUser.objects.select_related(
            "django_user",
            "assigned_island",
        ),
        pk=user_id,
    )

    if request.method == "POST":

        full_name = request.POST.get("full_name", "").strip()
        email = request.POST.get("email", "").strip()
        phone_number = request.POST.get("phone_number", "").strip()
        role = int(request.POST.get("role"))

        island_id = request.POST.get("assigned_island")

        assigned_island = None

        if island_id:
            assigned_island = get_object_or_404(
                DimIsland,
                pk=island_id,
            )

        with transaction.atomic():

            user.full_name = full_name
            user.email = email or None
            user.phone_number = phone_number or None
            user.role = role
            user.assigned_island = assigned_island
            user.save()

            user.django_user.email = email
            user.django_user.save()

        messages.success(
            request,
            "User updated successfully.",
        )

        return redirect("supervisor-users")

    islands = DimIsland.objects.order_by("island_name")

    return render(
        request,
        "supervisor/user_edit.html",
        {
            "user": user,
            "islands": islands,
            "role_choices": AppUser.ROLE_CHOICES,
        },
    )

@admin_required
def supervisor_user_reset_password(request, user_id):

    user = get_object_or_404(
        AppUser.objects.select_related("django_user"),
        pk=user_id,
    )

    if request.method == "POST":

        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")

        else:
            try:
                validate_password(password, user.django_user)

                user.django_user.set_password(password)
                user.django_user.save()

                messages.success(
                    request,
                    f"Password for '{user.full_name}' has been reset successfully."
                )

                return redirect("supervisor-users")

            except ValidationError as e:
                for error in e.messages:
                    messages.error(request, error)

    return render(
        request,
        "supervisor/user_reset_password.html",
        {
            "user": user,
        },
    )