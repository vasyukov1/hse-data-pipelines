# Отчёт: DataFrame vs RDD в Apache Spark – сравнительный анализ производительности

---

## Кейс A: Множественные агрегации

### Постановка задачи и причина выбора

Агрегации – одна из самых частых операций в аналитике. Кейс выбран, чтобы показать, насколько по-разному DataFrame и RDD справляются с задачей "посчитать сразу несколько метрик по группам" (`sum`, `avg`, `min` по 1 000 ключей на 5 млн строк).

### Реализация эксперимента

**DataFrame:**
```python
df.groupBy("key").agg(
    F.sum("value").alias("sum"),
    F.avg("value").alias("avg"),
    F.min("value").alias("min")
)
```

**RDD:**
```python
rdd.reduceByKey(lambda a, b: a + b).count()

avg = rdd.mapValues(lambda x: (x, 1)).reduceByKey(lambda a,b: (a[0]+b[0], a[1]+b[1])).mapValues(lambda sc: sc[0]/sc[1]).count()

rdd.reduceByKey(lambda a, b: a if a < b else b).count()
```

### Результаты

| Метод | Время |
|-------|-------|
| DataFrame | 0.10 с |
| RDD | 12.16 с |

### Почему такой результат?

**DataFrame:**

Из физического плана:

```
+- HashAggregate(keys=[key], functions=[sum(value), avg(value), min(value)], output=[key, sum, avg, min])
   +- Exchange hashpartitioning(key, 8), ENSURE_REQUIREMENTS, [plan_id=371]
      +- HashAggregate(keys=[key], functions=[partial_sum(value), partial_avg(value), partial_min(value)], output=[key, sum, sum, count, min])
```

Catalyst применил partial (local) + final (global) aggregation – это двухфазная схема:

- **Фаза 1 (local/partial):** каждый executor сначала частично агрегирует данные у себя, не отправляя ничего по сети.
- **Фаза 2 (global/final):** после одного shuffle данные объединяются в финальный результат.

Все три агрегата (`sum`, `avg`, `min`) вычисляются в одном проходе по данным. Tungsten генерирует байт-код JVM, который за один цикл обновляет все три аккумулятора одновременно, без лишних выделений памяти.

**Итого для DataFrame:** 1 shuffle, 1 проход по данным.

**RDD:**

Каждая метрика – отдельная операция `reduceByKey`, а значит отдельный проход по данным и отдельный shuffle. Три метрики = три shuffles. Дополнительно: Python-RDD сериализует данные через `pickle` при каждой передаче между JVM и Python-интерпретатором – это значительные накладные расходы.

**Итого для RDD:** 3 shuffles, 3 прохода по данным + накладные расходы сериализации.

### Вывод

Когда нужно несколько агрегатов – используйте `groupBy().agg(...)`. DataFrame автоматически объединяет их в один проход. RDD вынуждает программиста вручную управлять каждым проходом, что многократно дороже.

---

## Кейс B: Оконные функции – Top-N в группе

### Постановка задачи и причина выбора

Частая задача "найти топ-N записей в каждой группе": топ продаж по категориям, топ пользователей по активности и т.д. Выбрана для демонстрации специализированной оптимизации Catalyst для оконных функций.

### Реализация эксперимента

**DataFrame:**
```python
w = Window.partitionBy("key").orderBy(F.col("value").desc())

df_topk = df.withColumn("rn", F.row_number().over(w)).filter(F.col("rn") < 5).select("key", "value")
```

**RDD:**
```python
rdd.groupByKey().mapValues(lambda x: sorted(x, reverse=True)[:5]).count()
```

### Результаты

| Метод | Время |
|-------|-------|
| DataFrame | 0.37 с |
| RDD | 3.92 с |

### Почему такой результат?

**DataFrame:**

В Optimized Logical Plan виден специальный узел:

```
+- WindowGroupLimit [key], [value DESC NULLS LAST], row_number(), 4
```

Это оптимизация, которая вместо того чтобы сортировать все строки каждой группы и потом отфильтровать топ-4, отсекает лишние строки до финального shuffle. Это работает в два прохода:

- **WindowGroupLimit Partial** – на каждом executor локально отбирает не более 4 строк на группу.
- **Exchange (shuffle)** – пересылает только отобранные строки.
- **WindowGroupLimit Final** – финальная фильтрация после объединения.

В физическом плане:
```
WindowGroupLimit ... Final
  +- Sort [key ASC, value DESC]
     +- Exchange hashpartitioning(key, 8)
        +- WindowGroupLimit ... Partial
           +- Sort [key ASC, value DESC]
```

Помимо этого, план обёрнут в `AdaptiveSparkPlan` – это AQE (Adaptive Query Execution), механизм, который во время выполнения может менять план на основе реальных данных (например, выбрать другую стратегию join).

**RDD:**

`groupByKey()` собирает все значения группы в одну коллекцию на executor – это дорогостоящая операция по памяти. Затем Python сортирует весь список (`sorted()`), и только потом берётся первые 5. Если в группе 1000 элементов – все 1000 пересылаются и сортируются, хотя нужны только 4.

### Вывод

Для задачи Top-N в группе DataFrame не просто удобнее – он применяет специальный оптимизированный оператор, который принципиально сокращает объём работы. RDD вынужден работать напрямую, как сказано.

---

## Кейс C: Работа с вложенными типами – Struct и Array

### Постановка задачи и причина выбора

Реальные данные часто приходят в JSON-формате с вложенными структурами. Кейс демонстрирует, насколько DataFrame эффективнее работает с вложенными типами (`struct`, `array`, `explode`) по сравнению с ручным парсингом в RDD.

### Реализация эксперимента

**DataFrame:**
```python
df2 = df.select("key", "meta.subid", F.explode("values").alias("value"))
```

**RDD:**
```python
# сериализация в JSON
rdd = df.rdd.map(lambda row: json.dumps({
    "key": row["key"],
    "meta": {
        "subid": row["meta"]["subid"],
    },
    "values": row["values"]
}))

# парсинг JSON и разворачивание
parsed = rdd.map(lambda s: json.loads(s)) \ 
            .flatMap(lambda d: [ (d["key"], d["meta"]["subid"], v) for v in d["values"] ]) \
            .count()
```

### Результаты

| Метод | Время |
|-------|-------|
| DataFrame | 0.17 с |
| RDD | 11.38 с |

### Почему такой результат?

**DataFrame:**

В Optimized Logical Plan есть преобразование:
```
Project [(id % 1000) AS key, (id % 100) AS _extract_subid, array(...) AS values]
  +- Filter (size(array(...)) > 0)
     +- Range (...)
```

Catalyst применил projection pushdown – доступ к вложенному полю `meta.subid` упрощён до прямого вычисления `(id % 100)`, без создания промежуточного объекта struct. Физический план показывает работу в одной стадии без shuffle:

```
*(1) Generate explode(values), [key, _extract_subid]
  +- *(1) Project [...]
     +- *(1) Filter (size(...) > 0)
        +- *(1) Range (...)
```

Префикс `*(1)` означает Whole-Stage Code Generation – весь пайплайн скомпилирован в один блок байт-кода JVM. Данные хранятся в бинарном формате Tungsten, поля структуры извлекаются как смещения в памяти – без создания объектов. Никакого shuffle нет вообще.

**RDD:**

Данные сначала сериализуются из формата Spark в JSON-строку (`json.dumps`) – это уже дорого. Затем каждая строка парсится из JSON обратно в Python-объект (`json.loads`) – ещё дороже. После этого `flatMap` разворачивает вложенные массивы в Python. Это три дорогостоящих операции на каждую из 5 миллионов строк.

### Вывод

Вложенные данные в DataFrame хранятся в оптимизированном бинарном формате и обрабатываются без сериализации. RDD-подход требует явной сериализации/десериализации на уровне Python – дорого на больших данных.

---

## SQL Кейс 1: Broadcast Join

### Постановка задачи

Join большой таблицы (5 млн строк) с маленькой (1 000 строк). Сравниваются: SQL с явным хинтом `BROADCAST` и DataFrame API без подсказок.

### Реализация

**SQL с broadcast hint:**
```sql
SELECT /*+ BROADCAST(small) */ b.key, count(*)
FROM big b 
JOIN small s ON b.key = s.key
GROUP BY b.key
```

**DataFrame:**
```python
big.join(small, on="key").groupBy("key").count()
```

### Что показывает план

**SQL с хинтом:**
```
BroadcastHashJoin [key], [key], Inner, BuildRight
  +- BroadcastExchange HashedRelationBroadcastMode(...)
```

Маленькая таблица `small` разослана на все executors – каждый executor получает её полную копию. Join выполняется локально, без shuffle большой таблицы.

**DataFrame:**

Несмотря на то что таблица `small` маленькая, без явного хинта Catalyst может не гарантировать broadcast (зависит от настройки `spark.sql.autoBroadcastJoinThreshold`). Наивный DataFrame может использовать SortMergeJoin с shuffle обеих сторон.

### Вывод

SQL-хинт `/*+ BROADCAST(small) */` даёт программисту явный контроль над физическим планом. BroadcastHashJoin – один из наиболее мощных способов ускорить join: большая таблица не перемещается по сети вообще.

---

## SQL Кейс 2: CTE и повторное использование подзапросов

### Постановка задачи

CTE (Common Table Expressions) – способ написать читаемый SQL с повторно используемым подзапросом.

### Реализация

**SQL с CTE:**
```sql
WITH sub AS (
    SELECT key, sum(value) as s 
    FROM big 
    GROUP BY key
)
SELECT a.key, a.s, b.s
FROM sub a 
JOIN sub b ON a.key = b.key
WHERE a.s > 1000
```

**DataFrame:**
```python
df_sub = big.groupBy("key").agg(F.sum("value").alias("s"))
df_df_naive = df_sub.alias("a").join(df_sub.alias("b"), "key").filter(...)
```

### Что показывает план

В Optimized Logical Plan CTE раскрыт в два независимых агрегата:

```
Join Inner, (key = key)
  :- Filter (s > 1000) +- Aggregate +- Range(...)
  +- Aggregate +- Range(...)
```

То есть Catalyst не кэширует CTE автоматически – подзапрос вычисляется дважды. Это происходит и для варианта DataFrame с `df_sub` без явного `cache()`.

Физический план у обоих вариантов одинаков: два `HashAggregate` + `SortMergeJoin`.

### Вывод

CTE – это инструмент для читаемости кода, но не гарантия кэширования. Если подзапрос нужен несколько раз и он дорогой – нужно явно вызвать `.cache()` или `.persist()`.

---

## Общий вывод

### Почему DataFrame стабильно быстрее RDD

| Причина | DataFrame | RDD (Python) |
|---------|-----------|--------------|
| Количество shuffles | Сильно меньше | Кратно числу операций |
| Проходов по данным | 1 | По 1 на каждую операцию |
| Сериализация | Нет (бинарный формат Tungsten) | На каждой границе JVM и Python |
| Генерация кода | Whole-stage codegen | Интерпретация Python |
| Оптимизации Catalyst | Partial agg, WindowGroupLimit, Broadcast, Pushdown | Нет |
