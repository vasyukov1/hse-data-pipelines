package ru.hse.datapipelines.consultant

import org.apache.spark.sql.{SaveMode, SparkSession}
import org.apache.spark.sql.functions._

object ConsultantLogJob {
  private val WideTableTopDocuments = 30

  def main(args: Array[String]): Unit = {
    val inputPath = args.lift(0).getOrElse("data")
    val outputPath = args.lift(1).getOrElse("results")

    val spark = SparkSession
      .builder()
      .appName("consultant-log-analysis")
      .master(sys.props.getOrElse("spark.master", "local[*]"))
      .getOrCreate()

    import spark.implicits._

    spark.sparkContext.setLogLevel("WARN")

    // Парсинг файлов на (путь, содержимое).
    val parsedFiles = spark.sparkContext
      .wholeTextFiles(inputPath)
      .map { case (path, content) => LogParser.parseFile(path, content) }
      .cache()

    // Разделение на отдельные датасеты.
    val searches = parsedFiles.flatMap(_.searches).toDS().cache()
    val docOpens = parsedFiles.flatMap(_.docOpens).toDS().cache()
    val warnings = parsedFiles.flatMap(_.warnings).toDS()

    // Метрика 1: CARD-поиски, где среди найденных документов есть ACC_45616.
    val cardAccCount = searches
      .filter($"searchType" === "CARD" && array_contains($"documents", "ACC_45616"))
      .count()

    // Запись результата метрики 1.
    Seq(("ACC_45616", cardAccCount))
      .toDF("document_id", "card_search_count")
      .coalesce(1)
      .write
      .mode(SaveMode.Overwrite)
      .option("header", "true")
      .csv(s"$outputPath/card_acc_45616_count.csv")

    // Для второй метрики нужный только QS.
    val qsSearches = searches
      .filter($"searchType" === "QS")
      .select(
        $"sourceFile",
        $"searchId",
        $"eventDate".as("searchDate"),
        $"documents".as("foundDocuments")
      )

    // Метрика 2: 
    // - связь открытия с QS
    // - проверка, что документ найден
    // - восстановление даты
    // - подсчёт по дням
    val qsDocOpensByDay = docOpens
      // Связь открытия с QS.
      .join(qsSearches, Seq("sourceFile", "searchId"), "inner")
      .filter(expr("array_contains(foundDocuments, documentId)"))
      // Восстановление даты.
      .withColumn("resultDate", coalesce($"eventDate", $"searchDate"))
      .filter($"resultDate".isNotNull)
      // Подсчёт.
      .groupBy($"resultDate".as("date"), $"documentId".as("document_id"))
      .agg(count(lit(1)).as("open_count"))
      .orderBy($"date", $"document_id")

    // Сохранение результата подсчёта.
    qsDocOpensByDay
      .coalesce(1)
      .write
      .mode(SaveMode.Overwrite)
      .option("header", "true")
      .csv(s"$outputPath/qs_doc_opens_by_day.csv")

    // Построение таблицы для удобного просмотра.
    // Получение самых популярных документов.
    val topDocuments = qsDocOpensByDay
      .groupBy($"document_id")
      .agg(sum($"open_count").as("total_open_count"))
      .orderBy($"total_open_count".desc, $"document_id")
      .limit(WideTableTopDocuments)
      .select($"document_id")
      .as[String]
      .collect()
      .toSeq

    // Получение количества открытий популярных документов по дням.
    val qsDocOpensWideRaw = qsDocOpensByDay
      .filter($"document_id".isin(topDocuments: _*))
      .groupBy($"date")
      .pivot("document_id", topDocuments)
      .agg(sum($"open_count"))
      .na
      .fill(0)
      .orderBy($"date")

    // Переименование столбцов.
    val qsDocOpensWideTop = topDocuments.foldLeft(
      qsDocOpensWideRaw.withColumnRenamed("date", "день")
    ) { case (table, documentId) =>
      table.withColumnRenamed(documentId, s"количество_открытий_$documentId")
    }

    // Запись результата метрики 2.
    qsDocOpensWideTop
      .coalesce(1)
      .write
      .mode(SaveMode.Overwrite)
      .option("header", "true")
      .csv(s"$outputPath/qs_doc_opens_by_day_wide_top30.csv")

    // Запись предупреждений.
    warnings
      .coalesce(1)
      .write
      .mode(SaveMode.Overwrite)
      .option("header", "true")
      .csv(s"$outputPath/parse_warnings.csv")

    // Вывод результата в терминале.
    println(s"card_acc_45616_count=$cardAccCount")
    println(s"qs_doc_opens_by_day_rows=${qsDocOpensByDay.count()}")
    println(s"qs_doc_opens_by_day_wide_top_documents=${topDocuments.size}")
    println(s"parse_warnings_count=${warnings.count()}")

    spark.stop()
  }
}
