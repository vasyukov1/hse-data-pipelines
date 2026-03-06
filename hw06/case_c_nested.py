import json
from pyspark.sql import functions as F
from bench_helpers import mk_spark, time_action
spark = mk_spark("case_c", shuffle_partitions=8)

# === Generate dataset ===
N = 5_000_000
keys = 1000
df = spark.range(0, N).select(
    ((F.col("id") % keys).alias("key")),
    F.struct(
        (F.col("id") % 100).alias("subid"),
        (F.col("id") % 5).alias("flag")
    ).alias("meta"),
    F.array(*( (F.col("id") % 10 + i) for i in range(3) )).alias("values")
)

# === DataFrame ===
df2 = df.select("key", "meta.subid", F.explode("values").alias("value"))

def df_action():
    df2.count()

# === RDD ===
rdd = df.rdd.map(lambda row: json.dumps({
    "key": row["key"],
    "meta": {
        "subid": row["meta"]["subid"],
    },
    "values": row["values"]
}))

def rdd_action():
    parsed = rdd.map(lambda s: json.loads(s)) \
                .flatMap(lambda d: [ (d["key"], d["meta"]["subid"], v) for v in d["values"] ]) \
                .count()
    
# === Measure ===
df_time = time_action(df_action)
rdd_time = time_action(rdd_action)
print(f"| Method    | Time      |")
print(f"|-----------|-----------|")
print(f"| DataFrame | {sum(df_time) / len(df_time)} |")
print(f"| RDD       | {sum(rdd_time) / len(rdd_time)} |")
df2.explain(True)
