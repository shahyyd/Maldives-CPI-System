---maldives_cpi_database_schema_final.sql

-- ============================================================
-- MALDIVES CPI PRICE COLLECTION DATABASE
-- Final PostgreSQL Schema
-- Purpose: Android offline-first CPI price collection system
-- ============================================================


-- ============================================================
-- 1. USER AND DEVICE TABLES
-- ============================================================

create table app_user (
    user_id        bigserial primary key,
    username       varchar(100) not null unique,
    full_name      text not null,
    role_code      varchar(30) not null, -- admin, supervisor, collector
    phone_number   varchar(30),
    is_active      boolean not null default true,
    created_at     timestamptz not null default now()
);

create table app_device (
    device_id         bigserial primary key,
    device_uuid       uuid not null unique,
    device_name       text,
    assigned_user_id  bigint references app_user(user_id),
    is_active         boolean not null default true,
    last_sync_at      timestamptz,
    created_at        timestamptz not null default now()
);


-- ============================================================
-- 2. GEOGRAPHY TABLES
-- Region → Atoll → Island → Outlet
-- ============================================================

create table dim_region (
    region_id     bigserial primary key,
    region_code   varchar(20) not null unique,
    region_name   text not null
);

create table dim_atoll (
    atoll_id      bigserial primary key,
    atoll_code    varchar(20) not null unique,
    atoll_name    text not null,
    region_id     bigint not null references dim_region(region_id)
);

create table dim_island (
    island_id     bigserial primary key,
    island_code   varchar(20) not null unique,
    island_name   text not null,
    atoll_id      bigint not null references dim_atoll(atoll_id)
);

create table dim_outlet (
    outlet_id     bigserial primary key,
    outlet_code   varchar(50) unique,
    outlet_name   text not null,
    island_id     bigint not null references dim_island(island_id),
    address_text  text,
    latitude      numeric(10,7),
    longitude     numeric(10,7),
    is_active     boolean not null default true,
    created_at    timestamptz not null default now(),
    updated_at    timestamptz not null default now()
);


-- ============================================================
-- 3. PRODUCT / ITEM REFERENCE TABLES
-- ============================================================

create table dim_item (
    item_id       bigserial primary key,
    item_code     varchar(50) unique,
    item_name     text not null,
    coicop_code   varchar(20),
    item_group    varchar(30), -- food, non-food, service
    is_active     boolean not null default true,
    created_at    timestamptz not null default now(),
    updated_at    timestamptz not null default now()
);

create table dim_unit (
    unit_id     bigserial primary key,
    unit_code   varchar(20) unique,
    unit_name   text not null
);

create table dim_brand (
    brand_id     bigserial primary key,
    brand_name   text not null unique
);

create table dim_country (
    country_id     bigserial primary key,
    iso_code       varchar(3) unique,
    country_name   text not null unique
);


-- ============================================================
-- 4. CPI ROUND
-- One row per CPI collection month
-- ============================================================

create table cpi_round (
    round_id               bigserial primary key,
    survey_year            integer not null,
    survey_month           integer not null check (survey_month between 1 and 12),
    round_status           varchar(20) not null default 'OPEN',
    collection_start_date  date,
    collection_end_date    date,
    created_at             timestamptz not null default now(),
    unique (survey_year, survey_month)
);


-- ============================================================
-- 5. CPI COLLECTION ITEM
-- This replaces Survey Solutions roster/sample-spec logic.
-- It stores the active item/specification collected in each shop.
-- ============================================================

create table cpi_collection_item (
    collection_item_id  bigserial primary key,
    outlet_id           bigint not null references dim_outlet(outlet_id),
    item_id             bigint not null references dim_item(item_id),

    -- item specification details
    spec_name           text,
    spec_type           text,
    size_value          numeric(12,3),
    unit_id             bigint references dim_unit(unit_id),
    brand_id            bigint references dim_brand(brand_id),
    country_id          bigint references dim_country(country_id),
    other_spec          text,
    product_code        text,

    -- lifecycle management
    is_active           boolean not null default true,
    valid_from          date not null default current_date,
    valid_to            date,
    item_status         varchar(20) not null default 'ACTIVE',

    constraint chk_collection_item_status
        check (item_status in ('ACTIVE', 'INACTIVE', 'REPLACED', 'DISCONTINUED')),

    constraint unique_collection_item
        unique (outlet_id, item_id, spec_name, size_value)
);


-- ============================================================
-- 6. VISIT TABLE
-- Stores each outlet visit / price collection session.
-- Works offline and syncs later.
-- ============================================================

create table cpi_visit (
    visit_id            bigserial primary key,
    round_id            bigint not null references cpi_round(round_id),
    outlet_id           bigint not null references dim_outlet(outlet_id),
    collector_user_id   bigint not null references app_user(user_id),
    device_id           bigint references app_device(device_id),

    local_uuid          uuid unique, -- generated on tablet for offline sync
    start_time          timestamptz,
    end_time            timestamptz,

    gps_lat             numeric(10,7),
    gps_lon             numeric(10,7),
    gps_accuracy_m      numeric(8,2),

    visit_status        varchar(20) not null default 'COMPLETED',
    sync_status         varchar(20) not null default 'PENDING',

    created_on_device   boolean not null default true,
    server_received_at  timestamptz,
    last_modified_at    timestamptz not null default now(),
    is_deleted          boolean not null default false,

    remarks             text,
    created_at          timestamptz not null default now()
);


-- ============================================================
-- 7. FACT PRICE
-- Main CPI price observation table.
-- One row = one price observation for one collection item in one visit.
-- ============================================================

create table fact_price (
    price_id            bigserial primary key,
    visit_id            bigint not null references cpi_visit(visit_id),
    collection_item_id  bigint not null references cpi_collection_item(collection_item_id),
    device_id           bigint references app_device(device_id),

    local_uuid          uuid unique,

    availability        varchar(30) not null,
    observed_price      numeric(12,2),
    last_month_price    numeric(12,2),

    deviation_reason    text,
    is_outlier          boolean not null default false,
    quote_status        varchar(20) not null default 'DRAFT',
    sync_status         varchar(20) not null default 'PENDING',

    created_on_device   boolean not null default true,
    server_received_at  timestamptz,
    last_modified_at    timestamptz not null default now(),
    is_deleted          boolean not null default false,

    created_at          timestamptz not null default now(),
    updated_at          timestamptz not null default now(),

    unique (visit_id, collection_item_id),

    constraint chk_price_availability
        check (availability in (
            'AVAILABLE',
            'TEMP_UNAVAILABLE',
            'SEASONAL_UNAVAILABLE',
            'PERMANENT_UNAVAILABLE',
            'COMPLETE_STOP'
        )),

    constraint chk_observed_price_positive
        check (observed_price is null or observed_price > 0)
);


-- ============================================================
-- 8. REPLACEMENT TABLE
-- Used when an item is discontinued or replaced in the shop.
-- ============================================================

create table cpi_replacement (
    replacement_id              bigserial primary key,
    price_id                    bigint not null references fact_price(price_id),
    old_collection_item_id      bigint not null references cpi_collection_item(collection_item_id),

    new_name                    text,
    new_type                    text,
    new_size                    text,
    new_unit                    text,
    new_brand                   text,
    new_made_in                 text,
    new_price                   numeric(12,2),

    reason                      text,
    replacement_status          varchar(20) not null default 'PENDING',
    approved_collection_item_id bigint references cpi_collection_item(collection_item_id),

    device_id                   bigint references app_device(device_id),
    local_uuid                  uuid unique,

    sync_status                 varchar(20) not null default 'PENDING',
    created_on_device           boolean not null default true,
    server_received_at          timestamptz,
    last_modified_at            timestamptz not null default now(),
    is_deleted                  boolean not null default false,
    created_at                  timestamptz not null default now(),

    constraint chk_replacement_status
        check (replacement_status in ('PENDING', 'APPROVED', 'REJECTED'))
);


-- ============================================================
-- 9. PHOTO TABLE
-- Stores metadata for item/outlet photos.
-- Actual images should be stored in file storage/object storage.
-- ============================================================

create table cpi_photo (
    photo_id            bigserial primary key,
    price_id            bigint references fact_price(price_id),
    visit_id            bigint references cpi_visit(visit_id),
    device_id           bigint references app_device(device_id),

    local_uuid          uuid unique,
    file_name           text not null,
    file_path           text not null,
    mime_type           text,
    file_hash           text,
    photo_type          varchar(30),

    taken_at            timestamptz,
    sync_status         varchar(20) not null default 'PENDING',
    server_received_at  timestamptz,
    is_deleted          boolean not null default false,
    created_at          timestamptz not null default now()
);


-- ============================================================
-- 10. AUDIT LOG
-- Tracks important insert/update/delete actions.
-- ============================================================

create table cpi_audit_log (
    audit_id      bigserial primary key,
    entity_name   varchar(100) not null,
    entity_id     bigint not null,
    action_code   varchar(30) not null, -- INSERT, UPDATE, DELETE, APPROVE
    changed_by    bigint references app_user(user_id),
    changed_at    timestamptz not null default now(),
    old_value     jsonb,
    new_value     jsonb
);


-- ============================================================
-- 11. SYNC TABLES
-- Supports offline-first Android application.
-- ============================================================

create table sync_batch (
    sync_batch_id      bigserial primary key,
    device_id          bigint not null references app_device(device_id),
    user_id            bigint references app_user(user_id),

    sync_started_at    timestamptz not null default now(),
    sync_completed_at  timestamptz,
    sync_status        varchar(20) not null default 'PENDING',

    records_sent       integer not null default 0,
    records_accepted   integer not null default 0,
    records_rejected   integer not null default 0,

    error_message      text
);

create table sync_conflict_log (
    conflict_id      bigserial primary key,
    table_name       text not null,
    record_id        bigint,
    device_id        bigint references app_device(device_id),

    conflict_type    varchar(30),
    local_payload    jsonb,
    server_payload   jsonb,

    resolved_by      bigint references app_user(user_id),
    resolved_at      timestamptz,
    created_at       timestamptz not null default now()
);


-- ============================================================
-- 12. INDEXES FOR PERFORMANCE
-- ============================================================

create index idx_atoll_region
    on dim_atoll(region_id);

create index idx_island_atoll
    on dim_island(atoll_id);

create index idx_outlet_island
    on dim_outlet(island_id);

create index idx_collection_item_outlet
    on cpi_collection_item(outlet_id);

create index idx_collection_item_item
    on cpi_collection_item(item_id);

create index idx_visit_round
    on cpi_visit(round_id);

create index idx_visit_outlet
    on cpi_visit(outlet_id);

create index idx_visit_collector
    on cpi_visit(collector_user_id);

create index idx_price_visit
    on fact_price(visit_id);

create index idx_price_collection_item
    on fact_price(collection_item_id);

create index idx_price_status
    on fact_price(availability, quote_status);

create index idx_sync_batch_device
    on sync_batch(device_id, sync_started_at);


-- ============================================================
-- END OF SCHEMA
-- ============================================================