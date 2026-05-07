-- 1. Clear old staging data
truncate table staging_country;

-- 2. After this, import your Excel/CSV into staging_country
-- staging_country should have:
-- iso_code
-- country_name

-- 3. Insert clean country list into dim_country
insert into dim_country (iso_code, country_name)
select distinct
    trim(iso_code),
    trim(country_name)
from staging_country
where country_name is not null
on conflict (country_name) do nothing;

-- 4. Check result
select *
from dim_country
order by country_name;


COPY staging_country(iso_code, country_name)
FROM 'F:/CPI_CapiApplication/cpi/country list.csv'
DELIMITER ','
CSV HEADER;


SELECT * FROM staging_country;


INSERT INTO dim_country (iso_code, country_name)
SELECT DISTINCT
    trim(iso_code),
    trim(country_name)
FROM staging_country
WHERE country_name IS NOT NULL
ON CONFLICT (country_name) DO NOTHING;


select *
from staging_country
limit 10;

ALTER TABLE dim_country
ALTER COLUMN iso_code TYPE VARCHAR(10);

INSERT INTO dim_country (iso_code, country_name)
SELECT DISTINCT
    trim(iso_code),
    trim(country_name)
FROM staging_country
WHERE country_name IS NOT NULL
ON CONFLICT (country_name) DO NOTHING;


SELECT * FROM dim_country ORDER BY country_name;


TRUNCATE TABLE dim_country RESTART IDENTITY;

TRUNCATE TABLE cpi_collection_item, dim_country RESTART IDENTITY CASCADE;

INSERT INTO dim_country (iso_code, country_name)
SELECT DISTINCT
    trim(iso_code),
    trim(country_name)
FROM staging_country
WHERE country_name IS NOT NULL
ORDER BY trim(country_name);

SELECT *
FROM dim_country
ORDER BY country_id;

DROP TABLE staging_country;


alter table cpi_collection_item
add column material text;

alter table cpi_collection_item
add column display_description text;

alter table cpi_collection_item
add column last_price numeric(12,2);

alter table cpi_collection_item
add column last_price_month varchar(20);

select
    ci.collection_item_id,
    o.outlet_name,
    i.item_name,
    ci.spec_type,
    ci.size_value,
    u.unit_name,
    ci.material,
    b.brand_name,
    c.country_name,
    ci.last_price_month,
    ci.last_price
from cpi_collection_item ci
join dim_outlet o on ci.outlet_id = o.outlet_id
join dim_item i on ci.item_id = i.item_id
left join dim_unit u on ci.unit_id = u.unit_id
left join dim_brand b on ci.brand_id = b.brand_id
left join dim_country c on ci.country_id = c.country_id
where ci.outlet_id = 1
and ci.is_active = true
order by i.item_name;


