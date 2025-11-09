# Quick Start Guide - 5 Minutes to Your First Sync

## Prerequisites

- Databricks workspace access
- Azure Key Vault with database credentials
- Databricks secret scopes configured

## Step 1: Configure Your Database Connection (2 min)

Edit `config/connections.yml`:

### For Oracle:
```yaml
connections:
  my_oracle:
    type: oracle
    host: your-oracle-host.com
    port: 1521
    service_name: ORCL
    username: your_username
    secret_scope: your-keyvault-scope
    secret_key: oracle-password
    maven_coordinates: com.oracle.ojdbc:ojdbc8:19.3.0.0
```

### For Azure SQL:
```yaml
connections:
  my_azure_sql:
    type: azure_sql
    host: your-server.database.windows.net
    port: 1433
    database: your_database
    username: sqladmin
    secret_scope: your-keyvault-scope
    secret_key: azure-sql-password
    maven_coordinates: com.microsoft.sqlserver:mssql-jdbc:12.2.0.jre11
```

### For Databricks (Target):
```yaml
connections:
  my_databricks:
    type: databricks
    catalog: dev_bronze_db
    schema: my_schema
```

## Step 2: Define Your Pipeline (2 min)

Edit `config/pipelines.yml`:

### Simple Full Refresh:
```yaml
pipelines:
  - pipeline_id: my_first_sync
    enabled: true
    description: "Sync my table to Databricks"
    source:
      connection: my_oracle          # or my_azure_sql
      schema: my_schema
      table: my_table
    target:
      connection: my_databricks
      table: my_table
    sync_config:
      mode: full
      write_mode: overwrite
      partitions: 2
```

### Incremental Load:
```yaml
pipelines:
  - pipeline_id: my_incremental_sync
    enabled: true
    description: "Incremental sync with watermark"
    source:
      connection: my_oracle
      schema: my_schema
      table: my_table
    target:
      connection: my_databricks
      table: my_table
    sync_config:
      mode: incremental
      watermark_columns: [last_modified_date]
      write_mode: append
      partitions: 4
```

## Step 3: Add Task to Workflow (1 min)

Edit `dab_config/workflows.yml` and add your pipeline task:

```yaml
tasks:
  - task_key: my_first_sync
    notebook_task:
      notebook_path: ../src/universal_sync.py
      base_parameters:
        pipeline_id: my_first_sync      # Match your pipeline_id
        env: ${var.v_env}
        workspace_path: ${var.v_workspace_path}
      source: WORKSPACE
    libraries:
      - maven:
          coordinates: com.oracle.ojdbc:ojdbc8:19.3.0.0  # Match your DB driver
    job_cluster_key: job_cluster
```

**Important:** The `coordinates` should match your database type:
- Oracle: `com.oracle.ojdbc:ojdbc8:19.3.0.0`
- Azure SQL: `com.microsoft.sqlserver:mssql-jdbc:12.2.0.jre11`

## Step 4: Deploy and Run

```bash
# Deploy to development
databricks bundle deploy --target development

# Run the workflow
databricks bundle run universal-data-sync --target development
```

## That's It! 🎉

Your data is now syncing. Check the Databricks UI to monitor progress.

## Verify Results

```sql
-- Check your data
SELECT COUNT(*) FROM dev_bronze_db.my_schema.my_table;

-- Check watermark (for incremental loads)
SELECT * FROM dev_bronze_db.my_schema._watermarks
WHERE pipeline_id = 'my_first_sync';
```

## Next Steps

- Add more pipelines to `config/pipelines.yml`
- Set up scheduling in `dab_config/workflows.yml`
- Review [USER_GUIDE.md](USER_GUIDE.md) for advanced features
- Check [SETUP_CHECKLIST.md](SETUP_CHECKLIST.md) for production deployment

## Need Help?

- **Pipeline not running?** Check `enabled: true` in pipelines.yml
- **Connection failed?** Verify credentials in Azure Key Vault
- **No data synced?** Check watermark value in _watermarks table
- **Schema errors?** Ensure source/target schemas are compatible
