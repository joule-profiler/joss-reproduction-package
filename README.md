# JOSS Dataset

This repository contains the dataset and the scripts used for the JOSS (Journal of Open Source Software) paper "Joule Profiler: A phase-based energy measurement tool".

The Joule Profiler repository is available [here](https://github.com/joule-profiler/joule-profiler/).

The raw results are available [here](https://filesender.renater.fr/?s=download&token=5845fdda-1921-4352-933b-f12418e0194c) (too heavy for github) and the aggregated results are available in the `data.zip` archive.
The notebooks used for benchmarking and vizualization are available in the `notebooks/` folder:
- `full_comparison.py`: notebook for vizualization of the aggregated data.
- `prepare_data.py`: notebook for aggregation of the raw results.
The other notebooks are used to benchmark the different scenarios.

## Reproduce experiments

If you want to reproduce the experiments, you need to install [Joule Profiler](https://github.com/joule-profiler/joule-profiler/), [Alumet](https://alumet.dev/) and [perf stat](https://man7.org/linux/man-pages/man1/perf-stat.1.html)

