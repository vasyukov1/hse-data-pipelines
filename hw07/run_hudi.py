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
    table_path = "/tmp/lakehouse/hudi_table"
    shutil.rmtree("/tmp/lakehouse", ignore_errors=True)

    spark = SparkSession.builder \
        .appName("Hudi_Experiment") \
        .master("local[*]") \
        .config("spark.driver.memory", "4g") \
        .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer") \
        .config("spark.jars.packages", "org.apache.hudi:hudi-spark3.5-bundle_2.12:0.15.0") \
        .config("spark.sql.extensions", "org.apache.spark.sql.hudi.HoodieSparkSessionExtension") \
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.hudi.catalog.HoodieCatalog") \
        .getOrCreate()

    spark.sparkContext.setLogLevel("ERROR")

    print("=== HUDI EXPERIMENTS ===")
    
    total_rows = 1_000_000
    df = spark.range(0, total_rows).selectExpr("id", "cast(rand() * 1000 as int) as amount", "current_timestamp() as updated_at", "CAST(id % 10 AS STRING) as partition_key")
    
    hudi_options = {
        'hoodie.table.name': 'hudi_table',
        'hoodie.datasource.write.recordkey.field': 'id',
        'hoodie.datasource.write.partitionpath.field': 'partition_key',
        'hoodie.datasource.write.precombine.field': 'updated_at',
        'hoodie.datasource.write.table.type': 'MERGE_ON_READ',
        'hoodie.datasource.write.operation': 'bulk_insert'
    }

    start = time.time()
    df.write.format("hudi").options(**hudi_options).mode("overwrite").save(table_path)
    print(f"Write 100% time: {time.time() - start:.2f} s")

    print(f"Storage size: {get_size(table_path):.2f} MB")

    start = time.time()
    spark.read.format("hudi").load(table_path).agg({"amount": "sum"}).collect()
    print(f"Read time: {time.time() - start:.2f} s")

    hudi_options['hoodie.datasource.write.operation'] = 'upsert'
    for pct in[10, 20, 50]:
        fraction = pct / 100.0
        base_df = spark.read.format("hudi").load(table_path)
        update_df = base_df.sample(fraction=fraction).selectExpr("id", "amount + 100 as amount", "current_timestamp() as updated_at", "partition_key")
        
        start = time.time()
        update_df.write.format("hudi").options(**hudi_options).mode("append").save(table_path)
        print(f"Update {pct}% time: {time.time() - start:.2f} s")

    print("--- Concurrent Writes Test ---")
    def concurrent_update(thread_id):
        max_retries = 3
        
        hudi_options_concurrent = hudi_options.copy()
        hudi_options_concurrent['hoodie.write.concurrency.mode'] = 'optimistic_concurrency_control'
        hudi_options_concurrent['hoodie.write.lock.provider'] = 'org.apache.hudi.client.transaction.lock.InProcessLockProvider'
        
        for attempt in range(max_retries):
            try:
                base_df = spark.read.format("hudi").load(table_path)
                udf = base_df.limit(1000).selectExpr("id", f"amount + {thread_id} as amount", "current_timestamp() as updated_at", "partition_key")
                udf.write.format("hudi").options(**hudi_options_concurrent).mode("append").save(table_path)
                return f"Thread {thread_id} SUCCESS on attempt {attempt + 1}"
            except Exception as e:
                time.sleep(2)
        return f"Thread {thread_id} FAILED after {max_retries} attempts"

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(concurrent_update, i) for i in range(2)]
        for f in concurrent.futures.as_completed(futures):
            print(f.result())

    spark.stop()

if __name__ == "__main__":
    main()
