import logging
from aiogram import F, Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove, ContentType
import json


from datetime import datetime, timezone

import app.keyboards as kb
import app.database.requests as rq
from app.database.requests import async_session 


router = Router()

# TODO:
# Работа с временем: проверка, чтобы введенное время было больше нынешнего, с учетом часовых поясов
# Проверка введенных данных
# Помечать прошедшие поездки
# Настройки
# Отправка геолокации двумя способами: по кнопке или введя адрес вручную
# Красивые иконки
# 


class NewRideStates(StatesGroup):
    location = State()
    destination = State()
    destination_input = State()
    arrival_time = State()
    transport = State()
    notify_time_delta = State()

choose_mode = State()

class EditStates(StatesGroup):
    ride_id = State()
    parameter_to_edit = State()
    location = State()
    destination = State()
    arrival_time = State()
    transport = State()
    notify_time_delta = State()


rides = {}
user_coordinates = {}


@router.message(CommandStart())
@router.message(choose_mode, F.text == "Назад")
async def cmd_start(message: Message, state:FSMContext):
    await message.answer("Привет, это бот для напоминания о поездках! Выбери пункт в меню.", reply_markup=kb.main)


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer("Help message")   


@router.message(F.text == "Новая поездка")
async def cmd_new_ride(message: Message, state: FSMContext):
    await state.set_state(NewRideStates.location)
    await message.answer("Для создания поездки необходимо знать точку отправления.", reply_markup=kb.location)


@router.message(F.text == "Мои поездки")
async def cmd_my_rides(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    async with async_session() as session:
        user_rides = await rq.get_user_rides(user_id, session)

    if not user_rides:
        await message.answer(
            'У вас нет сохраненных поездок.\nЧтобы создать поездку, выберите пункт меню "Новая поездка"',
            reply_markup=kb.main
        )
        return

    answer = 'Ваши сохраненные поездки:\n'
    for count, ride in enumerate(user_rides, start=1):
        # Преобразуем JSON в обычный формат
        location = json.loads(ride.location)
        destination = json.loads(ride.destination)
        
        answer += (
            f"\n{count}. Место отправления: {location}\n"
            f"Место назначения: {destination}\n"
            f"Время прибытия: {ride.arrival_time}\n"
            f"Транспортное средство: {ride.transport}\n"
            f"Время до уведомления: {ride.notify_time_delta} минут(ы)\n"
        )

    await message.answer(answer, reply_markup=kb.edit_delete_back)


    

@router.message(choose_mode, F.text == "Редактировать")
async def edit_ride(message: Message, state: FSMContext):
     await state.update_data(choose_mode="edit")
     await state.set_state(EditStates.ride_id)
     await message.answer("Введите номер поездки", reply_markup=ReplyKeyboardRemove())

@router.message(choose_mode, F.text == "Удалить")
async def delete_ride(message: Message, state: FSMContext):
     await state.update_data(choose_mode="delete")
     await state.set_state(EditStates.ride_id)
     await message.answer("Введите номер поездки", reply_markup=ReplyKeyboardRemove())


# Редактирование поездки

@router.message(EditStates.ride_id)
async def process_edit_ride_id(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    try:
        ride_id = int(message.text)
    except ValueError:
        await message.answer("Введите корректный номер поездки (целое число).")
        return

    async with async_session() as session:
        user_rides = await rq.get_user_rides(user_id, session)

        if not user_rides or ride_id < 1 or ride_id > len(user_rides):
            await message.answer("Неправильный номер поездки.")
            return

        selected_ride = user_rides[ride_id - 1]

        selected_ride_id = selected_ride.ride_id
        await state.update_data(ride_id=selected_ride_id)

        state_data = await state.get_data()
        if state_data["choose_mode"] == "delete":
            await rq.delete_ride(selected_ride_id, session)
            await state.clear()
            await message.answer(f"Поездка номер {ride_id} удалена.", reply_markup=kb.main)
        else:
            await state.set_state(EditStates.parameter_to_edit)
            await message.answer(
                "Какой параметр поездки вы хотите изменить? Выберите в меню",
                reply_markup=kb.ride_params
            )



@router.message(F.text == "Место отправления", EditStates.parameter_to_edit)
async def edit_location(message: Message, state: FSMContext):
    await state.set_state(EditStates.location)
    await message.answer("Для изменения начальной точки отправьте геолокацию, нажав на кнопку внизу.", reply_markup=kb.location)
    

@router.message(EditStates.location)
async def process_new_location(message: Message, state: FSMContext):
    new_location = (message.location.longitude, message.location.latitude)
    ride_id = (await state.get_data())['ride_id']
    
    async with async_session() as session:
        await rq.update_ride(ride_id, {'location': json.dumps(new_location)}, session)
        
    await state.clear()
    await message.answer("Место отправления обновлено.", reply_markup=kb.main)


@router.message(F.text == "Место назначения", EditStates.parameter_to_edit)
async def edit_destination(message: Message, state: FSMContext):
    await state.set_state(EditStates.destination)
    await message.answer("Введите новое место назначения.", reply_markup=ReplyKeyboardRemove())

@router.message(EditStates.destination)
async def process_new_destination(message: Message, state: FSMContext):
    ride_id = (await state.get_data())['ride_id']
    new_destination = (message.location.longitude, message.location.latitude)

    async with async_session() as session:
        await rq.update_ride(ride_id, {'destination': new_destination}, session)
              
    await state.clear()
    await message.answer(f"Место назначения обновлено на: {new_destination}", reply_markup=kb.main)

    
    
@router.message(F.text == "Время прибытия", EditStates.parameter_to_edit)
async def edit_arrival_time(message: Message, state: FSMContext):
    await state.set_state(EditStates.arrival_time)
    await message.answer("Введите новое время прибытия.", reply_markup=ReplyKeyboardRemove())

@router.message(EditStates.arrival_time)
async def process_new_arrival_time(message: Message, state: FSMContext):
        new_arrival_time = message.text
        ride_id = (await state.get_data())['ride_id']
        
        if not rq.validate_arrival_time(new_arrival_time):
            await message.answer("Неверный формат времени. Используйте чч:мм.")
            return
        
        async with async_session() as session:
            await rq.update_ride(ride_id, {"arrival_time": rq.parse_time(new_arrival_time)}, session)
            
        await state.clear()
        await message.answer("Время прибытия обновлено.", reply_markup=kb.main)


@router.message(F.text == "Транспортное средство", EditStates.parameter_to_edit)
async def edit_transport(message: Message, state: FSMContext):
    await state.set_state(EditStates.transport)
    await message.answer("Введите новое транспортное средство", reply_markup=kb.transport_types)

@router.message(EditStates.transport)
async def process_new_transport(message: Message, state: FSMContext):
        new_transport = message.text
        ride_id = (await state.get_data())['ride_id']
        
        async with async_session() as session:
            await rq.update_ride(ride_id, {'transport': new_transport}, session)
            
        await state.clear()
        await message.answer("Транспортное средство обновлено.", reply_markup=kb.main)



@router.message(F.text == "Время до уведомления", EditStates.parameter_to_edit)
async def edit_notify_time_delta(message: Message, state: FSMContext):
    await state.set_state(EditStates.notify_time_delta)
    await message.answer("Введите новое время до уведомления", reply_markup=ReplyKeyboardRemove())

@router.message(EditStates.notify_time_delta)
async def process_new_notify_time_delta(message: Message, state: FSMContext):
        try:
            notify_time_delta = int(message.text)
        except ValueError:
            await message.answer("Введите корректное число минут.")
            return
        
        ride_id = (await state.get_data())["ride_id"]

        async with async_session() as session:
            await rq.update_ride(ride_id, {"notify_time_delta": notify_time_delta}, session)

        await state.clear()
        await message.answer("Время до уведомления обновлено.", reply_markup=kb.main)




# Создание новой поездки

@router.message(NewRideStates.location)
async def process_location(message: Message, state: FSMContext):
    await state.update_data(location=(message.location.latitude, message.location.longitude))
    await state.set_state(NewRideStates.destination_input)
    await message.answer("Введите место назначения одим из двух способов:", reply_markup=kb.destination)


@router.message(NewRideStates.destination_input, F.text == "Точка на карте")
async def process_destination_input(message: Message, state: FSMContext):
    await state.update_data(destination_input="location")

    await state.set_state(NewRideStates.destination)
    await message.answer('Чтобы отправить место назначение как точку на карте, выберите пункт "Геолокация" во вложениях',
                         reply_markup=ReplyKeyboardRemove())


@router.message(NewRideStates.destination_input, F.text == "Ввести адрес вручную")
async def process_destination_input(message: Message, state: FSMContext):
    await state.update_data(destination_input="text")

    await state.set_state(NewRideStates.destination)
    await message.answer("Введите место назначения",
                         reply_markup=ReplyKeyboardRemove())

@router.message(NewRideStates.destination)
async def process_destination(message: Message, state: FSMContext):
    state_data = await state.get_data()
    destination_input = state_data["destination_input"]
    if destination_input == "location":
          await state.update_data(destination=(message.location.latitude, message.location.longitude))
    elif destination_input == "text":
         # TODO: Перевести адрес в координаты
         await state.update_data(destination=message.text)
    await state.set_state(NewRideStates.arrival_time)
    await message.answer("Введите время прибытия")
     


@router.message(NewRideStates.arrival_time)
async def process_arrival_time(message: Message, state: FSMContext):
    arrival_time_str = message.text

    if not rq.validate_arrival_time(arrival_time_str):
        await message.answer("Неверный формат времени. Используйте чч:мм (например, 14:30).")
        return  
    
    await state.update_data(arrival_time=arrival_time_str)
    await state.set_state(NewRideStates.transport)
    await message.answer("Выберите транспортное средство", reply_markup=kb.transport_types)


@router.message(NewRideStates.transport)
async def process_transport(message: Message, state: FSMContext):
    await state.update_data(transport=message.text)
    await state.set_state(NewRideStates.notify_time_delta)
    await message.answer("Введите за какое время (в минутах) до выхода Вас уведомить?", reply_markup=ReplyKeyboardRemove())


@router.message(NewRideStates.notify_time_delta)
async def process_notify_time_delta(message: Message, state: FSMContext):
    await state.update_data(notify_time_delta=message.text)
    state_data = await state.get_data()
    user_id = message.from_user.id
    
    async with async_session() as session:
        async with session.begin(): 
            user = await rq.get_user_by_tg_id(user_id, session=session)
            if not user:
                await rq.add_user(user_id, session=session)
                user = await rq.get_user_by_tg_id(user_id, session=session)
            
            await rq.add_ride(user.user_id, state_data, session=session) 

        
    await state.clear()
    
    await message.answer(
        "Поездка создана!\n\n"
        f"Место отправления: {state_data['location']}\n"
        f"Место назначения: {state_data['destination']}\n"
        f"Время прибытия: {state_data['arrival_time']}\n"
        f"Транспортное средство: {state_data['transport']}\n"
        f"Время до уведомления: {state_data['notify_time_delta']} минут(ы)",
        reply_markup=kb.main
    )




@router.message()
async def unknown_command(message: Message):
    await message.answer("Извините, но я не знаю такую команду. Вы можете посмотреть список доступных команд в меню.", reply_markup=kb.main)




