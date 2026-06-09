sudo sysctl kernel.perf_event_paranoid=0
echo off | sudo tee /sys/devices/system/cpu/smt/control
sudo cpupower frequency-set -g performance
sh setup.sh
PYTHONPATH=src uv run $1
