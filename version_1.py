from pulp import LpProblem, LpMinimize, LpVariable, lpSum, LpStatus


# Хабы
hubs = {
    "H1": {"population": 10000, "max_time": 8},
    "H2": {"population": 5000, "max_time": 7},
    "H3": {"population": 20000, "max_time": 10},
    "H4": {"population": 3000, "max_time": 6},
}

# Возможные места строительства
sites = ["A", "B", "C"]

# Время движения от места до хаба
travel_time = {
    "A": {"H1": 4, "H2": 6, "H3": 7, "H4": 5},
    "B": {"H1": 8, "H2": 3, "H3": 9, "H4": 4},
    "C": {"H1": 5, "H2": 5, "H3": 6, "H4": 3},
}


# Создаем задачу минимизации
model = LpProblem(
    "Fire_Station_Location",
    LpMinimize
)


# Бинарные переменные
# z[A] = 1 → строим станцию в A
# z[A] = 0 → не строим
z = {
    site: LpVariable(
        f"z_{site}",
        cat="Binary"
    )
    for site in sites
}


# Целевая функция
# Минимизируем время с учетом населения
model += lpSum(
    hubs[hub]["population"]
    * travel_time[site][hub]
    * z[site]
    for site in sites
    for hub in hubs
)


# Должна быть выбрана ровно одна станция
model += lpSum(z[site] for site in sites) == 1


# Ограничение максимального времени
for hub in hubs:

    model += lpSum(
        travel_time[site][hub] * z[site]
        for site in sites
    ) <= hubs[hub]["max_time"]


# Запускаем решение
model.solve()


# Вывод результата
print("Статус:", LpStatus[model.status])

for site in sites:
    if z[site].value() == 1:
        print("Построить станцию в:", site)

print("Значение целевой функции:", model.objective.value())