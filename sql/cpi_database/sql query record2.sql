CREATE OR REPLACE VIEW collector_workload_summary AS

-- Normal outlet assignments
SELECT
    ca.assignment_id AS summary_id,
    i.island_name,
    o.outlet_name,
    COUNT(ci.collection_item_id) AS total_items,
    'Outlet assignment' AS assignment_type,
    'All items' AS item_split,
    u.full_name AS collector_name,
    COUNT(ci.collection_item_id) AS assigned_items,
    ca.is_active AS is_active,
    ca.assigned_at AS assigned_date

FROM collector_assignment ca
JOIN app_user u ON ca.collector_id = u.user_id
JOIN dim_outlet o ON ca.outlet_id = o.outlet_id
JOIN dim_island i ON o.island_id = i.island_id
LEFT JOIN cpi_collection_item ci 
    ON ci.outlet_id = o.outlet_id
    AND ci.is_active = TRUE

GROUP BY
    ca.assignment_id,
    i.island_name,
    o.outlet_name,
    u.full_name,
    ca.is_active,
    ca.assigned_at

UNION ALL

-- Item assignment aggregated by outlet and collector
SELECT
    MIN(cia.assignment_id) AS summary_id,
    i.island_name,
    o.outlet_name,
    total.total_items,
    'Item assignment' AS assignment_type,
    'Assigned split' AS item_split,
    u.full_name AS collector_name,
    COUNT(cia.collection_item_id) AS assigned_items,
    BOOL_OR(cia.is_active) AS is_active,
    MIN(cia.assigned_at) AS assigned_date

FROM collector_item_assignment cia
JOIN app_user u ON cia.collector_id = u.user_id
JOIN cpi_collection_item ci ON cia.collection_item_id = ci.collection_item_id
JOIN dim_outlet o ON ci.outlet_id = o.outlet_id
JOIN dim_island i ON o.island_id = i.island_id
JOIN (
    SELECT
        outlet_id,
        COUNT(collection_item_id) AS total_items
    FROM cpi_collection_item
    WHERE is_active = TRUE
    GROUP BY outlet_id
) total ON total.outlet_id = o.outlet_id

GROUP BY
    i.island_name,
    o.outlet_name,
    total.total_items,
    u.full_name;




ALTER TABLE collector_item_assignment
ADD COLUMN item_split VARCHAR(20);



SELECT * from cpi_visit







	