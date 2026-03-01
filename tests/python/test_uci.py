import subprocess
import time

p = subprocess.Popen(['python', 'main.py'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

p.stdin.write("uci\n")
p.stdin.write("isready\n")
p.stdin.write("position startpos\n")
p.stdin.write("go movetime 1000\n")
p.stdin.flush()

# Let the engine search for a bit more than 1 second
time.sleep(1.5)

p.stdin.write("quit\n")
p.stdin.flush()

out, err = p.communicate()
print("STDOUT:")
print(out)
print("STDERR:")
print(err)
