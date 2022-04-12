import threading
import time
import random

def worker(number):
    sec = random.randrange(1, 10)
    time.sleep(sec)

    print(f'I am Worker {str(number)}, I slept for {sec} seconds')


for i in range(5):
    t = threading.Thread(target=worker, args=(i,))
    t.start()


print("All Threads are queued, let's see when they finish!")
