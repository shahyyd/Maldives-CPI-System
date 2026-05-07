# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


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


class AppUser(models.Model):
    user_id = models.BigAutoField(primary_key=True)
    username = models.CharField(unique=True, max_length=100)
    full_name = models.TextField()
    role_code = models.CharField(max_length=30)
    phone_number = models.CharField(max_length=30, blank=True, null=True)
    is_active = models.BooleanField()
    created_at = models.DateTimeField()

    def __str__(self):
        return f"{self.full_name} ({self.role_code})"

    class Meta:
        managed = False
        db_table = 'app_user'


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
    outlet = models.ForeignKey('DimOutlet', models.DO_NOTHING)
    item = models.ForeignKey('DimItem', models.DO_NOTHING)
    spec_name = models.TextField(blank=True, null=True)
    spec_type = models.TextField(blank=True, null=True)
    size_value = models.DecimalField(max_digits=12, decimal_places=3, blank=True, null=True)
    unit = models.ForeignKey('DimUnit', models.DO_NOTHING, blank=True, null=True)
    brand = models.ForeignKey('DimBrand', models.DO_NOTHING, blank=True, null=True)
    country = models.ForeignKey('DimCountry', models.DO_NOTHING, blank=True, null=True)
    other_spec = models.TextField(blank=True, null=True)
    product_code = models.TextField(blank=True, null=True)
    is_active = models.BooleanField()
    valid_from = models.DateField()
    valid_to = models.DateField(blank=True, null=True)
    item_status = models.CharField(max_length=20)
    last_price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    last_price_month = models.CharField(max_length=20, blank=True, null=True)
    def __str__(self):
        return f"{self.outlet} - {self.item}"

    class Meta:
        managed = False
        db_table = 'cpi_collection_item'
        unique_together = (('outlet', 'item', 'spec_name', 'size_value'),)


class CpiPhoto(models.Model):
    photo_id = models.BigAutoField(primary_key=True)
    price = models.ForeignKey('FactPrice', models.DO_NOTHING, blank=True, null=True)
    visit = models.ForeignKey('CpiVisit', models.DO_NOTHING, blank=True, null=True)
    device = models.ForeignKey(AppDevice, models.DO_NOTHING, blank=True, null=True)
    local_uuid = models.UUIDField(unique=True, blank=True, null=True)
    file_name = models.TextField()
    file_path = models.TextField()
    mime_type = models.TextField(blank=True, null=True)
    file_hash = models.TextField(blank=True, null=True)
    photo_type = models.CharField(max_length=30, blank=True, null=True)
    taken_at = models.DateTimeField(blank=True, null=True)
    sync_status = models.CharField(max_length=20)
    server_received_at = models.DateTimeField(blank=True, null=True)
    is_deleted = models.BooleanField()
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'cpi_photo'


class CpiReplacement(models.Model):
    replacement_id = models.BigAutoField(primary_key=True)
    price = models.ForeignKey('FactPrice', models.DO_NOTHING)
    old_collection_item = models.ForeignKey(CpiCollectionItem, models.DO_NOTHING)
    device = models.ForeignKey(AppDevice, models.DO_NOTHING, blank=True, null=True)
    local_uuid = models.UUIDField(unique=True, blank=True, null=True)
    new_name = models.TextField(blank=True, null=True)
    new_type = models.TextField(blank=True, null=True)
    new_size = models.TextField(blank=True, null=True)
    new_unit = models.TextField(blank=True, null=True)
    new_brand = models.TextField(blank=True, null=True)
    new_made_in = models.TextField(blank=True, null=True)
    new_price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    reason = models.TextField(blank=True, null=True)
    replacement_status = models.CharField(max_length=20)
    approved_collection_item = models.ForeignKey(CpiCollectionItem, models.DO_NOTHING, related_name='cpireplacement_approved_collection_item_set', blank=True, null=True)
    sync_status = models.CharField(max_length=20)
    created_on_device = models.BooleanField()
    server_received_at = models.DateTimeField(blank=True, null=True)
    last_modified_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'cpi_replacement'


class CpiRound(models.Model):

    ROUND_STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('CLOSED', 'Closed'),
        ('LOCKED', 'Locked'),
    ]

    round_id = models.BigAutoField(primary_key=True)
    survey_year = models.IntegerField()
    survey_month = models.IntegerField()

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
    outlet = models.ForeignKey('DimOutlet', models.DO_NOTHING)
    collector_user = models.ForeignKey(AppUser, models.DO_NOTHING)
    device = models.ForeignKey(AppDevice, models.DO_NOTHING, blank=True, null=True)
    local_uuid = models.UUIDField(unique=True, blank=True, null=True)
    start_time = models.DateTimeField(blank=True, null=True)
    end_time = models.DateTimeField(blank=True, null=True)
    gps_lat = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    gps_lon = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    gps_accuracy_m = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    visit_status = models.CharField(max_length=20)
    sync_status = models.CharField(max_length=20)
    created_on_device = models.BooleanField()
    server_received_at = models.DateTimeField(blank=True, null=True)
    last_modified_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField()

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


class DimItem(models.Model):
    item_id = models.BigAutoField(primary_key=True)
    item_code = models.CharField(unique=True, max_length=50, blank=True, null=True)
    item_name = models.TextField()
    coicop_code = models.CharField(max_length=20, blank=True, null=True)
    item_group = models.CharField(max_length=30, blank=True, null=True)
    is_active = models.BooleanField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    def __str__(self):
        return self.item_name

    class Meta:
        managed = False
        db_table = 'dim_item'


class DimOutlet(models.Model):
    outlet_id = models.BigAutoField(primary_key=True)
    outlet_code = models.CharField(unique=True, max_length=50, blank=True, null=True)
    outlet_name = models.TextField()
    address_text = models.TextField(blank=True, null=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
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
    is_outlier = models.BooleanField()
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

    collector = models.ForeignKey(
        AppUser,
        on_delete=models.CASCADE,
        related_name="assignments"
    )

    outlet = models.ForeignKey(
        DimOutlet,
        on_delete=models.CASCADE,
        related_name="collector_assignments"
    )

    is_active = models.BooleanField(default=True)

    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "collector_assignment"
        unique_together = ("collector", "outlet")

    def __str__(self):
        return f"{self.collector} - {self.outlet}"