import subprocess
import os
import tqdm

def get_power_events(base_path: str = "/sys/bus/event_source/devices/power/events") -> list[str]:
    if not os.path.exists(base_path):
        raise FileNotFoundError(f"Unknown directory : {base_path}")

    return [
        entry for entry in os.listdir(base_path)
        if not entry.endswith(".scale") and not entry.endswith(".unit")
    ]

def get_socket_cores(socket: int) -> str:
    result = subprocess.run(["lscpu", "--parse=CPU,SOCKET"], capture_output=True, text=True)
    cores = sorted([
        int(line.split(",")[0])
        for line in result.stdout.splitlines()
        if not line.startswith("#") and line.split(",")[1] == str(socket)
    ])

    intervals = []
    start = cores[0]
    end = cores[0]
    for c in cores[1:]:
        if c == end + 1:
            end = c
        else:
            intervals.append((start, end))
            start = end = c
    intervals.append((start, end))

    return ",".join(
        str(s) if s == e else f"{s}-{e}"
        for s, e in intervals
    )

def warmup(cmd="programs/nbody 200000000", taskset=None, iter=1):
    taskset_args = ["taskset", "-c", taskset] if taskset else []
    for _ in tqdm.tqdm(range(iter), desc="Warmup"):
        _proc = subprocess.Popen(
            [*taskset_args, *cmd.split(" ") ],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        _proc.communicate()

def perf_exec(cmd, perf_args=[], events=[], output_file="perf_output.csv", taskset=None, perf_counters=False, cores=None, no_agg=False):
    perf_counters_args = ["instructions", "cpu-cycles", "branch-misses", "cache-misses"] if perf_counters else []
    no_agg_args = ["-A"] if no_agg else []
    events = [*events, *perf_counters_args]
    events_args = ["-e", ",".join(events)] if len(events) > 0 else []
    cores_args = ["-C", cores] if cores else []

    base = ["perf", "stat", *no_agg_args, *cores_args, "-o", output_file, "-x", ";", *[str(arg) for arg in perf_args], *events_args]
    taskset_args = ["taskset", "-c", taskset] if taskset else []
    full = [*base, *taskset_args, *cmd.split()]
    return subprocess.Popen(full, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

def profiler_exec(cmd, profiler_args=[], output_file="profiler_output.csv", sockets=[], profiler_path="joule-profiler", taskset=None, perf_counters=False, nvml=False, profiler_taskset=None):
    perf_counters_args = ["--perf"] if perf_counters else []
    nvml_args = ["--gpu"] if nvml else []
    socket_args = ["--sockets", *[str(socket) for socket in sockets]] if sockets else []
    base = [profiler_path, *perf_counters_args, *nvml_args, *socket_args, "-o", output_file, "--csv", *[str(arg) for arg in profiler_args], "profile", "--"]
    taskset_args = ["taskset", "-c", taskset] if taskset else []
    profiler_taskset_args = ["taskset", "-c", profiler_taskset] if profiler_taskset else []
    full = [*profiler_taskset_args, *base, *taskset_args, *cmd.split()]
    return subprocess.Popen(full, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

def alumet_exec(cmd, output_file="alumet-output.csv", config_file=None, taskset=None):
    config_args = ["--config", config_file] if config_file else []
    base = ["alumet-agent", *config_args, "--output-file", output_file, "exec", "--"]
    taskset_args = ["taskset", "-c", taskset] if taskset else []
    full = [*base, *taskset_args, *cmd.split()]
    return subprocess.Popen(full, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
