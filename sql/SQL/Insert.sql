INSERT INTO dim_outlet (
    outlet_code,
    outlet_name,
    is_active,
    created_at,
    updated_at,
    island_id
)
SELECT
    v.outlet_code,
    v.outlet_name,
    TRUE,
    NOW(),
    NOW(),
    i.island_id
FROM (
    VALUES
    ('0091','Afaas Mart','442'),
    ('2301','Agora','442'),
    ('0121','Binma','442'),
    ('0151','Choice mart','442'),
    ('0171','Daily Baazaaru','591'),
    ('0201','Day night mart','442'),
    ('0211','Eureka Five Eleven','591'),
    ('0061','Fantastic','442'),
    ('0141','Goanbili','268'),
    ('0101','Haitheri mart','591'),
    ('0191','Hazash Mart','591'),
    ('0161','Ihusaan','442'),
    ('0011','JJ Mart','442'),
    ('0041','MHA Mart','442'),
    ('0181','Nide Mart','442'),
    ('0241','Olive Tree','591'),
    ('0131','On The Way','442'),
    ('0221','Red Wave Mega Mall','591'),
    ('0021','Red wave Plaza','442'),
    ('0051','STO','442'),
    ('0081','Shop And Save','442'),
    ('0231','Sifco','442'),
    ('0031','Sosun Plaza','442'),
    ('0071','VB Mart','442'),
    ('0111','Villa Mart','442')
) AS v(outlet_code, outlet_name, island_code)
JOIN dim_island i
    ON i.island_code = v.island_code;


select * from dim_outlet;

SELECT COUNT(*) FROM cpi_collection_item;
SELECT COUNT(*) FROM cpi_visit;
SELECT COUNT(*) FROM fact_price;

DELETE FROM dim_outlet;


SELECT setval('dim_outlet_outlet_id_seq', 1, false);

SELECT outlet_id, outlet_name
FROM dim_outlet;



create table dim_outlet_type (
    outlet_type_id bigserial primary key,
    broad_type varchar(20) not null,
    outlet_type_name text not null unique
);

insert into dim_outlet_type (broad_type, outlet_type_name)
values
('Food', 'fish market weekly collection form'),
('Food', 'FOOD AND GENERAL PRODUCTS'),
('Nonfood', 'Educational institutes & tution class'),
('Nonfood', 'medical clinics- MEDICAL CENTRES AND PHARMACIES'),
('Nonfood', 'Bookshop & printers'),
('Nonfood', 'Garments'),
('Nonfood', 'HARDWARE'),
('Food', 'RESTAURANTS & SHORT EATS'),
('Nonfood', 'Electronics & Mobile'),
('Nonfood', 'TRANSPORT'),
('Nonfood', 'Clothing'),
('Nonfood', 'HAIRDRESSING SALOONS'),
('Nonfood', 'FOOTWEAR'),
('Nonfood', 'OTHER SERVICES'),
('Nonfood', 'FURNITURE'),
('Nonfood', 'Pharmacy- MEDICAL CENTRES AND PHARMACIES'),
('Nonfood', 'HOUSEHOLD STUFFS');

alter table dim_outlet
add column outlet_type_id bigint references dim_outlet_type(outlet_type_id);


ALTER TABLE cpi_collection_item
ADD CONSTRAINT unique_outlet_item UNIQUE (outlet_id, item_id, brand_id, size_value);

ALTER TABLE cpi_collection_item
ADD COLUMN display_name text;


