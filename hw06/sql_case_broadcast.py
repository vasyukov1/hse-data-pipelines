from pyspark.sql import functions as F
from bench_helpers import mk_spark, time_action
spark = mk_spark("sql_broadcast", shuffle_partitions=200)

# === Generate dataset ===
big = spark.range(0, 5_000_000).select((F.col("id") % 100000).alias("key"), F.col("id").alias("value"))
small = spark.range(0, 1000).select((F.col("id") % 100000).alias("key"), (F.col("id")%10).alias("s"))

big.createOrReplaceTempView("big")
small.createOrReplaceTempView("small")

# === DataFrame ===
sql_q = """
SELECT /*+ BROADCAST(small) */ b.key, count(*)
FROM big b
JOIN small s ON b.key = s.key
GROUP BY b.key
"""
df_sql = spark.sql(sql_q)

df_df = big.join(small, on="key").groupBy("key").count()

# === Measure ===
sql_times = time_action(lambda: df_sql.count())
df_times = time_action(lambda: df_df.count())
print(f"| Method    | Time      |")
print(f"|-----------|-----------|")
print(f"| Broadcast | {sum(df_times) / len(df_times)} |")
print(f"| Base      | {sum(sql_times) / len(sql_times)} |")
df_sql.explain(True)
df_df.explain(True)
