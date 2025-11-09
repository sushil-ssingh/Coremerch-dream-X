-- Create schema for coremerch pipelines
-- Run this in Databricks SQL Editor or as a notebook

-- Create the schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS dev_ent_bronze_db.cormerch
COMMENT 'Core Merchandising data from Oracle sources';

-- Verify schema was created
SHOW SCHEMAS IN dev_ent_bronze_db LIKE 'cormerch';

-- Grant permissions (update with your group names)
-- GRANT ALL PRIVILEGES ON SCHEMA dev_ent_bronze_db.coremerch TO `g_az_sf_coremerch_engineers`;
