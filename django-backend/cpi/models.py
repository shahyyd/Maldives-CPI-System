# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User


class AppDevice(models.Model):
    device_id = models.BigAutoField(primary_key=True)
    device_uuid = models.UUIDField(unique=True)
    device_name = models.TextField(blank=True, null=True)
    assigned_user = models.ForeignKey('AppUser', models.DO_NOTHING, blank=True, null=True)
    is_active = models.BooleanField()
    last_sync_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'app_device'




from django.contrib.auth.models import User

class AppUser(models.Model):

    ROLE_ADMIN = 1
    ROLE_SUPERVISOR = 2
    ROLE_COLLECTOR = 3
    ROLE_VIEWER = 4

    ROLE_CHOICES = [
        (ROLE_ADMIN, "Administrator"),
        (ROLE_SUPERVISOR, "Supervisor"),
        (ROLE_COLLECTOR, "Collector"),
        (ROLE_VIEWER, "Viewer"),
    ]

    user_id = models.BigAutoField(
        primary_key=True,
        db_column="user_id"
    )

    django_user = models.OneToOneField(
        User,
        db_column="django_user_id",
        on_delete=models.PROTECT,
        related_name="cpi_profile",
        null=True,
        blank=True,
    )

    full_name = models.CharField(max_length=200)

    email = models.EmailField(
        blank=True,
        null=True
    )

    phone_number = models.CharField(
        max_length=30,
        blank=True,
        null=True
    )

    role = models.PositiveSmallIntegerField(
        choices=ROLE_CHOICES,
        default=ROLE_COLLECTOR
    )

    assigned_island = models.ForeignKey(
        "DimIsland",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="users",
    )

    is_active = models.BooleanField(default=True)



    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "app_user"

    def __str__(self):
        return self.full_name

    @property
    def is_admin(self):
        return self.role == self.ROLE_ADMIN

    @property
    def is_supervisor(self):
        return self.role == self.ROLE_SUPERVISOR

    @property
    def is_collector(self):
        return self.role == self.ROLE_COLLECTOR
    
    @property
    def can_manage_operations(self):
        return self.role in (
            self.ROLE_ADMIN,
            self.ROLE_SUPERVISOR,
        )

    @property
    def is_viewer(self):
        return self.role == self.ROLE_VIEWER
    
    @property
    def username(self):
        return self.django_user.username if self.django_user else ""


class CpiAuditLog(models.Model):
    audit_id = models.BigAutoField(primary_key=True)
    entity_name = models.CharField(max_length=100)
    entity_id = models.BigIntegerField()
    action_code = models.CharField(max_length=30)
    changed_by = models.ForeignKey(AppUser, models.DO_NOTHING, db_column='changed_by', blank=True, null=True)
    changed_at = models.DateTimeField()
    old_value = models.JSONField(blank=True, null=True)
    new_value = models.JSONField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'cpi_audit_log'


class CpiCollectionItem(models.Model):

    collection_item_id = models.BigAutoField(primary_key=True)

    outlet = models.ForeignKey(
        'DimOutlet',
        models.DO_NOTHING
    )

    basket_item = models.ForeignKey(
        'CpiBasket',
        models.PROTECT,
        db_column='basket_id',
        blank=True,
        null=True,
        related_name='collection_items'
    )

    replaces_collection_item = models.ForeignKey(
        "self",
        models.DO_NOTHING,
        db_column="replaces_collection_item_id",
        blank=True,
        null=True,
        related_name="replacement_children",
    )

    matched_basket_name = models.TextField(
        blank=True,
        null=True
    )

    specification_no = models.CharField(
        max_length=10,
        blank=True,
        null=True
    )

    product_code = models.TextField(blank=True, null=True)

    product_name = models.TextField(blank=True, null=True)
    brand = models.TextField(blank=True, null=True)
    product_specification = models.TextField(blank=True, null=True)
    sort_order = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)

    excel_product_code = models.TextField(blank=True, null=True)
    excel_specification = models.TextField(blank=True, null=True)
    legacy_item_code = models.TextField(blank=True, null=True)

    is_active = models.BooleanField(default=True)

    valid_from = models.DateField(default=timezone.now)

    valid_to = models.DateField(blank=True, null=True)

    STATUS_ACTIVE = "ACTIVE"
    STATUS_ACTIVE_REPLACEMENT = "ACTIVE_REPLACEMENT"
    STATUS_REPLACED = "REPLACED"
    STATUS_UNAVAILABLE = "UNAVAILABLE"
    STATUS_INACTIVE = "INACTIVE"

    ITEM_STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_ACTIVE_REPLACEMENT, "Active Replacement"),
        (STATUS_REPLACED, "Replaced"),
        (STATUS_UNAVAILABLE, "Unavailable"),
        (STATUS_INACTIVE, "Inactive"),
    ]

    item_status = models.CharField(
        max_length=30,
        choices=ITEM_STATUS_CHOICES,
        default=STATUS_ACTIVE,
    )

    last_price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)

    last_price_month = models.CharField(max_length=20, blank=True, null=True)
    excel_subgroup = models.TextField(blank=True, null=True)
    spec_type = models.CharField(max_length=255, blank=True, null=True)
    size_value = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)

    unit = models.TextField(blank=True, null=True)

    brand_fk = models.ForeignKey('DimBrand', models.DO_NOTHING, db_column='brand_id', blank=True, null=True)

    country = models.ForeignKey('DimCountry', models.DO_NOTHING, db_column='country_id', blank=True, null=True)

    imported_country = models.ForeignKey('DimCountry',models.DO_NOTHING,db_column='imported_country_id',blank=True,null=True,related_name='imported_collection_items')

    other_spec = models.TextField(blank=True, null=True)
    material = models.TextField(blank=True, null=True)
    
    def save(self, *args, **kwargs):

        if not self.item_status:
            self.item_status = "ACTIVE"

        if not self.valid_from:
            self.valid_from = timezone.now().date()

        creating = self.collection_item_id is None

        if creating and not self.specification_no:
            existing_count = CpiCollectionItem.objects.filter(outlet=self.outlet, basket_item=self.basket_item).count()

            self.specification_no = f"{existing_count + 1:03d}"

        island_code = self.outlet.island.island_code if self.outlet.island else "000"
        outlet_code = self.outlet.outlet_code if self.outlet.outlet_code else "000"
        basket_item_code = self.basket_item.basket_code.zfill(3) if self.basket_item and self.basket_item.basket_code else "000"

        self.product_code = f"{island_code}|{outlet_code}|{basket_item_code}|{self.specification_no}"

        super().save(*args, **kwargs)

    def __str__(self):

        text = f"{self.outlet}"

        if self.product_name:
            text += f" - {self.product_name}"

        if self.brand:
            text += f" - {self.brand}"

        if self.product_specification:
            text += f" - {self.product_specification}"

        return text

    class Meta:
        managed = False
        db_table = 'cpi_collection_item'

        unique_together = (('outlet', 'basket_item', 'specification_no'),)


class CpiPhoto(models.Model):
    photo_id = models.BigAutoField(primary_key=True)
    price = models.ForeignKey('FactPrice', models.DO_NOTHING, blank=True, null=True)
    collection_item = models.ForeignKey('CpiCollectionItem', models.DO_NOTHING, db_column='collection_item_id', blank=True, null=True)
    visit = models.ForeignKey('CpiVisit', models.DO_NOTHING, blank=True, null=True)
    device = models.ForeignKey(AppDevice, models.DO_NOTHING, blank=True, null=True)
    local_uuid = models.UUIDField(unique=True, blank=True, null=True)
    file_name = models.TextField()
    file_path = models.TextField()
    mime_type = models.TextField(blank=True, null=True)
    file_hash = models.TextField(blank=True, null=True)
    photo_type = models.CharField(max_length=30, blank=True, null=True)
    STATUS_CHOICES = [("PENDING", "Pending"),("APPROVED", "Approved"),("REJECTED", "Rejected"),("REPLACED", "Replaced"),]
    rejection_reason = models.TextField(blank=True, default="")
    reviewed_at = models.DateTimeField(null=True, blank=True)

    reviewed_by = models.ForeignKey(
        AppUser,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_photos"
    )
    status = models.CharField(max_length=20,choices=STATUS_CHOICES,default="PENDING",)
    taken_at = models.DateTimeField(blank=True, null=True)
    sync_status = models.CharField(max_length=20)
    server_received_at = models.DateTimeField(blank=True, null=True)
    is_deleted = models.BooleanField()
    created_at = models.DateTimeField()
    replacement = models.ForeignKey('CpiReplacement', models.DO_NOTHING, db_column='replacement_id', blank=True, null=True)


    class Meta:
        managed = False
        db_table = 'cpi_photo'


class CpiReplacement(models.Model):

    STATUS_PENDING = "PENDING"
    STATUS_APPROVED = "APPROVED"
    STATUS_REJECTED = "REJECTED"
    STATUS_REVERTED = "REVERTED"
    STATUS_REPLACED_AGAIN = "REPLACED_AGAIN"

    REPLACEMENT_STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_REVERTED, "Original Item Restored"),
        (STATUS_REPLACED_AGAIN, "Replaced Again"),
    ]

    replacement_id = models.BigAutoField(primary_key=True)

    price = models.ForeignKey(
        "FactPrice",
        models.DO_NOTHING
    )

    old_collection_item = models.ForeignKey(
        CpiCollectionItem,
        models.DO_NOTHING,
        related_name="replacement_requests"
    )

    approved_collection_item = models.ForeignKey(
        CpiCollectionItem,
        models.DO_NOTHING,
        related_name="approved_replacement_records",
        blank=True,
        null=True
    )

    device = models.ForeignKey(
        AppDevice,
        models.DO_NOTHING,
        blank=True,
        null=True
    )

    local_uuid = models.UUIDField(
        unique=True,
        blank=True,
        null=True
    )

    new_name = models.TextField(blank=True, null=True)
    new_type = models.TextField(blank=True, null=True)
    new_size = models.TextField(blank=True, null=True)
    new_unit = models.TextField(blank=True, null=True)
    new_brand = models.TextField(blank=True, null=True)
    new_made_in = models.TextField(blank=True, null=True)

    new_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True
    )

    reason = models.TextField(blank=True, null=True)

    replacement_status = models.CharField(
        max_length=20,
        choices=REPLACEMENT_STATUS_CHOICES,
        default=STATUS_PENDING
    )

    sync_status = models.CharField(max_length=20)

    created_on_device = models.BooleanField()
    server_received_at = models.DateTimeField(blank=True, null=True)
    last_modified_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    created_at = models.DateTimeField()

    new_brand_fk = models.ForeignKey(
        "DimBrand",
        models.DO_NOTHING,
        db_column="new_brand_id",
        blank=True,
        null=True,
        related_name="replacement_new_brand_set"
    )

    new_made_in_fk = models.ForeignKey(
        "DimCountry",
        models.DO_NOTHING,
        db_column="new_made_in_id",
        blank=True,
        null=True,
        related_name="replacement_new_country_set"
    )

    new_coicop_code = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )

    rejection_comment = models.TextField(
        blank=True,
        null=True
    )

    reviewed_at = models.DateTimeField(
        blank=True,
        null=True
    )

    reviewed_by = models.ForeignKey(
        "AppUser",
        models.DO_NOTHING,
        db_column="reviewed_by_id",
        blank=True,
        null=True,
        related_name="reviewed_replacements"
    )

    class Meta:
        managed = False
        db_table = "cpi_replacement"

    def __str__(self):
        return (
            f"Replacement {self.replacement_id} - "
            f"{self.old_collection_item} - "
            f"{self.replacement_status}"
        )


class CpiRound(models.Model):

    ROUND_STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('PREPARED', 'Prepared'),
        ('OPEN', 'Open'),
        ('CLOSED', 'Closed'),
        ('LOCKED', 'Locked'),
    ]

    round_id = models.BigAutoField(primary_key=True)
    survey_year = models.IntegerField()
    survey_month = models.IntegerField()

    methodology = models.ForeignKey(
        'CpiMethodology',
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name='rounds',
        db_column='methodology_id'
    )

    round_status = models.CharField(
        max_length=20,
        choices=ROUND_STATUS_CHOICES
    )

    collection_start_date = models.DateField(blank=True, null=True)
    collection_end_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField()

    def __str__(self):
        return f"{self.survey_year}-{self.survey_month:02d} ({self.round_status})"

    class Meta:
        managed = False
        db_table = 'cpi_round'
        unique_together = (('survey_year', 'survey_month'),)


class CpiVisit(models.Model):
    visit_id = models.BigAutoField(primary_key=True)
    round = models.ForeignKey(CpiRound, models.DO_NOTHING)
    outlet = models.ForeignKey('DimOutlet', models.DO_NOTHING, null=True, blank=True)
    collector_user = models.ForeignKey(AppUser, models.DO_NOTHING, null=True, blank=True)
    device = models.ForeignKey(AppDevice, models.DO_NOTHING, blank=True, null=True)
    local_uuid = models.UUIDField(unique=True, blank=True, null=True)
    start_time = models.DateTimeField(blank=True, null=True)
    end_time = models.DateTimeField(blank=True, null=True)
    incomplete_reason = models.TextField(blank=True, null=True)
    gps_lat = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    gps_lon = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    gps_accuracy_m = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    gps_distance_meters = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    gps_within_range = models.BooleanField(blank=True, null=True)
    gps_recorded_at = models.DateTimeField(blank=True, null=True)
    visit_status = models.CharField(max_length=20)
    sync_status = models.CharField(max_length=20)
    created_on_device = models.BooleanField()
    server_received_at = models.DateTimeField(blank=True, null=True)
    last_modified_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField()
    review_status = models.CharField(max_length=30, default="PENDING_REVIEW")
    reviewed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'cpi_visit'


class DimAtoll(models.Model):
    atoll_id = models.BigAutoField(primary_key=True)
    atoll_code = models.CharField(unique=True, max_length=20, blank=True, null=True)
    atoll_name = models.TextField()
    region = models.ForeignKey('DimRegion', models.DO_NOTHING, blank=True, null=True)
    sort_order = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'dim_atoll'


class DimBrand(models.Model):
    brand_id = models.BigAutoField(primary_key=True)
    brand_name = models.TextField(unique=True)

    def __str__(self):
        return self.brand_name

    class Meta:
        managed = False
        db_table = 'dim_brand'


class DimCountry(models.Model):
    country_id = models.BigAutoField(primary_key=True)
    iso_code = models.CharField(unique=True, max_length=3, blank=True, null=True)
    country_name = models.TextField(unique=True)
    def __str__(self):
        return self.country_name

    class Meta:
        managed = False
        db_table = 'dim_country'


class DimIsland(models.Model):
    island_id = models.BigAutoField(primary_key=True)
    island_code = models.CharField(unique=True, max_length=20, blank=True, null=True)
    island_name = models.TextField()
    atoll = models.ForeignKey(DimAtoll, models.DO_NOTHING, blank=True, null=True)
    def __str__(self):
        return self.island_name

    class Meta:
        managed = False
        db_table = 'dim_island'


class DimOutlet(models.Model):
    outlet_id = models.BigAutoField(primary_key=True)
    outlet_code = models.CharField(unique=True, max_length=50, blank=True, null=True)
    outlet_name = models.TextField()
    outlet_type = models.ForeignKey('DimOutletType',models.DO_NOTHING,db_column='outlet_type_id',blank=True,null=True)
    
    address_text = models.TextField(blank=True, null=True)
    contact_no = models.TextField(blank=True, null=True)
    contact_person = models.TextField(blank=True, null=True)
    excel_sheet_name = models.CharField(max_length=150, blank=True, null=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    allowed_radius_meters = models.PositiveIntegerField(default=100)
    is_active = models.BooleanField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    island = models.ForeignKey(DimIsland, models.DO_NOTHING)
    def __str__(self):
        return self.outlet_name

    class Meta:
        managed = False
        db_table = 'dim_outlet'



class DimRegion(models.Model):
    region_id = models.BigAutoField(primary_key=True)
    region_code = models.CharField(unique=True, max_length=20, blank=True, null=True)
    region_name = models.TextField()
    def __str__(self):
        return self.region_name

    class Meta:
        managed = False
        db_table = 'dim_region'


class DimUnit(models.Model):
    unit_id = models.BigAutoField(primary_key=True)
    unit_code = models.CharField(unique=True, max_length=20, blank=True, null=True)
    unit_name = models.TextField()

    def save(self, *args, **kwargs):

        super().save(*args, **kwargs)

        if not self.unit_code and self.unit_id:

            self.unit_code = f"UNT{self.unit_id:04d}"

            super().save(update_fields=["unit_code"])

   
    def __str__(self):
        return self.unit_name

    class Meta:
        managed = False
        db_table = 'dim_unit'


class FactPrice(models.Model):
    price_id = models.BigAutoField(primary_key=True)
    visit = models.ForeignKey(CpiVisit, models.DO_NOTHING)
    collection_item = models.ForeignKey(CpiCollectionItem, models.DO_NOTHING)
    device = models.ForeignKey(AppDevice, models.DO_NOTHING, blank=True, null=True)
    local_uuid = models.UUIDField(unique=True, blank=True, null=True)
    availability = models.CharField(max_length=30)
    observed_price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)

    last_month_price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    supervisor_comment = models.TextField(blank=True, null=True)
    review_status = models.CharField(max_length=30, default="PENDING")
    reviewed_at = models.DateTimeField(blank=True, null=True)
    is_outlier = models.BooleanField()
    outlier_level = models.CharField(max_length=10,default="NONE")
    quote_status = models.CharField(max_length=20)
    sync_status = models.CharField(max_length=20)
    created_on_device = models.BooleanField()
    server_received_at = models.DateTimeField(blank=True, null=True)
    last_modified_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    def __str__(self):
        return f"{self.collection_item} - {self.observed_price}"

    class Meta:
        managed = False
        db_table = 'fact_price'
        unique_together = (('visit', 'collection_item'),)


class SyncBatch(models.Model):
    sync_batch_id = models.BigAutoField(primary_key=True)
    device = models.ForeignKey(AppDevice, models.DO_NOTHING)
    user = models.ForeignKey(AppUser, models.DO_NOTHING, blank=True, null=True)
    sync_started_at = models.DateTimeField()
    sync_completed_at = models.DateTimeField(blank=True, null=True)
    sync_status = models.CharField(max_length=20)
    records_sent = models.IntegerField()
    records_accepted = models.IntegerField()
    records_rejected = models.IntegerField()
    error_message = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'sync_batch'


class SyncConflictLog(models.Model):
    conflict_id = models.BigAutoField(primary_key=True)
    table_name = models.TextField()
    record_id = models.BigIntegerField(blank=True, null=True)
    device = models.ForeignKey(AppDevice, models.DO_NOTHING, blank=True, null=True)
    conflict_type = models.CharField(max_length=30, blank=True, null=True)
    local_payload = models.JSONField(blank=True, null=True)
    server_payload = models.JSONField(blank=True, null=True)
    resolved_by = models.ForeignKey(AppUser, models.DO_NOTHING, db_column='resolved_by', blank=True, null=True)
    resolved_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'sync_conflict_log'

    
class CollectorAssignment(models.Model):
    assignment_id = models.BigAutoField(primary_key=True)

    round = models.ForeignKey(
        "CpiRound",
        on_delete=models.CASCADE,
        related_name="outlet_assignments",
        db_column="round_id",
        null=True,
        blank=True,
    )

    collector = models.ForeignKey(
        AppUser,
        on_delete=models.CASCADE,
        related_name="assignments",
    )

    outlet = models.ForeignKey(
        DimOutlet,
        on_delete=models.CASCADE,
        related_name="collector_assignments",
    )

    is_active = models.BooleanField(default=True)
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "collector_assignment"

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "round",
                    "outlet",
                ],
                condition=models.Q(is_active=True),
                name="uq_collector_assignment_active_round_outlet",
            )
        ]
    


class CollectorItemAssignment(models.Model):
    assignment_id = models.BigAutoField(primary_key=True)

    round = models.ForeignKey(
        "CpiRound",
        models.DO_NOTHING,
        db_column="round_id",
    )

    collector = models.ForeignKey(
        AppUser,
        models.DO_NOTHING,
        db_column="collector_id",
    )

    collection_item = models.ForeignKey(
        CpiCollectionItem,
        models.DO_NOTHING,
        db_column="collection_item_id",
    )

    is_active = models.BooleanField()
    assigned_at = models.DateTimeField(auto_now_add=True)
    item_split = models.CharField(
        max_length=20,
        blank=True,
        null=True,
    )

    class Meta:
        managed = False
        db_table = "collector_item_assignment"

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "round",
                    "collection_item",
                ],
                condition=models.Q(is_active=True),
                name="uq_collector_item_assignment_active_round_item",
            )
        ]


class DimOutletType(models.Model):
    outlet_type_id = models.BigAutoField(primary_key=True)
    broad_type = models.TextField()
    outlet_type_name = models.TextField(unique=True)
    sort_order = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return self.outlet_type_name

    class Meta:
        managed = False
        db_table = 'dim_outlet_type'
    
class CollectorWorkloadSummary(models.Model):
    summary_id = models.BigIntegerField(primary_key=True)
    island_name = models.CharField(max_length=100)
    outlet_name = models.CharField(max_length=200)
    total_items = models.IntegerField()
    assignment_type = models.CharField(max_length=50)
    item_split = models.CharField(max_length=50)
    collector_name = models.CharField(max_length=150)
    assigned_items = models.IntegerField()
    is_active = models.BooleanField()
    assigned_date = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "collector_workload_summary"
        verbose_name = "Collector Workload Summary"
        verbose_name_plural = "Collector Workload Summary"

    def __str__(self):
        return f"{self.outlet_name} - {self.collector_name}"
    
class CpiMethodology(models.Model):
    methodology_id = models.BigAutoField(primary_key=True)

    methodology_code = models.CharField(max_length=20, unique=True)
    methodology_name = models.CharField(max_length=200)

    survey_name = models.CharField(max_length=100, blank=True, null=True)
    survey_period = models.CharField(max_length=30, blank=True, null=True)

    basket_name = models.CharField(max_length=150, blank=True, null=True)

    index_reference_period = models.CharField(max_length=50, blank=True, null=True)
    index_base = models.IntegerField(default=100)

    effective_from = models.DateField()
    effective_to = models.DateField(blank=True, null=True)

    methodology_status = models.CharField(max_length=20, default="DRAFT")

    remarks = models.TextField(blank=True, null=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "cpi_methodology"

    def __str__(self):
        return self.methodology_name
    
class CpiBasket(models.Model):
    basket_id = models.BigAutoField(primary_key=True)

    methodology = models.ForeignKey(
        CpiMethodology,
        on_delete=models.PROTECT,
        related_name="basket_items",
        db_column="methodology_id"
    )

    parent_basket = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="children",
        db_column="parent_basket_id"
    )

    basket_code = models.CharField(max_length=50)
    level = models.IntegerField(blank=True, null=True)
    coicop_2016 = models.CharField(max_length=50, blank=True, null=True)
    description = models.TextField()

    is_basket_item = models.BooleanField(default=False)
    display_order = models.IntegerField(blank=True, null=True)

    coicop_division_code = models.CharField(max_length=50, blank=True, null=True)
    coicop_division_name = models.TextField(blank=True, null=True)

    coicop_group_code = models.CharField(max_length=50, blank=True, null=True)
    coicop_group_name = models.TextField(blank=True, null=True)

    coicop_class_code = models.CharField(max_length=50, blank=True, null=True)
    coicop_class_name = models.TextField(blank=True, null=True)

    coicop_subclass_code = models.CharField(max_length=50, blank=True, null=True)
    coicop_subclass_name = models.TextField(blank=True, null=True)

    basket_item_code = models.CharField(max_length=50, blank=True, null=True)
    basket_item_name = models.TextField(blank=True, null=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "cpi_basket"
        unique_together = (("methodology", "basket_code"),)

    def __str__(self):
        return self.basket_item_name or self.description



class CpiWeight(models.Model):
    weight_id = models.BigAutoField(primary_key=True)

    methodology = models.ForeignKey(
        CpiMethodology,
        on_delete=models.PROTECT,
        related_name="weights"
    )

    basket = models.ForeignKey(
        CpiBasket,
        on_delete=models.PROTECT,
        related_name="weights"
    )

    weight_value = models.DecimalField(max_digits=18, decimal_places=8)
    weight_reference_period = models.CharField(max_length=50, blank=True, null=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cpi_weight"
        unique_together = ("methodology", "basket")

    def __str__(self):
        return f"{self.basket} - {self.weight_value}"