-- =============================================================================
-- ChainTruth: Database & Schema Setup
-- =============================================================================
-- Creates the CHAINTRUTH_DB database with four schemas:
--   RAW       - Bronze layer: raw entity tables with synthetic supply chain data
--   ONTOLOGY  - Metadata layer: entity types, relationships, metric definitions
--   ANALYTICS - Gold layer: dynamic tables, aggregated metrics (created later)
--   APP       - Presentation layer: Streamlit app, Cortex Agent (created later)
-- =============================================================================

USE ROLE SYSADMIN;

CREATE DATABASE IF NOT EXISTS CHAINTRUTH_DB
    COMMENT = 'ChainTruth: Governed supply chain analytics platform';

CREATE SCHEMA IF NOT EXISTS CHAINTRUTH_DB.RAW
    COMMENT = 'Bronze layer - raw entity tables with synthetic data';

CREATE SCHEMA IF NOT EXISTS CHAINTRUTH_DB.ONTOLOGY
    COMMENT = 'Metadata layer - entity types, relationships, metric registry';

CREATE SCHEMA IF NOT EXISTS CHAINTRUTH_DB.ANALYTICS
    COMMENT = 'Gold layer - dynamic tables and aggregated metric views';

CREATE SCHEMA IF NOT EXISTS CHAINTRUTH_DB.APP
    COMMENT = 'Presentation layer - Streamlit dashboard and Cortex Agent';

-- Warehouse for pipeline workloads
CREATE WAREHOUSE IF NOT EXISTS CHAINTRUTH_WH
    WAREHOUSE_SIZE = 'XSMALL'
    AUTO_SUSPEND = 60
    AUTO_RESUME = TRUE
    COMMENT = 'Compute for ChainTruth pipelines and queries';

USE WAREHOUSE CHAINTRUTH_WH;
USE DATABASE CHAINTRUTH_DB;
