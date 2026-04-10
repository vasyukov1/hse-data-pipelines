# Сравнение Trino, StarRocks и ClickHouse

## 1. Что нужно было сделать

По лекции нужно сравнить распределённые SQL-движки. Минимум в задании: `Trino` и `StarRocks`. Третьим движком я взял `ClickHouse`, потому что это один из самых популярных open-source движков для аналитики, и его удобно поставить рядом с Trino и StarRocks.

Я решил сделать работу в простом формате:

1. коротко объяснить, что это за движки;
2. посмотреть benchmark-результаты;
3. подготовить свои простые SQL-тесты;
4. сделать вывод, где какой движок лучше.

## 2. Что я сравнивал

### Trino

`Trino` — это не классическая аналитическая база со своим storage, а SQL-движок, который умеет ходить в разные источники данных через коннекторы. Его сильная сторона — федерация данных: можно одним SQL читать данные из разных систем.

### StarRocks

`StarRocks` — это MPP-движок для аналитики. Он ближе к BI и к lakehouse-сценариям. Его сильные стороны — высокая скорость, materialized views, cache и хорошая работа с тяжелыми аналитическими запросами.

### ClickHouse

`ClickHouse` — это колонночная аналитическая СУБД. Его основная сила — очень быстрые агрегации, фильтрация и `GROUP BY` на больших объёмах данных.

## 3. Как я сравнивал

Я использовал два типа сравнения.

### 3.1. Готовые benchmark-источники

Чтобы не сравнивать движки «на глаз», я взял:

- официальный benchmark `StarRocks` для сравнения `StarRocks` и `Trino`;
- открытый benchmark `ClickBench` для сравнения `StarRocks` и `ClickHouse`.

### 3.2. Свой бенчмарк

Чтобы работа не была только пересказом чужих графиков, я добавил свой простой сценарий тестирования в файле [run_microbench.py](/Users/alexvasyukov/Documents/GitHub/hse-data-pipelines/hw09/run_microbench.py).

Идея теста простая:

- генерируется небольшой синтетический датасет продаж;
- есть три таблицы:
  - `dim_customers`
  - `dim_products`
  - `fact_sales`
- для всех трёх движков используются одни и те же 4 запроса:
  - обычная агрегация по дням;
  - фильтр + агрегация по регионам;
  - `JOIN + GROUP BY + LIMIT`;
  - `COUNT DISTINCT + SUM`.

То есть я ориентировался не на экзотические тесты, а на типичные аналитические запросы.

## 4. Какие запросы я выбрал для простого теста

### Тест 1. Простая агрегация

Смысл: посмотреть, как движок считает выручку и количество заказов по датам.

```sql
SELECT sale_date, SUM(amount) AS revenue, COUNT(*) AS orders_cnt
FROM fact_sales
GROUP BY sale_date
ORDER BY sale_date;
```

### Тест 2. Фильтр + агрегация

Смысл: типичный BI-запрос, когда есть фильтр по времени и потом группировка.

```sql
SELECT c.region, SUM(f.amount) AS revenue, AVG(f.qty) AS avg_qty
FROM fact_sales f
JOIN dim_customers c ON f.customer_id = c.customer_id
WHERE f.sale_date BETWEEN '2024-06-01' AND '2024-08-31'
GROUP BY c.region
ORDER BY revenue DESC;
```

### Тест 3. Join + Group By + Top 10

Смысл: типичный аналитический запрос по витрине продаж.

```sql
SELECT c.region, p.category, SUM(f.amount) AS revenue, COUNT(*) AS orders_cnt
FROM fact_sales f
JOIN dim_customers c ON f.customer_id = c.customer_id
JOIN dim_products p ON f.product_id = p.product_id
GROUP BY c.region, p.category
ORDER BY revenue DESC
LIMIT 10;
```

### Тест 4. Count Distinct

Смысл: посмотреть, как движок ведёт себя на более тяжёлой агрегации.

```sql
SELECT c.segment, COUNT(DISTINCT f.customer_id) AS buyers, SUM(f.amount) AS revenue
FROM fact_sales f
JOIN dim_customers c ON f.customer_id = c.customer_id
WHERE f.discount >= 0.05
GROUP BY c.segment
ORDER BY revenue DESC;
```

## 5. Benchmark 1: StarRocks против Trino

Для сравнения `StarRocks` и `Trino` я использовал официальный benchmark StarRocks на `TPC-DS 1 TB` поверх `Iceberg`.

### Результат

| Движок | Полное время |
| --- | ---: |
| `StarRocks` | `368 404 ms` |
| `Trino` | `2 552 076 ms` |

### Простой вывод

В этом тесте `StarRocks` оказался быстрее `Trino` примерно в `6.9` раза.

### Почему так

Это логично, потому что:

- `StarRocks` сильнее заточен под тяжёлую аналитику;
- у него есть встроенные ускорители;
- `Trino` больше про универсальный SQL-слой над разными источниками.

То есть если нужна именно скорость аналитических запросов на lakehouse-сценарии, `StarRocks` здесь выглядит сильнее.

## 6. Benchmark 2: ClickHouse против StarRocks

Для сравнения `ClickHouse` и `StarRocks` я использовал `ClickBench`.

Я взял raw JSON snapshots и посчитал итоговые показатели в файле [reproduce_clickbench_metrics.py](hw09/reproduce_clickbench_metrics.py).

### Результаты

| Метрика | ClickHouse | StarRocks |
| --- | ---: | ---: |
| Load time | `312 s` | `608 s` |
| Data size | `15.25 GB` | `17.25 GB` |
| Hot runtime ratio | `1.00x` | `1.736x` |
| Cold runtime ratio | `1.00x` | `1.845x` |
| Combined ratio | `1.00x` | `1.703x` |

### Простой вывод

На этом benchmark `ClickHouse` оказался лучше `StarRocks`:

- быстрее загружает данные;
- занимает меньше места;
- быстрее отвечает на аналитические запросы.

### Но есть оговорка

Это не значит, что `ClickHouse` всегда лучше. Это значит только то, что:

- для нативной аналитики и `GROUP BY`-нагрузки `ClickHouse` очень силён;
- но `StarRocks` при этом остаётся сильным именно как lakehouse/BI engine.

## 7. Ключевые различия

| Критерий | Trino | StarRocks | ClickHouse |
| --- | --- | --- | --- |
| Главная роль | SQL-слой над разными источниками | быстрый аналитический engine для BI и lakehouse | очень быстрый аналитический storage engine |
| Сильная сторона | много коннекторов | BI, joins, materialized views, cache | агрегации и скорость |
| Где хорош | федерация данных | lakehouse + BI | clickstream, events, ad-hoc analytics |
| Главный минус | не всегда самый быстрый | сложнее, чем просто query engine | меньше похож на универсальный federation engine |

## 8. Риски внедрения

### Trino

Главный риск — ожидать от него скорости как от специализированной аналитической СУБД. Он хороший как единый SQL-слой, но не всегда лучший как основной BI engine.

### StarRocks

Главный риск — недооценить сложность настройки:

- materialized views;
- refresh;
- cache;
- работа с внешними таблицами.

Если всё это настроить хорошо, StarRocks очень силён. Если нет, можно не получить ожидаемую скорость.

### ClickHouse

Главный риск — ошибиться в модели данных. Для ClickHouse очень важны:

- ключ сортировки;
- партиционирование;
- структура таблиц;
- понимание, как будут идти запросы.

## 9. Итоговое решение

Если выбирать один движок для сценария:

- есть data lake;
- есть BI;
- нужны тяжёлые аналитические запросы;
- хочется и скорость, и работу с внешними форматами,

то я бы выбрал `StarRocks`.

### Почему именно StarRocks

Потому что он лучше всего выглядит как компромисс:

- быстрее Trino на lakehouse benchmark;
- ближе к ClickHouse по performance-мышлению;
- при этом умеет хорошо работать с внешними таблицами и open table formats.

## 10. Когда я бы выбрал не StarRocks

### Когда выбрать Trino

Если главная задача — это единый SQL-доступ к разным источникам, а не максимальная скорость тяжёлой аналитики.

### Когда выбрать ClickHouse

Если главная задача — это:

- очень быстрые агрегации;
- дашборды;
- event analytics;
- clickstream;
- логи и метрики.

## 11. Финальный вывод

Итог можно сформулировать очень просто:

- `Trino` — лучший как универсальный SQL-слой над разными системами;
- `ClickHouse` — лучший для очень быстрой нативной аналитики;
- `StarRocks` — лучший компромисс для `lakehouse + BI`.

Поэтому для этой работы итоговое решение: **выбрать StarRocks**.
