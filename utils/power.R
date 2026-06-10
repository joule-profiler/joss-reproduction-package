library(TOSTER)

powerTOSTpaired(alpha=0.05, statistical_power=0.8, low_eqbound_dz=-0.05, high_eqbound_dz=0.05) # 3425.539 => parallel

powerTOSTtwo(alpha = 0.05, statistical_power = 0.8, low_eqbound_d = -0.1, high_eqbound_d = 0.1) # 1712.769 => sequential

power.t.test(
  n         = 4000000,
  delta     = 0.1,
  sd        = 50,
  sig.level = 0.05,
  type      = "two.sample",
  alternative = "one.sided"
) # 0.8390009 => phases

# Parallel

# DRAM-0 (perf - Joule Profiler)

power_t_TOST(
  n = NULL,
  delta = 0.004, # mean_diff
  sd = 0.015, # diff_std
  eqb = 0.071, # equivalence margin
  alpha = 0.05,
  power = 0.8,
  type = "paired"
)

# PACKAGE-0 (perf - Joule Profiler)

power_t_TOST(
  n = NULL,
  delta = -0.314,
  sd = 0.272,
  eqb = 0.606,
  alpha = 0.05,
  power = 0.8,
  type = "paired"
)

# GPU-0 (Alumet - Joule Profiler)

power_t_TOST(
  n = NULL,
  delta = 1.392,
  sd = 2.187,
  eqb = 1.55,
  alpha = 0.05,
  power = 0.8,
  type = "paired"
)


# Sequential

# DRAM-0 (perf - Joule Profiler)

power_t_TOST(
  n = NULL,
  delta = 0.016,
  sd = 0.39,
  eqb = 0.266,
  alpha = 0.05,
  power = 0.8,
  type = "two.sample"
)

# PACKAGE-0 (perf - Joule Profiler)

power_t_TOST(
  n = NULL,
  delta = 1.393,
  sd = 7.628,
  eqb = 2.149,
  alpha = 0.05,
  power = 0.8,
  type = "two.sample"
)

# DRAM-0 (Alumet - Joule Profiler)

power_t_TOST(
  n = NULL,
  delta = 0.032,
  sd = 0.378,
  eqb = 0.266,
  alpha = 0.05,
  power = 0.8,
  type = "two.sample"
)

# PACKAGE-0 (Alumet - Joule Profiler)

power_t_TOST(
  n = NULL,
  delta = 0.404,
  sd = 7.289,
  eqb = 2.144,
  alpha = 0.05,
  power = 0.8,
  type = "two.sample"
)

# GPU-0 (Alumet - Joule Profiler)

power_t_TOST(
  n = NULL,
  delta = 1.055,
  sd = 13.991,
  eqb = 2.646,
  alpha = 0.05,
  power = 0.8,
  type = "two.sample"
)
