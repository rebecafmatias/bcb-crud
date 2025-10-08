# 💱 Exchange Rates BCB – Airflow ETL
## 📘 Overview

This project implements an ETL (Extract, Transform, Load) pipeline using Apache Airflow running inside an Astro CLI environment.
The goal is to automatically fetch daily exchange rates from the Central Bank of Brazil (BCB), transform the data, and store it in a PostgreSQL database for later analysis.

## 🧩 Project Structure

````
ASTRO-BCB/
├── dags/
│   └── exchange_rates.py         # Main ETL DAG
├── include/                      # Additional project resources
├── plugins/                      # Custom or community plugins
├── tests/                        # Optional test scripts
├── Dockerfile                    # Astro Runtime image configuration
├── requirements.txt              # Python dependencies
├── packages.txt                  # System dependencies (optional)
├── airflow_settings.yaml         # Local Airflow connections and variables
├── .vscode/                      # SQLTools configuration (ignored in Git)
├── .gitignore                    # Git ignore rules
└── README.md                     # Project documentation
````

## ⚙️ How the Pipeline Works
### 1. Extract

The extract task downloads the daily CSV file with exchange rates from the Central Bank of Brazil
(_https://www.bcb.gov.br/Download/fechamento/YYYYMMDD.csv_).

If the file for the previous day does not exist (weekend or holiday), the DAG automatically skips execution.

The file is temporarily saved under /usr/local/airflow/tmp.

### 2. Transform

The transform task reads the raw CSV, converts data types, adds a processing timestamp (dat_process), and saves a cleaned version of the file.

### 3. Load

The load task bulk loads the transformed data into the PostgreSQL table fact_exchange_rates using the COPY command for high performance.

## 🗃️ Table Structure

````
CREATE TABLE IF NOT EXISTS fact_exchange_rates (
  dt_fechamento DATE,
  cod_moeda TEXT,
  tipo_moeda TEXT,
  desc_moeda TEXT,
  taxa_compra REAL,
  taxa_venda REAL,
  paridade_compra REAL,
  paridade_venda REAL,
  dat_process TIMESTAMP,
  CONSTRAINT fact_exchange_rates_pk PRIMARY KEY (dt_fechamento, cod_moeda)
);
````

## 🚀 Running Locally

### Requirements

- Docker Desktop installed and running

- Astro CLI installed
→ [Official installation guide](https://docs.astronomer.io/astro/cli/install-cli)

### Steps

````
# 1. Start the Airflow environment
astro dev start

# 2. Access the Airflow UI
http://localhost:8080

# 3. Connect to the local PostgreSQL database
Host: localhost
Port: 5432
Database: postgres
User: postgres
Password: postgres
````

## 🧠 Useful SQL Queries
````
-- Total number of rows
SELECT COUNT(*) FROM public.fact_exchange_rates;

-- Last date loaded
SELECT MAX(dt_fechamento) FROM public.fact_exchange_rates;

-- Exchange rates for the latest date
SELECT cod_moeda, desc_moeda, taxa_compra, taxa_venda
FROM public.fact_exchange_rates
WHERE dt_fechamento = (SELECT MAX(dt_fechamento) FROM public.fact_exchange_rates);
````

## 🧰 Development Tips

- Stop the environment:
    `astro dev stop
    `

- The PostgreSQL service runs inside the Astro container —
the database is only available while the container is running.

- Data is persisted between restarts through Docker volumes.

## 🧩 Recommended Tools

| Tool                   | Purpose                                     |
| ---------------------- | ------------------------------------------- |
| **Beekeeper Studio**   | Lightweight SQL client for quick queries    |
| **DBeaver**            | Full-featured database explorer and modeler |
| **SQLTools (VS Code)** | Run queries directly from VS Code           |
| **Docker Desktop**     | Manage running containers                   |
| **Astro CLI**          | Run and manage Airflow locally              |


## 🏗️ Future Improvements

- Automate DAG execution only on business days.

- Add data quality checks (row count, null validation).

- Store data in a cloud warehouse (e.g., AWS Redshift or BigQuery).

- Create dashboards for visual analysis using Power BI or Metabase.

## 🧹 Code Quality and Pre-Commit Hooks

This project uses Poetry for dependency management and pre-commit hooks to maintain code quality and style consistency.

### 🧰 Tools Used

| Tool           | Purpose                                                |
| -------------- | ------------------------------------------------------ |
| **black**      | Automatically formats Python code following PEP 8      |
| **flake8**     | Linter for static code analysis and style enforcement  |
| **isort**      | Sorts and groups Python imports automatically          |
| **pre-commit** | Runs checks before every commit to keep the repo clean |

### ⚙️ Setup Instructions

After cloning the repository:

    # 1. Install dependencies via Poetry
    poetry install

    # 2. Install the pre-commit hooks defined in .pre-commit-config.yaml
    poetry run pre-commit install

    # 3. (Optional) Run all hooks manually on the entire project
    poetry run pre-commit run --all-files

### ✅ Benefits

- Ensures consistent formatting across all contributions

- Prevents linting or syntax issues from being committed

- Keeps imports organized and clean

- Makes the codebase easier to read and maintain


### 👩‍💻 Author
**Rebeca Feitosa - Junior Data Engineer**
