import logging
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
from airflow import DAG

# from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.providers.standard.operators.python import PythonOperator

dag = DAG(
    "exchange_rates_bcb_classic",
    schedule="@daily",
    catchup=False,
    start_date=datetime(2025, 10, 1),
    default_args={"owner": "airflow", "retries": 1},
    tags=["bcb"],
)

# Extracting data


def extract(ds_nodash: str, **_):
    base_url = "https://www.bcb.gov.br/Download/fechamento/"
    full_url = f"{base_url}{ds_nodash}.csv"
    logging.info(f"Downloading file from {full_url}")

    try:
        response = requests.get(full_url, timeout=30)
        logging.info(
            f"BCB status={response.status_code}, bytes={len(response.content)}"
        )
        if response.status_code != 200 or not response.content:
            return None
        elif response.status_code == 200:
            csv_data = response.content.decode("utf-8")
            temp_dir = Path("/usr/local/airflow/tmp")
            temp_dir.mkdir(parents=True, exist_ok=True)

            file_path = temp_dir / f"exchange_rates_{ds_nodash}.csv"
            file_path.write_text(csv_data, encoding="utf-8")

            logging.info(f"File saved at {file_path}")

            return str(file_path)
        else:
            logging.warning(f"Request failed: status {response.status_code}")
            return None
    except Exception as e:
        logging.error(e)
        return None


extract_task = PythonOperator(
    task_id="extract",
    python_callable=extract,
    op_kwargs={"ds_nodash": "{{ macros.ds_add(ds, -1) | replace('-', '') }}"},
    dag=dag,
)

# Transforming data


def transform(ti, **_):
    raw_path = ti.xcom_pull(task_ids="extract")
    if not raw_path:
        raise ValueError(
            "No csv path found from extract " "(status != 200 or no ds_nodash found)."
        )

    column_names = [
        "DT_FECHAMENTO",
        "COD_MOEDA",
        "TIPO_MOEDA",
        "DESC_MOEDA",
        "TAXA_COMPRA",
        "TAXA_VENDA",
        "PARIDADE_COMPRA",
        "PARIDADE_VENDA",
    ]

    data_types = {
        "COD_MOEDA": str,
        "TIPO_MOEDA": str,
        "DESC_MOEDA": str,
        "TAXA_COMPRA": float,
        "TAXA_VENDA": float,
        "PARIDADE_COMPRA": float,
        "PARIDADE_VENDA": float,
    }

    parse_dates = ["DT_FECHAMENTO"]

    df = pd.read_csv(
        raw_path,
        sep=";",
        decimal=",",
        thousands=".",
        encoding="utf-8",
        header=None,
        names=column_names,
        dtype=data_types,
        parse_dates=parse_dates,
    )

    df["dat_process"] = datetime.now()

    tmp_dir = Path("/usr/local/airflow/tmp")
    tmp_dir.mkdir(parents=True, exist_ok=True)
    processed_path = tmp_dir / f"{Path(raw_path).stem}_processed.csv"
    df.to_csv(processed_path, index=False)

    logging.info(f"Transform: {len(df)} rows -> {processed_path}")

    return str(processed_path)


transform_task = PythonOperator(task_id="transform", python_callable=transform, dag=dag)

# Creating table on postgres

create_table_ddl = """
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
"""
create_table_postgres = SQLExecuteQueryOperator(
    task_id="create_table_postgres",
    conn_id="postgres_astro",
    sql=create_table_ddl,
    dag=dag,
)

# Loading data into postgres table


def load(**kwargs):
    process_path = kwargs["ti"].xcom_pull(task_id="transform")
    if not process_path:
        raise ValueError("No csv path found.")

    table_name = "fact_exchange_rates"

    fact_exchange_rates_df = pd.read_csv(process_path, parse_dates=["DT_FECHAMENTO"])

    cols = [
        "DT_FECHAMENTO",
        "COD_MOEDA",
        "TIPO_MOEDA",
        "DESC_MOEDA",
        "TAXA_COMPRA",
        "TAXA_VENDA",
        "PARIDADE_COMPRA",
        "PARIDADE_VENDA",
        "dat_process",
    ]
    rows = list(fact_exchange_rates_df[cols].itertuples(index=False, name=None))

    postgres_hook = PostgresHook(postgres_conn_id="postgres_astro", schema="astro")

    postgres_hook.insert_rows(
        table=table_name,
        rows=rows,
        target_fields=[
            "dt_fechamento",
            "cod_moeda",
            "tipo_moeda",
            "desc_moeda",
            "taxa_compra",
            "taxa_venda",
            "paridade_compra",
            "paridade_venda",
            "dat_process",
        ],
        commit_every=1000,
    )


load_task = PythonOperator(task_id="load", python_callable=load, dag=dag)

extract_task >> transform_task >> create_table_postgres >> load_task
