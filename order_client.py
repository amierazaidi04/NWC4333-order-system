import random
import socket
import sys
import threading
import time

HOST, PORT = "127.0.0.1", 5003
NUM_ORDERS = int(sys.argv[1]) if len(sys.argv) > 1 else 200
results = []
lock = threading.Lock()


def customer(i):
    start = time.perf_counter()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(10)
        s.connect((HOST, PORT))
        s.send(f"ORDER|item{random.randint(0, 4)}|1".encode())
        reply = s.recv(1024).decode()
        s.close()

        with lock:
            results.append((reply.split("|")[0], time.perf_counter() - start))
    except Exception:
        with lock:
            results.append(("NET_ERROR", time.perf_counter() - start))


if __name__ == "__main__":
    t0 = time.perf_counter()
    threads = [threading.Thread(target=customer, args=(i,)) for i in range(NUM_ORDERS)]

    print(f"Spawning {NUM_ORDERS} client connections simultaneously...")
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    total = time.perf_counter() - t0

    if results:
        ok = sum(1 for r, _ in results if r == "ORDER_OK")
        errors = sum(1 for r, _ in results if r == "NET_ERROR")
        avg = sum(t for _, t in results) / len(results)
        print(f"\n[METRICS] orders={NUM_ORDERS} | OK={ok} | network errors={errors} | "
              f"total time={total:.2f}s | throughput={NUM_ORDERS/total:.0f} orders/s | "
              f"avg response={avg*1000:.0f} ms")
