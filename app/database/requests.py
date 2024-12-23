
from app.database.models import async_session, User, Ride
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
import json
from sqlalchemy.orm import selectinload
import re
from sqlalchemy.exc import IntegrityError
from datetime import datetime, time
from math import ceil

import app.api as ap

import aiohttp
import json

async def get_user_settings(tg_id: int, session: AsyncSession):
    result = await session.execute(select(User).where(User.tg_id == tg_id))
    user = result.scalar_one_or_none()
    if user:
        return user.notification_bufer
    return -1


async def set_user_settings(tg_id: int, new_notification_buffer: int,  session: AsyncSession):
    result = await session.execute(select(User).where(User.tg_id == tg_id))
    user = result.scalar()
    print(user)
    user.notification_bufer = new_notification_buffer
    await session.commit()

async def get_user_by_tg_id(user_id: int, session: AsyncSession):
    result = await session.execute(select(User).where(User.tg_id == user_id))
    return result.scalar_one_or_none()


async def add_user(user_id: int, session: AsyncSession):
    user = User(tg_id=user_id)
    session.add(user)
    await session.commit()


async def add_ride(tg_id, state_data, session, api_key_2gis):
    location_json = json.dumps(state_data['location'])
    destination_json = json.dumps(state_data['destination'])
    
    transport_type = state_data["transport"]  
    arrival_time_str = state_data['arrival_time']
    
    arrival_time_obj = parse_time(arrival_time_str)
    
    route_info = ap.calc_time(api_key_2gis, state_data['location'], state_data['destination'], state_data["transport_api_format"])

    ride = Ride(
        location=location_json,
        destination=destination_json,
        transport=transport_type,
        arrival_time=arrival_time_obj,
        notify_time_delta=state_data["notify_time_delta"],
        location_text=state_data.get('location_text', 'Неизвестное место отправления'),
        destination_text=state_data.get('destination_text', 'Неизвестное место назначения'),
        tg_id=tg_id,
        path=route_info.get('path'),
        ride_time=route_info.get('total_duration'),
    )

    session.add(ride)
    await session.commit()

async def calc_notification_time(arrival_time, ride_time, notify_time_delta, notification_buffer):
    total_ride_length = (ride_time + notify_time_delta) * (1 + 1 / notification_buffer)
    return arrival_time - total_ride_length

async def get_user_rides(tg_id: int, session: AsyncSession):    
    result = await session.execute(select(User).where(User.tg_id == tg_id).options(selectinload(User.rides)))
    
    user = result.scalar_one_or_none()
    if user:
        for ride in user.rides:
            return user.rides    
    return []



async def update_ride(ride_id: int, data: dict, session: AsyncSession, api_key_2gis, api_key_geocoder):
    # Фильтруем переданные данные, чтобы исключить None значения
    update_data = {k: v for k, v in data.items() if v is not None}
    
    # Проверка, нужно ли пересчитывать маршрут или адреса
    if 'location' in update_data or 'destination' in update_data or 'transport' in update_data:
        async with session.begin():
            ride = await session.get(Ride, ride_id)
            if ride:
                new_location = update_data.get('location', ride.location)
                new_destination = update_data.get('destination', ride.destination)
                
                if isinstance(new_location, str):
                    new_location = json.loads(new_location)
                if isinstance(new_destination, str):
                    new_destination = json.loads(new_destination)

                if not isinstance(new_location, (list, tuple)) or len(new_location) != 2:
                    raise ValueError(f"Invalid location format: {new_location}")
                if not isinstance(new_destination, (tuple, list)) or len(new_destination) != 2:
                    raise ValueError(f"Invalid destination format: {new_destination}")
                
                new_location_text = ap.get_address_from_coordinates(api_key_geocoder, new_location[0], new_location[1])
                new_destination_text = ap.get_address_from_coordinates(api_key_geocoder, new_destination[0], new_destination[1])
                
                update_data['location_text'] = new_location_text
                update_data['destination_text'] = new_destination_text
                
                state_data = {
                    'location': (new_location[0], new_location[1]),
                    'destination': (new_destination[0], new_destination[1]),
                    'transport': update_data.get('transport', ride.transport)
                }
                if state_data['transport'] == "Общественный транспорт":
                    transport_type = "public_transport"
                elif state_data['transport'] == "Автомобиль":
                    transport_type = "car"
                elif state_data['transport'] == "Пешком":
                    transport_type = "walk"
                route_info = ap.calc_time(api_key_2gis, state_data['location'], state_data['destination'], transport_type)
                
                update_data['ride_time'] = route_info.get("total_duration")
                update_data['path'] = route_info.get("path")
    
    await session.execute(
        update(Ride).where(Ride.ride_id == ride_id).values(**update_data)
    )
    await session.commit()
    
    
async def delete_ride(ride_id: int, session: AsyncSession):
    await session.execute(delete(Ride).where(Ride.ride_id == ride_id))
    await session.commit()


# Функция валидации времени в формате чч:мм
def validate_arrival_time(time_str: str) -> bool:
    pattern = r'^[0-2][0-9]:[0-5][0-9]$'
    return bool(re.match(pattern, time_str))


# Преобразование строки в объект времени
def parse_time(time_str: str) -> time:
    return datetime.strptime(time_str, "%H:%M").time()

def calc_notification_time(arrival_time, ride_time, notify_time_delta, notification_buffer):
    arrival_time_minutes = arrival_time.hour * 60 + arrival_time.minute
    total_ride_length = ceil((ride_time + notify_time_delta) * (1 + 1 / notification_buffer))
    time_to_notify_minutes = arrival_time_minutes - total_ride_length
    notification_time = time(time_to_notify_minutes // 60, time_to_notify_minutes % 60)

    return datetime.combine(datetime.now().date(), notification_time)

