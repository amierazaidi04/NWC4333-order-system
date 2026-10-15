# NWC4333 Final Project: Scalable Online Order-Processing System (Option B)

**Members:**
WAN NUR AMIERA UMAMAH BINTI WAN ZAIDI 
NUR ALIYA ZULAIKHA BINTI MOHD YUSOF 
NUR FARHANA BINTI FAUZI

## What this project does
An online shop can receive many orders at the same time. This system accepts orders over TCP, queues them, processes them with a fixed pool of worker threads, keeps stock correct with locks, and logs every order in a SQLite database. It also demonstrates and fixes two concurrency problems: the race condition (overselling) and deadlock.

## Requirements
- Python 3 (tested on Python 3.13, Windows)
- No extra packages. Only the Python standard library is used.

## Files
`order_system.py`: Shared logic and demos: stock, locks, order log, race condition demo, deadlock demo, scalability test
`order_server.py`: TCP order server (accept, queue, worker pool)
`order_client.py`: Load-test client: sends many simultaneous orders and prints metrics
`results/`: Test outputs and screenshots
`docs/`: Diagrams

## How to run
All commands are run from this folder. On Windows use `py`, on Linux use `python3`.

**1. Concurrency demos (no server needed)**

```
py order_system.py
```

**2. TCP server and load test (two terminals)**

Terminal 1, start the server. The number is the worker count (default 4):

```
py order_server.py 4
```

Terminal 2, send 200 simultaneous orders:

```
py order_client.py 200
```

Stop the server with Ctrl+C. The database file `orders.db` is created automatically. Delete it between test runs so the saved count starts from zero.
