import os
import time
import shutil
import concurrent.futures
from pyspark.sql import SparkSession

def get_size(path):
    total_size = 0
    for dirpath, _, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)
    return total_size / (1024 * 1024)

def main():
    warehouse_path = "/tmp/lakehouse_iceberg"
    shutil.rmtree(warehouse_path, ignore_errors=True)

    spark = SparkSession.builder \
        .appName("Iceberg_Experiment") \
        .master("local[*]") \
        .config("spark.driver.memory", "4g") \
        .config("spark.jars.packages", "org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.5.0") \
        .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \
        .config("spark.sql.catalog.local", "org.apache.iceberg.spark.SparkCatalog") \
        .config("spark.sql.catalog.local.type", "hadoop") \
        .config("spark.sql.catalog.local.warehouse", warehouse_path) \
        .getOrCreate()

    spark.sparkContext.setLogLevel("ERROR")

    print("=== ICEBERG EXPERIMENTS ===")
    
    total_rows = 1_000_000
    df = spark.range(0, total_rows).selectExpr("id", "cast(rand() * 1000 as int) as amount", "current_timestamp() as updated_at")
    
    start = time.time()
    df.sortWithinPartitions("id").writeTo("local.db.iceberg_table").tableProperty("format-version", "2").createOrReplace()
    print(f"Write 100% time: {time.time() - start:.2f} s")

    table_dir = f"{warehouse_path}/db/iceberg_table"
    print(f"Storage size: {get_size(table_dir):.2f} MB")

    start = time.time()
    spark.read.table("local.db.iceberg_table").agg({"amount": "sum"}).collect()
    print(f"Read time: {time.time() - start:.2f} s")

    for pct in [10, 20, 50]:
        fraction = pct / 100.0
        base_df = spark.read.table("local.db.iceberg_table")
        update_df = base_df.sample(fraction=fraction).selectExpr("id", "amount + 100 as amount", "current_timestamp() as updated_at")
        update_df.createOrReplaceTempView("source_table")
        
        start = time.time()
        spark.sql("""
            MERGE INTO local.db.iceberg_table t
            USING source_table s
            ON t.id = s.id
            WHEN MATCHED THEN UPDATE SET t.amount = s.amount, t.updated_at = s.updated_at
        """)
        print(f"Update {pct}% time: {time.time() - start:.2f} s")

    print("--- Concurrent Writes Test ---")
    def concurrent_update(thread_id):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                spark.sql(f"""
                    UPDATE local.db.iceberg_table 
                    SET amount = amount + {thread_id} 
                    WHERE id < 1000
                """)
                return f"Thread {thread_id} SUCCESS on attempt {attempt + 1}"
            except Exception as e:
                time.sleep(1)
        return f"Thread {thread_id} FAILED after {max_retries} attempts"

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(concurrent_update, i) for i in range(2)]
        for f in concurrent.futures.as_completed(futures):
            print(f.result())

    spark.stop()

if __name__ == "__main__":
    main()
