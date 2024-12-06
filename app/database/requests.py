
from app.database.models import async_session, User, Ride
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
import json
from sqlalchemy.orm import selectinload
import re
from sqlalchemy.exc import IntegrityError
from datetime import datetime, time


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


async def add_ride(user_id: int, state_data: dict, session: AsyncSession):
    
    location_json = json.dumps(state_data['location'])
    destination_json = json.dumps(state_data['destination'])
    
    arrival_time_str = state_data['arrival_time']
    
    if not validate_arrival_time(arrival_time_str):
        raise ValueError("Неверный формат времени. Используйте чч:мм (например, 14:30).")
    
    arrival_time_obj = parse_time(arrival_time_str)


    ride = Ride(
        user_id=user_id,
        location=location_json,
        destination=destination_json,
        arrival_time=arrival_time_obj,
        transport=state_data['transport'],
        notify_time_delta=state_data['notify_time_delta']
    )
    session.add(ride)
    await session.commit()


async def get_user_rides(tg_id: int, session: AsyncSession):
    result = await session.execute(select(User).where(User.tg_id == tg_id).options(selectinload(User.rides)))
    user = result.scalar_one_or_none()
    if user:
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
