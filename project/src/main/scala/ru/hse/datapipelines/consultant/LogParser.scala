package ru.hse.datapipelines.consultant

import scala.annotation.tailrec
import scala.util.matching.Regex

final case class SearchEvent(
    searchId: String,           // Идентификатор результата поиска.
    searchType: String,         // Тип поиска: QS, CARD.
    eventDate: Option[String],  // Дата поиска.
    documents: Seq[String],     // Список документов из строки результата поиска.
    sourceFile: String,         // Файл лога.
    lineNumber: Int             // Номер строки.
)

final case class DocOpen(
    searchId: String,           // Ссылка на searchId из события QS/CARD.
    documentId: String,         // Идентификатор документа.
    eventDate: Option[String],  // Дата ткрытия.
    sourceFile: String,         // Файл лога.
    lineNumber: Int             // Номер строки.
)

final case class ParseWarning(
  sourceFile: String, // Файл лога.
  lineNumber: Int,    // Номер строки.
  message: String     // Сообщение предупреждения.
)

final case class ParsedFile(
    searches: Seq[SearchEvent],
    docOpens: Seq[DocOpen],
    warnings: Seq[ParseWarning]
)

object LogParser {
  private val SimpleDate: Regex =
    """^(\d{2})\.(\d{2})\.(\d{4})_(\d{2}):(\d{2}):(\d{2})$""".r

  private val VerboseDate: Regex =
    """^[A-Za-z]{3},_(\d{1,2})_([A-Za-z]{3})_(\d{4})_(\d{2}):(\d{2}):(\d{2})_[+-]\d{4}$""".r

  private val Months = Map(
    "Jan" -> "01",
    "Feb" -> "02",
    "Mar" -> "03",
    "Apr" -> "04",
    "May" -> "05",
    "Jun" -> "06",
    "Jul" -> "07",
    "Aug" -> "08",
    "Sep" -> "09",
    "Oct" -> "10",
    "Nov" -> "11",
    "Dec" -> "12"
  )

  def parseDateToken(token: String): Option[String] = token match {
    case SimpleDate(day, month, year, _, _, _) =>
      Some(s"$year-$month-$day")
    case VerboseDate(day, monthName, year, _, _, _) =>
      Months.get(monthName).map(month => f"$year-$month-${day.toInt}%02d")
    case _ =>
      None
  }

  def parseFile(sourceFile: String, content: String): ParsedFile = {
    val lines = content.split("\\r?\\n", -1).toVector
    val searches = Vector.newBuilder[SearchEvent]
    val docOpens = Vector.newBuilder[DocOpen]
    val warnings = Vector.newBuilder[ParseWarning]

    def warn(index: Int, message: String): Unit = warnings += ParseWarning(sourceFile, index + 1, message)

    def tokens(index: Int): Array[String] = lines(index).trim.split("\\s+").filter(_.nonEmpty)

    def parseResultLine(index: Int): Option[(String, Seq[String])] = {
      if (index >= lines.length) {
        None
      } else {
        val parts = tokens(index)
        if (parts.nonEmpty && isInteger(parts.head)) Some(parts.head -> parts.tail.toSeq) else None
      }
    }

    var i = 0
    while (i < lines.length) {
      val trimmed = lines(i).trim

      if (trimmed.startsWith("QS ")) {
        // Быстрый поиск: строка события содержит дату и текст запроса,
        // следующая строка содержит searchId и найденные документы.
        val parts = tokens(i)
        val date = parts.lift(1).flatMap(parseDateToken)
        if (date.isEmpty) warn(i, "QS event has missing or unsupported date")

        parseResultLine(i + 1) match {
          case Some((searchId, docs)) =>
            searches += SearchEvent(searchId, "QS", date, docs, sourceFile, i + 2)
            i += 2
          case None =>
            warn(i, "QS event is not followed by a valid result line")
            i += 1
        }
      } else if (trimmed.startsWith("CARD_SEARCH_START")) {
        // Карточка поиска: между START и END могут быть строки параметров
        // Для метрик нужны только дата старта и строка результатов после END.
        val parts = tokens(i)
        val date = parts.lift(1).flatMap(parseDateToken)
        if (date.isEmpty) warn(i, "CARD_SEARCH_START event has missing or unsupported date")

        val endIndex = findCardSearchEnd(lines, i + 1)
        endIndex match {
          case Some(j) =>
            parseResultLine(j + 1) match {
              case Some((searchId, docs)) =>
                searches += SearchEvent(searchId, "CARD", date, docs, sourceFile, j + 2)
                i = j + 2
              case None =>
                warn(j, "CARD_SEARCH_END is not followed by a valid result line")
                i = j + 1
            }
          case None =>
            warn(i, "CARD_SEARCH_START has no matching CARD_SEARCH_END")
            i += 1
        }
      } else if (trimmed.startsWith("DOC_OPEN")) {
        // DOC_OPEN бывает в двух вариантах:
        // 1) DOC_OPEN <date> <searchId> <documentId>
        // 2) DOC_OPEN <searchId> <documentId>
        val parts = tokens(i)
        parts.length match {
          case n if n >= 4 =>
            val date = parseDateToken(parts(1))
            if (date.isEmpty) warn(i, "DOC_OPEN event has unsupported date")
            docOpens += DocOpen(parts(2), parts(3), date, sourceFile, i + 1)
          case 3 =>
            docOpens += DocOpen(parts(1), parts(2), None, sourceFile, i + 1)
          case _ =>
            warn(i, "DOC_OPEN event has too few fields")
        }
        i += 1
      } else {
        i += 1
      }
    }

    ParsedFile(searches.result(), docOpens.result(), warnings.result())
  }

  private def isInteger(value: String): Boolean =
    value.matches("^-?\\d+$")

  private def findCardSearchEnd(lines: Vector[String], start: Int): Option[Int] = {
    @tailrec
    def loop(index: Int): Option[Int] = {
      if (index >= lines.length) None
      else if (lines(index).trim.startsWith("CARD_SEARCH_END")) Some(index)
      else loop(index + 1)
    }

    loop(start)
  }
}
