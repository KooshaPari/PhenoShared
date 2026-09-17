# AGENTS.md — Datamold

## Project Overview

- **Name**: Datamold (Data Platform & Transformation)
- **Description**: Data transformation, validation, and pipeline orchestration platform for ETL/ELT workflows
- **Location**: `/Users/<REDACTED>/CodeProjects/Phenotype/repos/Datamold`
- **Language Stack**: Python 3.12+, Apache Spark, dbt, SQL
- **Published**: Private (Phenotype org)

## Quick Start

```bash
# Navigate to project
cd /Users/<REDACTED>/CodeProjects/Phenotype/repos/Datamold

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env

# Run data pipeline
python -m datamold run pipeline.yaml

# Validate data
python -m datamold validate source.yaml
```

## Architecture

### Data Platform Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Orchestration Layer                          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐   │
│  │   Pipeline      │  │   Scheduler     │  │   Monitoring    │   │
│  │   Engine        │  │   (Airflow/Dag) │  │   (Metrics)     │   │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘   │
└───────────┼───────────────────┼───────────────────┼──────────────┘
            │                   │                   │
            └───────────────────┼───────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────┐
│                     Transformation Layer                           │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │              Data Transformation Engine                     │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │ │
│  │  │ Extract  │  │ Validate │  │ Transform│  │ Load     │  │ │
│  │  │ Source   │  │ Schema   │  │ dbt/Spark│  │ Target   │  │ │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   dbt Models    │  │   Spark Jobs    │  │   SQL           │ │
│  │   (SQL)         │  │   (Python)      │  │   Queries       │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
            │                   │                   │
┌───────────▼───────────────────▼───────────────────▼───────────┐
│                     Data Sources & Targets                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐│
│  │   Databases     │  │   Data Lake     │  │   APIs          ││
│  │   (PG/MySQL)    │  │   (S3/Delta)    │  │   (REST/GraphQL)││
│  └─────────────────┘  └─────────────────┘  └─────────────────┘│
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐│
│  │   Warehouses    │  │   Streams       │  │   Files         ││
│  │   (Snowflake)   │  │   (Kafka)       │  │   (CSV/JSON)    ││
│  └─────────────────┘  └─────────────────┘  └─────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### Data Pipeline Flow

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  Source  │───▶│ Extract  │───▶│ Validate │───▶│ Transform│───▶│  Load    │
│  System  │    │  Data    │    │  Quality │    │  Data    │    │  Target  │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
     │               │               │               │               │
     ▼               ▼               ▼               ▼               ▼
  Connection     Raw Data        Schema Check    dbt Models      Final Table
  Pool           Frames          Constraints     Spark Jobs      or API
```

## Quality Standards

### Data Quality

- **Schema Validation**: Great Expectations
- **Data Profiling**: pandas-profiling
- **Lineage**: OpenLineage
- **Testing**: dbt tests + custom validators

### Code Quality

- **Python**: black, ruff, mypy
- **SQL**: sqlfluff
- **dbt**: dbt-lint
- **Documentation**: dbt docs

## Git Workflow

### Branch Naming

Format: `<type>/<pipeline>/<description>`

Types: `feat`, `fix`, `model`, `source`, `test`

Examples:
- `feat/users/add-dimension-table`
- `fix/orders/correct-revenue-calc`
- `model/analytics/add-funnel-metrics`

### Commit Messages

Format: `<type>(<scope>): <description>`

Examples:
- `feat(models): add user activity mart`
- `fix(sources): correct API pagination`
- `test(quality): add uniqueness checks`

## File Structure

```
Datamold/
├── datamold/                  # Main package
│   ├── __init__.py
│   ├── cli.py                 # Command line interface
│   ├── pipeline.py            # Pipeline orchestration
│   ├── sources/               # Source connectors
│   ├── transforms/            # Transformations
│   └── targets/               # Target connectors
├── models/                    # dbt models
│   ├── staging/
│   ├── marts/
│   └── sources.yml
├── pipelines/                 # Pipeline definitions
│   ├── ingestion/
│   └── transformation/
├── tests/                     # Test suite
│   ├── unit/
│   └── integration/
├── docs/                      # Documentation
├── requirements.txt
├── setup.py
└── AGENTS.md                  # This file
```

## CLI Commands

```bash
# Pipeline operations
python -m datamold run pipeline.yaml
python -m datamold validate source.yaml
python -m datamold test models/

# dbt commands
dbt run
dbt test
dbt docs generate
dbt docs serve

# Data quality
datamold check quality
datamold profile source.yaml

# Monitoring
datamold logs
datamold metrics
```

## Troubleshooting

### Pipeline failures

```bash
# Check logs
datamold logs --pipeline <name>

# Validate configuration
datamold validate pipeline.yaml

# Run in debug mode
datamold run pipeline.yaml --debug
```

### Data quality issues

```bash
# Profile data
datamold profile source.yaml

# Run specific tests
dbt test --select <model>

# Check lineage
datamold lineage --model <name>
```

## Resources

- [dbt Documentation](https://docs.getdbt.com/)
- [Apache Spark](https://spark.apache.org/docs/)
- [Great Expectations](https://docs.greatexpectations.io/)
- [Phenotype Registry](https://github.com/KooshaPari/phenotype-registry)

## Agent Notes

**Critical Implementation Details:**
- All pipelines must be idempotent
- Use incremental models for large datasets
- Document data lineage
- Handle schema drift gracefully

**Known Gotchas:**
- Column type changes require full refresh
- Partitioning strategy affects query cost
- Test data may differ from production
- API rate limits affect extraction

**Testing Strategy:**
- Unit tests for transforms
- Integration tests with test data
- dbt tests for data quality
- Monitor production anomalies
