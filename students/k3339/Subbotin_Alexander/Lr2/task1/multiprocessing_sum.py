import multiprocessing
import os
import time

TOTAL_NUMBER = 1_000_000_000
NUM_PROCESSES = os.cpu_count() or 4


def calculate_sum(start: int, end: int) -> int:
    total = 0
    for i in range(start, end + 1):
        total += i
    return total


def main() -> None:
    print(f"=== Multiprocessing: сумма от 1 до {TOTAL_NUMBER:_} ===")
    print(f"Процессов: {NUM_PROCESSES}")

    chunk_size = TOTAL_NUMBER // NUM_PROCESSES
    ranges: list[tuple[int, int]] = []

    for i in range(NUM_PROCESSES):
        start = i * chunk_size + 1
        end = (i + 1) * chunk_size if i < NUM_PROCESSES - 1 else TOTAL_NUMBER
        ranges.append((start, end))

    start_time = time.time()

    with multiprocessing.Pool(NUM_PROCESSES) as pool:
        results = pool.starmap(calculate_sum, ranges)

    total = sum(results)
    elapsed = time.time() - start_time

    expected = TOTAL_NUMBER * (TOTAL_NUMBER + 1) // 2
    print(f"Результат:  {total}")
    print(f"Ожидаемый:  {expected}")
    print(f"Совпадение: {total == expected}")
    print(f"Время:      {elapsed:.4f} сек")


if __name__ == "__main__":
    main()
