"""
Analyze the adam-vs-muon sweep from W&B.
Steps 2-7 of /analyze-sweep skill.
"""
import csv
import json
import os
import re
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import wandb

ENTITY = "hiremath-sujai1"
PROJECT = "adam-vs-muon"
GROUP = "adam-vs-muon"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PLOTS_DIR = os.path.join(BASE_DIR, "plots")
HIST_DIR = os.path.join(BASE_DIR, "histories")

os.makedirs(PLOTS_DIR, exist_ok=True)
os.makedirs(HIST_DIR, exist_ok=True)


# ── Step 2: Pull and store data ──────────────────────────────

def parse_run_name(name):
    """Parse trial-N-optimizer-lrX-sY format."""
    m = re.match(r"trial-(\d+)-(\w+)-lr([\d.]+)-s(\d+)", name)
    if m:
        return {"optimizer": m.group(2), "learning_rate": float(m.group(3)), "seed": int(m.group(4))}
    return {}


def pull_data():
    api = wandb.Api()
    runs = list(api.runs(f"{ENTITY}/{PROJECT}", filters={"group": GROUP}))
    print(f"Found {len(runs)} total runs")

    finished = [r for r in runs if r.state == "finished"]
    failed = [r for r in runs if r.state in ("failed", "crashed")]
    if failed:
        print(f"  Skipping {len(failed)} failed/crashed runs")
    print(f"  {len(finished)} finished runs to analyze")

    # Extract summaries
    records = []
    for r in finished:
        cfg = dict(r.config) if r.config else {}
        if not cfg:
            cfg = parse_run_name(r.name)

        summary = {k: v for k, v in r.summary.items() if not k.startswith("_") and isinstance(v, (int, float))}
        runtime = r.summary.get("_wandb", {}).get("runtime", None)

        record = {"name": r.name, **cfg, **summary, "runtime_s": runtime, "state": r.state}
        records.append(record)

    # Write runs.csv
    if records:
        all_keys = list(dict.fromkeys(k for rec in records for k in rec.keys()))
        csv_path = os.path.join(BASE_DIR, "runs.csv")
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=all_keys)
            writer.writeheader()
            writer.writerows(records)
        print(f"  Saved: {csv_path}")

    # Fetch per-epoch histories
    metric_keys = ["train_loss", "val_loss", "val_r2", "val_mse", "best_val_r2"]
    print("  Fetching per-epoch histories...")
    histories = {}
    for i, r in enumerate(finished):
        cfg = dict(r.config) if r.config else parse_run_name(r.name)
        hist = r.history(keys=metric_keys, pandas=False)
        key = (cfg.get("optimizer"), cfg.get("learning_rate"), cfg.get("seed"))
        histories[key] = hist
        # Save to JSON
        hist_path = os.path.join(HIST_DIR, f"{r.name}.json")
        with open(hist_path, "w") as f:
            json.dump({"config": cfg, "history": hist}, f)
        if (i + 1) % 10 == 0:
            print(f"    {i+1}/{len(finished)}")

    print(f"  Saved {len(histories)} history files to {HIST_DIR}/")
    return records, histories


# ── Step 3: Auto-detect config and metrics ───────────────────

def detect_structure(records):
    # Find config columns (values that differ)
    config_cols = []
    metric_cols = []
    skip = {"name", "state", "runtime_s"}

    for key in records[0].keys():
        if key in skip:
            continue
        vals = [r.get(key) for r in records if r.get(key) is not None]
        if not vals:
            continue
        unique = set(str(v) for v in vals)
        if len(unique) > 1 and all(isinstance(r.get(key), (int, float, str)) for r in records if r.get(key) is not None):
            # Check if it looks like a config param or a metric
            if isinstance(vals[0], str) or key in ("optimizer", "learning_rate", "seed", "batch_size", "epochs"):
                config_cols.append(key)
            elif isinstance(vals[0], (int, float)):
                # Seed detection: ≥8 unique ints in [0,100]
                if all(isinstance(v, int) for v in vals) and len(set(vals)) >= 8 and all(0 <= v <= 100 for v in vals):
                    config_cols.append(key)
                else:
                    metric_cols.append(key)

    # Detect primary metric
    primary = None
    score_keys = ["r2", "accuracy", "acc", "reward", "score"]
    for m in metric_cols:
        for sk in score_keys:
            if sk in m.lower():
                primary = m
                break
        if primary:
            break
    if not primary and metric_cols:
        # Use highest variance
        variances = {}
        for m in metric_cols:
            vals = [r[m] for r in records if r.get(m) is not None]
            variances[m] = np.var(vals) if vals else 0
        primary = max(variances, key=variances.get)

    # Detect loss metrics
    loss_cols = [m for m in metric_cols if "loss" in m.lower()]

    # Direction
    higher_better_keys = ["r2", "accuracy", "acc", "reward", "score"]
    higher_is_better = any(k in primary.lower() for k in higher_better_keys) if primary else True

    print(f"\n  Detected sweep over: {', '.join(config_cols)}")
    print(f"  Primary metric: {primary} ({'higher' if higher_is_better else 'lower'} is better)")
    print(f"  Loss metrics: {', '.join(loss_cols)}")

    return config_cols, metric_cols, primary, loss_cols, higher_is_better


# ── Step 4: Summary table ────────────────────────────────────

def print_summary(records, config_cols, primary, loss_cols, higher_is_better):
    # Group by non-seed config
    seed_col = "seed"
    group_cols = [c for c in config_cols if c != seed_col]

    grouped = defaultdict(list)
    for r in records:
        key = tuple(r.get(c) for c in group_cols)
        grouped[key].append(r)

    # Sort by primary metric
    def sort_key(item):
        vals = [r[primary] for r in item[1] if r.get(primary) is not None]
        return np.mean(vals) if vals else 0

    sorted_groups = sorted(grouped.items(), key=sort_key, reverse=higher_is_better)

    print(f"\n{'='*75}")
    print(f"  SWEEP: {GROUP}  |  {len(records)} runs  |  {ENTITY}/{PROJECT}")
    print(f"{'='*75}")
    header_cfg = "Config"
    print(f"  {header_cfg:<22} {primary+' (mean±std)':<24} {'Loss (final)':<14} {'Runtime':<10} {'N':>3}")
    print(f"  {'-'*72}")

    for key, runs in sorted_groups:
        label = ", ".join(f"{c}={v}" for c, v in zip(group_cols, key))
        pvals = [r[primary] for r in runs if r.get(primary) is not None]
        lvals = [r.get("val_loss") or r.get("train_loss", 0) for r in runs if r.get("val_loss") is not None or r.get("train_loss") is not None]
        rvals = [r["runtime_s"] for r in runs if r.get("runtime_s") is not None]

        p_str = f"{np.mean(pvals):.4f} ± {np.std(pvals):.4f}" if pvals else "N/A"
        l_str = f"{np.mean(lvals):.4f}" if lvals else "N/A"
        r_str = f"{np.mean(rvals):.0f}s" if rvals else "N/A"
        print(f"  {label:<22} {p_str:<24} {l_str:<14} {r_str:<10} {len(runs):>3}")

    print(f"  {'-'*72}")
    best_key, best_runs = sorted_groups[0]
    best_label = ", ".join(f"{c}={v}" for c, v in zip(group_cols, best_key))
    best_val = np.mean([r[primary] for r in best_runs if r.get(primary) is not None])
    print(f"  Best: {best_label}  ({primary} = {best_val:.4f})")
    print(f"{'='*75}")

    return group_cols, grouped, sorted_groups


# ── Step 5: Plots ────────────────────────────────────────────

def plot_boxplot(records, group_cols, grouped, primary, higher_is_better):
    sorted_keys = sorted(grouped.keys(), key=lambda k: np.mean([r[primary] for r in grouped[k] if r.get(primary)]), reverse=higher_is_better)

    labels = []
    data = []
    colors_list = []
    color_map = {}
    palette = ["#2196F3", "#FF5722", "#4CAF50", "#9C27B0", "#FF9800", "#00BCD4"]

    for key in sorted_keys:
        label = "\n".join(f"{c}={v}" for c, v in zip(group_cols, key))
        labels.append(label)
        vals = [r[primary] for r in grouped[key] if r.get(primary) is not None]
        data.append(vals)
        # Color by first group col
        first_val = str(key[0])
        if first_val not in color_map:
            color_map[first_val] = palette[len(color_map) % len(palette)]
        colors_list.append(color_map[first_val])

    fig, ax = plt.subplots(figsize=(max(10, len(labels) * 1.5), 6))
    bp = ax.boxplot(data, tick_labels=labels, patch_artist=True, widths=0.6)
    for patch, color in zip(bp["boxes"], colors_list):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)
    for i, d in enumerate(data):
        x = np.random.normal(i + 1, 0.04, size=len(d))
        ax.scatter(x, d, alpha=0.5, s=20, color="black", zorder=3)

    ax.set_ylabel(primary)
    ax.set_title(f"{primary} by Configuration")
    ax.grid(True, alpha=0.3, axis="y")
    plt.tight_layout()
    path = os.path.join(PLOTS_DIR, "01_metric_boxplot.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {path}")
    return path


def plot_loss_curves(histories, group_cols):
    grouped = defaultdict(list)
    for (opt, lr, seed), hist in histories.items():
        grouped[(opt, lr)].append(hist)

    color_map = {}
    palette = ["#2196F3", "#FF5722", "#4CAF50", "#9C27B0"]

    fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=True)
    for ax, metric, title in [(axes[0], "train_loss", "Train Loss"), (axes[1], "val_loss", "Val Loss")]:
        for (opt, lr), hists in sorted(grouped.items()):
            if opt not in color_map:
                color_map[opt] = palette[len(color_map) % len(palette)]
            arrays = []
            for h in hists:
                vals = [row[metric] for row in h if metric in row and row[metric] is not None]
                if vals:
                    arrays.append(vals)
            if not arrays:
                continue
            min_len = min(len(a) for a in arrays)
            arrays = [a[:min_len] for a in arrays]
            arr = np.array(arrays)
            mean = arr.mean(axis=0)
            std = arr.std(axis=0)
            epochs = np.arange(min_len)
            linestyle = "-" if list(sorted(grouped.keys()))[0][0] == opt else "--"
            alpha = {0.01: 1.0, 0.003: 0.7, 0.001: 0.45}.get(lr, 0.7)
            ax.plot(epochs, mean, label=f"{opt} lr={lr}", color=color_map[opt], linestyle=linestyle, alpha=alpha, linewidth=1.5)
            ax.fill_between(epochs, mean - std, mean + std, alpha=0.07, color=color_map[opt])
        ax.set_xlabel("Epoch")
        ax.set_ylabel(title)
        ax.set_title(title)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)

    fig.suptitle("Loss Curves (mean ± std across seeds)", fontsize=13)
    plt.tight_layout()
    path = os.path.join(PLOTS_DIR, "02_loss_curves.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {path}")
    return path


def plot_primary_curves(histories, primary):
    grouped = defaultdict(list)
    for (opt, lr, seed), hist in histories.items():
        grouped[(opt, lr)].append(hist)

    color_map = {}
    palette = ["#2196F3", "#FF5722", "#4CAF50", "#9C27B0"]

    fig, ax = plt.subplots(figsize=(10, 6))
    for (opt, lr), hists in sorted(grouped.items()):
        if opt not in color_map:
            color_map[opt] = palette[len(color_map) % len(palette)]
        arrays = []
        for h in hists:
            vals = [row[primary] for row in h if primary in row and row[primary] is not None]
            if vals:
                arrays.append(vals)
        if not arrays:
            continue
        min_len = min(len(a) for a in arrays)
        arrays = [a[:min_len] for a in arrays]
        arr = np.array(arrays)
        mean = arr.mean(axis=0)
        std = arr.std(axis=0)
        epochs = np.arange(min_len)
        linestyle = "-" if list(sorted(grouped.keys()))[0][0] == opt else "--"
        alpha = {0.01: 1.0, 0.003: 0.7, 0.001: 0.45}.get(lr, 0.7)
        ax.plot(epochs, mean, label=f"{opt} lr={lr}", color=color_map[opt], linestyle=linestyle, alpha=alpha, linewidth=1.5)
        ax.fill_between(epochs, mean - std, mean + std, alpha=0.07, color=color_map[opt])

    ax.set_xlabel("Epoch")
    ax.set_ylabel(primary)
    ax.set_title(f"{primary} Over Training (mean ± std across seeds)")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    path = os.path.join(PLOTS_DIR, "03_primary_curves.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {path}")
    return path


def plot_runtime(records, group_cols, grouped):
    labels, means, stds, colors_list = [], [], [], []
    color_map = {}
    palette = ["#2196F3", "#FF5722", "#4CAF50", "#9C27B0"]

    for key in sorted(grouped.keys()):
        rvals = [r["runtime_s"] for r in grouped[key] if r.get("runtime_s") is not None]
        if not rvals:
            continue
        label = "\n".join(f"{c}={v}" for c, v in zip(group_cols, key))
        labels.append(label)
        means.append(np.mean(rvals))
        stds.append(np.std(rvals))
        first_val = str(key[0])
        if first_val not in color_map:
            color_map[first_val] = palette[len(color_map) % len(palette)]
        colors_list.append(color_map[first_val])

    if not labels:
        print("  No runtime data, skipping runtime chart.")
        return None

    fig, ax = plt.subplots(figsize=(max(10, len(labels) * 1.5), 5))
    x = np.arange(len(labels))
    ax.bar(x, means, yerr=stds, color=colors_list, alpha=0.7, capsize=5)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Runtime (seconds)")
    ax.set_title("Wall-Clock Runtime per Trial (mean ± std)")
    ax.grid(True, alpha=0.3, axis="y")
    plt.tight_layout()
    path = os.path.join(PLOTS_DIR, "04_runtime.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {path}")
    return path


def plot_head_to_head(records, group_cols, grouped, primary, higher_is_better):
    # Check if first config dim has exactly 2 values (e.g., adam vs muon)
    first_col = group_cols[0]
    first_vals = sorted(set(r.get(first_col) for r in records))
    if len(first_vals) != 2:
        return None

    other_cols = group_cols[1:]
    other_vals = sorted(set(tuple(r.get(c) for c in other_cols) for r in records))

    a_label, b_label = first_vals
    a_means, b_means, a_stds, b_stds, x_labels = [], [], [], [], []

    for ov in other_vals:
        label = ", ".join(f"{c}={v}" for c, v in zip(other_cols, ov))
        x_labels.append(label)

        a_key = (a_label, *ov)
        b_key = (b_label, *ov)

        a_vals = [r[primary] for r in grouped.get(a_key, []) if r.get(primary) is not None]
        b_vals = [r[primary] for r in grouped.get(b_key, []) if r.get(primary) is not None]

        a_means.append(np.mean(a_vals) if a_vals else 0)
        b_means.append(np.mean(b_vals) if b_vals else 0)
        a_stds.append(np.std(a_vals) if a_vals else 0)
        b_stds.append(np.std(b_vals) if b_vals else 0)

    fig, ax = plt.subplots(figsize=(10, 6))
    x = np.arange(len(x_labels))
    width = 0.35
    ax.bar(x - width/2, a_means, width, yerr=a_stds, label=str(a_label), color="#2196F3", alpha=0.7, capsize=4)
    ax.bar(x + width/2, b_means, width, yerr=b_stds, label=str(b_label), color="#FF5722", alpha=0.7, capsize=4)
    ax.set_xticks(x)
    ax.set_xticklabels(x_labels)
    ax.set_ylabel(primary)
    ax.set_title(f"Head-to-Head: {a_label} vs {b_label}")
    ax.legend()
    ax.grid(True, alpha=0.3, axis="y")
    plt.tight_layout()
    path = os.path.join(PLOTS_DIR, "05_head_to_head.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {path}")
    return path


# ── Step 6: Key findings ─────────────────────────────────────

def generate_findings(records, group_cols, grouped, sorted_groups, primary, higher_is_better):
    findings = []

    # 1. Best config
    best_key, best_runs = sorted_groups[0]
    best_label = ", ".join(f"{c}={v}" for c, v in zip(group_cols, best_key))
    best_val = np.mean([r[primary] for r in best_runs if r.get(primary)])
    runner_key, runner_runs = sorted_groups[1]
    runner_label = ", ".join(f"{c}={v}" for c, v in zip(group_cols, runner_key))
    runner_val = np.mean([r[primary] for r in runner_runs if r.get(primary)])
    delta = abs(best_val - runner_val)
    findings.append(f"Best config: {best_label} ({primary}={best_val:.4f}), beating runner-up ({runner_label}) by {delta:.4f}")

    # 2. Effect of each hyperparameter
    seed_col = "seed"
    for i, col in enumerate(group_cols):
        vals_by_level = defaultdict(list)
        for key, runs in grouped.items():
            level = key[i]
            pvals = [r[primary] for r in runs if r.get(primary) is not None]
            vals_by_level[level].extend(pvals)
        level_means = {k: np.mean(v) for k, v in vals_by_level.items()}
        sorted_levels = sorted(level_means.items(), key=lambda x: x[1], reverse=higher_is_better)
        spread = max(level_means.values()) - min(level_means.values())
        best_level = sorted_levels[0]
        findings.append(
            f"Effect of {col}: spread = {spread:.4f}. "
            f"Best level: {col}={best_level[0]} ({primary}={best_level[1]:.4f}). "
            f"Ranking: {' > '.join(f'{k}({v:.4f})' for k, v in sorted_levels)}"
        )

    # 3. Stability
    stds = []
    for key, runs in grouped.items():
        pvals = [r[primary] for r in runs if r.get(primary) is not None]
        label = ", ".join(f"{c}={v}" for c, v in zip(group_cols, key))
        if pvals:
            stds.append((label, np.std(pvals), len(pvals)))
    stds.sort(key=lambda x: x[1])
    most_stable = stds[0]
    least_stable = stds[-1]
    findings.append(
        f"Most stable: {most_stable[0]} (std={most_stable[1]:.4f}). "
        f"Least stable: {least_stable[0]} (std={least_stable[1]:.4f})"
    )

    # 4. Runtime/cost tradeoff
    runtime_by_group = {}
    for key, runs in grouped.items():
        rvals = [r["runtime_s"] for r in runs if r.get("runtime_s")]
        if rvals:
            label = ", ".join(f"{c}={v}" for c, v in zip(group_cols, key))
            runtime_by_group[label] = np.mean(rvals)
    if runtime_by_group:
        fastest = min(runtime_by_group, key=runtime_by_group.get)
        slowest = max(runtime_by_group, key=runtime_by_group.get)
        ratio = runtime_by_group[slowest] / runtime_by_group[fastest]
        findings.append(
            f"Runtime: fastest={fastest} ({runtime_by_group[fastest]:.0f}s), "
            f"slowest={slowest} ({runtime_by_group[slowest]:.0f}s), "
            f"ratio={ratio:.1f}x"
        )

    # 5. Head-to-head
    first_col = group_cols[0]
    first_vals = sorted(set(k[0] for k in grouped.keys()))
    if len(first_vals) == 2:
        a, b = first_vals
        other_cols = group_cols[1:]
        other_vals = sorted(set(k[1:] for k in grouped.keys()))
        h2h = []
        for ov in other_vals:
            a_key = (a, *ov)
            b_key = (b, *ov)
            a_mean = np.mean([r[primary] for r in grouped.get(a_key, []) if r.get(primary)])
            b_mean = np.mean([r[primary] for r in grouped.get(b_key, []) if r.get(primary)])
            winner = a if (a_mean > b_mean) == higher_is_better else b
            ov_label = ", ".join(f"{c}={v}" for c, v in zip(other_cols, ov))
            h2h.append(f"  {ov_label}: {a}={a_mean:.4f} vs {b}={b_mean:.4f} -> {winner} wins")
        findings.append(f"Head-to-head ({a} vs {b}):\n" + "\n".join(h2h))

    return findings


# ── Step 7: Save report ──────────────────────────────────────

def save_report(findings, records, group_cols, grouped, sorted_groups, primary, higher_is_better, plot_paths):
    report_path = os.path.join(BASE_DIR, "report.md")
    with open(report_path, "w") as f:
        f.write(f"# Sweep Analysis: {GROUP}\n\n")
        f.write(f"- **Entity/Project**: {ENTITY}/{PROJECT}\n")
        f.write(f"- **Runs**: {len(records)}\n")
        f.write(f"- **Primary metric**: {primary}\n")
        f.write(f"- **W&B**: https://wandb.ai/{ENTITY}/{PROJECT}?group={GROUP}\n\n")

        f.write("## Summary Table\n\n")
        f.write(f"| Config | {primary} (mean±std) | Val Loss | Runtime | N |\n")
        f.write("|--------|" + "-" * 24 + "|----------|---------|---|\n")
        for key, runs in sorted_groups:
            label = ", ".join(f"{c}={v}" for c, v in zip(group_cols, key))
            pvals = [r[primary] for r in runs if r.get(primary) is not None]
            lvals = [r["val_loss"] for r in runs if r.get("val_loss") is not None]
            rvals = [r["runtime_s"] for r in runs if r.get("runtime_s") is not None]
            p_str = f"{np.mean(pvals):.4f} ± {np.std(pvals):.4f}" if pvals else "N/A"
            l_str = f"{np.mean(lvals):.4f}" if lvals else "N/A"
            r_str = f"{np.mean(rvals):.0f}s" if rvals else "N/A"
            f.write(f"| {label} | {p_str} | {l_str} | {r_str} | {len(runs)} |\n")

        f.write("\n## Key Findings\n\n")
        for i, finding in enumerate(findings, 1):
            f.write(f"{i}. {finding}\n\n")

        f.write("## Plots\n\n")
        for p in plot_paths:
            if p:
                f.write(f"![{os.path.basename(p)}](plots/{os.path.basename(p)})\n\n")

    print(f"  Saved report: {report_path}")
    return report_path


# ── Main ─────────────────────────────────────────────────────

def main():
    print(f"Analyzing sweep: {GROUP}")
    print(f"  W&B: {ENTITY}/{PROJECT}\n")

    # Step 2
    records, histories = pull_data()

    # Step 3
    config_cols, metric_cols, primary, loss_cols, higher_is_better = detect_structure(records)

    # Step 4
    group_cols, grouped, sorted_groups = print_summary(records, config_cols, primary, loss_cols, higher_is_better)

    # Step 5
    print("\nGenerating plots...")
    plot_paths = []
    plot_paths.append(plot_boxplot(records, group_cols, grouped, primary, higher_is_better))
    plot_paths.append(plot_loss_curves(histories, group_cols))
    plot_paths.append(plot_primary_curves(histories, primary))
    plot_paths.append(plot_runtime(records, group_cols, grouped))
    plot_paths.append(plot_head_to_head(records, group_cols, grouped, primary, higher_is_better))

    # Step 6
    findings = generate_findings(records, group_cols, grouped, sorted_groups, primary, higher_is_better)
    print(f"\n{'='*75}")
    print("  KEY FINDINGS")
    print(f"{'='*75}")
    for i, finding in enumerate(findings, 1):
        print(f"  {i}. {finding}")
    print(f"{'='*75}")

    # Step 7
    save_report(findings, records, group_cols, grouped, sorted_groups, primary, higher_is_better, plot_paths)

    print(f"\n  W&B dashboard: https://wandb.ai/{ENTITY}/{PROJECT}?group={GROUP}")
    print(f"  Local data:    {BASE_DIR}/")
    print(f"  Plots:         {PLOTS_DIR}/")
    print(f"  Report:        {os.path.join(BASE_DIR, 'report.md')}")

    # Return plot paths for display
    return [p for p in plot_paths if p]


if __name__ == "__main__":
    main()
