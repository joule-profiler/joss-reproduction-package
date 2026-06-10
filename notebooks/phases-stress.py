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

    from lib import profiler_exec, get_power_events, get_socket_cores, warmup

    return (
        get_power_events,
        get_socket_cores,
        os,
        profiler_exec,
        random,
        subprocess,
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
    return PROFILER_PATH, RESULTS_DIR


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
    os,
    profiler_exec,
    random,
    subprocess,
    time,
    tqdm,
    warmup,
):
    _frequencies = [_i for _i in range(100, 1001, 100)]
    _iterations = 10
    _delay = 1
    _taskset = "2"
    _profiler_taskset = "4"
    _nb_samples = 10000

    warmup(cmd="stress-ng --cpu 0 --cpu-load 100 --timeout 10s", iter=10)

    for _frequency in _frequencies:
        os.makedirs(f"{RESULTS_DIR}/phases/{_frequency}hz/joule-profiler-stress", exist_ok=True)
        os.makedirs(f"{RESULTS_DIR}/phases/{_frequency}hz/base-stress", exist_ok=True)
    for _i in tqdm.tqdm(range(_iterations), desc="iterations"):
        random.shuffle(_frequencies)
        for _frequency in _frequencies:
            _interval_ms = (1 / _frequency) * 1000
            _profiler_out_stress = os.path.join(RESULTS_DIR, "phases", f"{_frequency}hz", "joule-profiler-stress", f"iteration_{_i}.csv")
            _output_file_stress = os.path.join(RESULTS_DIR, "phases", f"{_frequency}hz", "base-stress", f"iteration_{_i}.csv")
        
            def run_profiler_stress():
                _stress_proc = subprocess.Popen(["stress-ng", "--cpu", "0", "--cpu-load", "100"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                _proc = profiler_exec(f"programs/timer/target/release/timer {_interval_ms} {_nb_samples} false", profiler_path=PROFILER_PATH, output_file=_profiler_out_stress, taskset=_taskset, profiler_taskset=_profiler_taskset)
                _, _err = _proc.communicate()
                _stress_proc.terminate()
                _stress_proc.wait()
                if _err != "":
                    raise RuntimeError(f"Profiler stress exec error : {_err}")
                
            def run_base_stress():
                _stress_proc = subprocess.Popen(["stress-ng", "--cpu", "0", "--cpu-load", "100"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                _proc = subprocess.Popen(f"taskset -c {_profiler_taskset} programs/timer/target/release/timer {_interval_ms} {_nb_samples} true {_output_file_stress} {_taskset}".split(" "), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                _, _err = _proc.communicate()
                _stress_proc.terminate()
                _stress_proc.wait()
                if _err != "":
                    raise RuntimeError(f"Base stress exec error : {_err}")
                
            runs = [run_profiler_stress, run_base_stress]
            random.shuffle(runs)
            
            for run in runs:
                time.sleep(_delay)
                run()
    return


if __name__ == "__main__":
    app.run()
