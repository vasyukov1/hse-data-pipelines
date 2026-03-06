# Результаты

## Case A

```bash
| Method    | Time      |           
|-----------|-----------|
| DataFrame | 0.1010318753348353 |
| RDD       | 12.159524958328499 |
== Parsed Logical Plan ==
'Aggregate ['key], ['key, 'sum('value) AS sum#3, 'avg('value) AS avg#4, 'min('value) AS min#5]
+- Project [(id#0L % cast(1000 as bigint)) AS key#1L, (id#0L % cast(1000 as bigint)) AS value#2L]
   +- Range (0, 5000000, step=1, splits=Some(8))

== Analyzed Logical Plan ==
key: bigint, sum: bigint, avg: double, min: bigint
Aggregate [key#1L], [key#1L, sum(value#2L) AS sum#3L, avg(value#2L) AS avg#4, min(value#2L) AS min#5L]
+- Project [(id#0L % cast(1000 as bigint)) AS key#1L, (id#0L % cast(1000 as bigint)) AS value#2L]
   +- Range (0, 5000000, step=1, splits=Some(8))

== Optimized Logical Plan ==
Aggregate [key#1L], [key#1L, sum(value#2L) AS sum#3L, avg(value#2L) AS avg#4, min(value#2L) AS min#5L]
+- Project [(id#0L % 1000) AS key#1L, (id#0L % 1000) AS value#2L]
   +- Range (0, 5000000, step=1, splits=Some(8))

== Physical Plan ==
AdaptiveSparkPlan isFinalPlan=false
+- HashAggregate(keys=[key#1L], functions=[sum(value#2L), avg(value#2L), min(value#2L)], output=[key#1L, sum#3L, avg#4, min#5L])
   +- Exchange hashpartitioning(key#1L, 8), ENSURE_REQUIREMENTS, [plan_id=371]
      +- HashAggregate(keys=[key#1L], functions=[partial_sum(value#2L), partial_avg(value#2L), partial_min(value#2L)], output=[key#1L, sum#47L, sum#48, count#49L, min#50L])
         +- Project [(id#0L % 1000) AS key#1L, (id#0L % 1000) AS value#2L]
            +- Range (0, 5000000, step=1, splits=8)
```

## Case B 
```bash
| Method    | Time      |
|-----------|-----------|
| DataFrame | 0.36662002732434 |
| RDD       | 3.9235293746654256 |
== Parsed Logical Plan ==
'Project ['key, 'value]
+- Filter (rn#3 < 5)
   +- Project [key#1L, value#2L, rn#3]
      +- Project [key#1L, value#2L, rn#3, rn#3]
         +- Window [row_number() windowspecdefinition(key#1L, value#2L DESC NULLS LAST, specifiedwindowframe(RowFrame, unboundedpreceding$(), currentrow$())) AS rn#3], [key#1L], [value#2L DESC NULLS LAST]
            +- Project [key#1L, value#2L]
               +- Project [(id#0L % cast(1000 as bigint)) AS key#1L, (id#0L % cast(1000 as bigint)) AS value#2L]
                  +- Range (0, 5000000, step=1, splits=Some(8))

== Analyzed Logical Plan ==
key: bigint, value: bigint
Project [key#1L, value#2L]
+- Filter (rn#3 < 5)
   +- Project [key#1L, value#2L, rn#3]
      +- Project [key#1L, value#2L, rn#3, rn#3]
         +- Window [row_number() windowspecdefinition(key#1L, value#2L DESC NULLS LAST, specifiedwindowframe(RowFrame, unboundedpreceding$(), currentrow$())) AS rn#3], [key#1L], [value#2L DESC NULLS LAST]
            +- Project [key#1L, value#2L]
               +- Project [(id#0L % cast(1000 as bigint)) AS key#1L, (id#0L % cast(1000 as bigint)) AS value#2L]
                  +- Range (0, 5000000, step=1, splits=Some(8))

== Optimized Logical Plan ==
Project [key#1L, value#2L]
+- Filter (rn#3 < 5)
   +- Window [row_number() windowspecdefinition(key#1L, value#2L DESC NULLS LAST, specifiedwindowframe(RowFrame, unboundedpreceding$(), currentrow$())) AS rn#3], [key#1L], [value#2L DESC NULLS LAST]
      +- WindowGroupLimit [key#1L], [value#2L DESC NULLS LAST], row_number(), 4
         +- Project [(id#0L % 1000) AS key#1L, (id#0L % 1000) AS value#2L]
            +- Range (0, 5000000, step=1, splits=Some(8))

== Physical Plan ==
AdaptiveSparkPlan isFinalPlan=false
+- Project [key#1L, value#2L]
   +- Filter (rn#3 < 5)
      +- Window [row_number() windowspecdefinition(key#1L, value#2L DESC NULLS LAST, specifiedwindowframe(RowFrame, unboundedpreceding$(), currentrow$())) AS rn#3], [key#1L], [value#2L DESC NULLS LAST]
         +- WindowGroupLimit [key#1L], [value#2L DESC NULLS LAST], row_number(), 4, Final
            +- Sort [key#1L ASC NULLS FIRST, value#2L DESC NULLS LAST], false, 0
               +- Exchange hashpartitioning(key#1L, 8), ENSURE_REQUIREMENTS, [plan_id=666]
                  +- WindowGroupLimit [key#1L], [value#2L DESC NULLS LAST], row_number(), 4, Partial
                     +- Sort [key#1L ASC NULLS FIRST, value#2L DESC NULLS LAST], false, 0
                        +- Project [(id#0L % 1000) AS key#1L, (id#0L % 1000) AS value#2L]
                           +- Range (0, 5000000, step=1, splits=8)
```

## Case C

```bash
| Method    | Time      |
|-----------|-----------|
| DataFrame | 0.1738559446821455 |
| RDD       | 11.382787750005567 |
== Parsed Logical Plan ==
'Project ['key, 'meta.subid, 'explode('values) AS value#6]
+- Project [(id#0L % cast(1000 as bigint)) AS key#1L, struct(subid, (id#0L % cast(100 as bigint)), flag, (id#0L % cast(5 as bigint))) AS meta#4, array(((id#0L % cast(10 as bigint)) + cast(0 as bigint)), ((id#0L % cast(10 as bigint)) + cast(1 as bigint)), ((id#0L % cast(10 as bigint)) + cast(2 as bigint))) AS values#5]
   +- Range (0, 5000000, step=1, splits=Some(8))

== Analyzed Logical Plan ==
key: bigint, subid: bigint, value: bigint
Project [key#1L, meta#4.subid AS subid#7L, value#8L]
+- Generate explode(values#5), false, [value#8L]
   +- Project [(id#0L % cast(1000 as bigint)) AS key#1L, struct(subid, (id#0L % cast(100 as bigint)), flag, (id#0L % cast(5 as bigint))) AS meta#4, array(((id#0L % cast(10 as bigint)) + cast(0 as bigint)), ((id#0L % cast(10 as bigint)) + cast(1 as bigint)), ((id#0L % cast(10 as bigint)) + cast(2 as bigint))) AS values#5]
      +- Range (0, 5000000, step=1, splits=Some(8))

== Optimized Logical Plan ==
Project [key#1L, _extract_subid#37L AS subid#7L, value#8L]
+- Generate explode(values#5), [2], false, [value#8L]
   +- Project [(id#0L % 1000) AS key#1L, (id#0L % 100) AS _extract_subid#37L, array((id#0L % 10), ((id#0L % 10) + 1), ((id#0L % 10) + 2)) AS values#5]
      +- Filter (size(array((id#0L % 10), ((id#0L % 10) + 1), ((id#0L % 10) + 2)), false) > 0)
         +- Range (0, 5000000, step=1, splits=Some(8))

== Physical Plan ==
*(1) Project [key#1L, _extract_subid#37L AS subid#7L, value#8L]
+- *(1) Generate explode(values#5), [key#1L, _extract_subid#37L], false, [value#8L]
   +- *(1) Project [(id#0L % 1000) AS key#1L, (id#0L % 100) AS _extract_subid#37L, array((id#0L % 10), ((id#0L % 10) + 1), ((id#0L % 10) + 2)) AS values#5]
      +- *(1) Filter (size(array((id#0L % 10), ((id#0L % 10) + 1), ((id#0L % 10) + 2)), false) > 0)
         +- *(1) Range (0, 5000000, step=1, splits=8)
```

## SQL Case Broadcast
```bash
| Method    | Time      |
|-----------|-----------|
| Broadcast | 0.24200793067575432 |
| Base      | 0.2889991530003802 |
== Parsed Logical Plan ==
'UnresolvedHint BROADCAST, ['small]
+- 'Aggregate ['b.key], ['b.key, unresolvedalias('count(1))]
   +- 'Join Inner, ('b.key = 's.key)
      :- 'SubqueryAlias b
      :  +- 'UnresolvedRelation [big], [], false
      +- 'SubqueryAlias s
         +- 'UnresolvedRelation [small], [], false

== Analyzed Logical Plan ==
key: bigint, count(1): bigint
Aggregate [key#1L], [key#1L, count(1) AS count(1)#7L]
+- Join Inner, (key#1L = key#4L)
   :- SubqueryAlias b
   :  +- SubqueryAlias big
   :     +- View (`big`, [key#1L, value#2L])
   :        +- Project [(id#0L % cast(100000 as bigint)) AS key#1L, id#0L AS value#2L]
   :           +- Range (0, 5000000, step=1, splits=Some(8))
   +- SubqueryAlias s
      +- SubqueryAlias small
         +- View (`small`, [key#4L, s#5L])
            +- Project [(id#3L % cast(100000 as bigint)) AS key#4L, (id#3L % cast(10 as bigint)) AS s#5L]
               +- Range (0, 1000, step=1, splits=Some(8))

== Optimized Logical Plan ==
Aggregate [key#1L], [key#1L, count(1) AS count(1)#7L]
+- Project [key#1L]
   +- Join Inner, (key#1L = key#4L)
      :- Project [(id#0L % 100000) AS key#1L]
      :  +- Filter isnotnull((id#0L % 100000))
      :     +- Range (0, 5000000, step=1, splits=Some(8))
      +- Project [(id#3L % 100000) AS key#4L]
         +- Filter isnotnull((id#3L % 100000))
            +- Range (0, 1000, step=1, splits=Some(8))

== Physical Plan ==
AdaptiveSparkPlan isFinalPlan=false
+- HashAggregate(keys=[key#1L], functions=[count(1)], output=[key#1L, count(1)#7L])
   +- Exchange hashpartitioning(key#1L, 200), ENSURE_REQUIREMENTS, [plan_id=1626]
      +- HashAggregate(keys=[key#1L], functions=[partial_count(1)], output=[key#1L, count#62L])
         +- Project [key#1L]
            +- BroadcastHashJoin [key#1L], [key#4L], Inner, BuildRight, false
               :- Project [(id#0L % 100000) AS key#1L]
               :  +- Filter isnotnull((id#0L % 100000))
               :     +- Range (0, 5000000, step=1, splits=8)
               +- BroadcastExchange HashedRelationBroadcastMode(List(input[0, bigint, true]),false), [plan_id=1621]
                  +- Project [(id#3L % 100000) AS key#4L]
                     +- Filter isnotnull((id#3L % 100000))
                        +- Range (0, 1000, step=1, splits=8)

== Parsed Logical Plan ==
'Aggregate ['key], ['key, 'count(1) AS count#8]
+- Project [key#1L, value#2L, s#5L]
   +- Join Inner, (key#1L = key#4L)
      :- Project [(id#0L % cast(100000 as bigint)) AS key#1L, id#0L AS value#2L]
      :  +- Range (0, 5000000, step=1, splits=Some(8))
      +- Project [(id#3L % cast(100000 as bigint)) AS key#4L, (id#3L % cast(10 as bigint)) AS s#5L]
         +- Range (0, 1000, step=1, splits=Some(8))

== Analyzed Logical Plan ==
key: bigint, count: bigint
Aggregate [key#1L], [key#1L, count(1) AS count#8L]
+- Project [key#1L, value#2L, s#5L]
   +- Join Inner, (key#1L = key#4L)
      :- Project [(id#0L % cast(100000 as bigint)) AS key#1L, id#0L AS value#2L]
      :  +- Range (0, 5000000, step=1, splits=Some(8))
      +- Project [(id#3L % cast(100000 as bigint)) AS key#4L, (id#3L % cast(10 as bigint)) AS s#5L]
         +- Range (0, 1000, step=1, splits=Some(8))

== Optimized Logical Plan ==
Aggregate [key#1L], [key#1L, count(1) AS count#8L]
+- Project [key#1L]
   +- Join Inner, (key#1L = key#4L)
      :- Project [(id#0L % 100000) AS key#1L]
      :  +- Filter isnotnull((id#0L % 100000))
      :     +- Range (0, 5000000, step=1, splits=Some(8))
      +- Project [(id#3L % 100000) AS key#4L]
         +- Filter isnotnull((id#3L % 100000))
            +- Range (0, 1000, step=1, splits=Some(8))

== Physical Plan ==
AdaptiveSparkPlan isFinalPlan=false
+- HashAggregate(keys=[key#1L], functions=[count(1)], output=[key#1L, count#8L])
   +- Exchange hashpartitioning(key#1L, 200), ENSURE_REQUIREMENTS, [plan_id=1672]
      +- HashAggregate(keys=[key#1L], functions=[partial_count(1)], output=[key#1L, count#64L])
         +- Project [key#1L]
            +- BroadcastHashJoin [key#1L], [key#4L], Inner, BuildRight, false
               :- Project [(id#0L % 100000) AS key#1L]
               :  +- Filter isnotnull((id#0L % 100000))
               :     +- Range (0, 5000000, step=1, splits=8)
               +- BroadcastExchange HashedRelationBroadcastMode(List(input[0, bigint, true]),false), [plan_id=1667]
                  +- Project [(id#3L % 100000) AS key#4L]
                     +- Filter isnotnull((id#3L % 100000))
                        +- Range (0, 1000, step=1, splits=8)
```

## SQL Case CTE

```bash 
== Parsed Logical Plan ==
CTE [sub]
:  +- 'SubqueryAlias sub
:     +- 'Aggregate ['key], ['key, 'sum('value) AS s#3]
:        +- 'UnresolvedRelation [big], [], false
+- 'Project ['a.key, 'a.s, 'b.s]
   +- 'Filter ('a.s > 1000)
      +- 'Join Inner, ('a.key = 'b.key)
         :- 'SubqueryAlias a
         :  +- 'UnresolvedRelation [sub], [], false
         +- 'SubqueryAlias b
            +- 'UnresolvedRelation [sub], [], false

== Analyzed Logical Plan ==
key: bigint, s: bigint, s: bigint
WithCTE
:- CTERelationDef 0, false
:  +- SubqueryAlias sub
:     +- Aggregate [key#1L], [key#1L, sum(value#2L) AS s#3L]
:        +- SubqueryAlias big
:           +- View (`big`, [key#1L, value#2L])
:              +- Project [(id#0L % cast(100000 as bigint)) AS key#1L, id#0L AS value#2L]
:                 +- Range (0, 5000000, step=1, splits=Some(8))
+- Project [key#1L, s#3L, s#6L]
   +- Filter (s#3L > cast(1000 as bigint))
      +- Join Inner, (key#1L = key#5L)
         :- SubqueryAlias a
         :  +- SubqueryAlias sub
         :     +- CTERelationRef 0, true, [key#1L, s#3L], false, false
         +- SubqueryAlias b
            +- SubqueryAlias sub
               +- CTERelationRef 0, true, [key#5L, s#6L], false, false

== Optimized Logical Plan ==
Project [key#1L, s#3L, s#6L]
+- Join Inner, (key#1L = key#20L)
   :- Filter (isnotnull(s#3L) AND (s#3L > 1000))
   :  +- Aggregate [key#1L], [key#1L, sum(value#2L) AS s#3L]
   :     +- Project [(id#0L % 100000) AS key#1L, id#0L AS value#2L]
   :        +- Filter isnotnull((id#0L % 100000))
   :           +- Range (0, 5000000, step=1, splits=Some(8))
   +- Aggregate [key#20L], [key#20L, sum(value#21L) AS s#6L]
      +- Project [(id#19L % 100000) AS key#20L, id#19L AS value#21L]
         +- Filter isnotnull((id#19L % 100000))
            +- Range (0, 5000000, step=1, splits=Some(8))

== Physical Plan ==
AdaptiveSparkPlan isFinalPlan=false
+- Project [key#1L, s#3L, s#6L]
   +- SortMergeJoin [key#1L], [key#20L], Inner
      :- Sort [key#1L ASC NULLS FIRST], false, 0
      :  +- Filter (isnotnull(s#3L) AND (s#3L > 1000))
      :     +- HashAggregate(keys=[key#1L], functions=[sum(value#2L)], output=[key#1L, s#3L])
      :        +- Exchange hashpartitioning(key#1L, 8), ENSURE_REQUIREMENTS, [plan_id=53]
      :           +- HashAggregate(keys=[key#1L], functions=[partial_sum(value#2L)], output=[key#1L, sum#24L])
      :              +- Project [(id#0L % 100000) AS key#1L, id#0L AS value#2L]
      :                 +- Filter isnotnull((id#0L % 100000))
      :                    +- Range (0, 5000000, step=1, splits=8)
      +- Sort [key#20L ASC NULLS FIRST], false, 0
         +- HashAggregate(keys=[key#20L], functions=[sum(value#21L)], output=[key#20L, s#6L])
            +- Exchange hashpartitioning(key#20L, 8), ENSURE_REQUIREMENTS, [plan_id=56]
               +- HashAggregate(keys=[key#20L], functions=[partial_sum(value#21L)], output=[key#20L, sum#26L])
                  +- Project [(id#19L % 100000) AS key#20L, id#19L AS value#21L]
                     +- Filter isnotnull((id#19L % 100000))
                        +- Range (0, 5000000, step=1, splits=8)

== Parsed Logical Plan ==
'Filter '`>`('a.s, 1000)
+- Project [key#1L, s#11L, s#18L]
   +- Join Inner, (key#1L = key#16L)
      :- SubqueryAlias a
      :  +- Aggregate [key#1L], [key#1L, sum(value#2L) AS s#11L]
      :     +- Project [(id#0L % cast(100000 as bigint)) AS key#1L, id#0L AS value#2L]
      :        +- Range (0, 5000000, step=1, splits=Some(8))
      +- SubqueryAlias b
         +- Aggregate [key#16L], [key#16L, sum(value#17L) AS s#18L]
            +- Project [(id#15L % cast(100000 as bigint)) AS key#16L, id#15L AS value#17L]
               +- Range (0, 5000000, step=1, splits=Some(8))

== Analyzed Logical Plan ==
key: bigint, s: bigint, s: bigint
Filter (s#11L > cast(1000 as bigint))
+- Project [key#1L, s#11L, s#18L]
   +- Join Inner, (key#1L = key#16L)
      :- SubqueryAlias a
      :  +- Aggregate [key#1L], [key#1L, sum(value#2L) AS s#11L]
      :     +- Project [(id#0L % cast(100000 as bigint)) AS key#1L, id#0L AS value#2L]
      :        +- Range (0, 5000000, step=1, splits=Some(8))
      +- SubqueryAlias b
         +- Aggregate [key#16L], [key#16L, sum(value#17L) AS s#18L]
            +- Project [(id#15L % cast(100000 as bigint)) AS key#16L, id#15L AS value#17L]
               +- Range (0, 5000000, step=1, splits=Some(8))

== Optimized Logical Plan ==
Project [key#1L, s#11L, s#18L]
+- Join Inner, (key#1L = key#16L)
   :- Filter (isnotnull(s#11L) AND (s#11L > 1000))
   :  +- Aggregate [key#1L], [key#1L, sum(value#2L) AS s#11L]
   :     +- Project [(id#0L % 100000) AS key#1L, id#0L AS value#2L]
   :        +- Filter isnotnull((id#0L % 100000))
   :           +- Range (0, 5000000, step=1, splits=Some(8))
   +- Aggregate [key#16L], [key#16L, sum(value#17L) AS s#18L]
      +- Project [(id#15L % 100000) AS key#16L, id#15L AS value#17L]
         +- Filter isnotnull((id#15L % 100000))
            +- Range (0, 5000000, step=1, splits=Some(8))

== Physical Plan ==
AdaptiveSparkPlan isFinalPlan=false
+- Project [key#1L, s#11L, s#18L]
   +- SortMergeJoin [key#1L], [key#16L], Inner
      :- Sort [key#1L ASC NULLS FIRST], false, 0
      :  +- Filter (isnotnull(s#11L) AND (s#11L > 1000))
      :     +- HashAggregate(keys=[key#1L], functions=[sum(value#2L)], output=[key#1L, s#11L])
      :        +- Exchange hashpartitioning(key#1L, 8), ENSURE_REQUIREMENTS, [plan_id=114]
      :           +- HashAggregate(keys=[key#1L], functions=[partial_sum(value#2L)], output=[key#1L, sum#28L])
      :              +- Project [(id#0L % 100000) AS key#1L, id#0L AS value#2L]
      :                 +- Filter isnotnull((id#0L % 100000))
      :                    +- Range (0, 5000000, step=1, splits=8)
      +- Sort [key#16L ASC NULLS FIRST], false, 0
         +- HashAggregate(keys=[key#16L], functions=[sum(value#17L)], output=[key#16L, s#18L])
            +- Exchange hashpartitioning(key#16L, 8), ENSURE_REQUIREMENTS, [plan_id=117]
               +- HashAggregate(keys=[key#16L], functions=[partial_sum(value#17L)], output=[key#16L, sum#30L])
                  +- Project [(id#15L % 100000) AS key#16L, id#15L AS value#17L]
                     +- Filter isnotnull((id#15L % 100000))
                        +- Range (0, 5000000, step=1, splits=8)
```
