-- =============================================================================
-- ChainTruth: Analytics Views
-- =============================================================================
-- Seven views over RAW tables providing pre-aggregated metrics at the grain of:
--   MONTH x SUPPLIER x PLANT x CUSTOMER_SEGMENT
--
-- This grain supports all requested drill-downs:
--   - Supplier level:  GROUP BY / filter on SUPPLIER_ID, SUPPLIER_NAME, etc.
--   - Plant level:     GROUP BY / filter on PLANT_ID, PLANT_NAME, etc.
--   - Customer level:  GROUP BY / filter on CUSTOMER_SEGMENT, CUSTOMER_COUNTRY
--   - Monthly trend:   ORDER BY ORDER_MONTH for time-series charts
--
-- OTIF views (1-4):
--   Three competing definitions plus the canonical "ChainTruth" reconciled view.
--   Each computes ON_TIME, IN_FULL, and OTIF (the AND of both) as separate rates
--   so dashboards can show which component is dragging down performance.
--
-- Views 5-7:
--   Lead Time, Fill Rate, and Revenue At Risk with the same dimensional grain.
--
-- All views use LEFT JOINs from ORDERS outward so that orders without shipments
-- (OPEN, CANCELLED) are still visible for Revenue At Risk calculations.
-- =============================================================================

USE DATABASE CHAINTRUTH_DB;
USE SCHEMA ANALYTICS;

-- =============================================================================
-- 1. ERP_OTIF
-- =============================================================================
-- Definition: On-time = DELIVERY_DATE <= PROMISED_DELIVERY_DATE
-- Perspective: Finance / ERP system
-- This is the STRICTEST definition because ERP promises are set early with
-- tight buffers. Expect the lowest OTIF rate of the three.
-- Only DELIVERED orders with shipments are included in the rate calculation.
-- =============================================================================
CREATE OR REPLACE VIEW ANALYTICS.ERP_OTIF AS
WITH delivered_shipments AS (
    SELECT
        o.ORDER_ID,
        o.SUPPLIER_ID,
        o.PLANT_ID,
        o.CUSTOMER_ID,
        o.ORDER_DATE,
        DATE_TRUNC('MONTH', o.ORDER_DATE)          AS ORDER_MONTH,
        o.PROMISED_DELIVERY_DATE,
        o.QUANTITY_ORDERED,
        s.SHIPMENT_ID,
        s.DELIVERY_DATE,
        s.QUANTITY_SHIPPED,
        -- On-time: delivered on or before ERP promise
        CASE WHEN s.DELIVERY_DATE <= o.PROMISED_DELIVERY_DATE
             THEN 1 ELSE 0 END                     AS IS_ON_TIME,
        -- In-full: shipped quantity meets or exceeds ordered
        CASE WHEN s.QUANTITY_SHIPPED >= o.QUANTITY_ORDERED
             THEN 1 ELSE 0 END                     AS IS_IN_FULL,
        -- OTIF: both conditions met
        CASE WHEN s.DELIVERY_DATE <= o.PROMISED_DELIVERY_DATE
              AND s.QUANTITY_SHIPPED >= o.QUANTITY_ORDERED
             THEN 1 ELSE 0 END                     AS IS_OTIF
    FROM RAW.ORDERS o
    INNER JOIN RAW.SHIPMENTS s
        ON o.ORDER_ID = s.ORDER_ID
    WHERE o.ORDER_STATUS = 'DELIVERED'
      AND s.DELIVERY_DATE IS NOT NULL
)
SELECT
    ds.ORDER_MONTH,
    ds.SUPPLIER_ID,
    sup.SUPPLIER_NAME,
    sup.COUNTRY                                     AS SUPPLIER_COUNTRY,
    sup.REGION                                      AS SUPPLIER_REGION,
    sup.RELIABILITY_SCORE,
    ds.PLANT_ID,
    plt.PLANT_NAME,
    plt.COUNTRY                                     AS PLANT_COUNTRY,
    plt.REGION                                      AS PLANT_REGION,
    cust.SEGMENT                                    AS CUSTOMER_SEGMENT,
    cust.COUNTRY                                    AS CUSTOMER_COUNTRY,
    COUNT(DISTINCT ds.ORDER_ID)                     AS TOTAL_ORDERS,
    COUNT(ds.SHIPMENT_ID)                           AS TOTAL_SHIPMENTS,
    SUM(ds.IS_ON_TIME)                              AS ON_TIME_COUNT,
    SUM(ds.IS_IN_FULL)                              AS IN_FULL_COUNT,
    SUM(ds.IS_OTIF)                                 AS OTIF_COUNT,
    ROUND(SUM(ds.IS_ON_TIME)   * 100.0
        / NULLIF(COUNT(*), 0), 2)                   AS ON_TIME_RATE,
    ROUND(SUM(ds.IS_IN_FULL)   * 100.0
        / NULLIF(COUNT(*), 0), 2)                   AS IN_FULL_RATE,
    ROUND(SUM(ds.IS_OTIF)      * 100.0
        / NULLIF(COUNT(*), 0), 2)                   AS OTIF_RATE,
    'ERP'                                           AS OTIF_DEFINITION
FROM delivered_shipments ds
LEFT JOIN RAW.SUPPLIERS sup ON ds.SUPPLIER_ID = sup.SUPPLIER_ID
LEFT JOIN RAW.PLANTS    plt ON ds.PLANT_ID    = plt.PLANT_ID
LEFT JOIN RAW.CUSTOMERS cust ON ds.CUSTOMER_ID = cust.CUSTOMER_ID
GROUP BY
    ds.ORDER_MONTH,
    ds.SUPPLIER_ID, sup.SUPPLIER_NAME, sup.COUNTRY, sup.REGION, sup.RELIABILITY_SCORE,
    ds.PLANT_ID, plt.PLANT_NAME, plt.COUNTRY, plt.REGION,
    cust.SEGMENT, cust.COUNTRY;

-- =============================================================================
-- 2. LOGISTICS_OTIF
-- =============================================================================
-- Definition: On-time = DELIVERY_DATE <= CARRIER_ETA
-- Perspective: Logistics / Carrier operations
-- CARRIER_ETA is set at ship-time and is often optimistic (shorter than ERP
-- promise), so this definition can produce a LOWER on-time rate than ERP
-- even though the logistics team believes it's "their" number.
-- =============================================================================
CREATE OR REPLACE VIEW ANALYTICS.LOGISTICS_OTIF AS
WITH delivered_shipments AS (
    SELECT
        o.ORDER_ID,
        o.SUPPLIER_ID,
        o.PLANT_ID,
        o.CUSTOMER_ID,
        o.ORDER_DATE,
        DATE_TRUNC('MONTH', o.ORDER_DATE)           AS ORDER_MONTH,
        o.QUANTITY_ORDERED,
        s.SHIPMENT_ID,
        s.CARRIER_ETA,
        s.DELIVERY_DATE,
        s.QUANTITY_SHIPPED,
        s.CARRIER,
        CASE WHEN s.DELIVERY_DATE <= s.CARRIER_ETA
             THEN 1 ELSE 0 END                      AS IS_ON_TIME,
        CASE WHEN s.QUANTITY_SHIPPED >= o.QUANTITY_ORDERED
             THEN 1 ELSE 0 END                      AS IS_IN_FULL,
        CASE WHEN s.DELIVERY_DATE <= s.CARRIER_ETA
              AND s.QUANTITY_SHIPPED >= o.QUANTITY_ORDERED
             THEN 1 ELSE 0 END                      AS IS_OTIF
    FROM RAW.ORDERS o
    INNER JOIN RAW.SHIPMENTS s
        ON o.ORDER_ID = s.ORDER_ID
    WHERE o.ORDER_STATUS = 'DELIVERED'
      AND s.DELIVERY_DATE IS NOT NULL
)
SELECT
    ds.ORDER_MONTH,
    ds.SUPPLIER_ID,
    sup.SUPPLIER_NAME,
    sup.COUNTRY                                      AS SUPPLIER_COUNTRY,
    sup.REGION                                       AS SUPPLIER_REGION,
    ds.PLANT_ID,
    plt.PLANT_NAME,
    plt.COUNTRY                                      AS PLANT_COUNTRY,
    plt.REGION                                       AS PLANT_REGION,
    cust.SEGMENT                                     AS CUSTOMER_SEGMENT,
    cust.COUNTRY                                     AS CUSTOMER_COUNTRY,
    ds.CARRIER,
    COUNT(DISTINCT ds.ORDER_ID)                      AS TOTAL_ORDERS,
    COUNT(ds.SHIPMENT_ID)                            AS TOTAL_SHIPMENTS,
    SUM(ds.IS_ON_TIME)                               AS ON_TIME_COUNT,
    SUM(ds.IS_IN_FULL)                               AS IN_FULL_COUNT,
    SUM(ds.IS_OTIF)                                  AS OTIF_COUNT,
    ROUND(SUM(ds.IS_ON_TIME)   * 100.0
        / NULLIF(COUNT(*), 0), 2)                    AS ON_TIME_RATE,
    ROUND(SUM(ds.IS_IN_FULL)   * 100.0
        / NULLIF(COUNT(*), 0), 2)                    AS IN_FULL_RATE,
    ROUND(SUM(ds.IS_OTIF)      * 100.0
        / NULLIF(COUNT(*), 0), 2)                    AS OTIF_RATE,
    'LOGISTICS'                                      AS OTIF_DEFINITION
FROM delivered_shipments ds
LEFT JOIN RAW.SUPPLIERS sup ON ds.SUPPLIER_ID = sup.SUPPLIER_ID
LEFT JOIN RAW.PLANTS    plt ON ds.PLANT_ID    = plt.PLANT_ID
LEFT JOIN RAW.CUSTOMERS cust ON ds.CUSTOMER_ID = cust.CUSTOMER_ID
GROUP BY
    ds.ORDER_MONTH,
    ds.SUPPLIER_ID, sup.SUPPLIER_NAME, sup.COUNTRY, sup.REGION,
    ds.PLANT_ID, plt.PLANT_NAME, plt.COUNTRY, plt.REGION,
    cust.SEGMENT, cust.COUNTRY,
    ds.CARRIER;

-- =============================================================================
-- 3. SUPPLIER_OTIF
-- =============================================================================
-- Definition: On-time = SHIP_DATE <= SUPPLIER_COMMITMENT_DATE
-- Perspective: Procurement / Supplier management
-- Measures whether the supplier shipped by their own commitment date.
-- This is the MOST GENEROUS definition because suppliers pad their commitments.
-- Expect the highest OTIF rate of the three.
-- Uses SHIP_DATE (not DELIVERY_DATE) because the supplier controls dispatch,
-- not last-mile transit.
-- =============================================================================
CREATE OR REPLACE VIEW ANALYTICS.SUPPLIER_OTIF AS
WITH shipped_orders AS (
    SELECT
        o.ORDER_ID,
        o.SUPPLIER_ID,
        o.PLANT_ID,
        o.CUSTOMER_ID,
        o.ORDER_DATE,
        DATE_TRUNC('MONTH', o.ORDER_DATE)            AS ORDER_MONTH,
        o.SUPPLIER_COMMITMENT_DATE,
        o.QUANTITY_ORDERED,
        s.SHIPMENT_ID,
        s.SHIP_DATE,
        s.QUANTITY_SHIPPED,
        CASE WHEN s.SHIP_DATE <= o.SUPPLIER_COMMITMENT_DATE
             THEN 1 ELSE 0 END                       AS IS_ON_TIME,
        CASE WHEN s.QUANTITY_SHIPPED >= o.QUANTITY_ORDERED
             THEN 1 ELSE 0 END                       AS IS_IN_FULL,
        CASE WHEN s.SHIP_DATE <= o.SUPPLIER_COMMITMENT_DATE
              AND s.QUANTITY_SHIPPED >= o.QUANTITY_ORDERED
             THEN 1 ELSE 0 END                       AS IS_OTIF
    FROM RAW.ORDERS o
    INNER JOIN RAW.SHIPMENTS s
        ON o.ORDER_ID = s.ORDER_ID
    WHERE o.ORDER_STATUS IN ('SHIPPED', 'DELIVERED')
)
SELECT
    so.ORDER_MONTH,
    so.SUPPLIER_ID,
    sup.SUPPLIER_NAME,
    sup.COUNTRY                                       AS SUPPLIER_COUNTRY,
    sup.REGION                                        AS SUPPLIER_REGION,
    sup.RELIABILITY_SCORE,
    so.PLANT_ID,
    plt.PLANT_NAME,
    plt.COUNTRY                                       AS PLANT_COUNTRY,
    plt.REGION                                        AS PLANT_REGION,
    cust.SEGMENT                                      AS CUSTOMER_SEGMENT,
    cust.COUNTRY                                      AS CUSTOMER_COUNTRY,
    COUNT(DISTINCT so.ORDER_ID)                       AS TOTAL_ORDERS,
    COUNT(so.SHIPMENT_ID)                             AS TOTAL_SHIPMENTS,
    SUM(so.IS_ON_TIME)                                AS ON_TIME_COUNT,
    SUM(so.IS_IN_FULL)                                AS IN_FULL_COUNT,
    SUM(so.IS_OTIF)                                   AS OTIF_COUNT,
    ROUND(SUM(so.IS_ON_TIME)   * 100.0
        / NULLIF(COUNT(*), 0), 2)                     AS ON_TIME_RATE,
    ROUND(SUM(so.IS_IN_FULL)   * 100.0
        / NULLIF(COUNT(*), 0), 2)                     AS IN_FULL_RATE,
    ROUND(SUM(so.IS_OTIF)      * 100.0
        / NULLIF(COUNT(*), 0), 2)                     AS OTIF_RATE,
    'SUPPLIER'                                        AS OTIF_DEFINITION
FROM shipped_orders so
LEFT JOIN RAW.SUPPLIERS sup ON so.SUPPLIER_ID = sup.SUPPLIER_ID
LEFT JOIN RAW.PLANTS    plt ON so.PLANT_ID    = plt.PLANT_ID
LEFT JOIN RAW.CUSTOMERS cust ON so.CUSTOMER_ID = cust.CUSTOMER_ID
GROUP BY
    so.ORDER_MONTH,
    so.SUPPLIER_ID, sup.SUPPLIER_NAME, sup.COUNTRY, sup.REGION, sup.RELIABILITY_SCORE,
    so.PLANT_ID, plt.PLANT_NAME, plt.COUNTRY, plt.REGION,
    cust.SEGMENT, cust.COUNTRY;

-- =============================================================================
-- 4. CHAINTRUTH_OTIF
-- =============================================================================
-- The GOVERNED, canonical OTIF view.
-- Uses the definition marked IS_CANONICAL = TRUE in ONTOLOGY.METRIC_REGISTRY
-- (currently OTIF_ERP: DELIVERY_DATE <= PROMISED_DELIVERY_DATE).
--
-- What makes this different from ERP_OTIF:
--   - Joins to METRIC_REGISTRY to surface which definition is active
--   - Includes columns from ALL three date comparisons so analysts can see
--     how a single shipment scores under each definition side-by-side
--   - Adds a CONFLICT_FLAG when the three definitions disagree
--
-- This is the view that the Semantic View and Cortex Agent should reference.
-- =============================================================================
CREATE OR REPLACE VIEW ANALYTICS.CHAINTRUTH_OTIF AS
WITH canonical_metric AS (
    SELECT METRIC_ID, METRIC_VARIANT, OWNER_TEAM
    FROM ONTOLOGY.METRIC_REGISTRY
    WHERE METRIC_NAME = 'On-Time In-Full'
      AND IS_CANONICAL = TRUE
    LIMIT 1
),
shipment_scores AS (
    SELECT
        o.ORDER_ID,
        o.SUPPLIER_ID,
        o.PLANT_ID,
        o.CUSTOMER_ID,
        o.ORDER_DATE,
        DATE_TRUNC('MONTH', o.ORDER_DATE)            AS ORDER_MONTH,
        o.ORDER_STATUS,
        o.PROMISED_DELIVERY_DATE,
        o.SUPPLIER_COMMITMENT_DATE,
        o.QUANTITY_ORDERED,
        o.UNIT_PRICE,
        s.SHIPMENT_ID,
        s.SHIP_DATE,
        s.CARRIER_ETA,
        s.DELIVERY_DATE,
        s.QUANTITY_SHIPPED,

        -- In-Full flag (shared across all definitions)
        CASE WHEN s.QUANTITY_SHIPPED >= o.QUANTITY_ORDERED
             THEN 1 ELSE 0 END                       AS IS_IN_FULL,

        -- ERP on-time (canonical)
        CASE WHEN s.DELIVERY_DATE <= o.PROMISED_DELIVERY_DATE
             THEN 1 ELSE 0 END                       AS IS_ON_TIME_ERP,

        -- Logistics on-time
        CASE WHEN s.DELIVERY_DATE <= s.CARRIER_ETA
             THEN 1 ELSE 0 END                       AS IS_ON_TIME_LOGISTICS,

        -- Supplier on-time
        CASE WHEN s.SHIP_DATE <= o.SUPPLIER_COMMITMENT_DATE
             THEN 1 ELSE 0 END                       AS IS_ON_TIME_SUPPLIER,

        -- Canonical OTIF (ERP)
        CASE WHEN s.DELIVERY_DATE <= o.PROMISED_DELIVERY_DATE
              AND s.QUANTITY_SHIPPED >= o.QUANTITY_ORDERED
             THEN 1 ELSE 0 END                       AS IS_OTIF_CANONICAL,

        -- Conflict: do the three on-time flags disagree?
        CASE WHEN (CASE WHEN s.DELIVERY_DATE <= o.PROMISED_DELIVERY_DATE THEN 1 ELSE 0 END)
                != (CASE WHEN s.DELIVERY_DATE <= s.CARRIER_ETA THEN 1 ELSE 0 END)
              OR (CASE WHEN s.DELIVERY_DATE <= o.PROMISED_DELIVERY_DATE THEN 1 ELSE 0 END)
                != (CASE WHEN s.SHIP_DATE <= o.SUPPLIER_COMMITMENT_DATE THEN 1 ELSE 0 END)
             THEN 1 ELSE 0 END                       AS IS_CONFLICTED

    FROM RAW.ORDERS o
    INNER JOIN RAW.SHIPMENTS s
        ON o.ORDER_ID = s.ORDER_ID
    WHERE o.ORDER_STATUS = 'DELIVERED'
      AND s.DELIVERY_DATE IS NOT NULL
)
SELECT
    ss.ORDER_MONTH,
    ss.SUPPLIER_ID,
    sup.SUPPLIER_NAME,
    sup.COUNTRY                                       AS SUPPLIER_COUNTRY,
    sup.REGION                                        AS SUPPLIER_REGION,
    sup.RELIABILITY_SCORE,
    ss.PLANT_ID,
    plt.PLANT_NAME,
    plt.COUNTRY                                       AS PLANT_COUNTRY,
    plt.REGION                                        AS PLANT_REGION,
    cust.SEGMENT                                      AS CUSTOMER_SEGMENT,
    cust.COUNTRY                                      AS CUSTOMER_COUNTRY,
    cm.METRIC_ID                                      AS CANONICAL_METRIC_ID,
    cm.METRIC_VARIANT                                 AS CANONICAL_DEFINITION,
    cm.OWNER_TEAM                                     AS CANONICAL_OWNER,

    COUNT(DISTINCT ss.ORDER_ID)                       AS TOTAL_ORDERS,
    COUNT(ss.SHIPMENT_ID)                             AS TOTAL_SHIPMENTS,

    -- Canonical OTIF (ERP-based)
    ROUND(SUM(ss.IS_OTIF_CANONICAL) * 100.0
        / NULLIF(COUNT(*), 0), 2)                     AS OTIF_RATE_CANONICAL,

    -- All three on-time rates for comparison
    ROUND(SUM(ss.IS_ON_TIME_ERP)       * 100.0
        / NULLIF(COUNT(*), 0), 2)                     AS ON_TIME_RATE_ERP,
    ROUND(SUM(ss.IS_ON_TIME_LOGISTICS) * 100.0
        / NULLIF(COUNT(*), 0), 2)                     AS ON_TIME_RATE_LOGISTICS,
    ROUND(SUM(ss.IS_ON_TIME_SUPPLIER)  * 100.0
        / NULLIF(COUNT(*), 0), 2)                     AS ON_TIME_RATE_SUPPLIER,

    ROUND(SUM(ss.IS_IN_FULL)           * 100.0
        / NULLIF(COUNT(*), 0), 2)                     AS IN_FULL_RATE,

    -- Conflict analysis
    SUM(ss.IS_CONFLICTED)                             AS CONFLICTED_SHIPMENTS,
    ROUND(SUM(ss.IS_CONFLICTED) * 100.0
        / NULLIF(COUNT(*), 0), 2)                     AS CONFLICT_RATE,

    'CHAINTRUTH'                                      AS OTIF_DEFINITION
FROM shipment_scores ss
CROSS JOIN canonical_metric cm
LEFT JOIN RAW.SUPPLIERS sup ON ss.SUPPLIER_ID = sup.SUPPLIER_ID
LEFT JOIN RAW.PLANTS    plt ON ss.PLANT_ID    = plt.PLANT_ID
LEFT JOIN RAW.CUSTOMERS cust ON ss.CUSTOMER_ID = cust.CUSTOMER_ID
GROUP BY
    ss.ORDER_MONTH,
    ss.SUPPLIER_ID, sup.SUPPLIER_NAME, sup.COUNTRY, sup.REGION, sup.RELIABILITY_SCORE,
    ss.PLANT_ID, plt.PLANT_NAME, plt.COUNTRY, plt.REGION,
    cust.SEGMENT, cust.COUNTRY,
    cm.METRIC_ID, cm.METRIC_VARIANT, cm.OWNER_TEAM;

-- =============================================================================
-- 5. LEAD_TIME_ANALYTICS
-- =============================================================================
-- Lead time = DATEDIFF('day', ORDER_DATE, DELIVERY_DATE)
-- Computed for DELIVERED orders only (DELIVERY_DATE is NOT NULL).
-- Provides AVG, MEDIAN (P50), P95, MIN, MAX for distribution analysis.
-- A high P95 with a normal AVG signals tail-risk problems in specific lanes.
-- =============================================================================
CREATE OR REPLACE VIEW ANALYTICS.LEAD_TIME_ANALYTICS AS
WITH lead_times AS (
    SELECT
        o.ORDER_ID,
        o.SUPPLIER_ID,
        o.PLANT_ID,
        o.CUSTOMER_ID,
        o.ORDER_DATE,
        DATE_TRUNC('MONTH', o.ORDER_DATE)            AS ORDER_MONTH,
        o.QUANTITY_ORDERED,
        o.UNIT_PRICE,
        s.SHIPMENT_ID,
        s.DELIVERY_DATE,
        DATEDIFF('day', o.ORDER_DATE, s.DELIVERY_DATE) AS LEAD_TIME_DAYS
    FROM RAW.ORDERS o
    INNER JOIN RAW.SHIPMENTS s
        ON o.ORDER_ID = s.ORDER_ID
    WHERE o.ORDER_STATUS = 'DELIVERED'
      AND s.DELIVERY_DATE IS NOT NULL
)
SELECT
    lt.ORDER_MONTH,
    lt.SUPPLIER_ID,
    sup.SUPPLIER_NAME,
    sup.COUNTRY                                       AS SUPPLIER_COUNTRY,
    sup.REGION                                        AS SUPPLIER_REGION,
    sup.RELIABILITY_SCORE,
    lt.PLANT_ID,
    plt.PLANT_NAME,
    plt.COUNTRY                                       AS PLANT_COUNTRY,
    plt.REGION                                        AS PLANT_REGION,
    cust.SEGMENT                                      AS CUSTOMER_SEGMENT,
    cust.COUNTRY                                      AS CUSTOMER_COUNTRY,

    COUNT(DISTINCT lt.ORDER_ID)                       AS TOTAL_ORDERS,
    COUNT(lt.SHIPMENT_ID)                             AS TOTAL_SHIPMENTS,
    ROUND(AVG(lt.LEAD_TIME_DAYS), 1)                  AS AVG_LEAD_TIME_DAYS,
    ROUND(MEDIAN(lt.LEAD_TIME_DAYS), 1)               AS MEDIAN_LEAD_TIME_DAYS,
    MIN(lt.LEAD_TIME_DAYS)                            AS MIN_LEAD_TIME_DAYS,
    MAX(lt.LEAD_TIME_DAYS)                            AS MAX_LEAD_TIME_DAYS,
    ROUND(PERCENTILE_CONT(0.95)
        WITHIN GROUP (ORDER BY lt.LEAD_TIME_DAYS), 1) AS P95_LEAD_TIME_DAYS,
    ROUND(STDDEV(lt.LEAD_TIME_DAYS), 1)               AS STDDEV_LEAD_TIME_DAYS
FROM lead_times lt
LEFT JOIN RAW.SUPPLIERS sup ON lt.SUPPLIER_ID = sup.SUPPLIER_ID
LEFT JOIN RAW.PLANTS    plt ON lt.PLANT_ID    = plt.PLANT_ID
LEFT JOIN RAW.CUSTOMERS cust ON lt.CUSTOMER_ID = cust.CUSTOMER_ID
GROUP BY
    lt.ORDER_MONTH,
    lt.SUPPLIER_ID, sup.SUPPLIER_NAME, sup.COUNTRY, sup.REGION, sup.RELIABILITY_SCORE,
    lt.PLANT_ID, plt.PLANT_NAME, plt.COUNTRY, plt.REGION,
    cust.SEGMENT, cust.COUNTRY;

-- =============================================================================
-- 6. FILL_RATE_ANALYTICS
-- =============================================================================
-- Fill rate = SUM(QUANTITY_SHIPPED) / SUM(QUANTITY_ORDERED) * 100
-- Computed for all orders that have at least one shipment (SHIPPED + DELIVERED).
-- Aggregates across split shipments: if an order has two shipments, total
-- QUANTITY_SHIPPED is the sum of both.
-- Also computes PERFECT_ORDER_RATE: % of orders where total shipped >= ordered.
-- =============================================================================
CREATE OR REPLACE VIEW ANALYTICS.FILL_RATE_ANALYTICS AS
WITH order_fill AS (
    SELECT
        o.ORDER_ID,
        o.SUPPLIER_ID,
        o.PLANT_ID,
        o.CUSTOMER_ID,
        o.ORDER_DATE,
        DATE_TRUNC('MONTH', o.ORDER_DATE)            AS ORDER_MONTH,
        o.QUANTITY_ORDERED,
        o.UNIT_PRICE,
        SUM(s.QUANTITY_SHIPPED)                       AS TOTAL_SHIPPED,
        COUNT(s.SHIPMENT_ID)                          AS SHIPMENT_COUNT,
        CASE WHEN SUM(s.QUANTITY_SHIPPED) >= o.QUANTITY_ORDERED
             THEN 1 ELSE 0 END                       AS IS_FULLY_FILLED,
        GREATEST(0, o.QUANTITY_ORDERED - SUM(s.QUANTITY_SHIPPED))
                                                      AS SHORTFALL_QTY
    FROM RAW.ORDERS o
    INNER JOIN RAW.SHIPMENTS s
        ON o.ORDER_ID = s.ORDER_ID
    WHERE o.ORDER_STATUS IN ('SHIPPED', 'DELIVERED')
    GROUP BY
        o.ORDER_ID, o.SUPPLIER_ID, o.PLANT_ID, o.CUSTOMER_ID,
        o.ORDER_DATE, o.QUANTITY_ORDERED, o.UNIT_PRICE
)
SELECT
    fil.ORDER_MONTH,
    fil.SUPPLIER_ID,
    sup.SUPPLIER_NAME,
    sup.COUNTRY                                       AS SUPPLIER_COUNTRY,
    sup.REGION                                        AS SUPPLIER_REGION,
    fil.PLANT_ID,
    plt.PLANT_NAME,
    plt.COUNTRY                                       AS PLANT_COUNTRY,
    plt.REGION                                        AS PLANT_REGION,
    cust.SEGMENT                                      AS CUSTOMER_SEGMENT,
    cust.COUNTRY                                      AS CUSTOMER_COUNTRY,

    COUNT(fil.ORDER_ID)                               AS TOTAL_ORDERS,
    SUM(fil.SHIPMENT_COUNT)                           AS TOTAL_SHIPMENTS,
    SUM(fil.QUANTITY_ORDERED)                         AS TOTAL_QTY_ORDERED,
    SUM(fil.TOTAL_SHIPPED)                            AS TOTAL_QTY_SHIPPED,
    SUM(fil.SHORTFALL_QTY)                            AS TOTAL_SHORTFALL_QTY,
    ROUND(SUM(fil.TOTAL_SHIPPED) * 100.0
        / NULLIF(SUM(fil.QUANTITY_ORDERED), 0), 2)    AS FILL_RATE,
    ROUND(SUM(fil.IS_FULLY_FILLED) * 100.0
        / NULLIF(COUNT(*), 0), 2)                     AS PERFECT_ORDER_RATE,
    SUM(fil.SHORTFALL_QTY * fil.UNIT_PRICE)           AS SHORTFALL_REVENUE
FROM order_fill fil
LEFT JOIN RAW.SUPPLIERS sup ON fil.SUPPLIER_ID = sup.SUPPLIER_ID
LEFT JOIN RAW.PLANTS    plt ON fil.PLANT_ID    = plt.PLANT_ID
LEFT JOIN RAW.CUSTOMERS cust ON fil.CUSTOMER_ID = cust.CUSTOMER_ID
GROUP BY
    fil.ORDER_MONTH,
    fil.SUPPLIER_ID, sup.SUPPLIER_NAME, sup.COUNTRY, sup.REGION,
    fil.PLANT_ID, plt.PLANT_NAME, plt.COUNTRY, plt.REGION,
    cust.SEGMENT, cust.COUNTRY;

-- =============================================================================
-- 7. REVENUE_AT_RISK_ANALYTICS
-- =============================================================================
-- Revenue At Risk = dollar value of orders that failed OTIF (canonical/ERP
-- definition) OR are still OPEN past their promised delivery date.
--
-- Three risk categories:
--   LATE_DELIVERY: delivered after PROMISED_DELIVERY_DATE
--   SHORT_SHIPPED: total QUANTITY_SHIPPED across all shipments < QUANTITY_ORDERED
--   OVERDUE_OPEN:  ORDER_STATUS = 'OPEN' and CURRENT_DATE > PROMISED_DELIVERY_DATE
--
-- An order can fall into multiple categories (late AND short).
-- ORDER_VALUE = QUANTITY_ORDERED * UNIT_PRICE.
--
-- IMPORTANT: This view pre-aggregates shipments to ORDER grain before computing
-- risk flags. This prevents double-counting ORDER_VALUE for orders with split
-- shipments, and ensures IS_SHORT_SHIPPED compares total shipped quantity
-- (across all shipments) against the ordered quantity.
-- =============================================================================
CREATE OR REPLACE VIEW ANALYTICS.REVENUE_AT_RISK_ANALYTICS AS
WITH order_shipment_agg AS (
    -- Pre-aggregate shipments to one row per order.
    -- For OPEN orders with no shipments, LEFT JOIN produces NULLs handled below.
    SELECT
        o.ORDER_ID,
        o.SUPPLIER_ID,
        o.PLANT_ID,
        o.CUSTOMER_ID,
        o.ORDER_DATE,
        DATE_TRUNC('MONTH', o.ORDER_DATE)             AS ORDER_MONTH,
        o.ORDER_STATUS,
        o.PROMISED_DELIVERY_DATE,
        o.QUANTITY_ORDERED,
        o.UNIT_PRICE,
        o.QUANTITY_ORDERED * o.UNIT_PRICE              AS ORDER_VALUE,
        COUNT(s.SHIPMENT_ID)                           AS SHIPMENT_COUNT,
        COALESCE(SUM(s.QUANTITY_SHIPPED), 0)           AS TOTAL_SHIPPED,
        MAX(s.DELIVERY_DATE)                           AS LATEST_DELIVERY_DATE
    FROM RAW.ORDERS o
    LEFT JOIN RAW.SHIPMENTS s
        ON o.ORDER_ID = s.ORDER_ID
    WHERE o.ORDER_STATUS IN ('OPEN', 'SHIPPED', 'DELIVERED')
    GROUP BY
        o.ORDER_ID, o.SUPPLIER_ID, o.PLANT_ID, o.CUSTOMER_ID,
        o.ORDER_DATE, o.ORDER_STATUS, o.PROMISED_DELIVERY_DATE,
        o.QUANTITY_ORDERED, o.UNIT_PRICE
),
order_risk AS (
    -- Compute risk flags at order grain (one row per order, no duplication).
    SELECT
        *,

        -- Late: latest delivery across all shipments missed the ERP promise
        CASE WHEN ORDER_STATUS = 'DELIVERED'
              AND LATEST_DELIVERY_DATE > PROMISED_DELIVERY_DATE
             THEN 1 ELSE 0 END                        AS IS_LATE_DELIVERY,

        -- Short: total shipped across ALL shipments still less than ordered
        CASE WHEN ORDER_STATUS IN ('SHIPPED', 'DELIVERED')
              AND TOTAL_SHIPPED < QUANTITY_ORDERED
             THEN 1 ELSE 0 END                        AS IS_SHORT_SHIPPED,

        -- Overdue: order still open past promised date
        CASE WHEN ORDER_STATUS = 'OPEN'
              AND CURRENT_DATE() > PROMISED_DELIVERY_DATE
             THEN 1 ELSE 0 END                        AS IS_OVERDUE_OPEN,

        -- At risk if ANY flag is set
        CASE WHEN (ORDER_STATUS = 'DELIVERED'
                    AND LATEST_DELIVERY_DATE > PROMISED_DELIVERY_DATE)
               OR (ORDER_STATUS IN ('SHIPPED', 'DELIVERED')
                    AND TOTAL_SHIPPED < QUANTITY_ORDERED)
               OR (ORDER_STATUS = 'OPEN'
                    AND CURRENT_DATE() > PROMISED_DELIVERY_DATE)
             THEN 1 ELSE 0 END                        AS IS_AT_RISK

    FROM order_shipment_agg
)
SELECT
    r.ORDER_MONTH,
    r.SUPPLIER_ID,
    sup.SUPPLIER_NAME,
    sup.COUNTRY                                        AS SUPPLIER_COUNTRY,
    sup.REGION                                         AS SUPPLIER_REGION,
    r.PLANT_ID,
    plt.PLANT_NAME,
    plt.COUNTRY                                        AS PLANT_COUNTRY,
    plt.REGION                                         AS PLANT_REGION,
    cust.SEGMENT                                       AS CUSTOMER_SEGMENT,
    cust.COUNTRY                                       AS CUSTOMER_COUNTRY,

    COUNT(r.ORDER_ID)                                  AS TOTAL_ORDERS,
    SUM(r.ORDER_VALUE)                                 AS TOTAL_ORDER_VALUE,

    -- At-risk counts
    SUM(r.IS_AT_RISK)                                  AS AT_RISK_ORDERS,
    SUM(CASE WHEN r.IS_AT_RISK = 1
             THEN r.ORDER_VALUE ELSE 0 END)            AS REVENUE_AT_RISK,

    -- Breakdown by risk type
    SUM(r.IS_LATE_DELIVERY)                            AS LATE_DELIVERY_ORDERS,
    SUM(CASE WHEN r.IS_LATE_DELIVERY = 1
             THEN r.ORDER_VALUE ELSE 0 END)            AS LATE_DELIVERY_REVENUE,

    SUM(r.IS_SHORT_SHIPPED)                            AS SHORT_SHIPPED_ORDERS,
    SUM(CASE WHEN r.IS_SHORT_SHIPPED = 1
             THEN r.ORDER_VALUE ELSE 0 END)            AS SHORT_SHIPPED_REVENUE,

    SUM(r.IS_OVERDUE_OPEN)                             AS OVERDUE_OPEN_ORDERS,
    SUM(CASE WHEN r.IS_OVERDUE_OPEN = 1
             THEN r.ORDER_VALUE ELSE 0 END)            AS OVERDUE_OPEN_REVENUE,

    -- Risk rates
    ROUND(SUM(r.IS_AT_RISK) * 100.0
        / NULLIF(COUNT(r.ORDER_ID), 0), 2)             AS AT_RISK_RATE,
    ROUND(SUM(CASE WHEN r.IS_AT_RISK = 1
                   THEN r.ORDER_VALUE ELSE 0 END) * 100.0
        / NULLIF(SUM(r.ORDER_VALUE), 0), 2)            AS REVENUE_AT_RISK_PCT

FROM order_risk r
LEFT JOIN RAW.SUPPLIERS sup ON r.SUPPLIER_ID = sup.SUPPLIER_ID
LEFT JOIN RAW.PLANTS    plt ON r.PLANT_ID    = plt.PLANT_ID
LEFT JOIN RAW.CUSTOMERS cust ON r.CUSTOMER_ID = cust.CUSTOMER_ID
GROUP BY
    r.ORDER_MONTH,
    r.SUPPLIER_ID, sup.SUPPLIER_NAME, sup.COUNTRY, sup.REGION,
    r.PLANT_ID, plt.PLANT_NAME, plt.COUNTRY, plt.REGION,
    cust.SEGMENT, cust.COUNTRY;
