import marimo

__generated_with = "0.23.9"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    from pathlib import Path
    import polars as pl
    import time

    return Path, mo, pl, time


@app.cell
def _():
    RESULTS_PATH = "results"
    OUTPUT_DIR = "data"
    return OUTPUT_DIR, RESULTS_PATH


@app.cell
def _(OUTPUT_DIR, Path, RESULTS_PATH):
    results_base_path = Path(RESULTS_PATH)
    output_dir = Path(OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir, results_base_path


@app.cell
def _(mo, results_base_path):
    available_runs = sorted([d.name for d in results_base_path.glob("*") if d.is_dir()])

    run_selector = (
        mo.ui.dropdown(
            options=available_runs,
            value=available_runs[-1] if available_runs else None,
            label="Select a run to analyze",
        )
        if available_runs
        else None
    )

    run_selector
    return (run_selector,)


@app.cell
def _(results_base_path, run_selector):
    BASE = results_base_path / run_selector.value

    if run_selector.value.endswith("nvml"):
        TYPE = "gpu"
    elif run_selector.value.endswith("phases"):
        TYPE = "phases"
    else:
        TYPE = None
    return BASE, TYPE


@app.cell
def _(Path, pl):
    def parse_perf_file(path: Path) -> pl.DataFrame:
        columns = ["cpu", "value", "unit", "event", "run_time", "coverage", "extra_value", "extra_label"]
        return pl.read_csv(
            path,
            separator=";",
            has_header=False,
            new_columns=columns,
        ) \
            .filter(pl.col("cpu") == "CPU0") \
            .rename({"value": "metric_value", "unit": "metric_unit"}) \
            .with_columns([
                pl.when(pl.col("event").is_in(["energy-pkg", "power/energy-pkg/"])).then(pl.lit("PACKAGE-0"))
                    .when(pl.col("event").is_in(["energy-ram", "power/energy-ram/"])).then(pl.lit("DRAM-0"))
                    .when(pl.col("event").is_in(["energy-cores", "power/energy-cores/"])).then(pl.lit("CORE-0"))
                    .when(pl.col("event").is_in(["energy-gpu", "power/energy-gpu/"])).then(pl.lit("UNCORE-0"))
                    .when(pl.col("event").is_in(["energy-psys", "power/energy-psys/"])).then(pl.lit("PSYS"))
                .alias("metric_name"),

                pl.lit(path.stem.split("_")[1]).cast(pl.UInt32).alias("iteration").cast(pl.UInt16),

                pl.lit("J").alias("metric_unit"),

                pl.lit("perf").alias("source")
            ]) \
        .select(["metric_name", "metric_value", "metric_unit", "iteration", "source"])

    return (parse_perf_file,)


@app.cell
def _(Path, pl):
    def parse_joule_profiler_file(path: Path, type: str = None) -> pl.DataFrame:
        df = pl.read_csv(path, separator=";") \
            .with_columns([
                pl.when(pl.col("metric_unit") == 	
    "µJ").then(pl.col("metric_value") / 1_000_000)
                    .when(pl.col("metric_unit") == "mJ").then(pl.col("metric_value") / 1_000)
                    .alias("metric_value"),

                pl.lit("J").alias("metric_unit"),

                pl.lit(path.stem.split("_")[1]).cast(pl.UInt32).alias("iteration").cast(pl.UInt16),
                pl.lit("joule-profiler").alias("source")
            ])

        if type == "gpu":
            df = df.filter(pl.col("metric_name") == "GPU-0").select(["metric_name", "metric_value", "metric_unit", "iteration", "source"])

        elif type == "phases":
            df = df.drop(["metric_name", "metric_value", "metric_unit"])
            df = df.group_by(df.columns).first()
            df = (
                df
                .filter(
                    (pl.col("start_token") != "START") &
                    (pl.col("end_token") != "END")
                )
                .with_columns([
                    pl.col("start_token")
                    .str.extract(r"__PHASE_(\d+)__")
                    .cast(pl.Int64)
                    .alias("phase_id")
                ])
                .with_columns([
                    (pl.col("timestamp") - pl.col("phase_id")).alias("delay")
                ])
                .with_columns([
                    pl.cum_count("phase_id").cast(pl.UInt32).alias("measurement_index")
                ])
                .with_columns([
                    pl.lit(100).alias("frequency")
                ])
                .select(["delay", "measurement_index", "frequency", "iteration", "source"])
                .sort(["measurement_index", "delay"])
            )
        else:
            df = df.select(["metric_name", "metric_value", "metric_unit", "iteration", "source"])
        return df

    return (parse_joule_profiler_file,)


@app.cell
def _(Path, pl):
    def parse_alumet_file(path: Path, type: str = None) -> pl.DataFrame:
        df = pl.read_csv(path, separator=";")

        gpu_ids = (
            df.filter(pl.col("metric").str.contains("nvml_energy_consumption_mJ"))
            .select("resource_id").unique()
            .sort("resource_id")
            .with_row_index("gpu_index")
            .with_columns(
                pl.concat_str([pl.lit("GPU-"), pl.col("gpu_index").cast(pl.String)]).alias("gpu_label")
            )
        )

        df = df.join(gpu_ids, on="resource_id", how="left")

        df = df.with_columns(
            pl.col("value").cast(pl.Float64, strict=False),
            pl.col("resource_id").cast(pl.Int8, strict=False)
        )

        df = df.filter(
                (pl.col("metric").str.contains("rapl_consumed_energy_J") & (pl.col("resource_id") != 1))
                | pl.col("metric").str.contains("nvml_energy_consumption_mJ")
            ).with_columns([
                pl.when(pl.col("__late_attributes").str.ends_with("package"))
                  .then(pl.lit("PACKAGE-0"))
                  .when(pl.col("__late_attributes").str.ends_with("pp1"))
                  .then(pl.lit("UNCORE-0"))
                  .when(pl.col("__late_attributes").str.ends_with("platform"))
                  .then(pl.lit("PSYS"))
                  .when(pl.col("__late_attributes").str.ends_with("pp0"))
                  .then(pl.lit("CORE-0"))
                  .when(pl.col("__late_attributes").str.ends_with("dram"))
                  .then(pl.lit("DRAM-0"))
                    .when(pl.col("metric").str.contains("nvml_energy_consumption_mJ"))
                  .then(pl.col("gpu_label"))

                  .alias("metric_name"),


                pl.when(pl.col("metric").str.ends_with("J")).then(pl.lit("J"))
                    .when(pl.col("metric").str.ends_with("mJ")).then(pl.lit("mJ"))
                    .alias("metric_unit"),

                pl.lit(path.stem.split("_")[1]).alias("iteration").cast(pl.UInt16),
                pl.lit("alumet").alias("source"),

                pl.when(pl.col("metric").str.ends_with("mJ")).then(pl.col("value") / 1000)
                   .otherwise(pl.col("value")).alias("metric_value")
            ])

        if type == "gpu":
            df = df.filter(pl.col("metric_name") == "GPU-0")

        df = df.group_by(["metric_name", "metric_unit", "iteration", "source"], maintain_order=True).agg(pl.col("metric_value").sum())

        df = df.select(["metric_name", "metric_value", "metric_unit", "iteration", "source"])

        return df

    return (parse_alumet_file,)


@app.cell
def _(BASE, parse_perf_file, pl):
    PERF_DIR = BASE / "perf"
    perf_df = [parse_perf_file(p) for p in PERF_DIR.glob("*.csv")]
    perf_df = pl.concat(perf_df).sort(by="iteration") if perf_df else None
    return (perf_df,)


@app.cell
def _(BASE, TYPE, parse_alumet_file, pl):
    ALUMET_DIR = BASE / "alumet"
    alumet_df = [parse_alumet_file(p, type=TYPE) for p in ALUMET_DIR.glob("*.csv")]
    alumet_df = pl.concat(alumet_df).sort(by="iteration") if alumet_df else None
    return (alumet_df,)


@app.cell
def _(BASE, TYPE, parse_joule_profiler_file, pl):
    joule_profiler_stress_df = None
    joule_profiler_df = None

    if TYPE == "phases":
        _dfs = []
        _dfs_stress = []
        for _freq in BASE.glob("*"):
            _path = _freq / "joule-profiler"
            for _p in _path.glob("*.csv"):
                _df = parse_joule_profiler_file(_p, type=TYPE).with_columns(pl.lit(_freq.name.removesuffix("hz")).cast(pl.UInt16).alias("frequency"))
                _dfs.append(_df)
            _path_stress = _freq / "joule-profiler-stress"

            for _p in _path_stress.glob("*.csv"):
                _df = parse_joule_profiler_file(_p, type=TYPE).with_columns(pl.lit(_freq.name.removesuffix("hz")).cast(pl.UInt16).alias("frequency"))
                _dfs_stress.append(_df)

            if _dfs:
                joule_profiler_df = pl.concat(_dfs).select(["delay", "measurement_index", "frequency", "iteration", "source"]).sort(by=["frequency", "iteration", "measurement_index"])

            if _dfs_stress:
                joule_profiler_stress_df = pl.concat(_dfs_stress).with_columns([pl.lit("joule-profiler-stress").alias("source")]).select(["delay", "measurement_index", "frequency", "iteration", "source"]).sort(by=["frequency", "iteration", "measurement_index"])

    else:
        JOULE_PROFILER_DIR = BASE / "joule-profiler"
        joule_profiler_df = [parse_joule_profiler_file(p, type=TYPE) for p in JOULE_PROFILER_DIR.glob("*.csv")]
        joule_profiler_df = pl.concat(joule_profiler_df).sort(by="iteration") if joule_profiler_df else None
    return joule_profiler_df, joule_profiler_stress_df


@app.cell
def _(BASE, TYPE, pl):
    PHASE_BASE_DIR = BASE
    base_phases_df = None
    base_stress_phases_df = None

    if TYPE == "phases":
        _dfs = []
        _dfs_stress = []
        for _freq in BASE.glob("*"):
            _path = _freq / "base"
            for _i, _p in enumerate(_path.glob("*.csv")):
                _df = (
                    pl.read_csv(_p, new_columns=["delay"])
                    .with_columns([
                        pl.lit(_i).cast(pl.UInt16).alias("iteration"),
                        pl.lit(_freq.name.removesuffix("hz"))
                        .cast(pl.UInt16)
                        .alias("frequency"),
                        pl.lit("base").alias("source")
                    ])
                    .select(["delay", "frequency", "iteration", "source"])
                ).with_row_index("measurement_index", offset=1).sort(["measurement_index"])
                _dfs.append(_df)
            _path_stress = _freq / "base-stress"
            for _i, _p in enumerate(_path_stress.glob("*.csv")):
                _df = (
                    pl.read_csv(_p, new_columns=["delay"])
                    .with_columns([
                        pl.lit(_i).cast(pl.UInt16).alias("iteration"),
                        pl.lit(_freq.name.removesuffix("hz"))
                        .cast(pl.UInt16)
                        .alias("frequency"),
                        pl.lit("base-stress").alias("source")
                    ])
                    .select(["delay", "frequency", "iteration", "source"])
                ).with_row_index("measurement_index", offset=1).sort(["measurement_index"])
                _dfs_stress.append(_df)

        if _dfs:
            base_phases_df = (
                pl.concat(_dfs)
                .select(["delay", "measurement_index", "frequency", "iteration", "source"])
            )

        if _dfs_stress:
            base_stress_phases_df = (
                pl.concat(_dfs_stress)
                .select(["delay", "measurement_index", "frequency", "iteration", "source"])
            )
    return base_phases_df, base_stress_phases_df


@app.cell
def _(
    TYPE,
    alumet_df,
    base_phases_df,
    base_stress_phases_df,
    joule_profiler_df,
    joule_profiler_stress_df,
    perf_df,
    pl,
):
    _to_join = []
    if joule_profiler_df is not None:
        _to_join.append(joule_profiler_df)
    if perf_df is not None:
        _to_join.append(perf_df)
    if alumet_df is not None:
        _to_join.append(alumet_df)
    if base_phases_df is not None:
        _to_join.append(base_phases_df)
    if base_stress_phases_df is not None:
        _to_join.append(base_stress_phases_df)
    if joule_profiler_stress_df is not None:
        _to_join.append(joule_profiler_stress_df)

    if TYPE == "phases":
        df = pl.concat(_to_join, how="vertical").sort(by=["iteration", "frequency", "measurement_index", "source"])
    else:
        df = pl.concat(_to_join, how="vertical").sort(by=["iteration", "source", "metric_name"])
    return (df,)


@app.cell
def _(alumet_df, base_phases_df, joule_profiler_df, mo, perf_df):
    _joule_profiler_record_nb = joule_profiler_df.height if joule_profiler_df is not None else 0
    _number_of_joule_profiler_records = mo.stat(
        value=_joule_profiler_record_nb,
        label="Number of Joule Profiler records"
    )

    _perf_record_nb = perf_df.height if perf_df is not None else 0
    _number_of_perf_records = mo.stat(
        value=_perf_record_nb,
        label="Number of perf records",
    )

    _alumet_record_nb = alumet_df.height if alumet_df is not None else 0
    _number_of_alumet_records = mo.stat(
        value=_alumet_record_nb,
        label="Number of Alumet records"
    )

    _base_phases_records = base_phases_df.height if base_phases_df is not None else 0
    _number_of_base_phases_records = mo.stat(
        value=_base_phases_records,
        label="Other records"
    )

    _total_records = mo.stat(
        value=(_joule_profiler_record_nb + _perf_record_nb + _alumet_record_nb + _base_phases_records),
        label="Total number of records",
    )

    mo.hstack([_total_records, _number_of_joule_profiler_records, _number_of_perf_records, _number_of_alumet_records, _number_of_base_phases_records])
    return


@app.cell
def _(df):
    df
    return


@app.cell(disabled=True)
def _(df, pl):
    import altair as alt
    alt.data_transformers.enable("vegafusion")

    df_sorted = df.filter(pl.col("frequency") == 1000).filter(pl.col("delay") < 20).sort("measurement_index")

    base = (
        alt.Chart(df_sorted)
        .mark_point()
        .encode(
            x=alt.X("measurement_index:Q", title="Measurement Index"),
            y=alt.Y("delay:Q", title="Delay"),
            tooltip=["measurement_index", "delay", "source"]
        )
        .properties(
            width=700,
            height=200
        )
    )

    chart = (
        base
        .facet(
            row=alt.Row("source:N", title="Source")
        )
        .properties(
            title="Évolution du delay"
        )
        .resolve_scale(y="independent")
    )

    chart
    return


@app.cell
def _(mo):
    export_button = mo.ui.run_button(label="Exporter to CSV")
    return (export_button,)


@app.cell
def _(df, export_button, mo, output_dir, run_selector, time):
    if export_button.value:
        _output_file = output_dir / f"{run_selector.value}-{time.time()}.csv"
        df.write_csv(_output_file)
        export_display = mo.vstack(
            [
                export_button,
                mo.md(
                    f"**Data exported successfully:** `{_output_file}`"
                ).callout(kind="success"),
            ]
        )
    else:
        export_display = export_button

    export_display
    return


if __name__ == "__main__":
    app.run()
