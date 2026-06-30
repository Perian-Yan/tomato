#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Plot focus-session statistics from data/focus_sessions.csv.

Examples:
    python3 scripts/plot_focus_stats.py day 2026-06-30
    python3 scripts/plot_focus_stats.py range 2026-06-01 2026-06-30
"""

import argparse
import csv
import statistics
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = BASE_DIR / "data" / "focus_sessions.csv"
DEFAULT_OUTPUT_DIR = BASE_DIR / "stats"


@dataclass(frozen=True)
class FocusSession:
    ended_at: datetime
    duration_minutes: float


def parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"日期格式应为 YYYY-MM-DD：{value}") from exc


def load_sessions(path: Path) -> list[FocusSession]:
    if not path.exists():
        raise FileNotFoundError(f"找不到专注记录文件：{path}")

    sessions: list[FocusSession] = []
    with path.open("r", newline="", encoding="utf-8") as log_file:
        reader = csv.DictReader(log_file)
        for row in reader:
            try:
                ended_at = datetime.fromisoformat(row["ended_at"])
                duration_seconds = float(row["duration_seconds"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"记录文件格式不正确，问题行：{row}") from exc

            if duration_seconds > 0:
                sessions.append(FocusSession(ended_at, duration_seconds / 60))

    return sessions


def summarize(values: list[float]) -> dict[str, float | int]:
    if not values:
        return {
            "sessions": 0,
            "total": 0.0,
            "mean": 0.0,
            "variance": 0.0,
            "q1": 0.0,
            "q3": 0.0,
        }

    sorted_values = sorted(values)
    q1 = percentile(sorted_values, 25)
    q3 = percentile(sorted_values, 75)

    return {
        "sessions": len(values),
        "total": sum(values),
        "mean": statistics.mean(values),
        "variance": statistics.pvariance(values),
        "q1": q1,
        "q3": q3,
    }


def percentile(sorted_values: list[float], percent: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]

    position = (len(sorted_values) - 1) * percent / 100
    lower_index = int(position)
    upper_index = min(lower_index + 1, len(sorted_values) - 1)
    fraction = position - lower_index
    return sorted_values[lower_index] * (1 - fraction) + sorted_values[upper_index] * fraction


def period_name(ended_time: time) -> str:
    if ended_time < time(12, 0):
        return "上午"
    if ended_time < time(18, 0):
        return "下午"
    return "晚上"


def day_stats(sessions: list[FocusSession], selected_date: date) -> list[tuple[str, dict[str, float | int]]]:
    grouped: dict[str, list[float]] = {"上午": [], "下午": [], "晚上": []}
    for session in sessions:
        if session.ended_at.date() == selected_date:
            grouped[period_name(session.ended_at.time())].append(session.duration_minutes)

    return [(name, summarize(grouped[name])) for name in ["上午", "下午", "晚上"]]


def daterange(start: date, end: date) -> list[date]:
    days = (end - start).days
    return [date.fromordinal(start.toordinal() + offset) for offset in range(days + 1)]


def range_stats(
    sessions: list[FocusSession],
    start_date: date,
    end_date: date,
) -> list[tuple[str, dict[str, float | int]]]:
    grouped: dict[date, list[float]] = defaultdict(list)
    for session in sessions:
        ended_date = session.ended_at.date()
        if start_date <= ended_date <= end_date:
            grouped[ended_date].append(session.duration_minutes)

    return [(day.isoformat(), summarize(grouped[day])) for day in daterange(start_date, end_date)]


def print_table(title: str, rows: list[tuple[str, dict[str, float | int]]]) -> None:
    print(title)
    print("分组, 次数, 总专注时长(min), 平均值(min/次), Q1, Q3, 方差")
    for label, stats in rows:
        print(
            f"{label}, {stats['sessions']}, {stats['total']:.2f}, "
            f"{stats['mean']:.2f}, {stats['q1']:.2f}, {stats['q3']:.2f}, {stats['variance']:.2f}"
        )


def plot_rows(title: str, rows: list[tuple[str, dict[str, float | int]]], output_path: Path) -> None:
    try:
        import matplotlib.pyplot as plt
        from matplotlib import font_manager
    except ImportError as exc:
        raise RuntimeError("缺少 matplotlib，请先安装：sudo apt install python3-matplotlib") from exc

    cjk_font_names = [
        "Noto Sans CJK SC",
        "Noto Sans CJK",
        "WenQuanYi Micro Hei",
        "SimHei",
        "Microsoft YaHei",
    ]
    available_fonts = {font.name for font in font_manager.fontManager.ttflist}
    has_cjk_font = any(name in available_fonts for name in cjk_font_names)

    label_translation = {"上午": "Morning", "下午": "Afternoon", "晚上": "Evening"}
    labels = [
        label if has_cjk_font else label_translation.get(label, label)
        for label, _ in rows
    ]
    totals = [stats["total"] for _, stats in rows]
    means = [stats["mean"] for _, stats in rows]
    q1_values = [stats["q1"] for _, stats in rows]
    q3_values = [stats["q3"] for _, stats in rows]
    lower_errors = [max(0.0, mean - q1) for mean, q1 in zip(means, q1_values)]
    upper_errors = [max(0.0, q3 - mean) for mean, q3 in zip(means, q3_values)]

    output_path.parent.mkdir(parents=True, exist_ok=True)

    if has_cjk_font:
        plt.rcParams["font.sans-serif"] = cjk_font_names + ["DejaVu Sans"]
    else:
        plt.rcParams["font.sans-serif"] = ["DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False

    fig, total_axis = plt.subplots(figsize=(max(8, len(labels) * 0.62), 5.8), constrained_layout=True)
    mean_axis = total_axis.twinx()
    x_positions = list(range(len(labels)))

    if has_cjk_font:
        plot_title = title
        total_label = "总专注时长"
        mean_label = "平均专注时长（Q1–Q3）"
        total_ylabel = "总专注时长（分钟）"
        mean_ylabel = "平均值（分钟/次）"
        empty_note = "无记录"
    else:
        plot_title = "Focus statistics"
        total_label = "Total focus time"
        mean_label = "Mean focus time (Q1-Q3)"
        total_ylabel = "Total focus time (minutes)"
        mean_ylabel = "Mean (minutes/session)"
        empty_note = "No records"

    bars = total_axis.bar(
        x_positions,
        totals,
        width=0.62,
        color="#E85D75",
        alpha=0.82,
        label=total_label,
        zorder=2,
    )
    error_lines = mean_axis.errorbar(
        x_positions,
        means,
        yerr=[lower_errors, upper_errors],
        color="#2563EB",
        ecolor="#1E40AF",
        elinewidth=1.8,
        capsize=5,
        marker="o",
        markersize=6,
        linewidth=2.4,
        label=mean_label,
        zorder=4,
    )

    total_axis.set_title(plot_title, fontsize=15, pad=14)
    total_axis.set_ylabel(total_ylabel, color="#A8324A")
    mean_axis.set_ylabel(mean_ylabel, color="#1D4ED8")
    total_axis.tick_params(axis="y", labelcolor="#A8324A")
    mean_axis.tick_params(axis="y", labelcolor="#1D4ED8")

    total_axis.set_xticks(x_positions)
    total_axis.set_xticklabels(labels)
    if len(labels) > 8:
        total_axis.tick_params(axis="x", rotation=45)

    total_axis.grid(axis="y", alpha=0.22, linestyle="--", zorder=1)
    total_axis.spines["top"].set_visible(False)
    mean_axis.spines["top"].set_visible(False)

    max_total = max(totals, default=0)
    max_mean_error = max((mean + upper for mean, upper in zip(means, upper_errors)), default=0)
    total_axis.set_ylim(0, max_total * 1.22 if max_total > 0 else 1)
    mean_axis.set_ylim(0, max_mean_error * 1.3 if max_mean_error > 0 else 1)

    for bar, total in zip(bars, totals):
        if total <= 0:
            continue
        total_axis.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{total:.0f}",
            ha="center",
            va="bottom",
            fontsize=9,
            color="#6B1025",
        )

    if not any(totals):
        total_axis.text(
            0.5,
            0.5,
            empty_note,
            transform=total_axis.transAxes,
            ha="center",
            va="center",
            fontsize=14,
            color="#777777",
        )

    total_axis.legend([bars, error_lines], [total_label, mean_label], loc="upper left")
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="读取番茄钟专注记录并画统计图")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help=f"记录文件，默认：{DEFAULT_INPUT}")
    parser.add_argument("--output", type=Path, help="输出图片路径，默认保存到 stats/ 目录")

    subparsers = parser.add_subparsers(dest="command", required=True)

    day_parser = subparsers.add_parser("day", help="统计指定某一天的上午、下午、晚上")
    day_parser.add_argument("date", type=parse_date, help="日期，格式 YYYY-MM-DD")
    day_parser.add_argument("--input", type=Path, default=argparse.SUPPRESS, help="记录文件")
    day_parser.add_argument("--output", type=Path, default=argparse.SUPPRESS, help="输出图片路径")

    range_parser = subparsers.add_parser("range", help="统计给定时间段内每一天")
    range_parser.add_argument("start_date", type=parse_date, help="开始日期，格式 YYYY-MM-DD")
    range_parser.add_argument("end_date", type=parse_date, help="结束日期，格式 YYYY-MM-DD")
    range_parser.add_argument("--input", type=Path, default=argparse.SUPPRESS, help="记录文件")
    range_parser.add_argument("--output", type=Path, default=argparse.SUPPRESS, help="输出图片路径")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        sessions = load_sessions(args.input)

        if args.command == "day":
            rows = day_stats(sessions, args.date)
            title = f"{args.date.isoformat()} 专注统计"
            output = args.output or DEFAULT_OUTPUT_DIR / f"focus-day-{args.date.isoformat()}.png"
        elif args.command == "range":
            if args.end_date < args.start_date:
                parser.error("结束日期不能早于开始日期")
            rows = range_stats(sessions, args.start_date, args.end_date)
            title = f"{args.start_date.isoformat()} 至 {args.end_date.isoformat()} 专注统计"
            output = args.output or DEFAULT_OUTPUT_DIR / (
                f"focus-range-{args.start_date.isoformat()}_{args.end_date.isoformat()}.png"
            )
        else:
            parser.error("未知命令")

        print_table(title, rows)
        plot_rows(title, rows, output)
        print(f"\n图已保存：{output}")
        return 0
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
