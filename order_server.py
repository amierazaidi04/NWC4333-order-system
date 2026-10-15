import socket
import sys
import threading
import time
from queue import Queue

from order_system import OrderLog, new_stock, DB_LATENCY

HOST, PORT = "127.0.0.1", 5003
NUM_WORKERS = int(sys.argv[1]) if len(sys.argv) > 1 else 4
VERBOSE = False

stock = new_stock(qty=10_000)
locks = {k: threading.Lock() for k in stock}
task_queue = Queue()
log = OrderLog("orders.db")


def handle_request(conn, addr):
    try:
        message = conn.recv(1024).decode().strip()
        if not message:
            return

        parts = message.split("|")
        cmd = parts[0].upper()

        if cmd == "ORDER" and len(parts) == 3 and parts[1] in stock and parts[2].isdigit() and int(parts[2]) > 0:
            item, qty = parts[1], int(parts[2])
            with locks[item]:                      
                time.sleep(DB_LATENCY)             
                if stock[item] >= qty:
                    stock[item] -= qty
                    reply, status = f"ORDER_OK|{item}|{stock[item]}", "OK"
                else:
                    reply, status = f"ORDER_REJECTED|{item}|out of stock", "REJECTED"
            log.add(item, qty, status)

        elif cmd == "STOCK":
            reply = "STOCK|" + "|".join(f"{k}={v}" for k, v in stock.items())
        elif cmd == "ORDER" and len(parts) == 3 and parts[1] not in stock:
            reply = "ERROR|Invalid product"
        else:
            reply = "ERROR|Invalid command"

        conn.send(reply.encode())
        if VERBOSE:
            print(f"[{threading.current_thread().name}] {addr} -> {reply}")
    except Exception as e:
        print(f"Connection error with {addr}: {e}")
    finally:
        conn.close()


def worker():
    while True:
        conn, addr = task_queue.get()
        try:
            handle_request(conn, addr)
        finally:
            task_queue.task_done()


if __name__ == "__main__":
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(128)
    
    server.settimeout(1.0)  
    
    print(f"[LISTENING] Order server running on {HOST}:{PORT}")
    print(f"Workers: {NUM_WORKERS}")

    for i in range(NUM_WORKERS):
        threading.Thread(target=worker, name=f"Worker-{i+1}", daemon=True).start()

    try:
        while True:
            try:
                conn, addr = server.accept()
                task_queue.put((conn, addr))
                if VERBOSE:
                    print(f"New client: {addr} | Queue size: {task_queue.qsize()}")
            except socket.timeout:
                continue  
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] KeyboardInterrupt received!")
    finally:
        print("Shutting down server safely...")
        server.close()
        import os
        print("Orders saved inside database:", log.close())
        os._exit(0)
