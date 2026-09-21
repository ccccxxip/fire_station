import csv
import math
import os
from pulp import LpProblem, LpMinimize, LpVariable, lpSum, LpStatus, value

# --- 1. Чтение данных из CSV файлов ---
# Файлы лежат в папке data

DATA_DIR = 'data'

def read_csv(filename):
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)

locations_data = read_csv('locations.csv')
hubs_data = read_csv('hubs.csv')
params_data = read_csv('parameters.csv')

# Парсинг параметров
params = {row['parameter']: float(row['value']) for row in params_data}
BUDGET_LIMIT = params['budget']
AVG_SPEED = params['avg_speed']
SETUP_TIME = params['setup_time']
K = int(params['k'])

# Формирование словарей хабов и локаций
hubs = {}
for row in hubs_data:
    hub_id = f"H{row['hub_id']}"
    hubs[hub_id] = {
        "x": float(row['x_coord']),
        "y": float(row['y_coord']),
        "population": int(row['population']),
        "max_time": float(row['T_max']),
        "priority": row['priority'],
        "district": row['district_name']
    }

sites = {}
for row in locations_data:
    site_id = f"S{row['loc_id']}"
    sites[site_id] = {
        "x": float(row['x_coord']),
        "y": float(row['y_coord']),
        "cost": float(row['cost_mln']),
        "status": row['status'],
        "water_supply": row['water_supply'],
        "road_access": row['road_access'],
        "address": row['address']
    }

# --- 2. Расчет матрицы времени в пути ---
travel_time = {}
for s_id, s_data in sites.items():
    travel_time[s_id] = {}
    for h_id, h_data in hubs.items():
        distance_km = math.sqrt((s_data['x'] - h_data['x'])**2 + (s_data['y'] - h_data['y'])**2)
        time_min = (distance_km / AVG_SPEED) * 60 + SETUP_TIME
        travel_time[s_id][h_id] = round(time_min, 2)

# --- 3. Построение модели PuLP ---
model = LpProblem("Fire_Station_Optimization", LpMinimize)

z = {s_id: LpVariable(f"z_{s_id}", cat="Binary") for s_id in sites}

# Целевая функция: минимизация взвешенного времени
model += lpSum(
    travel_time[s][h] * hubs[h]["population"] * z[s]
    for s in sites for h in hubs
), "Total_Weighted_Response_Time"

# Ограничение 1: Бюджет
model += lpSum(sites[s]["cost"] * z[s] for s in sites) <= BUDGET_LIMIT, "Budget_Constraint"

# Ограничение 2: Максимальное время прибытия для каждого хаба
for h_id, h_data in hubs.items():
    model += lpSum(
        travel_time[s][h_id] * z[s] for s in sites
    ) <= h_data["max_time"], f"MaxTime_{h_id}"

# Ограничение 3: Только доступные локации
for s_id, s_data in sites.items():
    if s_data['status'] != 'available':
        model += z[s_id] == 0, f"Unavailable_{s_id}"

# Ограничение 4: Ровно K станций
model += lpSum(z[s] for s in sites) == K, "Exact_Stations_Count"

# --- 4. Решение и вывод результатов ---
model.solve()

print(f"\nСтатус решения: {LpStatus[model.status]}")

if model.status == 1:
    print(f"Общее взвешенное время: {value(model.objective)}")
    total_cost = sum(sites[s]['cost'] * z[s].varValue for s in sites)
    print(f"Затраченный бюджет: {total_cost} млн руб.")
    
    print("\nРекомендуемые станции к строительству:")
    for s_id in sites:
        if z[s_id].varValue == 1:
            print(f"  ✅ {s_id} | Адрес: {sites[s_id]['address']} | "
                  f"Стоимость: {sites[s_id]['cost']} млн | "
                  f"Дороги: {sites[s_id]['road_access']} | Вода: {sites[s_id]['water_supply']}")
    
    print(f"\nИтого затрачено: {total_cost} / {BUDGET_LIMIT} млн руб.")
else:
    print("️ Оптимальное решение не найдено!")
    print("При K=1 невозможно выбрать одну станцию, которая покроет все хабы в пределах T_max.")
    print("Попробуйте увеличить K до 2 или 3 в файле parameters.csv")