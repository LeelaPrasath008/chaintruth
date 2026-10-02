-- =============================================================================
-- ChainTruth: Synthetic Data Generation
-- =============================================================================
-- A single stored procedure that populates all 9 tables (6 RAW + 3 ONTOLOGY).
--
-- DATA VOLUME:
--   50 suppliers, 200 parts, 10 plants, 50 customers, 5000 orders, 5000 shipments
--
-- DESIGN FOR CONFLICTING OTIF:
--   The three OTIF dates are generated with intentional drift:
--
--   PROMISED_DELIVERY_DATE (ERP)
--     = ORDER_DATE + supplier's avg lead time + small buffer (3-7 days)
--     This is the tightest deadline — the ERP promise to the customer.
--
--   SUPPLIER_COMMITMENT_DATE (Supplier)
--     = ORDER_DATE + supplier's avg lead time + larger buffer (5-15 days)
--     Suppliers pad their commitments, so this is more generous.
--
--   CARRIER_ETA (Logistics)
--     = SHIP_DATE + transit time estimate (2-10 days based on region)
--     Set at ship-time, reflects carrier speed, not original promise.
--
--   DELIVERY_DATE (Actual)
--     = SHIP_DATE + actual transit (randomized around carrier estimate)
--     Low-reliability suppliers have higher variance → more late deliveries.
--
--   RESULT: A shipment can be:
--     - ON TIME by ERP but LATE by Logistics (ETA was optimistic)
--     - ON TIME by Supplier but LATE by ERP (supplier had more slack)
--     - ON TIME by all three (genuinely good delivery)
--     - LATE by all three (genuinely bad delivery)
--
--   This produces 3 different OTIF rates from the SAME underlying data,
--   which is the core "chain truth" problem the platform solves.
--
-- QUANTITY LOGIC (for Fill Rate):
--   ~70% of shipments ship the full ordered quantity.
--   ~20% ship 80-99% (minor shortfall).
--   ~10% ship 50-79% (significant shortfall).
--   This produces a realistic Fill Rate around 92-95%.
-- =============================================================================

USE DATABASE CHAINTRUTH_DB;
USE WAREHOUSE CHAINTRUTH_WH;

CREATE OR REPLACE PROCEDURE RAW.SP_GENERATE_SYNTHETIC_DATA()
RETURNS VARCHAR
LANGUAGE SQL
AS
$$
BEGIN

    -- =========================================================================
    -- SUPPLIERS (50)
    -- =========================================================================
    -- Reliability scores follow a realistic distribution: most suppliers are
    -- decent (0.7-0.95), a few are excellent (>0.95), and a few are poor (<0.7).
    -- LEAD_TIME_DAYS_AVG varies by region to simulate geographic distance.
    -- =========================================================================
    INSERT OVERWRITE INTO RAW.SUPPLIERS
    WITH supplier_base AS (
        SELECT
            'SUP-' || LPAD(SEQ4()::VARCHAR, 3, '0') AS SUPPLIER_ID,
            SEQ4() AS RN
        FROM TABLE(GENERATOR(ROWCOUNT => 50))
    ),
    supplier_attrs AS (
        SELECT
            SUPPLIER_ID,
            RN,
            CASE MOD(RN, 10)
                WHEN 0 THEN 'China'     WHEN 1 THEN 'Germany'   WHEN 2 THEN 'USA'
                WHEN 3 THEN 'Japan'     WHEN 4 THEN 'India'     WHEN 5 THEN 'Mexico'
                WHEN 6 THEN 'Brazil'    WHEN 7 THEN 'South Korea' WHEN 8 THEN 'Taiwan'
                WHEN 9 THEN 'Vietnam'
            END AS COUNTRY,
            CASE
                WHEN MOD(RN, 10) IN (0, 3, 7, 8, 9) THEN 'APAC'
                WHEN MOD(RN, 10) IN (1)              THEN 'EMEA'
                WHEN MOD(RN, 10) IN (2)              THEN 'NA'
                WHEN MOD(RN, 10) IN (4)              THEN 'APAC'
                WHEN MOD(RN, 10) IN (5, 6)           THEN 'LATAM'
            END AS REGION
        FROM supplier_base
    )
    SELECT
        SUPPLIER_ID,
        'Supplier ' || SUBSTRING(SUPPLIER_ID, 5) AS SUPPLIER_NAME,
        COUNTRY,
        REGION,
        -- Reliability: beta-like distribution skewed toward 0.75-0.95
        ROUND(GREATEST(0.3, LEAST(1.0,
            0.75 + (UNIFORM(-25::FLOAT, 25::FLOAT, RANDOM()) / 100.0)
        )), 2) AS RELIABILITY_SCORE,
        -- Lead time varies by region
        CASE REGION
            WHEN 'APAC'  THEN UNIFORM(12, 25, RANDOM())
            WHEN 'EMEA'  THEN UNIFORM(8, 18, RANDOM())
            WHEN 'NA'    THEN UNIFORM(5, 12, RANDOM())
            WHEN 'LATAM' THEN UNIFORM(10, 20, RANDOM())
        END AS LEAD_TIME_DAYS_AVG,
        CURRENT_TIMESTAMP() AS CREATED_AT,
        CURRENT_TIMESTAMP() AS UPDATED_AT
    FROM supplier_attrs;

    -- =========================================================================
    -- PARTS (200)
    -- =========================================================================
    -- Four categories with different cost profiles.
    -- CRITICALITY is assigned so ~20% are HIGH, ~50% MEDIUM, ~30% LOW.
    -- =========================================================================
    INSERT OVERWRITE INTO RAW.PARTS
    WITH part_base AS (
        SELECT
            'PRT-' || LPAD(SEQ4()::VARCHAR, 4, '0') AS PART_ID,
            SEQ4() AS RN
        FROM TABLE(GENERATOR(ROWCOUNT => 200))
    )
    SELECT
        PART_ID,
        CASE MOD(RN, 4)
            WHEN 0 THEN 'Sensor Module '
            WHEN 1 THEN 'Steel Bracket '
            WHEN 2 THEN 'Polymer Resin '
            WHEN 3 THEN 'Carton Assembly '
        END || SUBSTRING(PART_ID, 5) AS PART_NAME,
        CASE MOD(RN, 4)
            WHEN 0 THEN 'Electronics'
            WHEN 1 THEN 'Mechanical'
            WHEN 2 THEN 'Chemical'
            WHEN 3 THEN 'Packaging'
        END AS CATEGORY,
        CASE MOD(RN, 4)
            WHEN 0 THEN ROUND(UNIFORM(50.00::FLOAT, 500.00::FLOAT, RANDOM()), 2)
            WHEN 1 THEN ROUND(UNIFORM(10.00::FLOAT, 150.00::FLOAT, RANDOM()), 2)
            WHEN 2 THEN ROUND(UNIFORM(5.00::FLOAT, 80.00::FLOAT, RANDOM()), 2)
            WHEN 3 THEN ROUND(UNIFORM(1.00::FLOAT, 20.00::FLOAT, RANDOM()), 2)
        END AS UNIT_COST,
        ROUND(UNIFORM(0.1::FLOAT, 50.0::FLOAT, RANDOM()), 1) AS WEIGHT_KG,
        CASE
            WHEN MOD(RN, 5) = 0 THEN 'HIGH'
            WHEN MOD(RN, 5) IN (1, 2) THEN 'MEDIUM'
            ELSE 'LOW'
        END AS CRITICALITY,
        CURRENT_TIMESTAMP() AS CREATED_AT,
        CURRENT_TIMESTAMP() AS UPDATED_AT
    FROM part_base;

    -- =========================================================================
    -- PLANTS (10)
    -- =========================================================================
    -- Geographically distributed. Capacity varies to create utilization skew.
    -- =========================================================================
    INSERT OVERWRITE INTO RAW.PLANTS
    WITH plant_base AS (
        SELECT SEQ4() AS RN
        FROM TABLE(GENERATOR(ROWCOUNT => 10))
    )
    SELECT
        'PLT-' || LPAD(RN::VARCHAR, 2, '0') AS PLANT_ID,
        CASE RN
            WHEN 0 THEN 'Shanghai Hub'      WHEN 1 THEN 'Munich Center'
            WHEN 2 THEN 'Detroit Works'      WHEN 3 THEN 'Tokyo Precision'
            WHEN 4 THEN 'Chennai Forge'      WHEN 5 THEN 'Monterrey Plant'
            WHEN 6 THEN 'Sao Paulo Ops'      WHEN 7 THEN 'Seoul Tech'
            WHEN 8 THEN 'Taipei Micro'       WHEN 9 THEN 'Hanoi Assembly'
        END AS PLANT_NAME,
        CASE RN
            WHEN 0 THEN 'China'     WHEN 1 THEN 'Germany'   WHEN 2 THEN 'USA'
            WHEN 3 THEN 'Japan'     WHEN 4 THEN 'India'     WHEN 5 THEN 'Mexico'
            WHEN 6 THEN 'Brazil'    WHEN 7 THEN 'South Korea' WHEN 8 THEN 'Taiwan'
            WHEN 9 THEN 'Vietnam'
        END AS COUNTRY,
        CASE
            WHEN RN IN (0, 3, 7, 8, 9) THEN 'APAC'
            WHEN RN IN (1)              THEN 'EMEA'
            WHEN RN IN (2)              THEN 'NA'
            WHEN RN IN (4)              THEN 'APAC'
            WHEN RN IN (5, 6)           THEN 'LATAM'
        END AS REGION,
        CASE
            WHEN RN IN (0, 2) THEN UNIFORM(800, 1200, RANDOM())  -- large plants
            WHEN RN IN (3, 7) THEN UNIFORM(400, 700, RANDOM())   -- medium plants
            ELSE UNIFORM(150, 400, RANDOM())                       -- small plants
        END AS CAPACITY_UNITS_PER_DAY,
        CURRENT_TIMESTAMP() AS CREATED_AT,
        CURRENT_TIMESTAMP() AS UPDATED_AT
    FROM plant_base;

    -- =========================================================================
    -- CUSTOMERS (50)
    -- =========================================================================
    -- Three segments: Enterprise (~30%), SMB (~50%), Government (~20%).
    -- Enterprise customers have higher-value orders → more Revenue At Risk.
    -- =========================================================================
    INSERT OVERWRITE INTO RAW.CUSTOMERS
    WITH cust_base AS (
        SELECT
            'CUS-' || LPAD(SEQ4()::VARCHAR, 3, '0') AS CUSTOMER_ID,
            SEQ4() AS RN
        FROM TABLE(GENERATOR(ROWCOUNT => 50))
    )
    SELECT
        CUSTOMER_ID,
        'Customer ' || SUBSTRING(CUSTOMER_ID, 5) AS CUSTOMER_NAME,
        CASE
            WHEN MOD(RN, 10) < 3 THEN 'Enterprise'
            WHEN MOD(RN, 10) < 8 THEN 'SMB'
            ELSE 'Government'
        END AS SEGMENT,
        CASE MOD(RN, 8)
            WHEN 0 THEN 'USA'      WHEN 1 THEN 'Germany'  WHEN 2 THEN 'Japan'
            WHEN 3 THEN 'UK'       WHEN 4 THEN 'Canada'   WHEN 5 THEN 'Australia'
            WHEN 6 THEN 'France'   WHEN 7 THEN 'Singapore'
        END AS COUNTRY,
        CASE
            WHEN MOD(RN, 8) IN (0, 4)    THEN 'NA'
            WHEN MOD(RN, 8) IN (1, 3, 6) THEN 'EMEA'
            WHEN MOD(RN, 8) IN (2, 7)    THEN 'APAC'
            ELSE 'APAC'
        END AS REGION,
        CURRENT_TIMESTAMP() AS CREATED_AT,
        CURRENT_TIMESTAMP() AS UPDATED_AT
    FROM cust_base;

    -- =========================================================================
    -- ORDERS (5000)
    -- =========================================================================
    -- Spread across the last 12 months.
    -- Links: CUSTOMER_ID, PART_ID, SUPPLIER_ID, PLANT_ID (randomly assigned).
    --
    -- PROMISED_DELIVERY_DATE = ORDER_DATE + supplier avg lead time + 3..7 days buffer
    --   (ERP sets a tight deadline based on historical supplier performance)
    --
    -- SUPPLIER_COMMITMENT_DATE = ORDER_DATE + supplier avg lead time + 5..15 days
    --   (Suppliers pad their commitments — always more generous than ERP)
    --
    -- STATUS distribution: ~10% OPEN, ~15% SHIPPED, ~70% DELIVERED, ~5% CANCELLED
    -- =========================================================================
    INSERT OVERWRITE INTO RAW.ORDERS
    WITH order_base AS (
        SELECT
            'ORD-' || LPAD(SEQ4()::VARCHAR, 5, '0') AS ORDER_ID,
            SEQ4() AS RN
        FROM TABLE(GENERATOR(ROWCOUNT => 5000))
    ),
    order_refs AS (
        SELECT
            o.ORDER_ID,
            o.RN,
            -- randomly assign foreign keys
            'CUS-' || LPAD(UNIFORM(0, 49, RANDOM())::VARCHAR, 3, '0') AS CUSTOMER_ID,
            'PRT-' || LPAD(UNIFORM(0, 199, RANDOM())::VARCHAR, 4, '0') AS PART_ID,
            'SUP-' || LPAD(UNIFORM(0, 49, RANDOM())::VARCHAR, 3, '0') AS SUPPLIER_ID,
            'PLT-' || LPAD(UNIFORM(0, 9, RANDOM())::VARCHAR, 2, '0') AS PLANT_ID,
            -- order date spread across last 12 months
            DATEADD('day', -UNIFORM(0, 365, RANDOM()), CURRENT_DATE()) AS ORDER_DATE,
            -- single roll for status distribution (5% cancelled, 10% open, 15% shipped, 70% delivered)
            UNIFORM(0, 99, RANDOM()) AS STATUS_ROLL
        FROM order_base o
    ),
    order_with_supplier AS (
        SELECT
            r.*,
            COALESCE(s.LEAD_TIME_DAYS_AVG, 14) AS LT_AVG
        FROM order_refs r
        LEFT JOIN RAW.SUPPLIERS s ON r.SUPPLIER_ID = s.SUPPLIER_ID
    )
    SELECT
        ORDER_ID,
        CUSTOMER_ID,
        PART_ID,
        SUPPLIER_ID,
        PLANT_ID,
        ORDER_DATE,
        -- ERP promised date: lead time + tight buffer (3-7 days)
        DATEADD('day', LT_AVG + UNIFORM(3, 7, RANDOM()), ORDER_DATE)
            AS PROMISED_DELIVERY_DATE,
        -- Supplier commitment: lead time + generous buffer (5-15 days)
        DATEADD('day', LT_AVG + UNIFORM(5, 15, RANDOM()), ORDER_DATE)
            AS SUPPLIER_COMMITMENT_DATE,
        -- quantity: 1-500 units, skewed toward smaller orders
        GREATEST(1, ROUND(ABS(NORMAL(50, 80, RANDOM()))))::INTEGER AS QUANTITY_ORDERED,
        -- unit price: varies by part cost with markup
        ROUND(UNIFORM(10.00::FLOAT, 500.00::FLOAT, RANDOM()), 2) AS UNIT_PRICE,
        -- status distribution (uses single STATUS_ROLL from CTE)
        CASE
            WHEN STATUS_ROLL < 5  THEN 'CANCELLED'
            WHEN STATUS_ROLL < 15 THEN 'OPEN'
            WHEN STATUS_ROLL < 30 THEN 'SHIPPED'
            ELSE 'DELIVERED'
        END AS ORDER_STATUS,
        CURRENT_TIMESTAMP() AS CREATED_AT,
        CURRENT_TIMESTAMP() AS UPDATED_AT
    FROM order_with_supplier;

    -- =========================================================================
    -- SHIPMENTS (~5000)
    -- =========================================================================
    -- Two-phase generation to hit ~5000 shipments:
    --
    -- Phase 1: One PRIMARY shipment per SHIPPED or DELIVERED order (~4250).
    -- Phase 2: ~750 SPLIT shipments for a random subset of DELIVERED orders.
    --          Split shipments represent a second partial delivery — common when
    --          the first shipment was short (backorder fulfillment) or when large
    --          orders are deliberately split across multiple trucks/containers.
    --
    -- SHIP_DATE = ORDER_DATE + supplier lead time (± noise from reliability)
    --   Low-reliability suppliers ship later than committed.
    --
    -- CARRIER_ETA = SHIP_DATE + transit estimate (2-10 days by region)
    --   Logistics sets this at ship-time. It's often optimistic.
    --
    -- DELIVERY_DATE (for DELIVERED orders):
    --   = SHIP_DATE + actual transit days
    --   Actual transit = carrier estimate + noise (reliability-driven)
    --   Low-reliability suppliers → higher noise → more late deliveries.
    --
    -- QUANTITY_SHIPPED (primary):
    --   ~70% ship full quantity, ~20% ship 80-99%, ~10% ship 50-79%
    --
    -- QUANTITY_SHIPPED (split):
    --   Small follow-up quantity: 10-30% of original order.
    -- =========================================================================
    INSERT OVERWRITE INTO RAW.SHIPMENTS
    WITH eligible_orders AS (
        SELECT
            o.ORDER_ID,
            o.ORDER_DATE,
            o.QUANTITY_ORDERED,
            o.ORDER_STATUS,
            o.SUPPLIER_ID,
            o.PLANT_ID,
            COALESCE(s.RELIABILITY_SCORE, 0.75) AS REL_SCORE,
            COALESCE(s.LEAD_TIME_DAYS_AVG, 14) AS LT_AVG,
            COALESCE(p.REGION, 'APAC') AS PLANT_REGION
        FROM RAW.ORDERS o
        LEFT JOIN RAW.SUPPLIERS s ON o.SUPPLIER_ID = s.SUPPLIER_ID
        LEFT JOIN RAW.PLANTS p ON o.PLANT_ID = p.PLANT_ID
        WHERE o.ORDER_STATUS IN ('SHIPPED', 'DELIVERED')
    ),
    -- Phase 1: primary shipments (one per eligible order)
    primary_shipments AS (
        SELECT
            ORDER_ID,
            ORDER_DATE,
            QUANTITY_ORDERED,
            ORDER_STATUS,
            REL_SCORE,
            LT_AVG,
            PLANT_REGION,
            DATEADD('day',
                LT_AVG + ROUND((1.0 - REL_SCORE) * UNIFORM(0, 10, RANDOM()))::INTEGER,
                ORDER_DATE
            ) AS SHIP_DATE,
            CASE PLANT_REGION
                WHEN 'APAC'  THEN UNIFORM(5, 12, RANDOM())
                WHEN 'EMEA'  THEN UNIFORM(3, 8, RANDOM())
                WHEN 'NA'    THEN UNIFORM(2, 6, RANDOM())
                WHEN 'LATAM' THEN UNIFORM(4, 10, RANDOM())
            END AS TRANSIT_ESTIMATE,
            CASE PLANT_REGION
                WHEN 'APAC'  THEN UNIFORM(5, 12, RANDOM())
                WHEN 'EMEA'  THEN UNIFORM(3, 8, RANDOM())
                WHEN 'NA'    THEN UNIFORM(2, 6, RANDOM())
                WHEN 'LATAM' THEN UNIFORM(4, 10, RANDOM())
            END + ROUND((1.0 - REL_SCORE) * UNIFORM(-2, 8, RANDOM()))::INTEGER
                AS ACTUAL_TRANSIT,
            UNIFORM(0, 99, RANDOM()) AS FILL_ROLL,
            'PRIMARY' AS SHIPMENT_TYPE
        FROM eligible_orders
    ),
    -- Phase 2: split shipments for ~750 random DELIVERED orders
    -- Pick DELIVERED orders and assign a random rank; take top ~750
    split_candidates AS (
        SELECT
            ORDER_ID,
            ORDER_DATE,
            QUANTITY_ORDERED,
            ORDER_STATUS,
            REL_SCORE,
            LT_AVG,
            PLANT_REGION,
            ROW_NUMBER() OVER (ORDER BY RANDOM()) AS SPLIT_RANK
        FROM eligible_orders
        WHERE ORDER_STATUS = 'DELIVERED'
    ),
    split_shipments AS (
        SELECT
            ORDER_ID,
            ORDER_DATE,
            QUANTITY_ORDERED,
            ORDER_STATUS,
            REL_SCORE,
            LT_AVG,
            PLANT_REGION,
            -- Split shipment ships 3-7 days after the primary would have shipped
            DATEADD('day',
                LT_AVG + ROUND((1.0 - REL_SCORE) * UNIFORM(0, 10, RANDOM()))::INTEGER + UNIFORM(3, 7, RANDOM()),
                ORDER_DATE
            ) AS SHIP_DATE,
            CASE PLANT_REGION
                WHEN 'APAC'  THEN UNIFORM(5, 12, RANDOM())
                WHEN 'EMEA'  THEN UNIFORM(3, 8, RANDOM())
                WHEN 'NA'    THEN UNIFORM(2, 6, RANDOM())
                WHEN 'LATAM' THEN UNIFORM(4, 10, RANDOM())
            END AS TRANSIT_ESTIMATE,
            CASE PLANT_REGION
                WHEN 'APAC'  THEN UNIFORM(5, 12, RANDOM())
                WHEN 'EMEA'  THEN UNIFORM(3, 8, RANDOM())
                WHEN 'NA'    THEN UNIFORM(2, 6, RANDOM())
                WHEN 'LATAM' THEN UNIFORM(4, 10, RANDOM())
            END + ROUND((1.0 - REL_SCORE) * UNIFORM(-2, 8, RANDOM()))::INTEGER
                AS ACTUAL_TRANSIT,
            100 AS FILL_ROLL,  -- always partial (triggers the <50-79% branch is irrelevant; handled below)
            'SPLIT' AS SHIPMENT_TYPE
        FROM split_candidates
        WHERE SPLIT_RANK <= 750
    ),
    -- Combine both phases and assign sequential SHIPMENT_IDs
    all_shipments AS (
        SELECT *, ROW_NUMBER() OVER (ORDER BY ORDER_ID, SHIPMENT_TYPE) AS RN
        FROM (
            SELECT * FROM primary_shipments
            UNION ALL
            SELECT * FROM split_shipments
        )
    )
    SELECT
        'SHP-' || LPAD(RN::VARCHAR, 5, '0') AS SHIPMENT_ID,
        ORDER_ID,
        SHIP_DATE,
        DATEADD('day', TRANSIT_ESTIMATE, SHIP_DATE) AS CARRIER_ETA,
        CASE
            WHEN ORDER_STATUS = 'DELIVERED'
                THEN DATEADD('day', GREATEST(1, ACTUAL_TRANSIT), SHIP_DATE)
            ELSE NULL
        END AS DELIVERY_DATE,
        -- Quantity logic: primary uses fill-rate distribution; splits ship 10-30% of order
        CASE
            WHEN SHIPMENT_TYPE = 'SPLIT'
                THEN GREATEST(1, ROUND(QUANTITY_ORDERED * UNIFORM(0.10::FLOAT, 0.30::FLOAT, RANDOM()))::INTEGER)
            WHEN FILL_ROLL < 70 THEN QUANTITY_ORDERED
            WHEN FILL_ROLL < 90 THEN GREATEST(1, ROUND(QUANTITY_ORDERED * UNIFORM(0.80::FLOAT, 0.99::FLOAT, RANDOM()))::INTEGER)
            ELSE GREATEST(1, ROUND(QUANTITY_ORDERED * UNIFORM(0.50::FLOAT, 0.79::FLOAT, RANDOM()))::INTEGER)
        END AS QUANTITY_SHIPPED,
        CASE UNIFORM(0, 5, RANDOM())
            WHEN 0 THEN 'FedEx'    WHEN 1 THEN 'DHL'       WHEN 2 THEN 'UPS'
            WHEN 3 THEN 'Maersk'   WHEN 4 THEN 'DB Schenker' WHEN 5 THEN 'Kuehne+Nagel'
        END AS CARRIER,
        ROUND(GREATEST(1, ACTUAL_TRANSIT) * QUANTITY_ORDERED * UNIFORM(0.05::FLOAT, 0.20::FLOAT, RANDOM()), 2)
            AS SHIPPING_COST,
        CURRENT_TIMESTAMP() AS CREATED_AT,
        CURRENT_TIMESTAMP() AS UPDATED_AT
    FROM all_shipments;

    -- =========================================================================
    -- ONTOLOGY: ENTITY_TYPE (6 entities)
    -- =========================================================================
    INSERT OVERWRITE INTO ONTOLOGY.ENTITY_TYPE
    SELECT * FROM VALUES
        ('SUPPLIER',  'Supplier',  'Organization that provides parts to manufacturing plants', 'CHAINTRUTH_DB.RAW.SUPPLIERS', 'SUPPLIER_ID', CURRENT_TIMESTAMP()),
        ('PART',      'Part',      'Item sourced from suppliers and assembled or shipped from plants', 'CHAINTRUTH_DB.RAW.PARTS', 'PART_ID', CURRENT_TIMESTAMP()),
        ('PLANT',     'Plant',     'Manufacturing or distribution site that fulfills customer orders', 'CHAINTRUTH_DB.RAW.PLANTS', 'PLANT_ID', CURRENT_TIMESTAMP()),
        ('CUSTOMER',  'Customer',  'End consumer who places orders for parts', 'CHAINTRUTH_DB.RAW.CUSTOMERS', 'CUSTOMER_ID', CURRENT_TIMESTAMP()),
        ('ORDER',     'Order',     'Purchase request from a customer for a specific part, fulfilled by a supplier from a plant', 'CHAINTRUTH_DB.RAW.ORDERS', 'ORDER_ID', CURRENT_TIMESTAMP()),
        ('SHIPMENT',  'Shipment',  'Physical movement of goods from plant to customer for a specific order', 'CHAINTRUTH_DB.RAW.SHIPMENTS', 'SHIPMENT_ID', CURRENT_TIMESTAMP());

    -- =========================================================================
    -- ONTOLOGY: RELATIONSHIP_TYPE (7 relationships)
    -- =========================================================================
    INSERT OVERWRITE INTO ONTOLOGY.RELATIONSHIP_TYPE
    SELECT * FROM VALUES
        ('REL_01', 'Customer places Order',     'CUSTOMER', 'ORDER',    'ONE_TO_MANY', 'CUSTOMER_ID', 'CUSTOMER_ID', 'A customer can place many orders', CURRENT_TIMESTAMP()),
        ('REL_02', 'Order contains Part',       'ORDER',    'PART',     'MANY_TO_ONE', 'PART_ID',     'PART_ID',     'Each order is for one part; a part appears in many orders', CURRENT_TIMESTAMP()),
        ('REL_03', 'Supplier fulfills Order',   'SUPPLIER', 'ORDER',    'ONE_TO_MANY', 'SUPPLIER_ID', 'SUPPLIER_ID', 'A supplier fulfills many orders', CURRENT_TIMESTAMP()),
        ('REL_04', 'Plant produces Order',      'PLANT',    'ORDER',    'ONE_TO_MANY', 'PLANT_ID',    'PLANT_ID',    'A plant produces goods for many orders', CURRENT_TIMESTAMP()),
        ('REL_05', 'Order has Shipment',        'ORDER',    'SHIPMENT', 'ONE_TO_MANY', 'ORDER_ID',    'ORDER_ID',    'An order can have one or more shipments', CURRENT_TIMESTAMP()),
        ('REL_06', 'Supplier supplies Part',    'SUPPLIER', 'PART',     'MANY_TO_MANY','SUPPLIER_ID', 'PART_ID',     'Many suppliers can supply many parts (via orders)', CURRENT_TIMESTAMP()),
        ('REL_07', 'Plant ships to Customer',   'PLANT',    'CUSTOMER', 'MANY_TO_MANY','PLANT_ID',    'CUSTOMER_ID', 'Plants serve many customers (via orders)', CURRENT_TIMESTAMP());

    -- =========================================================================
    -- ONTOLOGY: METRIC_REGISTRY (7 metrics, 3 are OTIF variants)
    -- =========================================================================
    INSERT OVERWRITE INTO ONTOLOGY.METRIC_REGISTRY
    SELECT * FROM VALUES
    -- OTIF: Three conflicting definitions — the core governance challenge
    (
        'OTIF_ERP', 'On-Time In-Full', 'ERP Definition',
        'Percentage of delivered orders where the delivery arrived on or before the ERP promised date AND the full quantity was shipped. This is the strictest definition because ERP promises are set early with tight buffers.',
        'COUNT_IF(s.DELIVERY_DATE <= o.PROMISED_DELIVERY_DATE AND s.QUANTITY_SHIPPED >= o.QUANTITY_ORDERED) / NULLIF(COUNT(*), 0) * 100',
        'PERCENTAGE', 'HIGHER_IS_BETTER', 'Finance',
        'RAW.ORDERS, RAW.SHIPMENTS',
        'DELIVERY_DATE, PROMISED_DELIVERY_DATE, QUANTITY_SHIPPED, QUANTITY_ORDERED',
        TRUE,  -- canonical definition
        CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP()
    ),
    (
        'OTIF_LOGISTICS', 'On-Time In-Full', 'Logistics Definition',
        'Percentage of delivered orders where the delivery arrived on or before the carrier ETA AND the full quantity was shipped. Logistics uses carrier ETA which is set at ship-time and is often optimistic.',
        'COUNT_IF(s.DELIVERY_DATE <= s.CARRIER_ETA AND s.QUANTITY_SHIPPED >= o.QUANTITY_ORDERED) / NULLIF(COUNT(*), 0) * 100',
        'PERCENTAGE', 'HIGHER_IS_BETTER', 'Logistics',
        'RAW.ORDERS, RAW.SHIPMENTS',
        'DELIVERY_DATE, CARRIER_ETA, QUANTITY_SHIPPED, QUANTITY_ORDERED',
        FALSE,
        CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP()
    ),
    (
        'OTIF_SUPPLIER', 'On-Time In-Full', 'Supplier Definition',
        'Percentage of shipped orders where the shipment departed on or before the supplier commitment date AND the full quantity was shipped. Suppliers measure against their own commitment which has the most generous buffer.',
        'COUNT_IF(s.SHIP_DATE <= o.SUPPLIER_COMMITMENT_DATE AND s.QUANTITY_SHIPPED >= o.QUANTITY_ORDERED) / NULLIF(COUNT(*), 0) * 100',
        'PERCENTAGE', 'HIGHER_IS_BETTER', 'Procurement',
        'RAW.ORDERS, RAW.SHIPMENTS',
        'SHIP_DATE, SUPPLIER_COMMITMENT_DATE, QUANTITY_SHIPPED, QUANTITY_ORDERED',
        FALSE,
        CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP()
    ),
    -- Lead Time
    (
        'LEAD_TIME', 'Lead Time', NULL,
        'Average number of days from order placement to actual delivery. Measures end-to-end supply chain velocity.',
        'AVG(DATEDIFF(''day'', o.ORDER_DATE, s.DELIVERY_DATE))',
        'DAYS', 'LOWER_IS_BETTER', 'Operations',
        'RAW.ORDERS, RAW.SHIPMENTS',
        'ORDER_DATE, DELIVERY_DATE',
        TRUE,
        CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP()
    ),
    -- Fill Rate
    (
        'FILL_RATE', 'Fill Rate', NULL,
        'Percentage of ordered quantity that was actually shipped. Measures inventory availability and fulfillment capability.',
        'SUM(s.QUANTITY_SHIPPED) / NULLIF(SUM(o.QUANTITY_ORDERED), 0) * 100',
        'PERCENTAGE', 'HIGHER_IS_BETTER', 'Supply Planning',
        'RAW.ORDERS, RAW.SHIPMENTS',
        'QUANTITY_SHIPPED, QUANTITY_ORDERED',
        TRUE,
        CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP()
    ),
    -- Revenue At Risk
    (
        'REVENUE_AT_RISK', 'Revenue At Risk', NULL,
        'Total dollar value of orders that are at risk due to late delivery (past ERP promised date) or quantity shortfall. Uses the canonical ERP OTIF definition.',
        'SUM(CASE WHEN s.DELIVERY_DATE > o.PROMISED_DELIVERY_DATE OR s.QUANTITY_SHIPPED < o.QUANTITY_ORDERED OR (o.ORDER_STATUS = ''OPEN'' AND CURRENT_DATE() > o.PROMISED_DELIVERY_DATE) THEN o.QUANTITY_ORDERED * o.UNIT_PRICE ELSE 0 END)',
        'USD', 'LOWER_IS_BETTER', 'Finance',
        'RAW.ORDERS, RAW.SHIPMENTS',
        'DELIVERY_DATE, PROMISED_DELIVERY_DATE, QUANTITY_SHIPPED, QUANTITY_ORDERED, UNIT_PRICE, ORDER_STATUS',
        TRUE,
        CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP()
    ),
    -- Revenue At Risk (count-based variant)
    (
        'ORDERS_AT_RISK', 'Orders At Risk', NULL,
        'Count of orders that are at risk due to late delivery or quantity shortfall. Companion to Revenue At Risk for volumetric analysis.',
        'COUNT_IF(s.DELIVERY_DATE > o.PROMISED_DELIVERY_DATE OR s.QUANTITY_SHIPPED < o.QUANTITY_ORDERED OR (o.ORDER_STATUS = ''OPEN'' AND CURRENT_DATE() > o.PROMISED_DELIVERY_DATE))',
        'COUNT', 'LOWER_IS_BETTER', 'Finance',
        'RAW.ORDERS, RAW.SHIPMENTS',
        'DELIVERY_DATE, PROMISED_DELIVERY_DATE, QUANTITY_SHIPPED, QUANTITY_ORDERED, ORDER_STATUS',
        TRUE,
        CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP()
    );

    RETURN 'Synthetic data generated: 50 suppliers, 200 parts, 10 plants, 50 customers, 5000 orders, ~5000 shipments (non-cancelled), 6 entity types, 7 relationships, 7 metrics (3 OTIF variants)';

END;
$$;
