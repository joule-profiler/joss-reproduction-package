# JOSS reproduction package

This repository contains the dataset and the scripts used for the [JOSS](https://joss.theoj.org/) (Journal of Open Source Software) paper "Joule Profiler: A phase-based energy measurement tool".

The Joule Profiler repository is available [here](https://github.com/joule-profiler/joule-profiler/).

The raw results are available [here](https://filesender.renater.fr/?s=download&token=5845fdda-1921-4352-933b-f12418e0194c) (too heavy for github) and the aggregated results are available in the `data.zip` archive.
The notebooks used for benchmarking and vizualization are available in the `notebooks/` folder:
- `full_comparison.py`: notebook for vizualization of the aggregated data.
- `prepare_data.py`: notebook for aggregation of the raw results.
The other notebooks are used to benchmark the different scenarios.

Our experiments were conducted on the [Grid'5000](https://www.grid5000.fr/w/Grid5000:Home) testbed, on the Chirop (Intel Xeon, RAPL, 512 GiB RAM) and Chifflot (Nvidia Tesla V100, NVML, 192 GiB RAM) clusters.

## Reproduce experiments

If you want to reproduce the experiments, you need to install [Joule Profiler](https://github.com/joule-profiler/joule-profiler/) (v2.1.1), [Alumet](https://alumet.dev/) (v0.9.3) and [perf](https://man7.org/linux/man-pages/man1/perf-stat.1.html) (Linux kernel v6.12)

You also need an Intel or AMD CPU with RAPL support and an Nvidia GPU supporting CUDA v11.8. 

### On Grid'5000

If you want to reproduce the experiments on the **Grid'5000** testbed, here is how to borrow a node and deploy a custom environment:

```
oarsub -p {cluster} -l host=1,walltime={time} "sleep 365d" -t deploy
kadeploy3 -m {node} debian12-big
```

We use debian12-big to have access to the NVIDIA open kernel modules and drivers pre-installed on the node.

### Setup environment

We are using [Nix](https://github.com/nixos/nix) to configure the reproducible environment.

All the scripts for configuration and experiments are in the `scripts/` folder and have to be executed in the project root directory.

If you don't have Nix on the node, then you can install it with the `install_nix.sh` script. (reload the terminal if nix is not found in the path)

Firstly, execute the `setup_nix.sh` script, it will initialize the nix environment, download the required dependencies and configure it for the benchmarks.  

Now, in the Nix environment, execute the `setup.sh`, it will:
- Install Joule Profiler and Alumet
- Compile the programs used for benchmarks
- Configure the perf_event_paranoid level, the performance governor and disable SMT
- Initialize the uv virtual environment

### Run experiments

There are several benchmark notebooks available in the `notebooks/` folder:
- `parallel.py`: CPU parallel benchmark (RAPL)
- `parallel_nvml.py`: GPU parallel benchmark (NVML)
- `sequential.py`: CPU sequential benchmark (RAPL)
- `sequential_nvml.py`: GPU sequential benchmark (NVML)
- `phases.py`: phase detection latency benchmark
- `phases-stress.py`: phase detection latency benchmark under CPU stress

To run a notebook, do:
```
scripts/run_notebook.sh notebooks/{notebook}
```

### Visualize results

This step only requires `uv` to be installed (no Nix environment needed).

The aggregated results are provided in the `data.zip` archive. The raw results are available for download [here](https://filesender.renater.fr/?s=download&token=5845fdda-1921-4352-933b-f12418e0194c).

To aggregate raw results, run `prepare_data.py` to generate the aggregated dataset into the `results/` folder, then use `full_comparison.py` to visualize it.

To visualize the results, run:
```
uvx marimo edit notebooks/full_comparison.py
```

### Prerequisites

- A **Grid'5000** account with access to Chirop or Chifflot cluster, or equivalent hardware
- Nix (or run `install_nix.sh`)
- `uv` for visualization only