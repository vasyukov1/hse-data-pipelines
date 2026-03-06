from pyspark.sql import functions as F
from bench_helpers import mk_spark, time_action
spark = mk_spark("case_a", shuffle_partitions=8)

# === Generate dataset ===
N = 5_000_000
keys = 1000
df = spark.range(0, N).select((F.col("id") % keys).alias("key"),
                              (F.col("id") % 1000).alias("value"))

# === DataFrame ===
df_aggs = df.groupBy("key").agg(
    F.sum("value").alias("sum"), 
    F.avg("value").alias("avg"), 
    F.min("value").alias("min")
)

def df_action():
    df_aggs.count()

# === RDD ===
rdd = df.rdd.map(lambda row: (row["key"], row["value"]))

def rdd_action():
    s = rdd.mapValues(lambda x: x).reduceByKey(lambda a,b: a+b).count()
    avg = rdd.mapValues(lambda x: (x, 1)).reduceByKey(lambda a,b: (a[0]+b[0], a[1]+b[1])).mapValues(lambda sc: sc[0]/sc[1]).count()
    m = rdd.reduceByKey(lambda a,b: a if a < b else b).count()

# === Measure ===
df_time = time_action(df_action)
rdd_time = time_action(rdd_action)
print(f"| Method    | Time      |")
print(f"|-----------|-----------|")
print(f"| DataFrame | {sum(df_time) / len(df_time)} |")
print(f"| RDD       | {sum(rdd_time) / len(rdd_time)} |")
df_aggs.explain(True)
