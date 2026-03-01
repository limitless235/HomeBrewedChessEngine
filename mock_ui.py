import subprocess
import time

p = subprocess.Popen(
    ['./engine'],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.DEVNULL,
    text=True,
    bufsize=1
)

def send(cmd):
    print("UI ->", cmd)
    p.stdin.write(cmd + "\n")
    p.stdin.flush()

send("uci")
print("Engine ->", p.stdout.readline().strip())
print("Engine ->", p.stdout.readline().strip())
print("Engine ->", p.stdout.readline().strip())

send("isready")
print("Engine ->", p.stdout.readline().strip())

send("position startpos moves e2e4")
send("go movetime 1000")

# Read stdout until bestmove
while True:
    line = p.stdout.readline()
    if not line:
        break
    line = line.strip()
    print("Engine ->", line)
    if line.startswith("bestmove"):
        break

send("quit")
p.wait()
