# Getting Started with Coremerch-dream-X

Welcome to the Universal Data Sync Framework! This guide will help you get started.

## 📁 What's in This Repository

```
Coremerch-dream-X/
├── config/
│   ├── connections.yml          # ← EDIT: Add your database connections
│   ├── pipelines.yml            # ← EDIT: Define your sync pipelines
│   └── examples/                # Example configurations
│       ├── oracle_to_databricks.yml
│       ├── azure_sql_to_databricks.yml
│       └── databricks_to_oracle.yml
│
├── src/
│   ├── universal_sync.py        # Main sync orchestrator
│   ├── database_adapters.py     # Database adapters (Oracle, Azure SQL, Databricks)
│   ├── watermark_manager.py     # Incremental load tracking
│   ├── config_loader.py         # Configuration parser
│   └── pipeline_validator.py    # Configuration validator
│
├── dab_config/
│   ├── variables.yml            # ← EDIT: Update team name, cluster settings
│   └── workflows.yml            # ← EDIT: Add tasks for your pipelines
│
├── databricks.yml               # ← EDIT: Update workspace URLs, service principals
│
└── docs/
    ├── QUICKSTART.md            # 5-minute quick start guide
    ├── USER_GUIDE.md            # Complete user guide
    ├── ARCHITECTURE.md          # System design details
    └── SETUP_CHECKLIST.md       # Step-by-step setup checklist
```

## 🚀 Quick Start (5 Minutes)

### 1. Update Databricks Configuration

Edit `databricks.yml`:
- Update workspace URLs for your environments
- Update service principal IDs
- Update group names for permissions

### 2. Update Variables

Edit `dab_config/variables.yml`:
- Set `v_team_name` to your team name
- Adjust cluster settings if needed

### 3. Configure Your First Connection

Edit `config/connections.yml` and add your database:

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
  
  my_databricks:
    type: databricks
    catalog: dev_bronze_db
    schema: my_schema
```

### 4. Define Your First Pipeline

Edit `config/pipelines.yml`:

```yaml
pipelines:
  - pipeline_id: my_first_sync
    enabled: true
    description: "My first data sync"
    source:
      connection: my_oracle
      schema: sales
      table: orders
    target:
      connection: my_databricks
      table: orders
    sync_config:
      mode: full
      write_mode: overwrite
      partitions: 2
```

### 5. Add Task to Workflow

Edit `dab_config/workflows.yml`:

```yaml
tasks:
  - task_key: my_first_sync
    notebook_task:
      notebook_path: ../src/universal_sync.py
      base_parameters:
        pipeline_id: my_first_sync
        env: ${var.v_env}
        workspace_path: ${var.v_workspace_path}
      source: WORKSPACE
    libraries:
      - maven:
          coordinates: com.oracle.ojdbc:ojdbc8:19.3.0.0
    job_cluster_key: job_cluster
```

### 6. Deploy and Run

```bash
# Deploy to development
databricks bundle deploy --target development

# Run the workflow
databricks bundle run universal-data-sync --target development
```

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| [QUICKSTART.md](docs/QUICKSTART.md) | Get started in 5 minutes |
| [USER_GUIDE.md](docs/USER_GUIDE.md) | Complete reference guide |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design details |
| [SETUP_CHECKLIST.md](docs/SETUP_CHECKLIST.md) | Production setup checklist |

## 📋 Example Configurations

Check the `config/examples/` folder for complete examples:

- **oracle_to_databricks.yml** - Oracle → Databricks sync patterns
- **azure_sql_to_databricks.yml** - Azure SQL → Databricks sync patterns
- **databricks_to_oracle.yml** - Databricks → Oracle export patterns

## 🎯 Common Use Cases

### Use Case 1: Oracle to Databricks (Incremental)
```yaml
- pipeline_id: oracle_orders
  source:
    connection: oracle_prod
    schema: sales
    table: orders
  target:
    connection: databricks_bronze
    table: orders
  sync_config:
    mode: incremental
    watermark_columns: [order_date]
    write_mode: append
```

### Use Case 2: Azure SQL to Databricks (Full)
```yaml
- pipeline_id: azure_customers
  source:
    connection: azure_sql_prod
    schema: dbo
    table: customers
  target:
    connection: databricks_bronze
    table: customers
  sync_config:
    mode: full
    write_mode: overwrite
```

### Use Case 3: Databricks to Oracle (Export)
```yaml
- pipeline_id: export_results
  source:
    connection: databricks_silver
    table: processed_data
  target:
    connection: oracle_prod
    schema: reporting
    table: databricks_export
  sync_config:
    mode: full
    write_mode: overwrite
```

## ✅ Setup Checklist

- [ ] Update `databricks.yml` with your workspace URLs
- [ ] Update `dab_config/variables.yml` with your team name
- [ ] Add database connections to `config/connections.yml`
- [ ] Define pipelines in `config/pipelines.yml`
- [ ] Add tasks to `dab_config/workflows.yml`
- [ ] Deploy to development
- [ ] Test your first pipeline
- [ ] Review logs and verify data
- [ ] Deploy to production

## 🆘 Troubleshooting

### Pipeline not running?
- Check `enabled: true` in pipelines.yml
- Verify pipeline_id matches in workflows.yml

### Connection failed?
- Verify credentials in Azure Key Vault
- Check network connectivity
- Review connection configuration

### No data synced?
- Check watermark value (may be ahead of source)
- Verify source has new data
- Review incremental filter logic

## 📞 Support

For help:
1. Check [QUICKSTART.md](docs/QUICKSTART.md)
2. Review example configurations in `config/examples/`
3. See [USER_GUIDE.md](docs/USER_GUIDE.md)
4. Run pipeline validator

## 🎉 Success!

Once you've completed the setup, you'll have a production-ready data sync framework that can:

✅ Sync data between any databases  
✅ Handle full refresh and incremental loads  
✅ Track watermarks automatically  
✅ Support bidirectional sync  
✅ Scale to any data volume  

**Happy syncing!** 🚀
