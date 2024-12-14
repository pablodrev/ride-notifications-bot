import requests
import json

# Функция для получения координат по адресу
def get_coordinates(api_key, address):
    url = "https://geocode-maps.yandex.ru/1.x/"
    params = {"apikey": api_key, "geocode": address, "format": "json"}
    response = requests.get(url, params=params)
    data = response.json()
    coordinates = data['response']['GeoObjectCollection']['featureMember'][0]['GeoObject']['Point']['pos']
    return map(float, coordinates.split())


# Объединенная функция для расчета времени маршрута
def calc_time(api_key_2gis, origin_coords, destination_coords, transport_type):
    if transport_type == 'public_transport':
        url = f"https://routing.api.2gis.com/public_transport/2.0?key={api_key_2gis}"
        headers = {"Content-Type": "application/json"}
        content = {
            "locale": "ru",
            "source": {
                "name": "Point A",
                "point": {"lat": float(origin_coords[0]), "lon": float(origin_coords[1])}
            },
            "target": {
                "name": "Point B",
                "point": {"lat": float(destination_coords[0]), "lon": float(destination_coords[1])}
            },
            "transport": [
                "pedestrian", "metro", "light_metro", "suburban_train", "aeroexpress", "tram", "bus", "trolleybus",
                "shuttle_bus", "monorail", " funicular_railway", "river_transport", "cable_car", "light_rail", "premetro",
                "mcc", "mcd"
            ]
        }
        response = requests.post(url, data=json.dumps(content), headers=headers)
        route_data = response.json()

        if not route_data or not isinstance(route_data, list):
            return "Маршрут не найден."

        # Выбираем первый маршрут (самый короткий)
        shortest_route = route_data[0]
        movements = []
        total_duration = 0

        for movement in shortest_route['movements']:
            mode = "пешком" if movement['type'] == 'walkway' else movement['type']
            distance = movement['distance']
            duration = movement['moving_duration']
            total_duration += duration
            if distance == 0 and duration == 0:
                continue
            if 'routes' in movement and movement['routes']:
                transport = ', '.join([f"{r['subtype_name']} {', '.join(r['names'])}" for r in movement['routes']])
                movements.append(f"{transport} ({distance} м, {duration // 60} мин)")
            else:
                movements.append(f"{mode} ({distance} м, {duration // 60} мин)")

        #response_message = f"Самый короткий маршрут займет {total_duration // 60} минут:\n"
        #response_message += " -> ".join(movements)
        # return response_message
        return {"path": " -> ".join(movements),
            "total_duration": total_duration,}

    elif transport_type == 'car':
        url = f"https://routing.api.2gis.com/carrouting/6.0.0/global?key={api_key_2gis}"
        headers = {"Content-Type": "application/json"}
        content = {
            "points": [
                {"type": "walking", "x": float(origin_coords[1]), "y": float(origin_coords[0])},
                {"type": "walking", "x": float(destination_coords[1]), "y": float(destination_coords[0])}
            ]
        }
        response = requests.post(url, data=json.dumps(content), headers=headers)
        print(response)
        response.raise_for_status()
        route_data = response.json()
        try:
            print(0)
        except requests.exceptions.HTTPError as http_err:
            return f"HTTP ошибка: {http_err}"
        except requests.exceptions.RequestException as req_err:
            return f"Ошибка запроса: {req_err}"
        except json.JSONDecodeError:
            return "Ошибка декодирования JSON ответа."
        except Exception as err:
            return f"Другая ошибка: {err}"

        if not route_data or not isinstance(route_data, dict):
            return "Маршрут на автомобиле не найден."

        car_route = route_data['result'][0]
        total_duration_car = car_route['total_duration'] // 60
        total_distance_car = car_route['total_distance']

        # return f"На автомобиле: {total_duration_car} минут, {total_distance_car} метров.\n"
        return {
            "total_duration": total_duration_car,
            "total_distance": total_distance_car,
            "path": f"Автомобильный маршрут {total_distance_car}"
        }

    elif transport_type == 'walk':
        url = f"https://routing.api.2gis.com/carrouting/6.0.0/global?key={api_key_2gis}"
        headers = {"Content-Type": "application/json"}
        content = {
            "points": [
                {"type": "walking", "x": float(origin_coords[1]), "y": float(origin_coords[0])},
                {"type": "walking", "x": float(destination_coords[1]), "y": float(destination_coords[0])}
            ],
            "type": "pedestrian"
        }
        try:
            response = requests.post(url, data=json.dumps(content), headers=headers)
            response.raise_for_status()
            route_data = response.json()
        except requests.exceptions.HTTPError as http_err:
            return f"HTTP ошибка: {http_err}"
        except requests.exceptions.RequestException as req_err:
            return f"Ошибка запроса: {req_err}"
        except json.JSONDecodeError:
            return "Ошибка декодирования JSON ответа."
        except Exception as err:
            return f"Другая ошибка: {err}"

        if not route_data or not isinstance(route_data, dict):
            return "Маршрут пешком не найден."

        walk_route = route_data['result'][0]
        total_duration_walk = walk_route['total_duration'] // 60
        total_distance_walk = walk_route['total_distance']

        #return f"Пешком: {total_duration_walk} минут, {total_distance_walk} метров.\n"
        return {
            "total_duration": total_duration_walk,
            "total_distance": total_distance_walk,
            "path": f"Пешеходный маршрут {total_distance_walk}"
        }


def get_address_from_coordinates(api_key, latitude, longitude):
    url = "https://geocode-maps.yandex.ru/1.x/"
    params = {"apikey": api_key, "geocode": f"{longitude},{latitude}", "format": "json"}
    response = requests.get(url, params=params)
    data = response.json()
    
    # Получаем адрес из данных ответа
    try:
        address = data['response']['GeoObjectCollection']['featureMember'][0]['GeoObject']['metaDataProperty']['GeocoderMetaData']['text']
    except (KeyError, IndexError):
        address = "Неизвестно"
    
    return address