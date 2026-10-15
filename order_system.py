import queue
import random
import sqlite3
import threading
import time

DB_LATENCY = 0.002 


def new_stock(items=5, qty=100):
    return {f"item{i}": qty for i in range(items)}


def make_orders(n, items=5, multi=False, seed=1):
    rnd = random.Random(seed)
    names = [f"item{i}" for i in range(items)]
    if multi:
        return [[(i, 1) for i in rnd.sample(names, 2)] for _ in range(n)]
    return [(rnd.choice(names), 1) for _ in range(n)]


class OrderLog:

    def __init__(self, path=":memory:"):
        self.q = queue.Queue()
        self.path = path
        self.count = 0
        self.ready = threading.Event()
        self.t = threading.Thread(target=self._run, daemon=True)
        self.t.start()
        self.ready.wait(1)

    def _run(self):
        con = sqlite3.connect(self.path)
        con.execute("CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY, item TEXT, qty INT, status TEXT)")
        self.ready.set()
        while True:
            row = self.q.get()
            if row is None:
                break
            con.execute("INSERT INTO orders(item, qty, status) VALUES (?,?,?)", row)
        con.commit()
        self.count = con.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        con.close()

    def add(self, item, qty, status):
        self.q.put((item, qty, status))

    def close(self):
        self.q.put(None)
        self.t.join()
        return self.count


def process_orders(order_list, num_workers=4, stock=None, use_lock=True, log=None):
    stock = stock if stock is not None else new_stock()
    locks = {k: threading.Lock() for k in stock}
    q = queue.Queue()
    stats = {"ok": 0, "rejected": 0}
    stats_lock = threading.Lock()

    def worker():
        while True:
            order = q.get()
            if order is None:
                return
            item, qty = order
            if use_lock:
                with locks[item]:
                    ok = _take(stock, item, qty)
            else:
                ok = _take(stock, item, qty)
            if log:
                log.add(item, qty, "OK" if ok else "REJECTED")
            with stats_lock:
                stats["ok" if ok else "rejected"] += 1

    threads = [threading.Thread(target=worker) for _ in range(num_workers)]
    for t in threads:
        t.start()
    for o in order_list:
        q.put(o)
    for _ in threads:
        q.put(None)
    for t in threads:
        t.join()
    return stock, stats


def _take(stock, item, qty):
    current = stock[item]            
    time.sleep(DB_LATENCY)           
    if current >= qty:
        stock[item] = current - qty  
        return True
    return False


def process_multi(order_list, num_workers=4, ordered=False, timeout=0.1):
    stock = new_stock(qty=10_000)
    locks = {k: threading.Lock() for k in stock}
    q = queue.Queue()
    stats = {"done": 0, "deadlock_timeouts": 0}
    sl = threading.Lock()

    def worker():
        while True:
            order = q.get()
            if order is None:
                return
            items = sorted(order) if ordered else list(order)
            first, second = items[0][0], items[1][0]
            if not (locks[first].acquire() if ordered else locks[first].acquire(timeout=timeout)):
                with sl:
                    stats["deadlock_timeouts"] += 1
                continue
            try:
                time.sleep(0.001) 
                if not (locks[second].acquire() if ordered else locks[second].acquire(timeout=timeout)):
                    with sl:
                        stats["deadlock_timeouts"] += 1
                    continue
                try:
                    for item, qty in order:
                        stock[item] -= qty
                    with sl:
                        stats["done"] += 1
                finally:
                    locks[second].release()
            finally:
                locks[first].release()

    threads = [threading.Thread(target=worker) for _ in range(num_workers)]
    for t in threads:
        t.start()
    for o in order_list:
        q.put(o)
    for _ in threads:
        q.put(None)
    for t in threads:
        t.join()
    return stats


def demo_race():
    print("\n=== 1. Race condition (no lock) vs lock ===")
    orders = make_orders(400)
    for use_lock in (False, True):
        start_stock = new_stock()
        total_before = sum(start_stock.values())
        stock, stats = process_orders(orders, num_workers=8, stock=start_stock, use_lock=use_lock)
        sold_expected = sum(q for _, q in orders)
        remaining = sum(stock.values())
        actual_sold = total_before - remaining
        print(f"lock={use_lock!s:5} | orders={sold_expected} | stock actually removed={actual_sold} "
              f"| lost updates={sold_expected - actual_sold}")


def demo_deadlock():
    print("\n=== 2. Deadlock vs lock ordering ===")
    orders = make_orders(100, multi=True)
    for ordered in (False, True):
        t0 = time.perf_counter()
        s = process_multi(orders, num_workers=8, ordered=ordered)
        dt = time.perf_counter() - t0
        print(f"lock ordering={ordered!s:5} | completed={s['done']} | "
              f"deadlock timeouts={s['deadlock_timeouts']} | time={dt:.2f}s")


def demo_scalability():
    print("\n=== 3. Scalability (workers vs throughput) ===")
    orders = make_orders(1000)
    base = None
    for w in (1, 2, 4, 8):
        log = OrderLog()
        t0 = time.perf_counter()
        _, stats = process_orders(orders, num_workers=w, stock=new_stock(qty=10_000), log=log)
        dt = time.perf_counter() - t0
        saved = log.close()
        tput = len(orders) / dt
        base = base or tput
        print(f"workers={w} | time={dt:.2f}s | throughput={tput:.0f} orders/s "
              f"| speedup={tput / base:.2f}x | saved to DB={saved}")


if __name__ == "__main__":
    demo_race()
    demo_deadlock()
    demo_scalability()
