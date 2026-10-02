-- =============================================================================
-- ChainTruth: Ontology Tables (Metadata Layer)
-- =============================================================================
-- The ontology layer is what makes ChainTruth a *governed* platform rather than
-- just another dashboard. It captures:
--
-- 1. ENTITY_TYPE     — registry of all business entities and their source tables
-- 2. RELATIONSHIP_TYPE — how entities connect (supplier→part, order→shipment, etc.)
-- 3. METRIC_REGISTRY — the critical piece: every metric definition, including
--                      the THREE conflicting OTIF definitions, with their SQL,
--                      owner, and lineage so stakeholders can see exactly why
--                      numbers differ across teams.
-- =============================================================================

USE DATABASE CHAINTRUTH_DB;
USE SCHEMA ONTOLOGY;

-- -----------------------------------------------------------------------------
-- ENTITY_TYPE: Catalog of business entities in the supply chain graph.
-- Used by the Cortex Agent to understand what objects exist and how to describe
-- them in natural language responses.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE TABLE ONTOLOGY.ENTITY_TYPE (
    ENTITY_TYPE_ID      VARCHAR(30)     NOT NULL,
    ENTITY_NAME         VARCHAR(50)     NOT NULL,
    DESCRIPTION         VARCHAR(500)    NOT NULL,
    SOURCE_TABLE        VARCHAR(100)    NOT NULL,  -- FQN: CHAINTRUTH_DB.RAW.<table>
    PRIMARY_KEY_COLUMN  VARCHAR(50)     NOT NULL,
    CREATED_AT          TIMESTAMP_NTZ   DEFAULT CURRENT_TIMESTAMP(),

    CONSTRAINT PK_ENTITY_TYPE PRIMARY KEY (ENTITY_TYPE_ID)
);

-- -----------------------------------------------------------------------------
-- RELATIONSHIP_TYPE: Directed edges in the supply chain entity graph.
-- FROM_ENTITY → TO_ENTITY with cardinality and the join column.
-- This powers lineage queries: "What entities does a Shipment depend on?"
-- and helps the Semantic View define correct join paths.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE TABLE ONTOLOGY.RELATIONSHIP_TYPE (
    RELATIONSHIP_ID     VARCHAR(30)     NOT NULL,
    RELATIONSHIP_NAME   VARCHAR(100)    NOT NULL,
    FROM_ENTITY_TYPE_ID VARCHAR(30)     NOT NULL,  -- FK → ENTITY_TYPE
    TO_ENTITY_TYPE_ID   VARCHAR(30)     NOT NULL,  -- FK → ENTITY_TYPE
    CARDINALITY         VARCHAR(20)     NOT NULL,  -- ONE_TO_MANY, MANY_TO_ONE, MANY_TO_MANY
    JOIN_COLUMN_FROM    VARCHAR(50)     NOT NULL,
    JOIN_COLUMN_TO      VARCHAR(50)     NOT NULL,
    DESCRIPTION         VARCHAR(500),
    CREATED_AT          TIMESTAMP_NTZ   DEFAULT CURRENT_TIMESTAMP(),

    CONSTRAINT PK_RELATIONSHIP PRIMARY KEY (RELATIONSHIP_ID)
);

-- -----------------------------------------------------------------------------
-- METRIC_REGISTRY: The heart of governance — every metric has a row here.
--
-- For OTIF specifically, three rows exist:
--   OTIF_ERP        → delivery_date <= promised_delivery_date
--   OTIF_LOGISTICS  → delivery_date <= carrier_eta
--   OTIF_SUPPLIER   → ship_date    <= supplier_commitment_date
--
-- Each row records:
--   METRIC_SQL      — the actual SQL expression (executable, not pseudocode)
--   OWNER_TEAM      — who owns this definition (Finance, Logistics, Procurement)
--   SOURCE_COLUMNS  — which columns feed the metric (for lineage)
--   IS_CANONICAL    — boolean: is this the "golden" definition? Only one per metric
--
-- The Semantic View and Cortex Agent reference IS_CANONICAL = TRUE definitions.
-- The dashboard shows all three OTIF variants side-by-side for reconciliation.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE TABLE ONTOLOGY.METRIC_REGISTRY (
    METRIC_ID           VARCHAR(30)     NOT NULL,
    METRIC_NAME         VARCHAR(100)    NOT NULL,
    METRIC_VARIANT      VARCHAR(50),              -- NULL for non-conflicting metrics
    DESCRIPTION         VARCHAR(1000)   NOT NULL,
    METRIC_SQL          VARCHAR(2000)   NOT NULL,  -- executable SQL expression
    UNIT                VARCHAR(20)     NOT NULL,  -- PERCENTAGE, DAYS, USD, COUNT
    DIRECTION           VARCHAR(20)     NOT NULL,  -- HIGHER_IS_BETTER, LOWER_IS_BETTER
    OWNER_TEAM          VARCHAR(50)     NOT NULL,  -- which team owns this definition
    SOURCE_TABLES       VARCHAR(500)    NOT NULL,  -- comma-separated FQNs
    SOURCE_COLUMNS      VARCHAR(500)    NOT NULL,  -- comma-separated column names
    IS_CANONICAL        BOOLEAN         NOT NULL DEFAULT FALSE,
    CREATED_AT          TIMESTAMP_NTZ   DEFAULT CURRENT_TIMESTAMP(),
    UPDATED_AT          TIMESTAMP_NTZ   DEFAULT CURRENT_TIMESTAMP(),

    CONSTRAINT PK_METRIC_REGISTRY PRIMARY KEY (METRIC_ID)
);
