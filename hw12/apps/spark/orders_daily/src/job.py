from pyspark.sql import SparkSession
from pyspark.sql import functions as F
import os


def main() -> None:
    input_path = os.environ.get("INPUT_PATH", "file:///opt/spark/app/data/orders.csv")
    output_path = os.environ.get("OUTPUT_PATH", "file:///tmp/orders_daily_report")

    spark = (
        SparkSession.builder.appName("orders-daily")
        .config("spark.sql.session.timeZone", "UTC")
        .getOrCreate()
    )

    orders = (
        spark.read.option("header", True).option("inferSchema", True).csv(input_path)
    )

    result = (
        orders.withColumn("order_date", F.to_date("created_at"))
        .groupBy("order_date", "product")
        .agg(
            F.count("*").alias("orders_total"),
            F.round(F.sum("amount"), 2).alias("amount_total"),
        )
        .orderBy("order_date", "product")
    )

    result.show(truncate=False)

    (
        result.coalesce(1)
        .write.mode("overwrite")
        .json(output_path)
    )

    spark.stop()


if __name__ == "__main__":
    main()
