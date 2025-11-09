# Quick Start Guide - Universal Data Sync

Get up and running in 5 minutes!

## Step 1: Add Your Database Connection (2 min)

Edit `config/connections.yml` and add your database:

### For Oracle:
```yaml
connections:
  my_oracle:
    type: oracle
    host: your-oracle-server.com
    port: 1521
    service_name: ORCL
    username: your_username
    secret_scope: your-keyvault-scope
    secret_key: your-password-key
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
    username: your_username
    secret_scope: your-keyvault-scope
    secret_key: your-password-key
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

Edit `config/pipelines.yml` and add your sync job:

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

## Common Scenarios

### Scenario 1: Oracle → Databricks (Full Refresh)
```yaml
# config/connections.yml
connections:
  oracle_prod:
    type: oracle
    host: oracle.company.com
    port: 1521
    service_name: PROD
    username: app_user
    secret_scope: kv-prod
    secret_key: oracle-password
    maven_coordinates: com.oracle.ojdbc:ojdbc8:19.3.0.0
  
  databricks_bronze:
    type: databricks
    catalog: prod_bronze_db
    schema: sales

# config/pipelines.yml
pipelines:
  - pipeline_id: oracle_sales_sync
    enabled: true
    source:
      connection: oracle_prod
      schema: sales
      table: orders
    target:
      connection: databricks_bronze
      table: orders
    sync_config:
      mode: full
      write_mode: overwrite
      partitions: 4
```

### Scenario 2: Azure SQL → Databricks (Incremental)
```yaml
# config/connections.yml
connections:
  azure_sql_prod:
    type: azure_sql
    host: myserver.database.windows.net
    database: production
    username: sqladmin
    secret_scope: kv-prod
    secret_key: sql-password
    maven_coordinates: com.microsoft.sqlserver:mssql-jdbc:12.2.0.jre11
  
  databricks_bronze:
    type: databricks
    catalog: prod_bronze_db
    schema: crm

# config/pipelines.yml
pipelines:
  - pipeline_id: azure_customers_sync
    enabled: true
    source:
      connection: azure_sql_prod
      schema: dbo
      table: customers
    target:
      connection: databricks_bronze
      table: customers
    sync_config:
      mode: incremental
      watermark_columns: [ModifiedDate]
      write_mode: append
      partitions: 2
```

### Scenario 3: Databricks → Oracle (Export)
```yaml
# config/pipelines.yml
pipelines:
  - pipeline_id: export_to_oracle
    enabled: true
    description: "Export processed data back to Oracle"
    source:
      connection: databricks_bronze
      table: processed_results
    target:
      connection: oracle_prod
      schema: reporting
      table: databricks_export
    sync_config:
      mode: full
      write_mode: overwrite
      partitions: 2
```

## Verification

After running, check:

1. **Databricks Job UI** - View run status and logs
2. **Target Table** - Query your data:
   ```sql
   SELECT COUNT(*) FROM prod_bronze_db.sales.orders
   ```
3. **Watermark Table** - Check sync history:
   ```sql
   SELECT * FROM prod_bronze_db.sales._watermarks
   ```

## Next Steps

- Add more pipelines to `config/pipelines.yml`
- Set up scheduling in `dab_config/workflows.yml`
- Monitor watermarks for incremental loads
- Review logs for optimization opportunities

## Need Help?

- **Pipeline not running?** Check `enabled: true` in pipelines.yml
- **Connection failed?** Verify credentials in Azure Key Vault
- **No data synced?** Check watermark value in _watermarks table
- **Schema errors?** Ensure source/target schemas are compatible

## Pro Tips

1. **Test with small tables first** - Validate connectivity
2. **Use full refresh initially** - Then switch to incremental
3. **Monitor partition counts** - Adjust based on data volume
4. **Check watermarks regularly** - Ensure they're advancing
5. **Use descriptive pipeline_ids** - Makes debugging easier
