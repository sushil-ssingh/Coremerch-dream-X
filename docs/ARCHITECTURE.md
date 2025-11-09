# Architecture Overview

## System Design

The Universal Data Sync framework uses a modular, adapter-based architecture to support multiple database types and sync patterns.

```
┌─────────────────────────────────────────────────────────────┐
│                    Configuration Layer                       │
│  ┌──────────────────┐         ┌─────────────────────┐      │
│  │ connections.yml  │         │   pipelines.yml     │      │
│  │  - Oracle        │         │  - Pipeline Defs    │      │
│  │  - Azure SQL     │         │  - Sync Config      │      │
│  │  - Databricks    │         │  - Watermarks       │      │
│  └──────────────────┘         └─────────────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   Orchestration Layer                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              universal_sync.py                        │  │
│  │  - Load Configuration                                 │  │
│  │  - Initialize Adapters                                │  │
│  │  - Manage Watermarks                                  │  │
│  │  - Execute Sync Logic                                 │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    Adapter Layer                             │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐   │
│  │   Oracle    │  │  Azure SQL   │  │   Databricks    │   │
│  │   Adapter   │  │   Adapter    │  │    Adapter      │   │
│  │             │  │              │  │                 │   │
│  │ - JDBC URL  │  │ - JDBC URL   │  │ - Delta Lake   │   │
│  │ - TO_DATE   │  │ - CONVERT    │  │ - CAST         │   │
│  │ - Read/Write│  │ - Read/Write │  │ - Read/Write   │   │
│  └─────────────┘  └──────────────┘  └─────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                     Data Layer                               │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐   │
│  │   Oracle    │  │  Azure SQL   │  │   Databricks    │   │
│  │  Database   │  │   Database   │  │   Delta Lake    │   │
│  └─────────────┘  └──────────────┘  └─────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Configuration Layer

**Purpose:** Declarative definition of connections and pipelines

**Files:**
- `config/connections.yml` - Database connection registry
- `config/pipelines.yml` - Pipeline definitions

**Key Features:**
- Environment-agnostic (dev/prod via variables)
- Secrets managed via Azure Key Vault
- Validation before execution

### 2. Orchestration Layer

**Purpose:** Coordinate sync operations

**Main Components:**

#### universal_sync.py
- Entry point for all sync operations
- Loads configuration
- Initializes adapters
- Manages execution flow
- Handles errors and logging

#### config_loader.py
- Parses YAML configurations
- Validates pipeline definitions
- Substitutes environment variables
- Provides configuration access

#### watermark_manager.py
- Tracks incremental load state
- Stores watermark values
- Supports multiple data types
- Handles initialization and updates

### 3. Adapter Layer

**Purpose:** Abstract database-specific operations

**Base Class: DatabaseAdapter**
```python
class DatabaseAdapter(ABC):
    - build_jdbc_url()
    - get_incremental_filter()
    - read_data()
    - write_data()
    - get_credentials()
```

**Implementations:**

#### OracleAdapter
- JDBC connection via Oracle driver
- TO_DATE() for date filtering
- Supports Oracle-specific options
- Handles timezones

#### AzureSQLAdapter
- JDBC connection via SQL Server driver
- CONVERT() for date filtering
- SSL/TLS encryption
- Azure AD authentication support

#### DatabricksAdapter
- Native Delta Lake operations
- CAST() for date filtering
- Merge/upsert support
- Catalog/schema management

### 4. Data Layer

**Purpose:** Physical data storage

**Components:**
- Source databases (Oracle, Azure SQL)
- Target databases (Databricks, Oracle, Azure SQL)
- Watermark tables (in Databricks)

## Data Flow

### Full Refresh Flow

```
1. Load pipeline config
2. Initialize source adapter
3. Initialize target adapter
4. Read all data from source
5. Write to target (overwrite)
6. Log completion
```

### Incremental Flow

```
1. Load pipeline config
2. Initialize source adapter
3. Initialize target adapter
4. Check watermark table
5. Build incremental filter
6. Read new/changed data from source
7. Extract new watermark value
8. Write to target (append)
9. Update watermark table
10. Log completion
```

### Merge/Upsert Flow

```
1. Load pipeline config
2. Initialize source adapter
3. Initialize target adapter
4. Check watermark table
5. Build incremental filter
6. Read new/changed data from source
7. Extract new watermark value
8. Perform merge operation:
   - Match on merge keys
   - Update existing records
   - Insert new records
9. Update watermark table
10. Log completion
```

## Extensibility

### Adding a New Database Type

1. **Create Adapter Class**
```python
class PostgreSQLAdapter(DatabaseAdapter):
    def build_jdbc_url(self):
        # PostgreSQL-specific URL
        
    def get_incremental_filter(self, columns, value):
        # PostgreSQL-specific SQL
        
    def read_data(self, ...):
        # JDBC read logic
        
    def write_data(self, ...):
        # JDBC write logic
```

2. **Register in Factory**
```python
def get_adapter(config, spark):
    adapters = {
        'oracle': OracleAdapter,
        'azure_sql': AzureSQLAdapter,
        'databricks': DatabricksAdapter,
        'postgresql': PostgreSQLAdapter  # Add here
    }
```

3. **Add Connection Config**
```yaml
connections:
  my_postgres:
    type: postgresql
    host: postgres.example.com
    port: 5432
    database: mydb
    username: user
    secret_scope: kv
    secret_key: pg-password
```

### Adding Custom Transformations

Extend the pipeline config to support transformations:

```yaml
pipelines:
  - pipeline_id: with_transformation
    source:
      connection: oracle_prod
      table: raw_data
    transformations:
      - type: filter
        condition: "status = 'ACTIVE'"
      - type: select
        columns: [id, name, date]
      - type: rename
        mapping:
          old_name: new_name
    target:
      connection: databricks_bronze
      table: transformed_data
```

## Performance Considerations

### Parallelism

- **Partitions:** Control read parallelism
  - More partitions = more parallel reads
  - Balance with cluster size
  - Typical: 1-16 partitions

- **Fetch Size:** Control batch size
  - Larger = fewer round trips
  - Smaller = less memory
  - Typical: 10,000-50,000

### Optimization Tips

1. **Use incremental loads** for large tables
2. **Partition appropriately** based on data volume
3. **Monitor watermarks** to ensure progress
4. **Use merge for updates** instead of full refresh
5. **Schedule during off-peak** hours
6. **Monitor cluster metrics** for bottlenecks

## Security

### Credential Management

- All passwords stored in Azure Key Vault
- Retrieved via Databricks secret scopes
- Never logged or displayed
- Scoped to specific connections

### Access Control

- Databricks workspace permissions
- Service principal authentication
- Group-based access (admin/engineer)
- Catalog/schema level permissions

### Network Security

- Private endpoints for databases
- VNet integration
- SSL/TLS encryption
- Firewall rules

## Monitoring

### Logging

- Pipeline start/end times
- Record counts
- Watermark values
- Error messages
- Duration metrics

### Metrics

Track in watermark table:
- Last sync timestamp
- Record count per sync
- Success/failure status
- Pipeline execution history

### Alerting

Set up alerts for:
- Failed pipelines
- Stale watermarks
- Zero records synced
- Long-running jobs

## Deployment

### Databricks Asset Bundles

```
databricks.yml
├── bundle definition
├── permissions
├── targets (dev/prod)
└── includes
    ├── variables.yml
    └── workflows.yml
```

### CI/CD Pipeline

```
1. Code commit
2. Validation (pipeline_validator.py)
3. Deploy to dev
4. Run tests
5. Deploy to prod
6. Monitor
```

## Best Practices

1. **Configuration Management**
   - Version control all configs
   - Use environment variables
   - Validate before deploy

2. **Testing**
   - Test in dev first
   - Validate record counts
   - Check watermarks
   - Monitor first runs

3. **Maintenance**
   - Review watermark table regularly
   - Archive old watermark records
   - Monitor cluster usage
   - Update drivers periodically

4. **Documentation**
   - Document custom queries
   - Explain business logic
   - Maintain runbooks
   - Update as changes occur
