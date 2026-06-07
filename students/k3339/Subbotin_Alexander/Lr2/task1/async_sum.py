import asyncio
import os
import time

TOTAL_NUMBER = 1_000_000_000
NUM_TASKS = os.cpu_count() or 4


async def calculate_sum(start: int, end: int) -> int:
    total = 0
    for i in range(start, end + 1):
        total += i
    return total


async def main() -> None:
    print(f"=== Async: сумма от 1 до {TOTAL_NUMBER:_} ===")
    print(f"Задач: {NUM_TASKS}")

    chunk_size = TOTAL_NUMBER // NUM_TASKS
    tasks: list[asyncio.Task[int]] = []

    start_time = time.time()

    for i in range(NUM_TASKS):
        start = i * chunk_size + 1
        end = (i + 1) * chunk_size if i < NUM_TASKS - 1 else TOTAL_NUMBER
        tasks.append(asyncio.create_task(calculate_sum(start, end)))

    results = await asyncio.gather(*tasks)
    total = sum(results)
    elapsed = time.time() - start_time

    expected = TOTAL_NUMBER * (TOTAL_NUMBER + 1) // 2
    print(f"Результат:  {total}")
    print(f"Ожидаемый:  {expected}")
    print(f"Совпадение: {total == expected}")
    print(f"Время:      {elapsed:.4f} сек")


if __name__ == "__main__":
    asyncio.run(main())
