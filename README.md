# NWC4333 Final Project: Scalable Online Order-Processing System (Option B)

Network Administration, UPTM. Group project (3 members).

**Members:** [Amiera] | [Aliya] | [Farhana]

## What this project does

An online shop can receive many orders at the same time. This system accepts orders over TCP, queues them, processes them with a fixed pool of worker threads, keeps stock correct with locks, and logs every order in a SQLite database. It also demonstrates and fixes two concurrency problems: the race condition (overselling) and deadlock.

## Requirements

- Python 3 (tested on Python 3.13, Windows)
- No extra packages. Only the Python standard library is used.

## Files

| File | Purpose |
|---|---|
| `order_system.py` | Shared logic and demos: stock, locks, order log, race condition demo, deadlock demo, scalability test |
| `order_server.py` | TCP order server (producer-consumer: accept, queue, worker pool) |
| `order_client.py` | Load-test client: sends many simultaneous orders and prints metrics |
| `config/` | [Member A: configuration files. Delete this row if the team has none] |
| `results/` | Test outputs and screenshots |
| `docs/` | Diagrams |

## How to run

All commands are run from this folder. On Windows use `py`, on Linux use `python3`.

**1. Concurrency demos (no server needed)**

```
py order_system.py
```

Prints three experiments: race condition with and without a lock, deadlock with and without lock ordering, and speedup with 1, 2, 4 and 8 workers.

**2. TCP server and load test (two terminals)**

Terminal 1, start the server. The number is the worker count (default 4):

```
py order_server.py 4
```

Terminal 2, send 200 simultaneous orders:

```
py order_client.py 200
```

Stop the server with Ctrl+C. It saves the orders and prints the count. The database file `orders.db` is created automatically. Delete it between test runs so the saved count starts from zero.

To see the activity of each request, set `VERBOSE = True` near the top of `order_server.py`.

## Message protocol

Format: `COMMAND|DATA`

```
Request: ORDER|item0|2
Reply:   ORDER_OK|item0|98   or   ORDER_REJECTED|item0|out of stock

Request: STOCK
Reply:   STOCK|item0=...|item1=...

Anything else
Reply:   ERROR|Invalid command
```

## Design summary

- **Producer-consumer:** the server accepts connections and puts them in a queue. A fixed number of worker threads take them out and process them.
- **Synchronisation:** one lock per product, so orders for different products run in parallel.
- **Deadlock prevention:** locks are always taken in sorted order.
- **Database:** one writer thread owns the SQLite connection, so workers never wait for the database.
- Database delay is simulated (`DB_LATENCY` in `order_system.py`).

## Test results

Test outputs and screenshots are in `results/`. Summary (update these numbers if you rerun the tests):

| Test | Result |
|---|---|
| Race condition, no lock | 222 of 400 orders were lost updates |
| Race condition, with lock | 0 lost updates |
| Deadlock, no lock ordering | 25 of 100 completed, 75 deadlock timeouts |
| Deadlock, sorted lock order | 100 of 100 completed, 0 timeouts |
| Scalability, 1 to 8 workers | 376 to 1493 orders/s (3.98x speedup) |

## Limitations

- Server and clients run on one computer, so there is no real network delay.
- Python's GIL limits CPU-bound parallelism. The speedup here is real because the simulated work is mostly waiting.
- Queued orders are lost if the server is stopped.
