# Coremerch-dream-X - Universal Data Sync Framework

**A configuration-driven framework for syncing data between any databases (Oracle, Azure SQL, Databricks) in any direction.**

## 🚀 Quick Start (5 Minutes)

### 1. Add Your Database Connection

Edit `config/connections.yml`:

```yaml
connections:
  my_oracle:
    type: oracle
    host: your-oracle-host.com
    port: 1521
    service_name: ORCL
    username: your_user
    secret_scope: your-keyvault
    secret_key: oracle-password
    maven_coordinates: com.oracle.ojdbc:ojdbc8:19.3.0.0
```

### 2. Define Your Pipeline

Edit `config/pipelines.yml`:

```yaml
pipelines:
  - pipeline_id: my_first_sync
    enabled: true
    description: "Sync orders from Oracle to Databricks"
    source:
      connection: my_oracle
      schema: sales
      table: orders
    target:
      connection: databricks_bronze
      table: orders
    sync_config:
      mode: incremental
      watermark_columns: [last_modified_date]
      write_mode: append
      partitions: 4
```

### 3. Deploy and Run

```bash
databricks bundle deploy --target development
databricks bundle run universal-data-sync --target development
```

**That's it!** Your data is now syncing. 🎉

## 📖 Documentation

| Document | Description |
|----------|-------------|
| [QUICKSTART.md](docs/QUICKSTART.md) | Get started in 5 minutes |
| [USER_GUIDE.md](docs/USER_GUIDE.md) | Complete user guide |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design details |
| [SETUP_CHECKLIST.md](docs/SETUP_CHECKLIST.md) | Step-by-step setup |

## ✨ Features

### Supported Databases
- ✅ **Oracle Database** - Full JDBC support
- ✅ **Azure SQL Database** - Full JDBC support  
- ✅ **Databricks (Delta Lake)** - Native support
- 🔧 **Extensible** - Easy to add PostgreSQL, MySQL, etc.

### Sync Modes
- **Full Refresh** - Complete table overwrite
- **Incremental** - Only sync new/changed records using watermarks
- **Merge/Upsert** - Update existing records, insert new ones

### Sync Directions
- Oracle → Databricks
- Azure SQL → Databricks
- Databricks → Oracle
- Databricks → Azure SQL
- **Any combination!**

## 📁 Project Structure

```
Coremerch-dream-X/
├── config/
│   ├── connections.yml          # Database connections
│   ├── pipelines.yml            # Pipeline definitions
│   └── examples/                # Example configurations
│
├── src/
│   ├── universal_sync.py        # Main orchestrator
│   ├── database_adapters.py     # Database adapters
│   ├── watermark_manager.py     # Watermark management
│   ├── config_loader.py         # Config parser
│   └── pipeline_validator.py    # Config validator
│
├── dab_config/
│   ├── variables.yml            # Databricks variables
│   └── workflows.yml            # Workflow definitions
│
├── docs/                        # Documentation
├── tests/                       # Test files
└── databricks.yml               # Asset Bundle config
```

## 🎯 Use Cases

### Oracle to Databricks (Incremental)
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

### Databricks to Oracle (Export)
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

## 🔐 Security

- Passwords stored in Azure Key Vault
- Retrieved via Databricks secret scopes
- No credentials in code or config files
- Service principal authentication

## 📊 Monitoring

Built-in logging and watermark tracking:
```sql
SELECT * FROM bronze_db.schema._watermarks
ORDER BY last_updated DESC;
```

## 🆘 Support

For help:
1. Check [QUICKSTART.md](docs/QUICKSTART.md)
2. Review [USER_GUIDE.md](docs/USER_GUIDE.md)
3. See example configurations
4. Run pipeline validator

## 📝 License

[Your License Here]

---

**Ready to get started?** Check out [docs/QUICKSTART.md](docs/QUICKSTART.md) and sync your first table in 5 minutes!
