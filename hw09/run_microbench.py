from __future__ import annotations

import json
import math
import os
import random
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pymysql
import requests


ROOT = Path(__file__).resolve().parent
TRINO_MEMORY_CATALOG = ROOT / "docker" / "trino" / "catalog" / "memory.properties"
RESULTS_PATH = ROOT / "microbench_results.json"

CLICKHOUSE_IMAGE = os.environ.get("HW09_CLICKHOUSE_IMAGE", "clickhouse/clickhouse-server:latest")
TRINO_IMAGE = os.environ.get("HW09_TRINO_IMAGE", "trinodb/trino:latest")
STARROCKS_IMAGE = os.environ.get("HW09_STARROCKS_IMAGE", "starrocks/allin1-ubuntu:latest")

CLICKHOUSE_CONTAINER = "hw09-clickhouse"
TRINO_CONTAINER = "hw09-trino"
STARROCKS_CONTAINER = "hw09-starrocks"

FACT_ROWS = int(os.environ.get("HW09_FACT_ROWS", "100000"))
CUSTOMER_ROWS = int(os.environ.get("HW09_CUSTOMER_ROWS", "10000"))
PRODUCT_ROWS = int(os.environ.get("HW09_PRODUCT_ROWS", "1000"))
INSERT_BATCH = int(os.environ.get("HW09_INSERT_BATCH", "1000"))
MEASURE_RUNS = 3


REGIONS = ["north", "south", "west", "east", "center"]
SEGMENTS = ["retail", "small_business", "enterprise"]
CATEGORIES = ["books", "tech", "home", "sport", "food"]


@dataclass
class EngineResult:
    engine: str
    version: str
    load_time_s: float
    query_times_s: dict[str, list[float]]


def sh(cmd: list[str], check: bool = True, capture: bool = True) -> str:
    proc = subprocess.run(
        cmd,
        check=check,
        text=True,
        capture_output=capture,
    )
    return proc.stdout.strip() if capture else ""


def docker_rm(name: str) -> None:
    subprocess.run(["docker", "rm", "-f", name], check=False, capture_output=True, text=True)


def docker_pull(image: str) -> None:
    print(f"[pull] {image}")
    subprocess.run(["docker", "pull", image], check=True)


def wait_until(fn, timeout: int, message: str) -> None:
    deadline = time.time() + timeout
    last_error = None
    while time.time() < deadline:
        try:
            if fn():
                return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
        time.sleep(2)
    raise RuntimeError(f"{message}. Last error: {last_error}")


def trino_query(sql: str) -> list[list[str]]:
    headers = {"X-Trino-User": "bench", "X-Trino-Catalog": "memory", "X-Trino-Schema": "hw09"}
    resp = requests.post("http://localhost:8080/v1/statement", data=sql.encode("utf-8"), headers=headers, timeout=60)
    resp.raise_for_status()
    payload = resp.json()
    rows: list[list[str]] = []
    while True:
        if "error" in payload:
            raise RuntimeError(payload["error"])
        rows.extend(payload.get("data", []))
        next_uri = payload.get("nextUri")
        if not next_uri:
            break
        payload = requests.get(next_uri, timeout=60).json()
    return rows


def clickhouse_query(sql: str) -> str:
    resp = requests.post("http://localhost:8123/", params={"query": sql}, timeout=120)
    resp.raise_for_status()
    return resp.text.strip()


def starrocks_conn():
    return pymysql.connect(
        host="127.0.0.1",
        port=9030,
        user="root",
        password="",
        autocommit=True,
        cursorclass=pymysql.cursors.Cursor,
    )


def starrocks_query(sql: str) -> list[tuple]:
    with starrocks_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            return list(cur.fetchall()) if cur.description else []


def sql_value(value) -> str:
    if isinstance(value, str):
        return "'" + value.replace("'", "''") + "'"
    if value is None:
        return "NULL"
    return str(value)


def chunks(rows: list[tuple], size: int) -> Iterable[list[tuple]]:
    for i in range(0, len(rows), size):
        yield rows[i : i + size]


def insert_values(engine: str, table: str, columns: list[str], rows: list[tuple]) -> None:
    for batch in chunks(rows, INSERT_BATCH):
        values = ", ".join("(" + ", ".join(sql_value(v) for v in row) + ")" for row in batch)
        sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES {values}"
        if engine == "trino":
            trino_query(sql)
        elif engine == "clickhouse":
            clickhouse_query(sql)
        elif engine == "starrocks":
            starrocks_query(sql)
        else:
            raise ValueError(engine)


def generate_data() -> dict[str, list[tuple]]:
    customers = []
    products = []
    sales = []

    for customer_id in range(1, CUSTOMER_ROWS + 1):
        region = REGIONS[(customer_id - 1) % len(REGIONS)]
        segment = SEGMENTS[(customer_id - 1) % len(SEGMENTS)]
        customers.append((customer_id, region, segment))

    for product_id in range(1, PRODUCT_ROWS + 1):
        category = CATEGORIES[(product_id - 1) % len(CATEGORIES)]
        base_price = round(10 + ((product_id * 13) % 4000) / 100, 2)
        products.append((product_id, category, base_price))

    for sale_id in range(1, FACT_ROWS + 1):
        customer_id = ((sale_id * 17) % CUSTOMER_ROWS) + 1
        product_id = ((sale_id * 13) % PRODUCT_ROWS) + 1
        month = ((sale_id * 7) % 12) + 1
        day = ((sale_id * 11) % 28) + 1
        sale_date = f"2024-{month:02d}-{day:02d}"
        qty = (sale_id % 5) + 1
        discount = round((sale_id % 10) / 100, 2)
        unit_price = round(10 + ((product_id * 13) % 4000) / 100, 2)
        amount = round(qty * unit_price * (1 - discount), 2)
        sales.append((sale_id, customer_id, product_id, sale_date, qty, amount, discount))

    return {"customers": customers, "products": products, "sales": sales}


def start_clickhouse() -> None:
    docker_rm(CLICKHOUSE_CONTAINER)
    subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            CLICKHOUSE_CONTAINER,
            "-p",
            "8123:8123",
            "-p",
            "9000:9000",
            CLICKHOUSE_IMAGE,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    wait_until(lambda: clickhouse_query("SELECT 1") == "1", 180, "ClickHouse did not start")


def start_trino() -> None:
    docker_rm(TRINO_CONTAINER)
    subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            TRINO_CONTAINER,
            "-p",
            "8080:8080",
            "-v",
            f"{TRINO_MEMORY_CATALOG}:/etc/trino/catalog/memory.properties:ro",
            TRINO_IMAGE,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    wait_until(lambda: len(trino_query("SHOW CATALOGS")) > 0, 240, "Trino did not start")


def start_starrocks() -> None:
    docker_rm(STARROCKS_CONTAINER)
    subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            STARROCKS_CONTAINER,
            "-p",
            "8030:8030",
            "-p",
            "9030:9030",
            STARROCKS_IMAGE,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    wait_until(lambda: len(starrocks_query("SELECT 1")) > 0, 360, "StarRocks did not start")


def setup_clickhouse(data: dict[str, list[tuple]]) -> EngineResult:
    clickhouse_query("DROP DATABASE IF EXISTS hw09")
    clickhouse_query("CREATE DATABASE hw09")
    clickhouse_query(
        """
        CREATE TABLE hw09.dim_customers (
            customer_id Int32,
            region String,
            segment String
        ) ENGINE = MergeTree ORDER BY customer_id
        """
    )
    clickhouse_query(
        """
        CREATE TABLE hw09.dim_products (
            product_id Int32,
            category String,
            base_price Float64
        ) ENGINE = MergeTree ORDER BY product_id
        """
    )
    clickhouse_query(
        """
        CREATE TABLE hw09.fact_sales (
            sale_id Int32,
            customer_id Int32,
            product_id Int32,
            sale_date Date,
            qty Int32,
            amount Float64,
            discount Float64
        ) ENGINE = MergeTree ORDER BY sale_id
        """
    )
    started = time.perf_counter()
    insert_values("clickhouse", "hw09.dim_customers", ["customer_id", "region", "segment"], data["customers"])
    insert_values("clickhouse", "hw09.dim_products", ["product_id", "category", "base_price"], data["products"])
    insert_values("clickhouse", "hw09.fact_sales", ["sale_id", "customer_id", "product_id", "sale_date", "qty", "amount", "discount"], data["sales"])
    load_time = time.perf_counter() - started
    version = clickhouse_query("SELECT version()")
    return EngineResult("ClickHouse", version, load_time, {})


def setup_trino(data: dict[str, list[tuple]]) -> EngineResult:
    try:
        trino_query("DROP SCHEMA memory.hw09 CASCADE")
    except Exception:  # noqa: BLE001
        pass
    trino_query("CREATE SCHEMA memory.hw09")
    trino_query("CREATE TABLE memory.hw09.dim_customers (customer_id INTEGER, region VARCHAR, segment VARCHAR)")
    trino_query("CREATE TABLE memory.hw09.dim_products (product_id INTEGER, category VARCHAR, base_price DOUBLE)")
    trino_query(
        "CREATE TABLE memory.hw09.fact_sales (sale_id INTEGER, customer_id INTEGER, product_id INTEGER, sale_date DATE, qty INTEGER, amount DOUBLE, discount DOUBLE)"
    )
    started = time.perf_counter()
    insert_values("trino", "memory.hw09.dim_customers", ["customer_id", "region", "segment"], data["customers"])
    insert_values("trino", "memory.hw09.dim_products", ["product_id", "category", "base_price"], data["products"])
    insert_values("trino", "memory.hw09.fact_sales", ["sale_id", "customer_id", "product_id", "sale_date", "qty", "amount", "discount"], data["sales"])
    load_time = time.perf_counter() - started
    version = trino_query("SELECT version()")[0][0]
    return EngineResult("Trino", version, load_time, {})


def setup_starrocks(data: dict[str, list[tuple]]) -> EngineResult:
    starrocks_query("DROP DATABASE IF EXISTS hw09")
    starrocks_query("CREATE DATABASE hw09")
    starrocks_query("USE hw09")
    starrocks_query(
        """
        CREATE TABLE hw09.dim_customers (
            customer_id INT,
            region STRING,
            segment STRING
        )
        DUPLICATE KEY(customer_id)
        DISTRIBUTED BY HASH(customer_id) BUCKETS 1
        PROPERTIES('replication_num'='1')
        """
    )
    starrocks_query(
        """
        CREATE TABLE hw09.dim_products (
            product_id INT,
            category STRING,
            base_price DOUBLE
        )
        DUPLICATE KEY(product_id)
        DISTRIBUTED BY HASH(product_id) BUCKETS 1
        PROPERTIES('replication_num'='1')
        """
    )
    starrocks_query(
        """
        CREATE TABLE hw09.fact_sales (
            sale_id INT,
            customer_id INT,
            product_id INT,
            sale_date DATE,
            qty INT,
            amount DOUBLE,
            discount DOUBLE
        )
        DUPLICATE KEY(sale_id)
        DISTRIBUTED BY HASH(sale_id) BUCKETS 1
        PROPERTIES('replication_num'='1')
        """
    )
    started = time.perf_counter()
    insert_values("starrocks", "hw09.dim_customers", ["customer_id", "region", "segment"], data["customers"])
    insert_values("starrocks", "hw09.dim_products", ["product_id", "category", "base_price"], data["products"])
    insert_values("starrocks", "hw09.fact_sales", ["sale_id", "customer_id", "product_id", "sale_date", "qty", "amount", "discount"], data["sales"])
    load_time = time.perf_counter() - started
    version = str(starrocks_query("SELECT version()")[0][0])
    return EngineResult("StarRocks", version, load_time, {})


def benchmark_trino() -> dict[str, list[float]]:
    queries = {
        "q1_daily_agg": """
            SELECT sale_date, ROUND(SUM(amount), 2) AS revenue, COUNT(*) AS orders_cnt
            FROM memory.hw09.fact_sales
            GROUP BY sale_date
            ORDER BY sale_date
        """,
        "q2_filter_region": """
            SELECT c.region, ROUND(SUM(f.amount), 2) AS revenue, ROUND(AVG(f.qty), 2) AS avg_qty
            FROM memory.hw09.fact_sales f
            JOIN memory.hw09.dim_customers c ON f.customer_id = c.customer_id
            WHERE f.sale_date BETWEEN DATE '2024-06-01' AND DATE '2024-08-31'
            GROUP BY c.region
            ORDER BY revenue DESC
        """,
        "q3_join_top10": """
            SELECT c.region, p.category, ROUND(SUM(f.amount), 2) AS revenue, COUNT(*) AS orders_cnt
            FROM memory.hw09.fact_sales f
            JOIN memory.hw09.dim_customers c ON f.customer_id = c.customer_id
            JOIN memory.hw09.dim_products p ON f.product_id = p.product_id
            GROUP BY c.region, p.category
            ORDER BY revenue DESC
            LIMIT 10
        """,
        "q4_distinct_segment": """
            SELECT c.segment, COUNT(DISTINCT f.customer_id) AS buyers, ROUND(SUM(f.amount), 2) AS revenue
            FROM memory.hw09.fact_sales f
            JOIN memory.hw09.dim_customers c ON f.customer_id = c.customer_id
            WHERE f.discount >= 0.05
            GROUP BY c.segment
            ORDER BY revenue DESC
        """,
    }
    return measure_queries("trino", queries)


def benchmark_clickhouse() -> dict[str, list[float]]:
    queries = {
        "q1_daily_agg": """
            SELECT sale_date, round(sum(amount), 2) AS revenue, count(*) AS orders_cnt
            FROM hw09.fact_sales
            GROUP BY sale_date
            ORDER BY sale_date
        """,
        "q2_filter_region": """
            SELECT c.region, round(sum(f.amount), 2) AS revenue, round(avg(f.qty), 2) AS avg_qty
            FROM hw09.fact_sales f
            INNER JOIN hw09.dim_customers c ON f.customer_id = c.customer_id
            WHERE f.sale_date BETWEEN toDate('2024-06-01') AND toDate('2024-08-31')
            GROUP BY c.region
            ORDER BY revenue DESC
        """,
        "q3_join_top10": """
            SELECT c.region, p.category, round(sum(f.amount), 2) AS revenue, count(*) AS orders_cnt
            FROM hw09.fact_sales f
            INNER JOIN hw09.dim_customers c ON f.customer_id = c.customer_id
            INNER JOIN hw09.dim_products p ON f.product_id = p.product_id
            GROUP BY c.region, p.category
            ORDER BY revenue DESC
            LIMIT 10
        """,
        "q4_distinct_segment": """
            SELECT c.segment, count(DISTINCT f.customer_id) AS buyers, round(sum(f.amount), 2) AS revenue
            FROM hw09.fact_sales f
            INNER JOIN hw09.dim_customers c ON f.customer_id = c.customer_id
            WHERE f.discount >= 0.05
            GROUP BY c.segment
            ORDER BY revenue DESC
        """,
    }
    return measure_queries("clickhouse", queries)


def benchmark_starrocks() -> dict[str, list[float]]:
    queries = {
        "q1_daily_agg": """
            SELECT sale_date, ROUND(SUM(amount), 2) AS revenue, COUNT(*) AS orders_cnt
            FROM hw09.fact_sales
            GROUP BY sale_date
            ORDER BY sale_date
        """,
        "q2_filter_region": """
            SELECT c.region, ROUND(SUM(f.amount), 2) AS revenue, ROUND(AVG(f.qty), 2) AS avg_qty
            FROM hw09.fact_sales f
            JOIN hw09.dim_customers c ON f.customer_id = c.customer_id
            WHERE f.sale_date BETWEEN DATE('2024-06-01') AND DATE('2024-08-31')
            GROUP BY c.region
            ORDER BY revenue DESC
        """,
        "q3_join_top10": """
            SELECT c.region, p.category, ROUND(SUM(f.amount), 2) AS revenue, COUNT(*) AS orders_cnt
            FROM hw09.fact_sales f
            JOIN hw09.dim_customers c ON f.customer_id = c.customer_id
            JOIN hw09.dim_products p ON f.product_id = p.product_id
            GROUP BY c.region, p.category
            ORDER BY revenue DESC
            LIMIT 10
        """,
        "q4_distinct_segment": """
            SELECT c.segment, COUNT(DISTINCT f.customer_id) AS buyers, ROUND(SUM(f.amount), 2) AS revenue
            FROM hw09.fact_sales f
            JOIN hw09.dim_customers c ON f.customer_id = c.customer_id
            WHERE f.discount >= 0.05
            GROUP BY c.segment
            ORDER BY revenue DESC
        """,
    }
    return measure_queries("starrocks", queries)


def measure_queries(engine: str, queries: dict[str, str]) -> dict[str, list[float]]:
    results: dict[str, list[float]] = {}
    runners = {
        "trino": trino_query,
        "clickhouse": clickhouse_query,
        "starrocks": starrocks_query,
    }
    run = runners[engine]
    for name, sql in queries.items():
        run(sql)
        times = []
        for _ in range(MEASURE_RUNS):
            started = time.perf_counter()
            run(sql)
            times.append(round(time.perf_counter() - started, 3))
        results[name] = times
    return results


def average(values: list[float]) -> float:
    return round(sum(values) / len(values), 3)


def print_summary(results: list[EngineResult]) -> None:
    print("\n=== LOAD TIME ===")
    for item in results:
        print(f"{item.engine}: {item.load_time_s:.2f} s")

    print("\n=== QUERY TIMES (average of 3 measured runs) ===")
    query_names = ["q1_daily_agg", "q2_filter_region", "q3_join_top10", "q4_distinct_segment"]
    for query_name in query_names:
        print(f"\n{query_name}")
        for item in results:
            print(f"  {item.engine}: {average(item.query_times_s[query_name]):.3f} s -> {item.query_times_s[query_name]}")


def write_results(results: list[EngineResult]) -> None:
    payload = {
        "dataset": {
            "fact_rows": FACT_ROWS,
            "customer_rows": CUSTOMER_ROWS,
            "product_rows": PRODUCT_ROWS,
        },
        "engines": [
            {
                "engine": item.engine,
                "version": item.version,
                "load_time_s": round(item.load_time_s, 3),
                "query_times_s": item.query_times_s,
                "query_avg_s": {key: average(values) for key, values in item.query_times_s.items()},
            }
            for item in results
        ],
    }
    RESULTS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    docker_pull(CLICKHOUSE_IMAGE)
    docker_pull(TRINO_IMAGE)
    docker_pull(STARROCKS_IMAGE)

    data = generate_data()
    print(f"[data] fact={len(data['sales'])}, customers={len(data['customers'])}, products={len(data['products'])}")

    start_clickhouse()
    start_trino()
    start_starrocks()

    clickhouse = setup_clickhouse(data)
    trino = setup_trino(data)
    starrocks = setup_starrocks(data)

    clickhouse.query_times_s = benchmark_clickhouse()
    trino.query_times_s = benchmark_trino()
    starrocks.query_times_s = benchmark_starrocks()

    results = [trino, starrocks, clickhouse]
    write_results(results)
    print_summary(results)
    print(f"\n[done] results saved to {RESULTS_PATH}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
