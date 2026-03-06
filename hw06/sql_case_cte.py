from pyspark.sql import functions as F
from bench_helpers import mk_spark, time_action
spark = mk_spark("sql_cte", shuffle_partitions=8)

big = spark.range(0, 5_000_000).select((F.col("id") % 100000).alias("key"), F.col("id").alias("value"))
big.createOrReplaceTempView("big")

# === DataFrame ===
sql_cte = """
WITH sub AS (
    SELECT key, sum(value) as s 
    FROM big 
    GROUP BY key
)
SELECT a.key, a.s, b.s
FROM sub a 
JOIN sub b ON a.key = b.key 
WHERE a.s > 1000
"""
df_sql = spark.sql(sql_cte)

df_sub = big.groupBy("key").agg(F.sum("value").alias("s"))
df_df_naive = df_sub.alias("a").join(df_sub.alias("b"), "key").filter(F.col("a.s") > 1000)

# === Measure ===
df_sql.explain(True)
df_df_naive.explain(True)
