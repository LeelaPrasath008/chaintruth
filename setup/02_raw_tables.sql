-- =============================================================================
-- ChainTruth: Raw Entity Tables (Bronze Layer)
-- =============================================================================
-- Six core supply chain entities. Key design decisions:
--
-- 1. CONFLICTING OTIF DATE COLUMNS
--    The three competing OTIF definitions are embedded directly in the data:
--
--    RAW.ORDERS.PROMISED_DELIVERY_DATE   (ERP perspective)
--      → ERP says OTIF = delivery_date <= promised_delivery_date
--
--    RAW.SHIPMENTS.CARRIER_ETA           (Logistics perspective)
--      → Logistics says OTIF = delivery_date <= carrier_eta
--
--    RAW.ORDERS.SUPPLIER_COMMITMENT_DATE (Supplier perspective)
--      → Supplier says OTIF = ship_date <= supplier_commitment_date
--
--    These three dates will intentionally diverge in the synthetic data,
--    producing different OTIF rates depending on which definition is used.
--    The ONTOLOGY.METRIC_REGISTRY table records all three definitions so
--    the platform can reconcile them.
--
-- 2. Each table carries CREATED_AT and UPDATED_AT for change tracking.
-- 3. VARCHAR primary keys use a prefixed format (SUP-001, PRT-001, etc.)
--    for human readability during demos.
-- =============================================================================

USE DATABASE CHAINTRUTH_DB;
USE SCHEMA RAW;

-- -----------------------------------------------------------------------------
-- SUPPLIERS: Organizations that provide parts to plants.
-- RELIABILITY_SCORE is a 0-1 float used in synthetic data to skew on-time
-- delivery probability — low-reliability suppliers produce more late shipments.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE TABLE RAW.SUPPLIERS (
    SUPPLIER_ID         VARCHAR(20)     NOT NULL,
    SUPPLIER_NAME       VARCHAR(100)    NOT NULL,
    COUNTRY             VARCHAR(50)     NOT NULL,
    REGION              VARCHAR(30)     NOT NULL,
    RELIABILITY_SCORE   FLOAT           NOT NULL,  -- 0.0 (unreliable) to 1.0 (perfect)
    LEAD_TIME_DAYS_AVG  INTEGER         NOT NULL,  -- average days from commitment to ship
    CREATED_AT          TIMESTAMP_NTZ   DEFAULT CURRENT_TIMESTAMP(),
    UPDATED_AT          TIMESTAMP_NTZ   DEFAULT CURRENT_TIMESTAMP(),

    CONSTRAINT PK_SUPPLIERS PRIMARY KEY (SUPPLIER_ID)
);

-- -----------------------------------------------------------------------------
-- PARTS: Items sourced from suppliers, assembled or shipped from plants.
-- CATEGORY drives analytical drill-downs (Electronics, Mechanical, etc.).
-- CRITICALITY flags parts whose shortage triggers Revenue At Risk alerts.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE TABLE RAW.PARTS (
    PART_ID             VARCHAR(20)     NOT NULL,
    PART_NAME           VARCHAR(100)    NOT NULL,
    CATEGORY            VARCHAR(30)     NOT NULL,  -- Electronics, Mechanical, Chemical, Packaging
    UNIT_COST           NUMBER(12,2)    NOT NULL,
    WEIGHT_KG           FLOAT           NOT NULL,
    CRITICALITY         VARCHAR(10)     NOT NULL,  -- HIGH, MEDIUM, LOW
    CREATED_AT          TIMESTAMP_NTZ   DEFAULT CURRENT_TIMESTAMP(),
    UPDATED_AT          TIMESTAMP_NTZ   DEFAULT CURRENT_TIMESTAMP(),

    CONSTRAINT PK_PARTS PRIMARY KEY (PART_ID)
);

-- -----------------------------------------------------------------------------
-- PLANTS: Manufacturing or distribution sites that fulfill orders.
-- CAPACITY_UNITS_PER_DAY is used in analytics to detect over-utilized plants.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE TABLE RAW.PLANTS (
    PLANT_ID                VARCHAR(20)     NOT NULL,
    PLANT_NAME              VARCHAR(100)    NOT NULL,
    COUNTRY                 VARCHAR(50)     NOT NULL,
    REGION                  VARCHAR(30)     NOT NULL,
    CAPACITY_UNITS_PER_DAY  INTEGER         NOT NULL,
    CREATED_AT              TIMESTAMP_NTZ   DEFAULT CURRENT_TIMESTAMP(),
    UPDATED_AT              TIMESTAMP_NTZ   DEFAULT CURRENT_TIMESTAMP(),

    CONSTRAINT PK_PLANTS PRIMARY KEY (PLANT_ID)
);

-- -----------------------------------------------------------------------------
-- CUSTOMERS: End consumers of shipped goods.
-- SEGMENT drives Revenue At Risk prioritization (Enterprise orders matter more).
-- -----------------------------------------------------------------------------
CREATE OR REPLACE TABLE RAW.CUSTOMERS (
    CUSTOMER_ID         VARCHAR(20)     NOT NULL,
    CUSTOMER_NAME       VARCHAR(100)    NOT NULL,
    SEGMENT             VARCHAR(20)     NOT NULL,  -- Enterprise, SMB, Government
    COUNTRY             VARCHAR(50)     NOT NULL,
    REGION              VARCHAR(30)     NOT NULL,
    CREATED_AT          TIMESTAMP_NTZ   DEFAULT CURRENT_TIMESTAMP(),
    UPDATED_AT          TIMESTAMP_NTZ   DEFAULT CURRENT_TIMESTAMP(),

    CONSTRAINT PK_CUSTOMERS PRIMARY KEY (CUSTOMER_ID)
);

-- -----------------------------------------------------------------------------
-- ORDERS: The central fact table. Each order links a customer to a part,
-- fulfilled by a supplier from a specific plant.
--
-- CRITICAL: Three date columns encode the conflicting OTIF definitions:
--   PROMISED_DELIVERY_DATE   → set by ERP when order is placed
--   SUPPLIER_COMMITMENT_DATE → set by the supplier, often more generous
--   (CARRIER_ETA lives on SHIPMENTS since it's set at ship-time)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE TABLE RAW.ORDERS (
    ORDER_ID                    VARCHAR(20)     NOT NULL,
    CUSTOMER_ID                 VARCHAR(20)     NOT NULL,
    PART_ID                     VARCHAR(20)     NOT NULL,
    SUPPLIER_ID                 VARCHAR(20)     NOT NULL,
    PLANT_ID                    VARCHAR(20)     NOT NULL,
    ORDER_DATE                  DATE            NOT NULL,
    PROMISED_DELIVERY_DATE      DATE            NOT NULL,  -- ERP's promise to customer
    SUPPLIER_COMMITMENT_DATE    DATE            NOT NULL,  -- supplier's promise to plant
    QUANTITY_ORDERED            INTEGER         NOT NULL,
    UNIT_PRICE                  NUMBER(12,2)    NOT NULL,
    ORDER_STATUS                VARCHAR(20)     NOT NULL,  -- OPEN, SHIPPED, DELIVERED, CANCELLED
    CREATED_AT                  TIMESTAMP_NTZ   DEFAULT CURRENT_TIMESTAMP(),
    UPDATED_AT                  TIMESTAMP_NTZ   DEFAULT CURRENT_TIMESTAMP(),

    CONSTRAINT PK_ORDERS PRIMARY KEY (ORDER_ID)
);

-- -----------------------------------------------------------------------------
-- SHIPMENTS: Physical movement of goods for an order.
-- One order can have multiple partial shipments (split shipments).
--
-- CARRIER_ETA is the logistics team's estimated arrival — the third OTIF date.
-- DELIVERY_DATE is NULL until the shipment is actually delivered.
-- QUANTITY_SHIPPED vs QUANTITY_ORDERED (on ORDERS) drives Fill Rate.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE TABLE RAW.SHIPMENTS (
    SHIPMENT_ID         VARCHAR(20)     NOT NULL,
    ORDER_ID            VARCHAR(20)     NOT NULL,
    SHIP_DATE           DATE            NOT NULL,
    CARRIER_ETA         DATE            NOT NULL,  -- logistics team's estimated delivery
    DELIVERY_DATE       DATE,                      -- NULL if in transit
    QUANTITY_SHIPPED    INTEGER         NOT NULL,
    CARRIER             VARCHAR(50)     NOT NULL,
    SHIPPING_COST       NUMBER(10,2)    NOT NULL,
    CREATED_AT          TIMESTAMP_NTZ   DEFAULT CURRENT_TIMESTAMP(),
    UPDATED_AT          TIMESTAMP_NTZ   DEFAULT CURRENT_TIMESTAMP(),

    CONSTRAINT PK_SHIPMENTS PRIMARY KEY (SHIPMENT_ID)
);
