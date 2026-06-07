import os
import threading
import time

TOTAL_NUMBER = 1_000_000_000
NUM_THREADS = os.cpu_count() or 4


def calculate_sum(start: int, end: int, results: list[int], index: int) -> None:
    total = 0
    for i in range(start, end + 1):
        total += i
    results[index] = total


def main() -> None:
    print(f"=== Threading: сумма от 1 до {TOTAL_NUMBER:_} ===")
    print(f"Потоков: {NUM_THREADS}")

    chunk_size = TOTAL_NUMBER // NUM_THREADS
    threads: list[threading.Thread] = []
    results = [0] * NUM_THREADS

    start_time = time.time()

    for i in range(NUM_THREADS):
        start = i * chunk_size + 1
        end = (i + 1) * chunk_size if i < NUM_THREADS - 1 else TOTAL_NUMBER
        t = threading.Thread(target=calculate_sum, args=(start, end, results, i))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    total = sum(results)
    elapsed = time.time() - start_time

    expected = TOTAL_NUMBER * (TOTAL_NUMBER + 1) // 2
    print(f"Результат:  {total}")
    print(f"Ожидаемый:  {expected}")
    print(f"Совпадение: {total == expected}")
    print(f"Время:      {elapsed:.4f} сек")


if __name__ == "__main__":
    main()
