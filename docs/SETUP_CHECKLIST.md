# Setup Checklist

Use this checklist to set up the Universal Data Sync framework in your environment.

## Prerequisites

- [ ] Databricks workspace access
- [ ] Azure Key Vault with database credentials
- [ ] Databricks secret scopes configured
- [ ] Service principal for CI/CD (optional)
- [ ] Git repository access

## Initial Setup

### 1. Repository Setup
- [ ] Clone/fork this repository
- [ ] Review project structure
- [ ] Read QUICKSTART.md
- [ ] Read README_UNIVERSAL_SYNC.md

### 2. Configure Connections

Edit `config/connections.yml`:

#### Oracle Connections
- [ ] Add Oracle development connection
- [ ] Add Oracle production connection
- [ ] Verify host, port, service_name
- [ ] Verify username
- [ ] Verify secret_scope and secret_key
- [ ] Test connection (optional)

#### Azure SQL Connections
- [ ] Add Azure SQL development connection
- [ ] Add Azure SQL production connection
- [ ] Verify host, database
- [ ] Verify username
- [ ] Verify secret_scope and secret_key
- [ ] Test connection (optional)

#### Databricks Connections
- [ ] Add Databricks bronze connection
- [ ] Add Databricks silver connection (if needed)
- [ ] Add Databricks gold connection (if needed)
- [ ] Verify catalog names
- [ ] Verify schema names

### 3. Configure Pipelines

Edit `config/pipelines.yml`:

- [ ] Review example pipelines in `config/pipelines.example.yml`
- [ ] Define your first pipeline
- [ ] Set pipeline_id (unique, descriptive)
- [ ] Set enabled: true
- [ ] Configure source connection
- [ ] Configure source schema/table
- [ ] Configure target connection
- [ ] Configure target table
- [ ] Choose sync mode (full/incremental)
- [ ] Set watermark columns (if incremental)
- [ ] Set write mode (append/overwrite/merge)
- [ ] Set partitions (based on data volume)
- [ ] Add description

### 4. Configure Workflows

Edit `dab_config/workflows.yml`:

- [ ] Add task for each pipeline
- [ ] Set task_key (matches pipeline_id)
- [ ] Set notebook_path to `../src/universal_sync.py`
- [ ] Set pipeline_id parameter
- [ ] Add appropriate JDBC library
  - [ ] Oracle: `com.oracle.ojdbc:ojdbc8:19.3.0.0`
  - [ ] Azure SQL: `com.microsoft.sqlserver:mssql-jdbc:12.2.0.jre11`
- [ ] Configure job cluster settings
- [ ] Set autoscale min/max workers

### 5. Configure Databricks Asset Bundle

Edit `databricks.yml`:

- [ ] Update bundle name
- [ ] Configure permissions
  - [ ] Add admin group
  - [ ] Add engineer group
- [ ] Configure local target
  - [ ] Set workspace host
  - [ ] Set environment variables
- [ ] Configure development target
  - [ ] Set workspace host
  - [ ] Set environment variables
  - [ ] Add service principal (if using)
- [ ] Configure production target
  - [ ] Set workspace host
  - [ ] Set environment variables
  - [ ] Add service principal (if using)

### 6. Update Variables

Edit `dab_config/variables.yml`:

- [ ] Set v_team_name
- [ ] Set v_node_type_id (cluster size)
- [ ] Set v_spark_version
- [ ] Review cluster policy

## Validation

### 7. Validate Configuration

- [ ] Run pipeline validator:
  ```bash
  databricks notebook run /path/to/pipeline_validator \
    --parameters workspace_path=/Workspace/path/to/project
  ```
- [ ] Fix any validation errors
- [ ] Verify all connections are valid
- [ ] Verify all pipelines are valid

### 8. Test in Development

- [ ] Deploy to development:
  ```bash
  databricks bundle deploy --target development
  ```
- [ ] Check deployment succeeded
- [ ] Verify job created in Databricks UI
- [ ] Verify notebooks uploaded

### 9. Run Test Pipeline

- [ ] Run a single pipeline:
  ```bash
  databricks bundle run universal-data-sync --target development
  ```
- [ ] Monitor job execution in Databricks UI
- [ ] Check logs for errors
- [ ] Verify data in target table:
  ```sql
  SELECT COUNT(*) FROM dev_bronze_db.schema.table;
  ```
- [ ] Check watermark table:
  ```sql
  SELECT * FROM dev_bronze_db.schema._watermarks;
  ```

### 10. Verify Results

- [ ] Compare record counts (source vs target)
- [ ] Verify data quality
- [ ] Check watermark values
- [ ] Review execution time
- [ ] Check for any errors/warnings

## Production Deployment

### 11. Prepare for Production

- [ ] Test all pipelines in development
- [ ] Document any custom queries
- [ ] Review security settings
- [ ] Update production connection configs
- [ ] Review cluster sizing
- [ ] Set up monitoring/alerting

### 12. Deploy to Production

- [ ] Deploy to production:
  ```bash
  databricks bundle deploy --target production
  ```
- [ ] Verify deployment
- [ ] Run smoke test
- [ ] Monitor first production run
- [ ] Verify data quality

### 13. Set Up Scheduling (Optional)

Edit `dab_config/workflows.yml`:

- [ ] Add schedule section:
  ```yaml
  schedule:
    quartz_cron_expression: "0 0 2 * * ?"
    timezone_id: "America/Chicago"
  ```
- [ ] Redeploy with schedule
- [ ] Verify schedule in Databricks UI

## Monitoring & Maintenance

### 14. Set Up Monitoring

- [ ] Create dashboard for pipeline metrics
- [ ] Set up alerts for failures
- [ ] Monitor watermark advancement
- [ ] Track execution times
- [ ] Monitor cluster utilization

### 15. Documentation

- [ ] Document custom queries
- [ ] Document business logic
- [ ] Create runbook for common issues
- [ ] Train team members
- [ ] Update as changes occur

### 16. Ongoing Maintenance

- [ ] Review logs weekly
- [ ] Check watermark table monthly
- [ ] Update JDBC drivers as needed
- [ ] Optimize slow pipelines
- [ ] Archive old watermark records

## Migration from Old Framework (If Applicable)

### 17. Migration Preparation

- [ ] Read MIGRATION_GUIDE.md
- [ ] Identify all existing pipelines
- [ ] Backup old configuration files
- [ ] Plan migration order

### 18. Migrate Pipelines

For each old pipeline:
- [ ] Extract connection details
- [ ] Add to `config/connections.yml`
- [ ] Convert to new pipeline format
- [ ] Add to `config/pipelines.yml`
- [ ] Add task to `dab_config/workflows.yml`
- [ ] Test in development
- [ ] Verify record counts match
- [ ] Deploy to production

### 19. Cleanup

- [ ] Archive old notebooks
- [ ] Remove old schema JSON files
- [ ] Archive old deployment files
- [ ] Update documentation
- [ ] Notify team of changes

## Troubleshooting

### Common Issues Checklist

If pipeline fails:
- [ ] Check pipeline is enabled
- [ ] Verify connection details
- [ ] Check credentials in Key Vault
- [ ] Verify network connectivity
- [ ] Review error logs
- [ ] Check watermark value
- [ ] Verify source table exists
- [ ] Check target permissions

If no data synced:
- [ ] Check watermark value (may be ahead)
- [ ] Verify source has new data
- [ ] Review incremental filter
- [ ] Check source table for changes

If schema errors:
- [ ] Verify column names match
- [ ] Check data type compatibility
- [ ] Review source schema
- [ ] Review target schema

## Success Criteria

You're ready for production when:
- [ ] All validations pass
- [ ] All test pipelines succeed
- [ ] Record counts match expectations
- [ ] Watermarks are advancing
- [ ] No errors in logs
- [ ] Team is trained
- [ ] Documentation is complete
- [ ] Monitoring is set up

## Quick Reference

### Deploy Commands
```bash
# Deploy to development
databricks bundle deploy --target development

# Deploy to production
databricks bundle deploy --target production

# Run workflow
databricks bundle run universal-data-sync --target development
```

### Validation Commands
```bash
# Validate configuration
databricks notebook run /path/to/pipeline_validator

# Check deployment
databricks bundle validate --target development
```

### SQL Queries
```sql
-- Check data
SELECT COUNT(*) FROM catalog.schema.table;

-- Check watermarks
SELECT * FROM catalog.schema._watermarks
ORDER BY last_updated DESC;

-- Check specific pipeline
SELECT * FROM catalog.schema._watermarks
WHERE pipeline_id = 'your_pipeline_id';
```

## Support Resources

- [ ] Bookmark QUICKSTART.md
- [ ] Bookmark README_UNIVERSAL_SYNC.md
- [ ] Bookmark MIGRATION_GUIDE.md
- [ ] Bookmark ARCHITECTURE.md
- [ ] Save this checklist for future reference

## Notes

Use this space for environment-specific notes:

```
Environment: _______________
Workspace URL: _______________
Key Vault: _______________
Service Principal: _______________
Team Contact: _______________

Custom Notes:
_________________________________
_________________________________
_________________________________
```

---

**Congratulations!** 🎉

Once you've completed this checklist, you'll have a fully functional, production-ready data sync framework!
