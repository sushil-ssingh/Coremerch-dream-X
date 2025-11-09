# Databricks notebook source
"""
Database Adapters - Abstract database-specific logic
Supports Oracle, Azure SQL, and Databricks
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pyspark.sql import DataFrame, SparkSession
from datetime import datetime


class DatabaseAdapter(ABC):
    """Base class for database adapters"""
    
    def __init__(self, connection_config: Dict[str, Any], spark: SparkSession):
        self.config = connection_config
        self.spark = spark
        self.db_type = connection_config.get('type')
        
    @abstractmethod
    def build_jdbc_url(self) -> str:
        """Build JDBC connection URL"""
        pass
    
    @abstractmethod
    def get_incremental_filter(self, watermark_columns: List[str], watermark_value: Any) -> str:
        """Generate SQL filter for incremental loads (database-specific syntax)"""
        pass
    
    @abstractmethod
    def read_data(self, schema: Optional[str], table: str, query: Optional[str], 
                  partitions: int, fetch_size: int) -> DataFrame:
        """Read data from source"""
        pass
    
    @abstractmethod
    def write_data(self, df: DataFrame, schema: Optional[str], table: str, 
                   write_mode: str, merge_keys: Optional[List[str]] = None):
        """Write data to target"""
        pass
    
    def get_driver(self) -> str:
        """Get JDBC driver class"""
        return self.config.get('driver', '')
    
    def get_maven_coordinates(self) -> str:
        """Get Maven coordinates for JDBC driver"""
        return self.config.get('maven_coordinates', '')
    
    def get_credentials(self, secret_scope: str, secret_key: str) -> str:
        """Retrieve password from Databricks secrets"""
        from databricks.sdk.runtime import dbutils
        return dbutils.secrets.get(scope=secret_scope, key=secret_key)


class OracleAdapter(DatabaseAdapter):
    """Oracle Database Adapter"""
    
    def build_jdbc_url(self) -> str:
        host = self.config['host']
        port = self.config['port']
        service = self.config['service_name']
        return f"jdbc:oracle:thin:@{host}:{port}/{service}"
    
    def get_incremental_filter(self, watermark_columns: List[str], watermark_value: Any) -> str:
        """Oracle-specific date comparison"""
        conditions = []
        for col in watermark_columns:
            if isinstance(watermark_value, datetime):
                date_str = watermark_value.strftime('%Y-%m-%d %H:%M:%S')
                condition = f"{col} > TO_DATE('{date_str}', 'YYYY-MM-DD HH24:MI:SS')"
            else:
                condition = f"{col} > '{watermark_value}'"
            conditions.append(condition)
        return ' OR '.join(conditions)
    
    def read_data(self, schema: Optional[str], table: str, query: Optional[str],
                  partitions: int, fetch_size: int) -> DataFrame:
        """Read from Oracle via JDBC"""
        url = self.build_jdbc_url()
        username = self.config['username']
        password = self.get_credentials(
            self.config['secret_scope'],
            self.config['secret_key']
        )
        
        # Use custom query or build table query
        if query:
            sql_query = query
        else:
            full_table = f"{schema}.{table}" if schema else table
            sql_query = f"SELECT * FROM {full_table}"
        
        df = self.spark.read.format("jdbc") \
            .option("url", url) \
            .option("query", sql_query) \
            .option("user", username) \
            .option("password", password) \
            .option("driver", self.get_driver()) \
            .option("oracle.jdbc.timezoneAsRegion", "false") \
            .option("oracle.jdbc.mapDateToTimestamp", "false") \
            .option("numPartitions", partitions) \
            .option("fetchSize", fetch_size) \
            .option("preferTimestampNTZ", "false") \
            .load()
        
        return df
    
    def write_data(self, df: DataFrame, schema: Optional[str], table: str,
                   write_mode: str, merge_keys: Optional[List[str]] = None):
        """Write to Oracle via JDBC"""
        url = self.build_jdbc_url()
        username = self.config['username']
        password = self.get_credentials(
            self.config['secret_scope'],
            self.config['secret_key']
        )
        
        full_table = f"{schema}.{table}" if schema else table
        
        # Map write modes
        jdbc_mode = "append" if write_mode == "append" else "overwrite"
        
        df.write.format("jdbc") \
            .option("url", url) \
            .option("dbtable", full_table) \
            .option("user", username) \
            .option("password", password) \
            .option("driver", self.get_driver()) \
            .mode(jdbc_mode) \
            .save()


class AzureSQLAdapter(DatabaseAdapter):
    """Azure SQL Database Adapter"""
    
    def build_jdbc_url(self) -> str:
        host = self.config['host']
        port = self.config.get('port', 1433)
        database = self.config['database']
        return f"jdbc:sqlserver://{host}:{port};database={database};encrypt=true;trustServerCertificate=false;hostNameInCertificate=*.database.windows.net;loginTimeout=30;"
    
    def get_incremental_filter(self, watermark_columns: List[str], watermark_value: Any) -> str:
        """Azure SQL-specific date comparison"""
        conditions = []
        for col in watermark_columns:
            if isinstance(watermark_value, datetime):
                date_str = watermark_value.strftime('%Y-%m-%d %H:%M:%S')
                condition = f"{col} > CONVERT(DATETIME, '{date_str}', 120)"
            else:
                condition = f"{col} > '{watermark_value}'"
            conditions.append(condition)
        return ' OR '.join(conditions)
    
    def read_data(self, schema: Optional[str], table: str, query: Optional[str],
                  partitions: int, fetch_size: int) -> DataFrame:
        """Read from Azure SQL via JDBC"""
        url = self.build_jdbc_url()
        username = self.config['username']
        password = self.get_credentials(
            self.config['secret_scope'],
            self.config['secret_key']
        )
        
        if query:
            sql_query = query
        else:
            full_table = f"{schema}.{table}" if schema else table
            sql_query = f"SELECT * FROM {full_table}"
        
        df = self.spark.read.format("jdbc") \
            .option("url", url) \
            .option("query", sql_query) \
            .option("user", username) \
            .option("password", password) \
            .option("driver", self.get_driver()) \
            .option("numPartitions", partitions) \
            .option("fetchSize", fetch_size) \
            .load()
        
        return df
    
    def write_data(self, df: DataFrame, schema: Optional[str], table: str,
                   write_mode: str, merge_keys: Optional[List[str]] = None):
        """Write to Azure SQL via JDBC"""
        url = self.build_jdbc_url()
        username = self.config['username']
        password = self.get_credentials(
            self.config['secret_scope'],
            self.config['secret_key']
        )
        
        full_table = f"{schema}.{table}" if schema else table
        jdbc_mode = "append" if write_mode == "append" else "overwrite"
        
        df.write.format("jdbc") \
            .option("url", url) \
            .option("dbtable", full_table) \
            .option("user", username) \
            .option("password", password) \
            .option("driver", self.get_driver()) \
            .mode(jdbc_mode) \
            .save()


class DatabricksAdapter(DatabaseAdapter):
    """Databricks (Delta Lake) Adapter"""
    
    def build_jdbc_url(self) -> str:
        """Not needed for Databricks internal operations"""
        return ""
    
    def get_incremental_filter(self, watermark_columns: List[str], watermark_value: Any) -> str:
        """Databricks SQL filter"""
        conditions = []
        for col in watermark_columns:
            if isinstance(watermark_value, datetime):
                date_str = watermark_value.strftime('%Y-%m-%d %H:%M:%S')
                condition = f"{col} > CAST('{date_str}' AS TIMESTAMP)"
            else:
                condition = f"{col} > '{watermark_value}'"
            conditions.append(condition)
        return ' OR '.join(conditions)
    
    def read_data(self, schema: Optional[str], table: str, query: Optional[str],
                  partitions: int, fetch_size: int) -> DataFrame:
        """Read from Databricks Delta table"""
        catalog = self.config.get('catalog')
        schema = self.config.get('schema', schema)
        
        if query:
            return self.spark.sql(query)
        else:
            full_table = f"{catalog}.{schema}.{table}"
            return self.spark.read.table(full_table)
    
    def write_data(self, df: DataFrame, schema: Optional[str], table: str,
                   write_mode: str, merge_keys: Optional[List[str]] = None):
        """Write to Databricks Delta table"""
        from delta.tables import DeltaTable
        
        catalog = self.config.get('catalog')
        schema = self.config.get('schema', schema)
        full_table = f"{catalog}.{schema}.{table}"
        
        # Set catalog and schema
        self.spark.sql(f"USE CATALOG {catalog}")
        self.spark.sql(f"USE SCHEMA {schema}")
        
        # Check if table exists
        table_exists = self.spark.catalog.tableExists(full_table)
        
        if write_mode == "merge" and merge_keys:
            # Perform merge/upsert operation
            if table_exists:
                delta_table = DeltaTable.forName(self.spark, full_table)
                
                # Build merge condition
                merge_condition = " AND ".join([
                    f"target.{key} = source.{key}" for key in merge_keys
                ])
                
                delta_table.alias("target").merge(
                    df.alias("source"),
                    merge_condition
                ).whenMatchedUpdateAll() \
                 .whenNotMatchedInsertAll() \
                 .execute()
            else:
                # Table doesn't exist, create it
                df.write.format("delta").mode("overwrite").saveAsTable(full_table)
        elif write_mode == "overwrite" and table_exists:
            # For overwrite mode with existing table, use overwriteSchema option
            df.write.format("delta") \
                .mode("overwrite") \
                .option("overwriteSchema", "true") \
                .saveAsTable(full_table)
        else:
            # Standard write modes
            df.write.format("delta").mode(write_mode).saveAsTable(full_table)


def get_adapter(connection_config: Dict[str, Any], spark: SparkSession) -> DatabaseAdapter:
    """Factory function to get appropriate database adapter"""
    db_type = connection_config.get('type', '').lower()
    
    adapters = {
        'oracle': OracleAdapter,
        'azure_sql': AzureSQLAdapter,
        'databricks': DatabricksAdapter
    }
    
    adapter_class = adapters.get(db_type)
    if not adapter_class:
        raise ValueError(f"Unsupported database type: {db_type}")
    
    return adapter_class(connection_config, spark)
