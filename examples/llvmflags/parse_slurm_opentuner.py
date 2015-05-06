import re
import matplotlib.pyplot as plt

SLURM_FILE = 'slurm-666113.out'

with open(SLURM_FILE) as f:
  times = []
  bests = []
  for line in f:
    if 'cost time' in line:
      time = int(line[1:7].strip())
      best = float(line.split('cost time=')[1].split(',')[0])
      times.append(time)
      bests.append(best)


plt.plot(times, bests, 'b-', label='OpenTuner')
plt.plot([-10, 4000], [0.1989]*2, 'r-', label='Base')
plt.xlabel('time elapsed (s)')
plt.ylabel('best execution time')
plt.legend()
plt.show()
