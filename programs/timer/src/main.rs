
use std::{fs::File, io::{BufRead, BufReader, Write}, process::{Command, Stdio}, time::{Duration, SystemTime, UNIX_EPOCH}};

use timerfd::{SetTimeFlags, TimerFd, TimerState};

pub fn get_timestamp_micros() -> u128 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_micros()
}

fn run_child(interval_ms: f64, nb_phases: u64) {
    let duration = Duration::from_micros((interval_ms * 1000.0).round() as u64);

    let mut timer = TimerFd::new().unwrap();
    timer.set_state(
        TimerState::Periodic {
            current: duration,
            interval: duration,
        },
        SetTimeFlags::Default,
    );

    for _ in 0..nb_phases {
        timer.read();

        let timestamp = get_timestamp_micros();
        println!("__PHASE_{timestamp}__");
        std::io::stdout().flush().unwrap();
    }
}

fn spawn_command(taskset: Option<&str>, bin: &str, args: &[&str]) -> Command {
    if let Some(ts) = taskset {
        let mut cmd = Command::new("taskset");
        cmd.args(["-c", ts, bin]).args(args).stdout(Stdio::piped());

        cmd
    } else {
        let mut cmd = Command::new(bin);
        cmd.args(args).stdout(Stdio::piped());
        cmd
    }
}

fn run_parent(
    bin: &str,
    interval_ms: f64,
    nb_phases: u64,
    output_file: &str,
    taskset: Option<&str>,
) {
    let args = [&interval_ms.to_string(), &nb_phases.to_string(), "false"];

    let mut child = spawn_command(taskset, bin, &args)
        .spawn()
        .expect("spawn failed");

    let stdout = child.stdout.take().unwrap();
    let mut reader = BufReader::new(stdout);

    let mut results = Vec::with_capacity(nb_phases as usize);
    let mut line = String::new();

    loop {
        line.clear();

        let n = reader.read_line(&mut line).unwrap();
        if n == 0 {
            break;
        }

        if line.ends_with('\n') {
            line.pop();
            if line.ends_with('\r') {
                line.pop();
            }
        }

        
        if let Some(ts_str) = line
        .trim()
        .strip_prefix("__PHASE_")
        .and_then(|s| s.strip_suffix("__"))
        {
            let now = get_timestamp_micros();
            let child_ts: u128 = ts_str.parse().unwrap();
            results.push(now - child_ts);
        }
    }

    child.wait().unwrap();

    let mut f = File::create(output_file).unwrap();

    for r in results {
        f.write_all(format!("{r}\n").as_bytes()).unwrap();
    }
}

#[tokio::main]
async fn main() {
    let args: Vec<String> = std::env::args().collect();

    let interval_ms: f64 = args[1].parse().unwrap();
    let nb_phases: u64 = args[2].parse().unwrap();
    let measure_delays: bool = args[3].parse().unwrap();

    if measure_delays {
        let output = &args[4];
        let taskset = args.get(5).map(|s| s.as_str());

        run_parent(&args[0], interval_ms, nb_phases, output, taskset);
    } else {
        run_child(interval_ms, nb_phases);
    }
}
