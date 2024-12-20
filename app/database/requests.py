
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



async def update_ride(rise_id:int, data:dict, session: AsyncSession ):
    # Фильтруем переданные данные, чтобы исключить None значения
    updare_data = {k: v for k, v in data.items() if v is not None}
    
    if 'location' in updare_data and isinstance(updare_data['location'], tuple):
        updare_data['location'] = json.dumps(updare_data['location'])
        
    if 'destination' in updare_data and isinstance(updare_data['destination'], tuple):
        updare_data['destination'] = json.dumps(updare_data['destination'])
        
    await session.execute(
        update(Ride).where(Ride.ride_id == rise_id).values(**updare_data)
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

