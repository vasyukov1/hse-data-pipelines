package ru.hse.datapipelines.consultant

import org.scalatest.funsuite.AnyFunSuite

class LogParserSpec extends AnyFunSuite {
  test("parses QS with simple date and result line") {
    val parsed = LogParser.parseFile(
      "sample",
      """SESSION_START 23.06.2020_03:53:29
        |QS 23.06.2020_03:55:06 {query}
        |276347703 LAW_71050 ACC_45616
        |DOC_OPEN 23.06.2020_03:56:47 276347703 ACC_45616
        |""".stripMargin
    )

    assert(parsed.searches.head.searchType == "QS")
    assert(parsed.searches.head.eventDate.contains("2020-06-23"))
    assert(parsed.searches.head.documents == Seq("LAW_71050", "ACC_45616"))
    assert(parsed.docOpens.head.eventDate.contains("2020-06-23"))
  }

  test("parses verbose date format") {
    assert(LogParser.parseDateToken("Fri,_26_Jun_2020_16:24:28_+0300").contains("2020-06-26"))
  }

  test("parses card search parameters and results") {
    val parsed = LogParser.parseFile(
      "sample",
      """CARD_SEARCH_START 07.06.2020_19:45:54
        |$134 регистрация государственных контрактов
        |CARD_SEARCH_END
        |269432656 PKBO_34940 ACC_45616
        |""".stripMargin
    )

    assert(parsed.searches.size == 1)
    assert(parsed.searches.head.searchType == "CARD")
    assert(parsed.searches.head.documents.contains("ACC_45616"))
  }

  test("parses DOC_OPEN without timestamp") {
    val parsed = LogParser.parseFile("sample", "DOC_OPEN  5181406 PAP_1393\n")

    assert(parsed.docOpens == Seq(DocOpen("5181406", "PAP_1393", None, "sample", 1)))
  }

  test("broken events produce warnings instead of exceptions") {
    val parsed = LogParser.parseFile(
      "sample",
      """QS 23.06.2020_03:55:06 {query}
        |DOC_OPEN
        |CARD_SEARCH_START 01.01.2020_00:00:00
        |$0 value
        |""".stripMargin
    )

    assert(parsed.warnings.exists(_.message.contains("QS event is not followed")))
    assert(parsed.warnings.exists(_.message.contains("DOC_OPEN event has too few fields")))
    assert(parsed.warnings.exists(_.message.contains("CARD_SEARCH_START has no matching")))
  }
}
