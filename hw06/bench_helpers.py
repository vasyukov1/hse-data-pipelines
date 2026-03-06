import time
from pyspark.sql import SparkSession

def mk_spark(app="bench", shuffle_partitions=200):
    spark = SparkSession.builder \
        .appName(app) \
        .config("spark.sql.shuffle.partitions", str(shuffle_partitions)) \
        .getOrCreate()
    return spark

def time_action(fun, n_warm=1, n_runs=3):
    times = []
    # warmup
    for i in range(n_warm):
        fun()
    # runs
    for i in range(n_runs):
        time0 = time.perf_counter()
        fun()
        time1 = time.perf_counter()
        times.append(time1 - time0)
    return times
