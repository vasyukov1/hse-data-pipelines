
# Delta
```sh
/usr/local/bin/python3 /Users/alexvasyukov/Documents/GitHub/hse-data-pipelines/hw07/run
_delta.py
:: loading settings :: url = jar:file:/Library/Frameworks/Python.framework/Versions/3.12/lib/python3.12/site-packages/pyspark/jars/ivy-2.5.1.jar!/org/apache/ivy/core/settings/ivysettings.xml
Ivy Default Cache set to: /Users/alexvasyukov/.ivy2/cache
The jars for the packages stored in: /Users/alexvasyukov/.ivy2/jars
io.delta#delta-spark_2.12 added as a dependency
:: resolving dependencies :: org.apache.spark#spark-submit-parent-fd490687-6dc7-4ec3-8150-8698ad604ba2;1.0
        confs: [default]
        found io.delta#delta-spark_2.12;3.1.0 in central
        found io.delta#delta-storage;3.1.0 in central
        found org.antlr#antlr4-runtime;4.9.3 in central
:: resolution report :: resolve 92ms :: artifacts dl 2ms
        :: modules in use:
        io.delta#delta-spark_2.12;3.1.0 from central in [default]
        io.delta#delta-storage;3.1.0 from central in [default]
        org.antlr#antlr4-runtime;4.9.3 from central in [default]
        ---------------------------------------------------------------------
        |                  |            modules            ||   artifacts   |
        |       conf       | number| search|dwnlded|evicted|| number|dwnlded|
        ---------------------------------------------------------------------
        |      default     |   3   |   0   |   0   |   0   ||   3   |   0   |
        ---------------------------------------------------------------------
:: retrieving :: org.apache.spark#spark-submit-parent-fd490687-6dc7-4ec3-8150-8698ad604ba2
        confs: [default]
        0 artifacts copied, 3 already retrieved (0kB/3ms)
26/03/12 23:54:27 WARN NativeCodeLoader: Unable to load native-hadoop library for your platform... using builtin-java classes where applicable
Setting default log level to "WARN".
To adjust logging level use sc.setLogLevel(newLevel). For SparkR, use setLogLevel(newLevel).
=== DELTA LAKE EXPERIMENTS ===
Write 100% time: 5.61 s                                                         
Storage size: 5.10 MB
Read time: 0.43 s
Update 10% time: 3.14 s                                                         
Update 20% time: 2.00 s
Update 50% time: 1.82 s
--- Concurrent Writes Test ---
Thread 1 SUCCESS on attempt 1
Thread 0 SUCCESS on attempt 2
```

# Iceberg
```sh
/usr/local/bin/python3 /Users/alexvasyukov/Documents/GitHub/hse-data-pipelines/hw07/run
_iceberg.py
:: loading settings :: url = jar:file:/Library/Frameworks/Python.framework/Versions/3.12/lib/python3.12/site-packages/pyspark/jars/ivy-2.5.1.jar!/org/apache/ivy/core/settings/ivysettings.xml
Ivy Default Cache set to: /Users/alexvasyukov/.ivy2/cache
The jars for the packages stored in: /Users/alexvasyukov/.ivy2/jars
org.apache.iceberg#iceberg-spark-runtime-3.5_2.12 added as a dependency
:: resolving dependencies :: org.apache.spark#spark-submit-parent-a02fd7a3-3a7e-4d93-af2e-b82ee044a2b6;1.0
        confs: [default]
        found org.apache.iceberg#iceberg-spark-runtime-3.5_2.12;1.5.0 in central
:: resolution report :: resolve 66ms :: artifacts dl 2ms
        :: modules in use:
        org.apache.iceberg#iceberg-spark-runtime-3.5_2.12;1.5.0 from central in [default]
        ---------------------------------------------------------------------
        |                  |            modules            ||   artifacts   |
        |       conf       | number| search|dwnlded|evicted|| number|dwnlded|
        ---------------------------------------------------------------------
        |      default     |   1   |   0   |   0   |   0   ||   1   |   0   |
        ---------------------------------------------------------------------
:: retrieving :: org.apache.spark#spark-submit-parent-a02fd7a3-3a7e-4d93-af2e-b82ee044a2b6
        confs: [default]
        0 artifacts copied, 1 already retrieved (0kB/2ms)
26/03/12 23:55:22 WARN NativeCodeLoader: Unable to load native-hadoop library for your platform... using builtin-java classes where applicable
Setting default log level to "WARN".
To adjust logging level use sc.setLogLevel(newLevel). For SparkR, use setLogLevel(newLevel).
=== ICEBERG EXPERIMENTS ===
Write 100% time: 2.97 s                                                         
Storage size: 2.24 MB
Read time: 0.54 s
Update 10% time: 1.44 s
Update 20% time: 1.28 s                                                         
Update 50% time: 1.28 s
--- Concurrent Writes Test ---
Thread 0 SUCCESS on attempt 1
26/03/12 23:55:39 ERROR ReplaceDataExec: Data source write support IcebergBatchWrite(table=local.db.iceberg_table, format=PARQUET) is aborting.
26/03/12 23:55:39 ERROR ReplaceDataExec: Data source write support IcebergBatchWrite(table=local.db.iceberg_table, format=PARQUET) aborted.
Thread 1 SUCCESS on attempt 2
```

# Hudi
```sh
/usr/local/bin/python3 /Users/alexvasyukov/Documents/GitHub/hse-data-pipelines/hw07/run
_hudi.py
:: loading settings :: url = jar:file:/Library/Frameworks/Python.framework/Versions/3.12/lib/python3.12/site-packages/pyspark/jars/ivy-2.5.1.jar!/org/apache/ivy/core/settings/ivysettings.xml
Ivy Default Cache set to: /Users/alexvasyukov/.ivy2/cache
The jars for the packages stored in: /Users/alexvasyukov/.ivy2/jars
org.apache.hudi#hudi-spark3.5-bundle_2.12 added as a dependency
:: resolving dependencies :: org.apache.spark#spark-submit-parent-87c50c3c-0244-45fa-ac5f-812f0bd81dba;1.0
        confs: [default]
        found org.apache.hudi#hudi-spark3.5-bundle_2.12;0.15.0 in central
        found org.apache.hive#hive-storage-api;2.8.1 in central
        found org.slf4j#slf4j-api;1.7.36 in central
:: resolution report :: resolve 104ms :: artifacts dl 3ms
        :: modules in use:
        org.apache.hive#hive-storage-api;2.8.1 from central in [default]
        org.apache.hudi#hudi-spark3.5-bundle_2.12;0.15.0 from central in [default]
        org.slf4j#slf4j-api;1.7.36 from central in [default]
        ---------------------------------------------------------------------
        |                  |            modules            ||   artifacts   |
        |       conf       | number| search|dwnlded|evicted|| number|dwnlded|
        ---------------------------------------------------------------------
        |      default     |   3   |   0   |   0   |   0   ||   3   |   0   |
        ---------------------------------------------------------------------
:: retrieving :: org.apache.spark#spark-submit-parent-87c50c3c-0244-45fa-ac5f-812f0bd81dba
        confs: [default]
        0 artifacts copied, 3 already retrieved (0kB/2ms)
26/03/12 23:56:13 WARN NativeCodeLoader: Unable to load native-hadoop library for your platform... using builtin-java classes where applicable
Setting default log level to "WARN".
To adjust logging level use sc.setLogLevel(newLevel). For SparkR, use setLogLevel(newLevel).
=== HUDI EXPERIMENTS ===
# WARNING: Unable to get Instrumentation. Dynamic Attach failed. You may add this JAR as -javaagent manually, or supply -Djdk.attach.allowAttachSelf
# WARNING: Unable to attach Serviceability Agent. Unable to attach even with module exceptions: [org.apache.hudi.org.openjdk.jol.vm.sa.SASupportException: Sense failed., org.apache.hudi.org.openjdk.jol.vm.sa.SASupportException: Sense failed., org.apache.hudi.org.openjdk.jol.vm.sa.SASupportException: Sense failed.]
Write 100% time: 7.38 s
Storage size: 41.63 MB
Read time: 0.89 s
Update 10% time: 11.56 s                                                        
Update 20% time: 10.39 s                                                        
Update 50% time: 12.68 s                                                        
--- Concurrent Writes Test ---
Thread 1 SUCCESS on attempt 1                                                   
Thread 0 SUCCESS on attempt 2
```