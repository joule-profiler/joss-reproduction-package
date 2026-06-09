import torch
import sys

N = 8192
DT = 0.01
EPS = 1e-5
STEPS = int(sys.argv[1]) if len(sys.argv) > 1 else 100

def main():
    device = "cuda"
    pos = torch.rand(N, 3, device=device, dtype=torch.float32)
    vel = torch.zeros(N, 3, device=device, dtype=torch.float32)

    print(f"Running N-body GPU stress test: N={N}, STEPS={STEPS}")

    for step in range(STEPS):
        diff = pos[:, None, :] - pos[None, :, :]
        dist_sqr = (diff * diff).sum(dim=2) + EPS
        inv_dist3 = dist_sqr ** (-1.5)
        acc = -(diff * inv_dist3[:, :, None]).sum(dim=1)

        vel = vel + acc * DT
        pos = pos + vel * DT

        if step % 10 == 0:
            print(f"step {step}")
            torch.cuda.synchronize()

    torch.cuda.synchronize()

if __name__ == "__main__":
    main()
