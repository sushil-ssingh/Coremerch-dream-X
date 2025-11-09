# Databricks notebook source
"""
Pipeline Validator - Validate configurations before deployment
Run this notebook to check your configuration files for errors
"""

from config_loader import ConfigLoader
from database_adapters import get_adapter
from pyspark.sql import SparkSession
import sys

# COMMAND ----------

def validate_all_configurations(workspace_path: str):
    """Validate all configuration files"""
    
    print("=" * 80)
    print("PIPELINE CONFIGURATION VALIDATOR")
    print("=" * 80)
    print()
    
    spark = SparkSession.builder.getOrCreate()
    loader = ConfigLoader(workspace_path)
    
    # Load configurations
    print("📂 Loading configurations...")
    try:
        connections = loader.load_connections()
        print(f"   ✓ Loaded {len(connections)} connections")
    except Exception as e:
        print(f"   ✗ Failed to load connections: {e}")
        return False
    
    try:
        pipelines = loader.load_pipelines()
        print(f"   ✓ Loaded {len(pipelines)} pipelines")
    except Exception as e:
        print(f"   ✗ Failed to load pipelines: {e}")
        return False
    
    print()
    
    # Validate connections
    print("🔌 Validating Connections...")
    print("-" * 80)
    
    connection_valid = True
    for conn_id, conn_config in connections.items():
        print(f"\n   Connection: {conn_id}")
        print(f"   Type: {conn_config.get('type', 'MISSING')}")
        
        # Check required fields
        required_fields = {
            'oracle': ['type', 'host', 'port', 'service_name', 'username', 'secret_scope', 'secret_key'],
            'azure_sql': ['type', 'host', 'database', 'username', 'secret_scope', 'secret_key'],
            'databricks': ['type', 'catalog', 'schema']
        }
        
        db_type = conn_config.get('type', '').lower()
        if db_type not in required_fields:
            print(f"   ✗ Unknown database type: {db_type}")
            connection_valid = False
            continue
        
        missing_fields = []
        for field in required_fields[db_type]:
            if field not in conn_config:
                missing_fields.append(field)
        
        if missing_fields:
            print(f"   ✗ Missing required fields: {', '.join(missing_fields)}")
            connection_valid = False
        else:
            print(f"   ✓ All required fields present")
            
            # Try to create adapter
            try:
                adapter = get_adapter(conn_config, spark)
                print(f"   ✓ Adapter created successfully")
            except Exception as e:
                print(f"   ✗ Failed to create adapter: {e}")
                connection_valid = False
    
    print()
    
    # Validate pipelines
    print("🔄 Validating Pipelines...")
    print("-" * 80)
    
    pipeline_valid = True
    enabled_count = 0
    disabled_count = 0
    
    for pipeline in pipelines:
        pipeline_id = pipeline.get('pipeline_id', 'UNKNOWN')
        enabled = pipeline.get('enabled', True)
        
        if enabled:
            enabled_count += 1
        else:
            disabled_count += 1
        
        status = "ENABLED" if enabled else "DISABLED"
        print(f"\n   Pipeline: {pipeline_id} [{status}]")
        
        if not enabled:
            print(f"   ⊘ Skipping validation (disabled)")
            continue
        
        # Validate pipeline structure
        is_valid, message = loader.validate_pipeline(pipeline)
        
        if not is_valid:
            print(f"   ✗ {message}")
            pipeline_valid = False
            continue
        
        # Check source connection
        source_conn = pipeline['source'].get('connection')
        if source_conn not in connections:
            print(f"   ✗ Source connection not found: {source_conn}")
            pipeline_valid = False
        else:
            print(f"   ✓ Source connection: {source_conn}")
        
        # Check target connection
        target_conn = pipeline['target'].get('connection')
        if target_conn not in connections:
            print(f"   ✗ Target connection not found: {target_conn}")
            pipeline_valid = False
        else:
            print(f"   ✓ Target connection: {target_conn}")
        
        # Check sync config
        sync_config = pipeline.get('sync_config', {})
        mode = sync_config.get('mode')
        
        if mode not in ['full', 'incremental']:
            print(f"   ✗ Invalid sync mode: {mode} (must be 'full' or 'incremental')")
            pipeline_valid = False
        else:
            print(f"   ✓ Sync mode: {mode}")
        
        # Check watermark for incremental
        if mode == 'incremental':
            watermark_cols = sync_config.get('watermark_columns', [])
            if not watermark_cols:
                print(f"   ⚠ Warning: Incremental mode but no watermark_columns defined")
            else:
                print(f"   ✓ Watermark columns: {', '.join(watermark_cols)}")
        
        # Check write mode
        write_mode = sync_config.get('write_mode')
        if write_mode not in ['append', 'overwrite', 'merge']:
            print(f"   ✗ Invalid write mode: {write_mode}")
            pipeline_valid = False
        else:
            print(f"   ✓ Write mode: {write_mode}")
        
        # Check merge keys if merge mode
        if write_mode == 'merge':
            merge_keys = sync_config.get('merge_keys', [])
            if not merge_keys:
                print(f"   ✗ Merge mode requires merge_keys")
                pipeline_valid = False
            else:
                print(f"   ✓ Merge keys: {', '.join(merge_keys)}")
    
    print()
    
    # Summary
    print("=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    print()
    print(f"Connections: {len(connections)} total")
    print(f"Pipelines: {enabled_count} enabled, {disabled_count} disabled")
    print()
    
    if connection_valid and pipeline_valid:
        print("✅ ALL VALIDATIONS PASSED")
        print()
        print("Your configuration is ready to deploy!")
        print()
        print("Next steps:")
        print("  1. databricks bundle deploy --target development")
        print("  2. databricks bundle run universal-data-sync --target development")
        return True
    else:
        print("❌ VALIDATION FAILED")
        print()
        print("Please fix the errors above before deploying.")
        return False

# COMMAND ----------

# Run validation
workspace_path = dbutils.widgets.get("workspace_path") if "workspace_path" in [w.name for w in dbutils.widgets.getAll()] else "/Workspace/path/to/project"

dbutils.widgets.text("workspace_path", workspace_path, "Workspace Path")
workspace_path = dbutils.widgets.get("workspace_path")

result = validate_all_configurations(workspace_path)

if result:
    dbutils.notebook.exit("VALIDATION_PASSED")
else:
    dbutils.notebook.exit("VALIDATION_FAILED")
