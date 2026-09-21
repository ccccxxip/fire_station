# Данные о хабах
hubs = {
    "H1": {"population": 10000, "max_time": 8},
    "H2": {"population": 5000, "max_time": 7},
    "H3": {"population": 20000, "max_time": 10},
    "H4": {"population": 3000, "max_time": 6},
}

# Время движения от каждого возможного места до каждого хаба
travel_time = {
    "A": {"H1": 4, "H2": 6, "H3": 7, "H4": 5},
    "B": {"H1": 8, "H2": 3, "H3": 9, "H4": 4},
    "C": {"H1": 5, "H2": 5, "H3": 6, "H4": 3},
}

best_site = None
best_score = float("inf")

# Проверяем каждое возможное место
for site in travel_time:

    feasible = True
    score = 0

    for hub, data in hubs.items():

        time = travel_time[site][hub]

        # Проверяем максимальное время
        if time > data["max_time"]:
            feasible = False
            break

        # Учитываем население
        score += time * data["population"]

    # Если место подходит, сравниваем его с предыдущими
    if feasible and score < best_score:
        best_score = score
        best_site = site


if best_site is not None:
    print("Оптимальное место:", best_site)
    print("Значение целевой функции:", best_score)
else:
    print("Подходящего места не найдено.")