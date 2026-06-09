cargo install joule-profiler-cli
cd programs/timer
cargo build --release
cd ..
gcc -pipe -Wall -O3 -fomit-frame-pointer -march=ivybridge nbody.c -o nbody
cd ..