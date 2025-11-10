# Databricks notebook source
"""
Universal Data Sync - Generic pipeline for syncing data between any databases
Supports: Oracle <-> Databricks, Azure SQL <-> Databricks, and any combination
"""

from databricks.sdk.runtime import dbutils
from pyspark.sql import SparkSession, functions as F
from datetime import datetime
import sys

# COMMAND ----------

# MAGIC %run ./database_adapters

# COMMAND ----------

# MAGIC %run ./watermark_manager

# COMMAND ----------

# MAGIC %run ./config_loader

# COMMAND ----------

# Widget parameters
dbutils.widgets.text("pipeline_id", "", "Pipeline ID")
dbutils.widgets.text("env", "dev", "Environment")
dbutils.widgets.text("workspace_path", "", "Workspace Path")

# Get parameters
pipeline_id = dbutils.widgets.get("pipeline_id")
env = dbutils.widgets.get("env")
workspace_path = dbutils.widgets.get("workspace_path")

# COMMAND ----------

def log_message(level: str, message: str):
    """Log messages with timestamp"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] [{level}] {message}")

# COMMAND ----------

def run_pipeline(pipeline_id: str, env: str, workspace_path: str):
    """Execute a data sync pipeline"""
    
    log_message("INFO", f"Starting pipeline: {pipeline_id}")
    log_message("INFO", f"Environment: {env}")
    
    # Initialize
    spark = SparkSession.builder.getOrCreate()
    config_loader = ConfigLoader(workspace_path)
    
    # Load configurations
    log_message("INFO", "Loading configurations...")
    connections = config_loader.load_connections()
    pipelines = config_loader.load_pipelines()
    
    # Get pipeline config
    pipeline_config = config_loader.get_pipeline(pipeline_id)
    if not pipeline_config:
        raise ValueError(f"Pipeline not found: {pipeline_id}")
    
    if not pipeline_config.get('enabled', True):
        log_message("WARNING", f"Pipeline is disabled: {pipeline_id}")
        return
    
    # Validate pipeline
    is_valid, message = config_loader.validate_pipeline(pipeline_config)
    if not is_valid:
        raise ValueError(f"Invalid pipeline configuration: {message}")
    
    log_message("INFO", f"Pipeline description: {pipeline_config.get('description', 'N/A')}")
    
    # Get source and target configurations
    source_config = pipeline_config['source']
    target_config = pipeline_config['target']
    sync_config = pipeline_config['sync_config']
    
    # Get connection details
    source_conn_id = source_config['connection']
    target_conn_id = target_config['connection']
    
    source_connection = config_loader.get_connection(source_conn_id)
    target_connection = config_loader.get_connection(target_conn_id)
    
    if not source_connection:
        raise ValueError(f"Source connection not found: {source_conn_id}")
    if not target_connection:
        raise ValueError(f"Target connection not found: {target_conn_id}")
    
    # Create database adapters
    log_message("INFO", f"Initializing source adapter: {source_connection['type']}")
    source_adapter = get_adapter(source_connection, spark)
    
    log_message("INFO", f"Initializing target adapter: {target_connection['type']}")
    target_adapter = get_adapter(target_connection, spark)
    
    # Extract sync parameters
    sync_mode = sync_config.get('mode', 'full')
    write_mode = sync_config.get('write_mode', 'overwrite')
    watermark_columns = sync_config.get('watermark_columns', [])
    partitions = sync_config.get('partitions', 1)
    fetch_size = sync_config.get('fetch_size', 10000)
    merge_keys = sync_config.get('merge_keys')
    
    # Source table details
    source_schema = source_config.get('schema')
    source_table = source_config['table']
    source_query = source_config.get('query')
    
    # Target table details
    target_schema = target_config.get('schema')
    target_table = target_config['table']
    
    log_message("INFO", f"Source: {source_schema}.{source_table if source_schema else source_table}")
    log_message("INFO", f"Target: {target_schema}.{target_table if target_schema else target_table}")
    log_message("INFO", f"Sync mode: {sync_mode}")
    log_message("INFO", f"Write mode: {write_mode}")
    
    # Initialize watermark manager (only for Databricks targets)
    watermark_manager = None
    if target_connection['type'] == 'databricks':
        target_catalog = target_connection.get('catalog')
        target_schema_name = target_connection.get('schema', target_schema)
        watermark_manager = WatermarkManager(spark, target_catalog, target_schema_name)
    
    # Build query based on sync mode
    final_query = source_query
    
    if sync_mode == 'incremental' and watermark_columns and watermark_manager:
        log_message("INFO", "Checking watermark for incremental load...")
        
        # Get current watermark
        watermark_value = watermark_manager.get_watermark(
            pipeline_id, source_conn_id, 
            source_schema or '', source_table
        )
        
        if watermark_value is None:
            log_message("INFO", "No watermark found, initializing...")
            watermark_manager.initialize_watermark(
                pipeline_id, source_conn_id,
                source_schema or '', source_table,
                watermark_columns[0]
            )
            watermark_value = watermark_manager.get_watermark(
                pipeline_id, source_conn_id,
                source_schema or '', source_table
            )
        
        log_message("INFO", f"Current watermark: {watermark_value} (type: {type(watermark_value).__name__})")
        
        # Show the actual filter being used
        filter_clause = source_adapter.get_incremental_filter(watermark_columns, watermark_value)
        log_message("INFO", f"Incremental filter: {filter_clause}")
        
        # Build incremental filter
        if not source_query:
            filter_clause = source_adapter.get_incremental_filter(watermark_columns, watermark_value)
            full_table = f"{source_schema}.{source_table}" if source_schema else source_table
            final_query = f"SELECT * FROM {full_table} WHERE {filter_clause}"
            log_message("INFO", f"Incremental query: {final_query}")
    
    # Read data from source
    log_message("INFO", "Reading data from source...")
    start_time = datetime.now()
    
    source_df = source_adapter.read_data(
        schema=source_schema,
        table=source_table,
        query=final_query,
        partitions=partitions,
        fetch_size=fetch_size
    )
    
    # Count records
    record_count = source_df.count()
    log_message("INFO", f"Records read: {record_count:,}")
    
    if record_count == 0:
        log_message("WARNING", "No data to sync")
        return {
            'status': 'SUCCESS',
            'records_synced': 0,
            'message': 'No new records found',
            'pipeline_id': pipeline_id
        }
    
    # For incremental loads, track new watermark
    new_watermark = None
    if sync_mode == 'incremental' and watermark_columns and record_count > 0:
        new_watermark = watermark_manager.get_max_watermark_from_df(source_df, watermark_columns)
        log_message("INFO", f"New watermark value: {new_watermark}")
    
    # Write data to target
    log_message("INFO", "Writing data to target...")
    
    target_adapter.write_data(
        df=source_df,
        schema=target_schema,
        table=target_table,
        write_mode=write_mode,
        merge_keys=merge_keys
    )
    
    # Update watermark
    if sync_mode == 'incremental' and new_watermark and watermark_manager:
        log_message("INFO", "Updating watermark...")
        watermark_manager.update_watermark(
            pipeline_id, source_conn_id,
            source_schema or '', source_table,
            watermark_columns[0], new_watermark,
            record_count
        )
    
    # Calculate duration
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    log_message("INFO", f"Pipeline completed successfully in {duration:.2f} seconds")
    log_message("INFO", f"Records synced: {record_count:,}")
    
    return {
        'status': 'SUCCESS',
        'records_synced': record_count,
        'duration_seconds': duration,
        'pipeline_id': pipeline_id
    }

# COMMAND ----------

# Execute pipeline
try:
    result = run_pipeline(pipeline_id, env, workspace_path)
    
    # Format success message with details
    if result:
        records = result.get('records_synced', 0)
        duration = result.get('duration_seconds', 0)
        if records == 0:
            message = f"SUCCESS: No new records to sync"
        else:
            message = f"SUCCESS: Synced {records:,} records in {duration:.1f}s"
        dbutils.notebook.exit(message)
    else:
        dbutils.notebook.exit("SUCCESS: No data to sync")
        
except Exception as e:
    log_message("ERROR", f"Pipeline failed: {str(e)}")
    import traceback
    traceback.print_exc()
    raise  # Re-raise the exception so Databricks marks it as failed
