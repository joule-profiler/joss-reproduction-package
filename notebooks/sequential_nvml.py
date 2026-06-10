import marimo

__generated_with = "0.21.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import subprocess
    import tqdm
    import time
    import os
    import random

    from lib import profiler_exec, alumet_exec, get_power_events, get_socket_cores, warmup

    return (
        alumet_exec,
        get_power_events,
        get_socket_cores,
        os,
        profiler_exec,
        random,
        time,
        tqdm,
        warmup,
    )


@app.cell
def _(os):
    PROFILER_PATH = "joule-profiler"
    RESULTS_DIR = "results"
    os.makedirs(RESULTS_DIR, exist_ok=True)
    SOCKET = 0
    return PROFILER_PATH, RESULTS_DIR, SOCKET


@app.cell
def _(get_power_events):
    power_events = get_power_events()
    power_events
    return


@app.cell
def _(get_socket_cores):
    socket_cores = get_socket_cores(0)
    socket_cores
    return


@app.cell
def _(
    PROFILER_PATH,
    RESULTS_DIR,
    SOCKET,
    alumet_exec,
    os,
    profiler_exec,
    random,
    time,
    tqdm,
    warmup,
):
    _cmd = f"python3 programs/gpu.py 200"
    _iterations = 2000
    _delay = 1
    _taskset = "2"

    os.makedirs(f"{RESULTS_DIR}/sequential_nvml/joule-profiler", exist_ok=True)
    os.makedirs(f"{RESULTS_DIR}/sequential_nvml/alumet", exist_ok=True)

    warmup(cmd=_cmd, taskset=_taskset, iter=10)

    for _i in tqdm.tqdm(range(_iterations)):
        _profiler_out = os.path.join(RESULTS_DIR, "sequential_nvml", "joule-profiler", f"iteration_{_i}.csv")
        _alumet_out = os.path.join(RESULTS_DIR, "sequential_nvml", "alumet", f"iteration_{_i}.csv")

        _runs = [
            ("joule-profiler", lambda: profiler_exec(_cmd, output_file=_profiler_out, profiler_path=PROFILER_PATH, taskset=_taskset, nvml=True, sockets=[SOCKET])),
            ("alumet", lambda: alumet_exec(_cmd, output_file=_alumet_out, taskset=_taskset, config_file="config/alumet-config_nvml.toml")),
        ]
        random.shuffle(_runs)

        _errors = {}
        for _tool, _fn in _runs:
            time.sleep(_delay)
            _proc = _fn()
            _, _err = _proc.communicate()
            _errors[_tool] = _err

        if _errors["joule-profiler"] != "":
            raise RuntimeError(f"profiler exec error : {_errors['joule-profiler']}")
        if "Error" in _errors["alumet"]:
            raise RuntimeError(f"alumet exec error : {_errors['alumet']}")
    return


if __name__ == "__main__":
    app.run()
