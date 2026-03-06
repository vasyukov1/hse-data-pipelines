from pyspark.sql import functions as F, Window
from bench_helpers import mk_spark, time_action
spark = mk_spark("case_b", shuffle_partitions=8)

# === Generate dataset ===
N = 5_000_000
keys = 1000
df = spark.range(0, N).select((F.col("id") % keys).alias("key"),
                              (F.col("id") % 1000).alias("value"))

# === DataFrame ===
w = Window.partitionBy("key").orderBy(F.col("value").desc())
df_topk = df.withColumn("rn", F.row_number().over(w)).filter(F.col("rn") < 5).select("key", "value")

def df_action():
    df_topk.count()

# === RDD ===
rdd = df.rdd.map(lambda row: (row["key"], row["value"]))

def rdd_action():
    topk = rdd.groupByKey().mapValues(lambda x: sorted(x, reverse=True)[:5]).count()

# === Measure ===
df_time = time_action(df_action)
rdd_time = time_action(rdd_action)
print(f"| Method    | Time      |")
print(f"|-----------|-----------|")
print(f"| DataFrame | {sum(df_time) / len(df_time)} |")
print(f"| RDD       | {sum(rdd_time) / len(rdd_time)} |")
df_topk.explain(True)
