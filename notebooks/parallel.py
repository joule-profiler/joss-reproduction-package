import marimo

__generated_with = "0.21.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import subprocess
    import tqdm
    import time
    import random
    import os

    from lib import profiler_exec, perf_exec, get_power_events, get_socket_cores, warmup

    return (
        get_power_events,
        get_socket_cores,
        os,
        perf_exec,
        profiler_exec,
        random,
        subprocess,
        tqdm,
        warmup,
    )


@app.cell
def _(os):
    PROFILER_PATH = "joule-profiler"
    RESULTS_DIR = "results"
    SOCKET = 0
    os.makedirs(RESULTS_DIR, exist_ok=True)
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
    os,
    perf_exec,
    power_events,
    profiler_exec,
    random,
    socket_cores,
    subprocess,
    tqdm,
    warmup,
):
    _delay = 1
    _iterations = 4000
    _taskset = socket_cores

    os.makedirs(f"{RESULTS_DIR}/parallel/perf", exist_ok=True)
    os.makedirs(f"{RESULTS_DIR}/parallel/joule-profiler", exist_ok=True)

    warmup(taskset=_taskset, iter=10)

    for _i in tqdm.tqdm(range(_iterations), delay=_delay):
        _perf_out = os.path.join(RESULTS_DIR, "parallel", "perf", f"iteration_{_i}.csv")
        _profiler_out = os.path.join(RESULTS_DIR, "parallel", "joule-profiler", f"iteration_{_i}.csv")

        _cmd = "sleep 10"
        _nbody_proc = subprocess.Popen(["taskset", "-c", _taskset, "programs/nbody", "100000000000"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        _runs = [
            ("perf", lambda: perf_exec(_cmd, output_file=_perf_out, taskset=_taskset, no_agg=True, events=power_events, cores=socket_cores)),
            ("joule-profiler", lambda: profiler_exec(_cmd, output_file=_profiler_out, sockets=[SOCKET], profiler_path=PROFILER_PATH, taskset=_taskset)),
        ]

        random.shuffle(_runs)
        time.sleep(_delay)
        _procs = {_tool: _fn() for _tool, _fn in _runs}
        _errors = {_tool: _proc.communicate()[1] for _tool, _proc in _procs.items()}

        _nbody_proc.kill()
        _nbody_proc.wait()

        if _errors["joule-profiler"] != "":
            raise RuntimeError(f"Profiler exec error : {_errors['joule-profiler']}")
        if _errors["perf"] != "":
            raise RuntimeError(f"perf_event exec error : {_errors['perf']}")
    return


if __name__ == "__main__":
    app.run()
