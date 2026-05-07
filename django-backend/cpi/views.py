from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import AppUser
from .serializers import LoginSerializer
from .models import CpiVisit
from django.views.decorators.csrf import csrf_exempt
from .models import DimCountry
from .models import CpiReplacement
from .serializers import LoginSerializer
from django.db import connection
from django.utils.dateparse import parse_datetime


from .models import CpiCollectionItem, CollectorAssignment
from .serializers import (
    CpiCollectionItemSerializer,
    FactPriceSerializer,
    AssignedOutletSerializer,
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
      
        "remarks": price.remarks or"",
        "new_item_name": replacement.new_name if replacement else "",
        "new_item_type": replacement.new_type if replacement else "",
        "new_item_size": replacement.new_size if replacement else "",
        "new_item_unit": replacement.new_unit if replacement else "",
        "new_item_brand": replacement.new_brand if replacement else "",
        "new_item_country_id": replacement.new_made_in if replacement else "",
        "new_item_price": str(replacement.new_price) if replacement and replacement.new_price is not None else "",
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
def outlet_items(request, outlet_id):
    items = (
        CpiCollectionItem.objects
        .filter(outlet_id=outlet_id, is_active=True)
        .select_related("outlet", "item", "unit", "brand", "country")
        .order_by("item__item_name", "spec_type")
    )

    serializer = CpiCollectionItemSerializer(items, many=True)
    return Response(serializer.data)


@api_view(["GET"])
def collector_outlets(request, collector_id):
    assignments = (
        CollectorAssignment.objects
        .filter(collector_id=collector_id, is_active=True)
        .select_related("outlet", "outlet__island")
        .order_by("outlet__island__island_name", "outlet__outlet_name")
    )

    serializer = AssignedOutletSerializer(assignments, many=True)
    return Response(serializer.data)


from django.utils import timezone
from .models import FactPrice




@csrf_exempt
@api_view(["POST"])
def start_visit(request):
    collector_id = request.data.get("collector_id")
    outlet_id = request.data.get("outlet_id")

    if not collector_id or not outlet_id:
        return Response({"error": "collector_id and outlet_id are required"}, status=400)

    visit = CpiVisit.objects.create(
        collector_user_id=collector_id,
        outlet_id=outlet_id,
        round_id=1,
        visit_status="IN_PROGRESS",
        sync_status="SYNCED",
        created_on_device=False,
        is_deleted=False,
        created_at=timezone.now(),
        last_modified_at=timezone.now(),
    )

    return Response({"visit_id": visit.visit_id}, status=201)


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
def submit_price(request):
    collection_item_id = request.data.get("collection_item")
    observed_price = request.data.get("observed_price")
    availability = request.data.get("availability")
    remarks = request.data.get("remarks", "")
    visit_id = request.data.get("visit_id")

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

    # calculate outlier
    is_outlier = False

    if observed_price and last_month_price:
        try:
            observed = float(observed_price)
            previous = float(last_month_price)

            if previous > 0:
                change = abs(observed - previous) / previous
                is_outlier = change > 0.30
        except:
            is_outlier = False
    # ✅ ADD THIS BLOCK HERE
    if is_outlier and not remarks:
        return Response(
            {"error": "Remarks required for outlier"},
            status=400
        )

    price, created = FactPrice.objects.update_or_create(
        visit_id=visit_id,
        collection_item_id=collection_item_id,
        defaults={
            "observed_price": observed_price,
            "last_month_price": last_month_price,
            "availability": availability or "AVAILABLE",
            "is_outlier": is_outlier,
            "remarks": remarks,
            "quote_status": "SUBMITTED",
            "sync_status": "SYNCED",
            "created_on_device": False,
            "is_deleted": False,
            "created_at": timezone.now(),
            "updated_at": timezone.now(),
            "last_modified_at": timezone.now(),
        }
    )

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

        if replacement:
            replacement.new_name = request.data.get("new_item_name")
            replacement.new_type = request.data.get("new_item_type")
            replacement.new_size = request.data.get("new_item_size")
            replacement.new_unit = request.data.get("new_item_unit")
            replacement.new_brand = request.data.get("new_item_brand")
            replacement.new_made_in = str(request.data.get("new_item_country_id") or "")
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
                new_made_in=str(request.data.get("new_item_country_id") or ""),
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
            "is_outlier": is_outlier
        },
        status=201
    )


@api_view(["POST"])
def collector_login(request):
    username = request.data.get("username")

    if not username:
        return Response({"error": "Username is required"}, status=400)

    try:
        user = AppUser.objects.get(
            username=username,
            role_code="collector",
            is_active=True
        )
    except AppUser.DoesNotExist:
        return Response({"error": "Invalid collector login"}, status=401)

    serializer = LoginSerializer(user)
    return Response(serializer.data)