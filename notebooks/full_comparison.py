import marimo

__generated_with = "0.23.9"
app = marimo.App(width="full")


@app.cell
def _():
    import marimo as mo
    import altair as alt
    import polars as pl
    from pathlib import Path
    import statsmodels.stats.weightstats as weightstats
    import math

    return Path, alt, math, mo, pl, weightstats


@app.cell
def _(Path):
    DATA_DIR = "data"
    data_base_path = Path(DATA_DIR)
    INFO = False
    return INFO, data_base_path


@app.cell
def _(pl):
    def stats(df: pl.DataFrame) -> pl.DataFrame:
        columns = (
            df.select("metric_name").unique().sort("metric_name")["metric_name"].to_list()
        )

        pivot = (
            df.pivot(on="metric_name", values=["metric_value"], index="iteration")
            .drop("iteration")
            .select(columns)
        )

        def _quantiles(s: pl.Series) -> tuple:
            return (
                s.quantile(0.25, interpolation="nearest"),
                s.median(),
                s.quantile(0.75, interpolation="nearest"),
            )

        results = []
        for col in columns:
            series = pivot.select(col).to_series()
            mean = series.mean()
            std = series.std()
            q1, med, q3 = _quantiles(series)
            results.append({
                "metric":    col,
                "mean":      round(mean, 2),
                "std":       round(std, 2),
                "CV (%)":    round(std / mean * 100, 3),
                "quantiles": f"[{round(q1, 3)}, {round(med, 3)}, {round(q3, 3)}]",
            })

        return pl.DataFrame(results)

    return (stats,)


@app.cell
def _(INFO, alt, pl):
    def bland_altman(df, metric, tool: str):
        df_clean = (
            df.filter(pl.col("metric_name") == metric)
            .pivot(values="metric_value", index="iteration", on="source")
        )

        df_ba = df_clean.with_columns(
            [
                ((pl.col(tool) + pl.col("joule-profiler")) / 2).alias("mean_measure"),
                (pl.col(tool) - pl.col("joule-profiler")).alias("diff_measure"),
            ]
        )
        bias = df_ba.select(pl.col("diff_measure").mean()).item()
        sd = df_ba.select(pl.col("diff_measure").std()).item()
        loa_upper = bias + 1.96 * sd
        loa_lower = bias - 1.96 * sd

        rules_df = pl.DataFrame(
            {"y": [bias, loa_upper, loa_lower], "label": ["Bias", "Upper LoA", "Lower LoA"]}
        )

        total = df_ba.height
        within = df_ba.filter(
            (pl.col("diff_measure") >= loa_lower) & (pl.col("diff_measure") <= loa_upper)
        ).height
        pct = within / total * 100

        if INFO:
            print(f"{within}/{total} = {pct:.1f}% of measures in LoA")

        points = (
            alt.Chart(df_ba)
            .mark_point(size=60)
            .encode(
                x=alt.X("mean_measure:Q", title="Mean of the two tools (J)", scale=alt.Scale(zero=False)),
                y=alt.Y("diff_measure:Q", title="Difference between tools (J)"),
                tooltip=[tool, "joule-profiler", "mean_measure", "diff_measure"],
            )
        )
        rules = alt.Chart(rules_df).mark_rule(strokeDash=[6, 4]).encode(y="y:Q")
        labels = (
            alt.Chart(rules_df)
            .mark_text(align="left", dx=5, dy=-5)
            .encode(x=alt.value(5), y="y:Q", text="label:N")
        )
        return (points + rules + labels).properties(
            title=metric, width=600, height=400
        ).interactive()

    return (bland_altman,)


@app.cell
def _(math, pl, weightstats):
    def tost(
        df: pl.DataFrame,
        tool: str,
        equivalence_margin: float = 0.005,
        alpha: float = 0.05,
        paired: bool = True,
    ) -> pl.DataFrame:
        tool_a_name, tool_b_name = tool, "joule-profiler"

        energy_columns = (
            df.filter(pl.col("metric_unit") == "J")
            .select("metric_name").unique().sort("metric_name")["metric_name"]
        )
        columns = [*energy_columns]

        def _pivot(tool: str) -> pl.DataFrame:
            return (
                df.filter(pl.col("source").eq(tool))
                .pivot(on="metric_name", values=["metric_value"], index="iteration")
                .drop("iteration")
                .select(columns)
            )

        pivot_a = _pivot(tool_a_name)
        pivot_b = _pivot(tool_b_name)

        def _quantiles(s) -> tuple:
            s_pl = pl.Series(s)
            return (
                s_pl.quantile(0.25, interpolation="nearest"),
                s_pl.median(),
                s_pl.quantile(0.75, interpolation="nearest"),
            )

        results = []
        for col in columns:
            col_a = pivot_a.select(col)
            col_b = pivot_b.select(col)

            series_a = col_a.to_series()
            series_b = col_b.to_series()
            mean_a, mean_b = series_a.mean(), series_b.mean()
            std_a, std_b = series_a.std(), series_b.std()
            q1_a, med_a, q3_a = _quantiles(series_a)
            q1_b, med_b, q3_b = _quantiles(series_b)
            margin = mean_a * equivalence_margin

            diff = (col_a - col_b)[col]
            diff_mean = diff.mean()
            diff_std = diff.std()
            diff_percent = abs(diff_mean / mean_a * 100)

            if paired:
                corr_df = pl.concat(
                    [col_a.rename({col: tool_a_name}), col_b.rename({col: tool_b_name})],
                    how="horizontal",
                )
                r = corr_df.select(pl.corr(tool_a_name, tool_b_name)).item()
                r2 = r ** 2
                dz = diff_mean / diff_std
                dz_corr = dz * math.sqrt(2 * (1 - r))
                p, _, _ = weightstats.ttost_paired(series_a, series_b, low=-margin, upp=margin)
                extra = {
                    "dz_corr": round(dz_corr, 3),
                    "r²": round(r2, 3),
                }
            else:
                p, _, _ = weightstats.ttost_ind(series_a, series_b, low=-margin, upp=margin)
                pooled_std = math.sqrt((std_a ** 2 + std_b ** 2) / 2)
                d = (mean_a - mean_b) / pooled_std
                extra = {
                    "d": round(d, 3),
                }

            results.append({
                "domain": col,
                "equivalence": bool(p < alpha),
                "p_value": f"{round(p, 6)}",
                **extra,
                "equivalence margin": round(margin, 3),
                "mean diff": round(diff_mean, 3),
                "diff std": round(diff_std, 3),
                "diff_percent": round(diff_percent, 3),
                f"{tool_b_name} mean": round(mean_b, 2),
                f"{tool_a_name} mean": round(mean_a, 2),
                f"{tool_b_name} std": round(std_b, 2),
                f"{tool_a_name} std": round(std_a, 2),
                f"{tool_b_name} quantiles": f"[{round(q1_b, 3)}, {round(med_b, 3)}, {round(q3_b, 3)}]",
                f"{tool_a_name} quantiles": f"[{round(q1_a, 3)}, {round(med_a, 3)}, {round(q3_a, 3)}]",
                f"{tool_b_name} CV (%)": round(std_b / mean_b * 100, 3),
                f"{tool_a_name} CV (%)": round(std_a / mean_a * 100, 3),
            })

        return pl.DataFrame(results)

    return (tost,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Parallel
    """)
    return


@app.cell
def _(data_base_path, mo):
    _available_runs = sorted([d.name for d in data_base_path.glob("*") if d.is_file() and d.name.startswith("parallel-")])

    parallel_run_selector = mo.ui.dropdown(
            options=_available_runs,
            value=_available_runs[-1] if _available_runs else None,
            label="Select a parallel run"
        ) if _available_runs else None

    parallel_run_selector
    return (parallel_run_selector,)


@app.cell
def _(data_base_path, mo):
    _available_runs = sorted([d.name for d in data_base_path.glob("*") if d.is_file() and d.name.startswith("parallel_nvml")])

    parallel_nvml_run_selector = mo.ui.dropdown(
            options=_available_runs,
            value=_available_runs[-1] if _available_runs else None,
            label="Select a parallel NVML run"
        ) if _available_runs else None

    parallel_nvml_run_selector
    return (parallel_nvml_run_selector,)


@app.cell
def _(data_base_path, parallel_nvml_run_selector, parallel_run_selector, pl):
    parallel_df = []

    if parallel_run_selector is not None:
        _parallel_df = pl.read_csv(data_base_path / parallel_run_selector.value)
        parallel_df.append(_parallel_df)

    if parallel_nvml_run_selector is not None:
        _parallel_nvml_df = pl.read_csv(data_base_path / parallel_nvml_run_selector.value)
        parallel_df.append(_parallel_nvml_df)

    parallel_df = pl.concat(parallel_df).sort(["iteration", "metric_name", "source"])
    parallel_df
    return (parallel_df,)


@app.cell
def _(mo, parallel_df, pl, stats):
    _stats = stats(parallel_df.filter(pl.col("source") == "joule-profiler"))
    mo.vstack([mo.md("### Joule Profiler"), _stats])
    return


@app.cell
def _(mo, parallel_df, pl, stats):
    _stats = stats(parallel_df.filter(pl.col("source") == "perf"))
    mo.vstack([mo.md("### perf"), _stats])
    return


@app.cell
def _(mo, parallel_df, pl, stats):
    _stats = stats(parallel_df.filter(pl.col("source") == "alumet"))
    mo.vstack([mo.md("### Alumet"), _stats])
    return


@app.cell
def _(alt, parallel_df, pl):
    _charts = []
    _metrics = parallel_df["metric_name"].unique().sort().to_list()
    _metrics_no_gpu = [_m for _m in _metrics if not _m.startswith("GPU-")]
    _metrics_gpu = [_m for _m in _metrics if _m.startswith("GPU-")]
    _metrics = [*_metrics_no_gpu, *_metrics_gpu]

    _color_map = {
        "joule-profiler": "#d85a30",
        "alumet": "#378add",
        "perf": "#1d9e75",
    }

    _order = list(_color_map.keys())

    for _metric in _metrics:
        _df = parallel_df.filter(pl.col("metric_name") == _metric)
        _sources = _df["source"].unique().to_list()
        _domain = [_s for _s in _order if _s in _sources]

        _chart = alt.Chart(_df).mark_boxplot(extent="min-max", size=30).encode(
            x=alt.X(
                "source:N",
                title=None,
                axis=alt.Axis(labelAngle=-45),
                scale=alt.Scale(domain=_domain),
            ),
            y=alt.Y("metric_value:Q", title="Energy (J)", scale=alt.Scale(zero=False)),
            color=alt.Color(
                "source:N",
                legend=None,
                scale=alt.Scale(
                    domain=list(_color_map.keys()),
                    range=list(_color_map.values()),
                ),
            ),
        ).properties(width=160, height=280)

        _charts.append(_chart)

    alt.hconcat(*_charts)
    return


@app.cell
def _(mo):
    mo.md("""
    ## perf - Joule Profiler
    """)
    return


@app.cell
def _(parallel_df, pl, tost):
    _metrics = parallel_df.filter(pl.col("source") == "perf").get_column("metric_name").unique().to_list()
    tost(
        parallel_df.filter(pl.col("metric_name").is_in(_metrics)),
        tool="perf",
        equivalence_margin=0.001,
        alpha=0.05,
        paired=True
    )
    return


@app.cell
def _(bland_altman, mo, parallel_df, pl):
    _metrics = parallel_df.filter(pl.col("source") == "perf").get_column("metric_name").unique().to_list()
    mo.vstack([
        mo.hstack([
            bland_altman(parallel_df, m, tool="perf")
            for m in _metrics
        ])
    ]).style({
        "max-width": "100%",
        "overflow-x": "auto"
    })
    return


@app.cell
def _(mo):
    mo.md("""
    ## Alumet - Joule Profiler
    """)
    return


@app.cell
def _(parallel_df, pl, tost):
    _metrics = parallel_df.filter(pl.col("source") == "alumet").get_column("metric_name").unique().to_list()
    tost(
        parallel_df.filter(pl.col("metric_name").is_in(_metrics)),
        tool="alumet",
        equivalence_margin=0.001,
        alpha=0.05,
        paired=True
    )
    return


@app.cell
def _(bland_altman, mo, parallel_df, pl):
    _metrics = parallel_df.filter(pl.col("source") == "alumet").get_column("metric_name").unique().to_list()
    mo.vstack([
        mo.hstack([
            bland_altman(parallel_df, m, tool="alumet")
            for m in _metrics
        ])
    ]).style({
        "max-width": "100%",
        "overflow-x": "auto"
    })
    return


@app.cell
def _(alt, parallel_df, pl):
    _color_map = {
        "alumet": "#378add",
        "joule-profiler": "#d85a30",
        "perf": "#1d9e75",
    }

    _charts = []
    for _metric in parallel_df["metric_name"].unique().to_list():
        _subset = parallel_df.filter(pl.col("metric_name") == _metric)
        _sources = _subset["source"].unique().to_list()
        # _sorted_colors = [_color_map[k] for k in _sources]
        _sorted_colors = _color_map.values()

        _chart = (
            alt.Chart(_subset)
            .transform_window(
                ecdf="cume_dist()",
                sort=[{"field": "metric_value"}],
                groupby=["source"],
            )
            .mark_line(interpolate="step-after")
            .encode(
                x=alt.X("metric_value:Q", title="Énergie (J)"),
                y=alt.Y("ecdf:Q", title="ECDF"),
                color=alt.Color("source:N", scale=alt.Scale(
                    range=_sorted_colors
                )),
            )
            .properties(title=_metric, width=600, height=400).interactive(_metric)
        )
        _charts.append(_chart)

    alt.hconcat(*_charts)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Sequential
    """)
    return


@app.cell
def _(data_base_path, mo):
    _available_runs = sorted([d.name for d in data_base_path.glob("*") if d.is_file() and d.name.startswith("sequential-")])

    sequential_run_selector = mo.ui.dropdown(
            options=_available_runs,
            value=_available_runs[-1] if _available_runs else None,
            label="Select a sequential run"
        ) if _available_runs else None

    sequential_run_selector
    return (sequential_run_selector,)


@app.cell
def _(data_base_path, mo):
    _available_runs = sorted([d.name for d in data_base_path.glob("*") if d.is_file() and d.name.startswith("sequential_nvml-")])

    sequential_nvml_run_selector = mo.ui.dropdown(
            options=_available_runs,
            value=_available_runs[-1] if _available_runs else None,
            label="Select a sequential NVML run"
        ) if _available_runs else None

    sequential_nvml_run_selector
    return (sequential_nvml_run_selector,)


@app.cell
def _(
    data_base_path,
    pl,
    sequential_nvml_run_selector,
    sequential_run_selector,
):
    sequential_df = []

    if sequential_run_selector is not None:
        _sequential_df = pl.read_csv(data_base_path / sequential_run_selector.value)
        sequential_df.append(_sequential_df)

    if sequential_nvml_run_selector is not None:
        _sequential_nvml_df = pl.read_csv(data_base_path / sequential_nvml_run_selector.value)
        sequential_df.append(_sequential_nvml_df)

    sequential_df = pl.concat(sequential_df).sort(["iteration", "metric_name", "source"])
    sequential_df
    return (sequential_df,)


@app.cell
def _(mo, pl, sequential_df, stats):
    _stats = stats(sequential_df.filter(pl.col("source") == "joule-profiler"))
    mo.vstack([mo.md("### Joule Profiler"), _stats])
    return


@app.cell
def _(mo, pl, sequential_df, stats):
    _stats = stats(sequential_df.filter(pl.col("source") == "alumet"))
    mo.vstack([mo.md("### Alumet"), _stats])
    return


@app.cell
def _(mo, pl, sequential_df, stats):
    _stats = stats(sequential_df.filter(pl.col("source") == "perf"))
    mo.vstack([mo.md("### perf"), _stats])
    return


@app.cell
def _(alt, pl, sequential_df):
    _charts = []
    _metrics = sequential_df["metric_name"].unique().sort().to_list()
    _metrics_no_gpu = [_m for _m in _metrics if not _m.startswith("GPU-")]
    _metrics_gpu = [_m for _m in _metrics if _m.startswith("GPU-")]
    _metrics = [*_metrics_no_gpu, *_metrics_gpu]

    _color_map = {
        "joule-profiler": "#d85a30",
        "alumet": "#378add",
        "perf": "#1d9e75",
    }

    _order = list(_color_map.keys())

    for _metric in _metrics:
        _df = sequential_df.filter(pl.col("metric_name") == _metric)
        _sources = _df["source"].unique().to_list()
        _domain = [_s for _s in _order if _s in _sources]

        _chart = alt.Chart(_df).mark_boxplot(extent="min-max", size=30).encode(
            x=alt.X(
                "source:N",
                title=None,
                axis=alt.Axis(labelAngle=-45),
                scale=alt.Scale(domain=_domain),
            ),
            y=alt.Y("metric_value:Q", title="Energy (J)", scale=alt.Scale(zero=False)),
            color=alt.Color(
                "source:N",
                legend=None,
                scale=alt.Scale(
                    domain=list(_color_map.keys()),
                    range=list(_color_map.values()),
                ),
            ),
        ).properties(width=300, height=400)

        _charts.append(_chart)

    alt.hconcat(*_charts)
    return


@app.cell
def _(mo):
    mo.md("""
    ## perf - Joule Profiler
    """)
    return


@app.cell
def _(pl, sequential_df, tost):
    _metrics = sequential_df.filter(pl.col("source") == "perf").get_column("metric_name").unique().sort().to_list()
    tost(
        sequential_df.filter(pl.col("metric_name").is_in(_metrics)),
        tool="perf",
        equivalence_margin=0.005,
        alpha=0.05,
        paired=False
    )
    return


@app.cell
def _(bland_altman, mo, pl, sequential_df):
    _metrics = sequential_df.filter(pl.col("source") == "perf").get_column("metric_name").unique().sort().to_list()
    mo.vstack([
        mo.hstack([
            bland_altman(sequential_df, m, tool="perf")
            for m in _metrics
        ])
    ]).style({
        "max-width": "100%",
        "overflow-x": "auto"
    })
    return


@app.cell
def _(mo):
    mo.md("""
    ## Alumet - Joule Profiler
    """)
    return


@app.cell
def _(pl, sequential_df, tost):
    _metrics = sequential_df.filter(pl.col("source") == "alumet").get_column("metric_name").unique().sort().to_list()
    tost(
        sequential_df.filter(pl.col("metric_name").is_in(_metrics)),
        tool="alumet",
        equivalence_margin=0.005,
        alpha=0.05,
        paired=False
    )
    return


@app.cell
def _(bland_altman, mo, pl, sequential_df):
    _metrics = sequential_df.filter(pl.col("source") == "alumet").get_column("metric_name").unique().sort().to_list()
    mo.vstack([
        mo.hstack([
            bland_altman(sequential_df, m, tool="alumet")
            for m in _metrics
        ])
    ]).style({
        "max-width": "100%",
        "overflow-x": "auto"
    })
    return


@app.cell
def _(alt, mo, parallel_df, pl):
    _color_map = {
        "joule-profiler": "#d85a30",
        "alumet": "#378add",
        "perf": "#1d9e75",
    }

    _charts = []
    for _metric in parallel_df["metric_name"].unique().to_list():
        _subset = parallel_df.filter(pl.col("metric_name") == _metric)
        _sources = sorted(_subset["source"].unique().to_list())
        _sorted_colors = [_color_map[k] for k in _sources]

        _chart = (
            alt.Chart(_subset)
            .transform_window(
                ecdf="cume_dist()",
                sort=[{"field": "metric_value"}],
                groupby=["source"],
            )
            .mark_line(interpolate="step-after")
            .encode(
                x=alt.X("metric_value:Q", title="Energy (J)"),
                y=alt.Y("ecdf:Q", title="ECDF"),
                color=alt.Color("source:N", scale=alt.Scale(
                    range=_sorted_colors
                )),
            )
            .properties(title=_metric, width=600, height=400).interactive(_metric)
        )
        _charts.append(_chart)

    mo.hstack(_charts)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Phases
    """)
    return


@app.cell
def _(data_base_path, mo):
    _available_runs = sorted([d.name for d in data_base_path.glob("*") if d.is_file() and d.name.startswith("phases")])

    phases_run_selector = mo.ui.dropdown(
            options=_available_runs,
            value=_available_runs[-1] if _available_runs else None,
            label="Sélectionner une run à analyser"
        ) if _available_runs else None

    phases_run_selector
    return (phases_run_selector,)


@app.cell
def _(data_base_path, phases_run_selector, pl):
    phases_df = None

    if phases_run_selector is not None and phases_run_selector.value:
        phases_run_path = data_base_path / phases_run_selector.value
        phases_df = pl.read_csv(phases_run_path)

    phases_df
    return (phases_df,)


@app.cell
def _(mo, phases_df, pl):
    phases_stats_base = (
        phases_df
        .filter(pl.col("source") == "base")
        .group_by("frequency")
        .agg(
            pl.col("delay").mean().alias("mean"),
            pl.col("delay").std().alias("std"),
            pl.col("delay").quantile(0.25).alias("q1"),
            pl.col("delay").median().alias("median"),
            pl.col("delay").quantile(0.75).alias("q3"),
            pl.col("delay").min().alias("min"),
            pl.col("delay").max().alias("max"),
            (pl.col("delay").std() / pl.col("delay").mean() * 100).abs().round(decimals=3).alias("CV")
        )
        .sort("frequency")
    )
    mo.vstack([mo.md("### Base phases delay stats"), phases_stats_base])
    return (phases_stats_base,)


@app.cell
def _(mo, phases_df, pl):
    phases_base_stress = (
        phases_df
        .filter(pl.col("source") == "base-stress")
        .group_by("frequency")
        .agg(
            pl.col("delay").mean().alias("mean"),
            pl.col("delay").std().alias("std"),
            pl.col("delay").quantile(0.25).alias("q1"),
            pl.col("delay").median().alias("median"),
            pl.col("delay").quantile(0.75).alias("q3"),
            pl.col("delay").min().alias("min"),
            pl.col("delay").max().alias("max"),
            (pl.col("delay").std() / pl.col("delay").mean() * 100).abs().round(decimals=3).alias("CV")
        )
        .sort("frequency")
    )
    mo.vstack([mo.md("### Base Stress phases delay stats"), phases_base_stress])
    return (phases_base_stress,)


@app.cell
def _(mo, phases_df, pl):
    phases_stats_joule_profiler = (
        phases_df
        .filter(pl.col("source") == "joule-profiler")
        .group_by("frequency")
        .agg(
            pl.col("delay").mean().alias("mean"),
            pl.col("delay").std().alias("std"),
            pl.col("delay").quantile(0.25).alias("q1"),
            pl.col("delay").median().alias("median"),
            pl.col("delay").quantile(0.75).alias("q3"),
            pl.col("delay").min().alias("min"),
            pl.col("delay").max().alias("max"),
            (pl.col("delay").std() / pl.col("delay").mean() * 100).abs().round(decimals=3).alias("CV")
        )
        .sort("frequency")
    )
    mo.vstack([mo.md("### Joule Profiler phases delay stats"), phases_stats_joule_profiler])
    return (phases_stats_joule_profiler,)


@app.cell
def _(mo, phases_df, pl):
    phases_stats_joule_profiler_stress = (
        phases_df
        .filter(pl.col("source") == "joule-profiler-stress")
        .group_by("frequency")
        .agg(
            pl.col("delay").mean().alias("mean"),
            pl.col("delay").std().alias("std"),
            pl.col("delay").quantile(0.25).alias("q1"),
            pl.col("delay").median().alias("median"),
            pl.col("delay").quantile(0.75).alias("q3"),
            pl.col("delay").min().alias("min"),
            pl.col("delay").max().alias("max"),
            (pl.col("delay").std() / pl.col("delay").mean() * 100).abs().round(decimals=3).alias("CV")
        )
        .sort("frequency")
    )
    mo.vstack([mo.md("### Joule Profiler Stress phases delay stats"), phases_stats_joule_profiler_stress])
    return (phases_stats_joule_profiler_stress,)


@app.cell
def _(phases_stats_base, phases_stats_joule_profiler):
    diff = phases_stats_joule_profiler - phases_stats_base
    diff
    return


@app.cell
def _(phases_base_stress, phases_stats_joule_profiler_stress):
    phases_stats_joule_profiler_stress - phases_base_stress
    return


@app.cell
def _(alt, phases_df, pl):
    _sources_list = ["Baseline", "Joule Profiler", "Baseline Stress", "Joule Profiler Stress"]
    _colors = ["#378ADD", "#D85A30", "#1A5FA8", "#8B3010"]

    _agg = (
        phases_df
        .group_by("source", "frequency")
        .agg(
            pl.col("delay").median().alias("median"),
            pl.col("delay").quantile(0.25).alias("q1"),
            pl.col("delay").quantile(0.75).alias("q3"),
            pl.col("delay").quantile(0.95).alias("p95"),
        )
        .with_columns(
            lower=pl.col("q1"),
            upper=pl.col("q3"),
            source=pl.col("source").replace({
                "base": "Baseline",
                "joule-profiler": "Joule Profiler",
                "base-stress": "Baseline Stress",
                "joule-profiler-stress": "Joule Profiler Stress"
            }),
        )
        .sort("frequency")
        .to_dicts()
    )

    _src = alt.Data(values=_agg)

    _band = (
        alt.Chart(_src)
        .mark_area(opacity=0.2)
        .encode(
            x=alt.X("frequency:N", title="Frequency (Hz)", axis=alt.Axis(labelAngle=-45)),
            y=alt.Y("lower:Q"),
            y2=alt.Y2("upper:Q"),
            color=alt.Color(
                "source:N",
                scale=alt.Scale(domain=_sources_list, range=_colors),
                legend=None,
            ),
        )
    )

    _median = (
        alt.Chart(_src)
        .mark_line()
        .encode(
            x="frequency:N",
            y=alt.Y("median:Q", title="Delay (μs)"),
            color=alt.Color(
                "source:N",
                title="Source",
                scale=alt.Scale(domain=_sources_list, range=_colors),
            ),
        )
    )

    (_band + _median).interactive().properties(width=800, height=500)
    return


if __name__ == "__main__":
    app.run()
