# Databricks notebook source
"""
Watermark Manager - Handle incremental load watermarks
"""

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from datetime import datetime
from typing import Any, List, Optional
from delta.tables import DeltaTable


class WatermarkManager:
    """Manage watermarks for incremental data loads"""
    
    def __init__(self, spark: SparkSession, catalog: str, schema: str):
        self.spark = spark
        self.catalog = catalog
        self.schema = schema
        self.watermark_table = f"{catalog}.{schema}._watermarks"
        self._ensure_watermark_table()
    
    def _ensure_watermark_table(self):
        """Create watermark table if it doesn't exist - uses existing schema"""
        self.spark.sql(f"USE CATALOG {self.catalog}")
        self.spark.sql(f"USE SCHEMA {self.schema}")
        
        # Check if table exists and get its schema
        try:
            existing_df = self.spark.read.table(self.watermark_table)
            self.existing_columns = set(existing_df.columns)
            
            # Detect schema version
            if 'pipeline_id' in self.existing_columns:
                self.schema_version = 'v2'  # New schema
            else:
                self.schema_version = 'v1'  # Old schema (databaseName, tableName, etc.)
        except:
            # Table doesn't exist, create with new schema
            self.schema_version = 'v2'
            self.spark.sql(f"""
                CREATE TABLE IF NOT EXISTS {self.watermark_table} (
                    pipeline_id STRING,
                    source_connection STRING,
                    source_schema STRING,
                    source_table STRING,
                    watermark_column STRING,
                    watermark_type STRING,
                    watermark_value_timestamp TIMESTAMP,
                    watermark_value_bigint BIGINT,
                    watermark_value_int INT,
                    watermark_value_string STRING,
                    last_updated TIMESTAMP,
                    last_record_count BIGINT
                )
                USING DELTA
                PARTITIONED BY (pipeline_id)
            """)
    
    def get_watermark(self, pipeline_id: str, source_connection: str, 
                     source_schema: str, source_table: str) -> Optional[Any]:
        """Get current watermark value for a pipeline"""
        df = self.spark.read.table(self.watermark_table)
        
        # Use appropriate column names based on schema version
        if self.schema_version == 'v1':
            # Old schema: use tableName to match
            df = df.where(F.col("tableName") == source_table)
        else:
            # New schema: use all identifiers
            df = df.where(
                (F.col("pipeline_id") == pipeline_id) &
                (F.col("source_connection") == source_connection) &
                (F.col("source_schema") == source_schema) &
                (F.col("source_table") == source_table)
            )
        
        if df.count() == 0:
            return None
        
        row = df.first()
        
        # Get watermark type and value based on schema version
        if self.schema_version == 'v1':
            watermark_type = row.wmType
            if watermark_type == "timestamp":
                wm_value = row.timestampWm
                # Ensure it's a datetime object
                if wm_value and not isinstance(wm_value, datetime):
                    from pyspark.sql.types import TimestampType
                    # Convert to datetime if it's not already
                    return datetime.fromisoformat(str(wm_value))
                return wm_value
            elif watermark_type == "bigint":
                return row.bigIntWm
            elif watermark_type == "int":
                return row.intWm
            elif watermark_type == "string":
                return row.stringWm
        else:
            watermark_type = row.watermark_type
            if watermark_type == "timestamp":
                wm_value = row.watermark_value_timestamp
                # Ensure it's a datetime object
                if wm_value and not isinstance(wm_value, datetime):
                    return datetime.fromisoformat(str(wm_value))
                return wm_value
            elif watermark_type == "bigint":
                return row.watermark_value_bigint
            elif watermark_type == "int":
                return row.watermark_value_int
            elif watermark_type == "string":
                return row.watermark_value_string
        
        return None
    
    def initialize_watermark(self, pipeline_id: str, source_connection: str,
                           source_schema: str, source_table: str, 
                           watermark_column: str, watermark_type: str = "timestamp"):
        """Initialize watermark with default value"""
        default_timestamp = datetime(1900, 1, 1, 0, 0, 0)
        
        if self.schema_version == 'v1':
            # Old schema
            self.spark.sql(f"""
                INSERT INTO {self.watermark_table} (
                    databaseName, tableName, wmType, timestampWm,
                    bigIntWm, intWm, stringWm
                ) VALUES (
                    '{source_schema}', '{source_table}', 'timestamp',
                    CAST('1900-01-01 00:00:00' AS TIMESTAMP),
                    NULL, NULL, NULL
                )
            """)
        else:
            # New schema
            self.spark.sql(f"""
                INSERT INTO {self.watermark_table} (
                    pipeline_id, source_connection, source_schema, source_table,
                    watermark_column, watermark_type, watermark_value_timestamp,
                    watermark_value_bigint, watermark_value_int, watermark_value_string,
                    last_updated, last_record_count
                ) VALUES (
                    '{pipeline_id}', '{source_connection}', '{source_schema}', '{source_table}',
                    '{watermark_column}', '{watermark_type}', 
                    CAST('{default_timestamp}' AS TIMESTAMP),
                    NULL, NULL, NULL,
                    CURRENT_TIMESTAMP(), 0
                )
            """)
    
    def update_watermark(self, pipeline_id: str, source_connection: str,
                        source_schema: str, source_table: str,
                        watermark_column: str, new_value: Any, 
                        record_count: int):
        """Update watermark with new value"""
        # Determine watermark type from value
        if isinstance(new_value, datetime):
            watermark_type = "timestamp"
        elif isinstance(new_value, int):
            if new_value > 2147483647:  # Max INT value
                watermark_type = "bigint"
            else:
                watermark_type = "int"
        else:
            watermark_type = "string"
        
        # Check if watermark exists
        existing = self.get_watermark(pipeline_id, source_connection, source_schema, source_table)
        
        if existing is None:
            # Initialize first
            self.initialize_watermark(pipeline_id, source_connection, source_schema, 
                                     source_table, watermark_column, watermark_type)
        
        # Perform merge update
        watermark_table = DeltaTable.forName(self.spark, self.watermark_table)
        
        if self.schema_version == 'v1':
            # Old schema - use SQL INSERT/UPDATE instead of DataFrame
            from pyspark.sql import Row
            
            # Check if record exists
            existing_count = self.spark.sql(f"""
                SELECT COUNT(*) as cnt FROM {self.watermark_table}
                WHERE databaseName = '{source_schema}' AND tableName = '{source_table}'
            """).collect()[0]['cnt']
            
            if existing_count > 0:
                # Update existing record
                if watermark_type == "timestamp":
                    # Format timestamp properly
                    if isinstance(new_value, datetime):
                        ts_str = new_value.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        ts_str = str(new_value)
                    self.spark.sql(f"""
                        UPDATE {self.watermark_table}
                        SET timestampWm = CAST('{ts_str}' AS TIMESTAMP), wmType = 'timestamp'
                        WHERE databaseName = '{source_schema}' AND tableName = '{source_table}'
                    """)
                elif watermark_type == "bigint":
                    self.spark.sql(f"""
                        UPDATE {self.watermark_table}
                        SET bigIntWm = {new_value}, wmType = '{watermark_type}'
                        WHERE databaseName = '{source_schema}' AND tableName = '{source_table}'
                    """)
                elif watermark_type == "int":
                    self.spark.sql(f"""
                        UPDATE {self.watermark_table}
                        SET intWm = {new_value}, wmType = '{watermark_type}'
                        WHERE databaseName = '{source_schema}' AND tableName = '{source_table}'
                    """)
                else:
                    self.spark.sql(f"""
                        UPDATE {self.watermark_table}
                        SET stringWm = '{new_value}', wmType = '{watermark_type}'
                        WHERE databaseName = '{source_schema}' AND tableName = '{source_table}'
                    """)
            else:
                # Insert new record
                if watermark_type == "timestamp":
                    # Format timestamp properly
                    if isinstance(new_value, datetime):
                        ts_str = new_value.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        ts_str = str(new_value)
                    self.spark.sql(f"""
                        INSERT INTO {self.watermark_table} (databaseName, tableName, wmType, timestampWm)
                        VALUES ('{source_schema}', '{source_table}', 'timestamp', CAST('{ts_str}' AS TIMESTAMP))
                    """)
                elif watermark_type == "bigint":
                    self.spark.sql(f"""
                        INSERT INTO {self.watermark_table} (databaseName, tableName, wmType, bigIntWm)
                        VALUES ('{source_schema}', '{source_table}', '{watermark_type}', {new_value})
                    """)
                elif watermark_type == "int":
                    self.spark.sql(f"""
                        INSERT INTO {self.watermark_table} (databaseName, tableName, wmType, intWm)
                        VALUES ('{source_schema}', '{source_table}', '{watermark_type}', {new_value})
                    """)
                else:
                    self.spark.sql(f"""
                        INSERT INTO {self.watermark_table} (databaseName, tableName, wmType, stringWm)
                        VALUES ('{source_schema}', '{source_table}', '{watermark_type}', '{new_value}')
                    """)
        else:
            # New schema
            update_data = self.spark.createDataFrame([{
                'pipeline_id': pipeline_id,
                'source_connection': source_connection,
                'source_schema': source_schema,
                'source_table': source_table,
                'watermark_column': watermark_column,
                'watermark_type': watermark_type,
                'watermark_value_timestamp': new_value if watermark_type == "timestamp" else None,
                'watermark_value_bigint': new_value if watermark_type == "bigint" else None,
                'watermark_value_int': new_value if watermark_type == "int" else None,
                'watermark_value_string': str(new_value) if watermark_type == "string" else None,
                'last_updated': datetime.now(),
                'last_record_count': record_count
            }])
            
            watermark_table.alias('target').merge(
                update_data.alias('source'),
                """target.pipeline_id = source.pipeline_id AND 
                   target.source_connection = source.source_connection AND
                   target.source_schema = source.source_schema AND
                   target.source_table = source.source_table"""
            ).whenMatchedUpdateAll() \
             .whenNotMatchedInsertAll() \
             .execute()
    
    def get_max_watermark_from_df(self, df: DataFrame, 
                                  watermark_columns: List[str]) -> Any:
        """Extract maximum watermark value from DataFrame"""
        if len(watermark_columns) == 1:
            max_col = watermark_columns[0]
        else:
            # Use greatest of multiple columns
            df = df.withColumn('_max_watermark', F.greatest(*watermark_columns))
            max_col = '_max_watermark'
        
        max_value = df.agg({max_col: "max"}).collect()[0][0]
        
        # Ensure timestamp is properly formatted
        if max_value and hasattr(max_value, 'strftime'):
            # It's a datetime/timestamp - return as-is
            return max_value
        
        return max_value
