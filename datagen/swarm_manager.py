import subprocess
import os
import time
import multiprocessing
import signal
import sys

# --- Configuration ---
BLENDER_PATH = "/Applications/Blender.app/Contents/MacOS/Blender"
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
BUFFER_DIR = os.path.join(ROOT_DIR, "rolling_buffer")
WORKER_SCRIPT = os.path.join(ROOT_DIR, "worker_kernel.py")

MAX_WORKERS = multiprocessing.cpu_count() - 1  # Leave 1 core for the OS/DINO
BATCH_QUOTA = 50        # How many avatars each worker makes before dying
MAX_SAMPLES = 2000     # Throttle: pause generation if buffer exceeds this

os.makedirs(BUFFER_DIR, exist_ok=True)

class SwarmManager:
    def __init__(self):
        self.workers = []
        self.running = True

    def count_ready_samples(self):
        # Only count completed .png files (not .tmp)
        return len([f for f in os.listdir(BUFFER_DIR) if f.endswith(".png") and not f.endswith(".tmp")])

    def spawn_worker(self, worker_id):
        cmd = [
            BLENDER_PATH,
            "--background",
            "--python", WORKER_SCRIPT,
            "--", 
            BUFFER_DIR, 
            str(BATCH_QUOTA), 
            str(worker_id)
        ]
        # Start headless blender as a persistent background process
        return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def run(self):
        print(f"[*] Starting Swarm Manager with {MAX_WORKERS} potential workers.")
        print(f"[*] Rolling Buffer: {BUFFER_DIR}")
        
        while self.running:
            # 1. Cleanup finished workers
            self.workers = [w for w in self.workers if w.poll() is None]

            # 2. Check Throttle
            current_buffer = self.count_ready_samples()
            if current_buffer >= MAX_SAMPLES:
                print(f"[!] Buffer Full ({current_buffer}/{MAX_SAMPLES}). Throttling...")
                time.sleep(5)
                continue

            # 3. Fill the pool
            while len(self.workers) < MAX_WORKERS:
                worker_id = len(self.workers)
                new_worker = self.spawn_worker(worker_id)
                self.workers.append(new_worker)
                print(f"[+] Spawned worker {worker_id} (Batch Size: {BATCH_QUOTA})")

            time.sleep(2)  # Healthy heartbeat

    def stop(self):
        print("\n[*] Shutting down swarm...")
        self.running = False
        for w in self.workers:
            w.terminate()
        sys.exit(0)

if __name__ == "__main__":
    manager = SwarmManager()
    
    # Catch SIGINT for clean exit
    signal.signal(signal.SIGINT, lambda s, f: manager.stop())
    
    manager.run()
