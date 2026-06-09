import marimo

__generated_with = "0.23.1"
app = marimo.App(width="medium")


@app.cell
def _():
    import subprocess
    import tqdm
    import time
    import os
    import random

    from lib import profiler_exec, alumet_exec, perf_exec, get_power_events, get_socket_cores, warmup

    return (
        alumet_exec,
        get_power_events,
        get_socket_cores,
        os,
        perf_exec,
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
    return (power_events,)


@app.cell
def _(SOCKET, get_socket_cores):
    socket_cores = get_socket_cores(SOCKET)
    socket_cores
    return (socket_cores,)


@app.cell
def _(
    PROFILER_PATH,
    RESULTS_DIR,
    SOCKET,
    alumet_exec,
    os,
    perf_exec,
    power_events,
    profiler_exec,
    random,
    socket_cores,
    time,
    tqdm,
    warmup,
):
    _cmd = f"programs/nbody 200000000"
    _iterations = 2000
    _delay = 1
    _taskset = "2"

    os.makedirs(f"{RESULTS_DIR}/sequential/perf", exist_ok=True)
    os.makedirs(f"{RESULTS_DIR}/sequential/joule-profiler", exist_ok=True)
    os.makedirs(f"{RESULTS_DIR}/sequential/alumet", exist_ok=True)

    warmup(taskset=_taskset, iter=10)

    for _i in tqdm.tqdm(range(_iterations)):
        _perf_out = os.path.join(RESULTS_DIR, "sequential", "perf", f"iteration_{_i}.csv")
        _profiler_out = os.path.join(RESULTS_DIR, "sequential", "joule-profiler", f"iteration_{_i}.csv")
        _alumet_out = os.path.join(RESULTS_DIR, "sequential", "alumet", f"iteration_{_i}.csv")

        _runs = [
            ("perf", lambda: perf_exec(_cmd, output_file=_perf_out, taskset=_taskset, no_agg=True, events=power_events, cores=socket_cores)),
            ("joule-profiler", lambda: profiler_exec(_cmd, output_file=_profiler_out, taskset=_taskset, sockets=[SOCKET], profiler_path=PROFILER_PATH)),
            ("alumet", lambda: alumet_exec(_cmd, config_file="config/alumet-config.toml", output_file=_alumet_out, taskset=_taskset)),
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
        if _errors["perf"] != "":
            raise RuntimeError(f"perf_event exec error : {_errors['perf']}")
        if "Error" in _errors["alumet"]:
            raise RuntimeError(f"alumet exec error : {_errors['alumet']}")
    return


if __name__ == "__main__":
    app.run()
