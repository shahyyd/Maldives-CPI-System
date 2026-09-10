-- View: public.collector_workload_summary

-- DROP VIEW public.collector_workload_summary;

CREATE OR REPLACE VIEW public.collector_workload_summary
 AS
 SELECT ca.assignment_id AS summary_id,
    i.island_name,
    o.outlet_name,
    count(ci.collection_item_id) AS total_items,
    'Outlet assignment'::text AS assignment_type,
    'All items'::text AS item_split,
    u.full_name AS collector_name,
    count(ci.collection_item_id) AS assigned_items,
    ca.is_active,
    ca.assigned_at AS assigned_date
   FROM collector_assignment ca
     JOIN app_user u ON ca.collector_id = u.user_id
     JOIN dim_outlet o ON ca.outlet_id = o.outlet_id
     JOIN dim_island i ON o.island_id = i.island_id
     LEFT JOIN cpi_collection_item ci ON ci.outlet_id = o.outlet_id AND ci.is_active = true
  GROUP BY ca.assignment_id, i.island_name, o.outlet_name, u.full_name, ca.is_active, ca.assigned_at
UNION ALL
 SELECT min(cia.assignment_id) AS summary_id,
    i.island_name,
    o.outlet_name,
    total.total_items,
    'Item assignment'::text AS assignment_type,
    min(cia.item_split::text) AS item_split,
    u.full_name AS collector_name,
    count(cia.collection_item_id) AS assigned_items,
    bool_or(cia.is_active) AS is_active,
    min(cia.assigned_at) AS assigned_date
   FROM collector_item_assignment cia
     JOIN app_user u ON cia.collector_id = u.user_id
     JOIN cpi_collection_item ci ON cia.collection_item_id = ci.collection_item_id
     JOIN dim_outlet o ON ci.outlet_id = o.outlet_id
     JOIN dim_island i ON o.island_id = i.island_id
     JOIN ( SELECT cpi_collection_item.outlet_id,
            count(cpi_collection_item.collection_item_id) AS total_items
           FROM cpi_collection_item
          WHERE cpi_collection_item.is_active = true
          GROUP BY cpi_collection_item.outlet_id) total ON total.outlet_id = o.outlet_id
  GROUP BY i.island_name, o.outlet_name, total.total_items, u.full_name;

ALTER TABLE public.collector_workload_summary
    OWNER TO postgres;

