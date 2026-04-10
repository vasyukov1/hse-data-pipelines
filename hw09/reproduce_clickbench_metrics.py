from __future__ import annotations

import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"


def load_snapshot(filename: str) -> dict:
    path = DATA_DIR / filename
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def gmean(values: list[float]) -> float:
    return math.exp(sum(math.log(value) for value in values) / len(values))


def hot_timing(timings: list[float]) -> float:
    return min(timings[1], timings[2])


def build_summary(clickhouse: dict, starrocks: dict) -> dict:
    ch_results = clickhouse["result"]
    sr_results = starrocks["result"]

    if len(ch_results) != len(sr_results):
        raise ValueError("Query count mismatch between ClickHouse and StarRocks snapshots")

    cold_ratios: list[float] = []
    hot_ratios: list[float] = []
    starrocks_hot_faster = 0
    starrocks_cold_faster = 0

    for ch_query, sr_query in zip(ch_results, sr_results):
        ch_cold = ch_query[0]
        sr_cold = sr_query[0]
        ch_hot = hot_timing(ch_query)
        sr_hot = hot_timing(sr_query)

        cold_ratios.append(sr_cold / ch_cold)
        hot_ratios.append(sr_hot / ch_hot)

        if sr_hot < ch_hot:
            starrocks_hot_faster += 1
        if sr_cold < ch_cold:
            starrocks_cold_faster += 1

    cold_ratio = gmean(cold_ratios)
    hot_ratio = gmean(hot_ratios)
    load_ratio = starrocks["load_time"] / clickhouse["load_time"]
    size_ratio = starrocks["data_size"] / clickhouse["data_size"]

    combined_ratio = math.exp(
        0.1 * math.log(load_ratio)
        + 0.1 * math.log(size_ratio)
        + 0.2 * math.log(cold_ratio)
        + 0.6 * math.log(hot_ratio)
    )

    return {
        "clickhouse_snapshot": {
            "date": clickhouse["date"],
            "machine": clickhouse["machine"],
            "load_time_s": clickhouse["load_time"],
            "data_size_bytes": clickhouse["data_size"],
            "queries": len(ch_results),
        },
        "starrocks_snapshot": {
            "date": starrocks["date"],
            "machine": starrocks["machine"],
            "load_time_s": starrocks["load_time"],
            "data_size_bytes": starrocks["data_size"],
            "queries": len(sr_results),
        },
        "pairwise_ratios_starrocks_vs_clickhouse": {
            "load_ratio": round(load_ratio, 6),
            "size_ratio": round(size_ratio, 6),
            "cold_gmean_ratio": round(cold_ratio, 6),
            "hot_gmean_ratio": round(hot_ratio, 6),
            "combined_ratio": round(combined_ratio, 6),
        },
        "query_level_wins_for_starrocks": {
            "hot_queries_faster": starrocks_hot_faster,
            "cold_queries_faster": starrocks_cold_faster,
        },
        "method": {
            "cold_run": "first execution of each query",
            "hot_run": "minimum of second and third execution of each query",
            "combined_formula": {
                "load_time_share": 0.1,
                "data_size_share": 0.1,
                "cold_share": 0.2,
                "hot_share": 0.6,
            },
        },
    }


def main() -> None:
    clickhouse = load_snapshot("clickbench_clickhouse_c6a.4xlarge.json")
    starrocks = load_snapshot("clickbench_starrocks_c6a.4xlarge.json")
    summary = build_summary(clickhouse, starrocks)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
