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
    table_path = "/tmp/lakehouse/delta_table"
    shutil.rmtree("/tmp/lakehouse", ignore_errors=True)

    spark = SparkSession.builder \
        .appName("Delta_Experiment") \
        .master("local[*]") \
        .config("spark.driver.memory", "4g") \
        .config("spark.jars.packages", "io.delta:delta-spark_2.12:3.1.0") \
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("ERROR")

    print("=== DELTA LAKE EXPERIMENTS ===")
    
    total_rows = 1_000_000
    df = spark.range(0, total_rows).selectExpr("id", "cast(rand() * 1000 as int) as amount", "current_timestamp() as updated_at")
    
    start = time.time()
    df.write.format("delta").mode("overwrite").save(table_path)
    print(f"Write 100% time: {time.time() - start:.2f} s")
    print(f"Storage size: {get_size(table_path):.2f} MB")

    start = time.time()
    spark.read.format("delta").load(table_path).agg({"amount": "sum"}).collect()
    print(f"Read time: {time.time() - start:.2f} s")

    spark.read.format("delta").load(table_path).createOrReplaceTempView("target_table")
    
    for pct in [10, 20, 50]:
        fraction = pct / 100.0
        base_df = spark.read.format("delta").load(table_path)
        update_df = base_df.sample(fraction=fraction).selectExpr("id", "amount + 100 as amount", "current_timestamp() as updated_at")
        update_df.createOrReplaceTempView("source_table")
        
        start = time.time()
        spark.sql("""
            MERGE INTO target_table t
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
                    UPDATE target_table 
                    SET amount = amount + {thread_id} 
                    WHERE id < 1000
                """)
                return f"Thread {thread_id} SUCCESS on attempt {attempt + 1}"
            except Exception as e:
                time.sleep(1)
        return f"Thread {thread_id} FAILED after {max_retries} attempts"

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures =[executor.submit(concurrent_update, i) for i in range(2)]
        for f in concurrent.futures.as_completed(futures):
            print(f.result())

    spark.stop()

if __name__ == "__main__":
    main()
