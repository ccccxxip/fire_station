from itertools import combinations
import math
import pandas as pd

# =====================================================================
# 1. ЗАГРУЗКА И ПОДГОТОВКА ДАННЫХ ИЗ ФАЙЛОВ
# =====================================================================
hubs_df = pd.read_csv("data/hubs.csv")
locs_df = pd.read_csv("data/locations.csv")
params_df = pd.read_csv("data/parameters.csv")

# Преобразуем таблицу параметров в удобный словарь
params = dict(zip(params_df["parameter"], params_df["value"]))

BUDGET_LIMIT = float(params.get("budget", 60.0))  # Бюджет на станцию (млн руб.)
AVG_SPEED_KMH = float(params.get("avg_speed", 50.0))  # Скорость (км/ч)
SETUP_TIME_MIN = float(params.get("setup_time", 2.0))  # Время сбора (мин)
POP_GROWTH = float(params.get("population_growth", 15.0)) / 100.0  # Рост 15%

# Коэффициенты весов приоритетов районов
PRIORITY_WEIGHTS = {"critical": 3.0, "high": 2.0, "medium": 1.5, "low": 1.0}

# Флаг учета времени сбора (2 мин):
# True - с учетом выезда из депо; False - чистое время движения по слайду
USE_SETUP_TIME = False

# =====================================================================
# 2. ФИЛЬТРАЦИЯ ПЛОЩАДОК ПО БЮДЖЕТУ И СТАТУСУ
# =====================================================================
valid_locs = locs_df[
    (locs_df["status"] == "available") & (locs_df["cost_mln"] <= BUDGET_LIMIT)
].copy()

rejected_locs = locs_df[~locs_df["loc_id"].isin(valid_locs["loc_id"])]

print("=" * 80)
print("АНАЛИЗ ДОСТУПНОСТИ ПЛОЩАДОК ДЛЯ СТРОИТЕЛЬСТВА")
print("=" * 80)
print(f"Всего локаций в базе: {len(locs_df)}")
print(f"Допущено к оптимизации: {len(valid_locs)}")
for _, r in rejected_locs.iterrows():
    reason = (
        f"Статус '{r['status']}'"
        if r["status"] != "available"
        else f"Превышен бюджет ({r['cost_mln']} > {BUDGET_LIMIT} млн)"
    )
    print(f"  - Исключена площадка {r['loc_id']} ({r['address']}): {reason}")
print()

# =====================================================================
# 3. ПОСТРОЕНИЕ МАТРИЦЫ ВРЕМЕНИ T_im (МИНУТЫ)
# =====================================================================
speed_km_min = AVG_SPEED_KMH / 60.0  # км/мин (50 / 60 ≈ 0.833)

travel_time = {}
for _, loc in valid_locs.iterrows():
    loc_id = int(loc["loc_id"])
    travel_time[loc_id] = {}
    for _, hub in hubs_df.iterrows():
        hub_id = int(hub["hub_id"])
        # Евклидово расстояние между хабом и площадкой
        dist = math.hypot(
            hub["x_coord"] - loc["x_coord"], hub["y_coord"] - loc["y_coord"]
        )
        # Время доезда: время сбора + расстояние / скорость
        t = (SETUP_TIME_MIN if USE_SETUP_TIME else 0.0) + (dist / speed_km_min)
        travel_time[loc_id][hub_id] = round(t, 2)


# =====================================================================
# 4. ИТЕРАЦИОННЫЙ ПОИСК МИНИМАЛЬНОГО ЧИСЛА СТАНЦИЙ (k-step)
# =====================================================================
def solve_fire_station_placement():
    available_loc_ids = list(travel_time.keys())
    max_possible_k = len(available_loc_ids)

    print("=" * 80)
    print(f"ЗАПУСК ОПТИМИЗАЦИОННОГО ПОИСКА (РЕЖИМ SETUP_TIME: {USE_SETUP_TIME})")
    print("=" * 80)

    for k in range(1, max_possible_k + 1):
        best_combo = None
        best_score = float("inf")
        best_assignment = {}

        # Перебор всех сочетаний из M доступных по k станций
        for combo in combinations(available_loc_ids, k):
            feasible = True
            combo_score = 0
            current_assignment = {}

            for _, hub in hubs_df.iterrows():
                hub_id = int(hub["hub_id"])
                t_max = float(hub["T_max"])
                pop = float(hub["population"]) * (1.0 + POP_GROWTH)
                weight = PRIORITY_WEIGHTS.get(hub["priority"], 1.0)

                # Выбираем станцию из combo, которая ближе всего к данному хабу
                best_t_for_hub = min(travel_time[loc_id][hub_id] for loc_id in combo)
                best_station = min(
                    combo, key=lambda loc_id: travel_time[loc_id][hub_id]
                )

                # Проверка соблюдения норматива времени безопасности
                if best_t_for_hub > t_max:
                    feasible = False
                    break

                current_assignment[hub_id] = {
                    "hub_name": hub["district_name"],
                    "station_id": best_station,
                    "arrival_time": best_t_for_hub,
                    "t_max": t_max,
                    "priority": hub["priority"],
                }
                # Взвешенное время: время * население * приоритет
                combo_score += best_t_for_hub * pop * weight

            if feasible and combo_score < best_score:
                best_score = combo_score
                best_combo = combo
                best_assignment = current_assignment

        # Вывод статуса текущей итерации k
        if best_combo is not None:
            print(f"-> [k = {k}]: НАЙДЕНО ДОПУСТИМОЕ РЕШЕНИЕ СО 100% ПОКРЫТИЕМ!\n")
            print("=" * 80)
            print("ИТОГОВЫЙ ПЛАН РАЗМЕЩЕНИЯ ПОЖАРНЫХ СТАНЦИЙ")
            print("=" * 80)
            print(f"Необходимое количество станций: {k}")
            print(f"Минимальное взвешенное время: {best_score:,.2f}")
            print("\nВыбранные площадки под строительство:")
            for loc_id in best_combo:
                row = valid_locs[valid_locs["loc_id"] == loc_id].iloc[0]
                print(
                    f"  * Площадка #{loc_id} ({row['address']}): "
                    f"Стоимость = {row['cost_mln']} млн руб. | "
                    f"Водоснабжение: {row['water_supply']} | "
                    f"Подъезд: {row['road_access']}"
                )

            print("\nЗакрепление районов города за станциями:")
            print("-" * 80)
            print(
                f"{'Хаб ID':<7}{'Район города':<25}{'Станция':<12}"
                f"{'Время (мин)':<14}{'Норматив':<10}{'Статус':<8}"
            )
            print("-" * 80)
            for hub_id, info in best_assignment.items():
                print(
                    f"{hub_id:<7}{info['hub_name']:<25}№{info['station_id']:<11}"
                    f"{info['arrival_time']:<14.2f}{info['t_max']:<10.1f}OK"
                )
            print("-" * 80)
            return

        else:
            print(
                f"-> [k = {k}]: Невозможно покрыть все районы за норматив T_max. "
                "Увеличиваем k..."
            )

    print(
        "\nВнимание: При текущих жестких ограничениях полное покрытие невозможно."
    )


if __name__ == "__main__":
    solve_fire_station_placement()