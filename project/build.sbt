ThisBuild / scalaVersion := "3.8.3"
ThisBuild / organization := "ru.hse.datapipelines"

lazy val root = (project in file("."))
  .settings(
    name := "consultant-spark-project",
    version := "0.1.0",
    libraryDependencies ++= Seq(
      "org.apache.spark" % "spark-core_2.13" % "3.5.8" % Provided,
      "org.apache.spark" % "spark-sql_2.13" % "3.5.8" % Provided,
      "org.scalatest" %% "scalatest" % "3.2.19" % Test
    ),
    // Spark 3.5.x is published for Scala 2.12/2.13. With Scala 3 we must depend
    // on the Scala 2.13 Spark artifacts explicitly instead of using %%.
    Compile / mainClass := Some("ru.hse.datapipelines.consultant.ConsultantLogJob"),
    assembly / mainClass := Some("ru.hse.datapipelines.consultant.ConsultantLogJob"),
    assembly / assemblyJarName := "consultant-spark-project.jar",
    assembly / assemblyMergeStrategy := {
      case PathList("META-INF", xs @ _*) => MergeStrategy.discard
      case x                             => (assembly / assemblyMergeStrategy).value(x)
    }
  )
