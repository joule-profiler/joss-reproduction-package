cargo install joule-profiler-cli
cargo install --git https://github.com/alumet-dev/alumet --tag v0.9.3 alumet-agent

cd programs/timer
cargo build --release
cd ..
gcc -pipe -Wall -O3 -fomit-frame-pointer -march=ivybridge nbody.c -o nbody
cd ..

sudo sysctl kernel.perf_event_paranoid=0
sudo cpupower frequency-set -g performance
echo off | sudo tee /sys/devices/system/cpu/smt/control

uv venv
source .venv/bin/activate
uv pip install -e .

echo 'installation done'