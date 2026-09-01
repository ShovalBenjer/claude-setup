import statistics
import subprocess
import sys
import time
from pathlib import Path

C=[("/bin/true (compiled floor)",["/bin/true"]),
   ("python3 -S -E -c pass",["python3","-S","-E","-c","pass"]),
   ("python3 -c pass",["python3","-c","pass"]),
   ("/bin/dash -c :",["/bin/dash","-c",":"])]
W,N=40,400
print(f"WSL2 Ubuntu, ext4 cwd, fork+exec. {W} warmup + {N} runs\n")
print("{:<30}{:>10}{:>10}{:>10}".format("candidate","median","min","p90")); print("-"*60)
for l,a in C:
    try:
        for _ in range(W): subprocess.run(a,stdin=subprocess.DEVNULL,capture_output=True)
    except FileNotFoundError:
        print("{:<30}{:>10}".format(l,"MISSING")); continue
    s=[]
    for _ in range(N):
        t=time.perf_counter(); subprocess.run(a,stdin=subprocess.DEVNULL,capture_output=True); s.append((time.perf_counter()-t)*1000)
    s.sort()
    print("{:<30}{:>8.3f}ms{:>8.3f}ms{:>8.3f}ms".format(l,statistics.median(s),s[0],s[int(N*.9)]))
