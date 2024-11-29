import logging
from aiogram import F, Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove

import app.keyboards as kb

router = Router()

# TODO:
# Работа с временем: проверка, чтобы введенное время было больше нынешнего, с учетом часовых поясов
# Проверка введенных данных
# Редактирование поездки
# Удаление поездки
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
    if user_id not in rides:
        answer = 'У вас нет сохраненных поездок.\nЧтобы создать поездку, выберите пункт меню "Новая поездка"'
        reply_kb = kb.main
    else:
        answer = 'Ваши сохраненные поездки:\n'
        count = 1
        user_rides = rides[user_id]
        for ride in user_rides:
            answer += '\n{}. Место отправления: {}\nМесто назначения: {}\nВремя прибытия: {}\nТранспортное средство: {}\nВремя до уведомления: {} минут\n'.format(
                count,
                ride['location'],
                ride['destination'],
                ride['arrival_time'],
                ride['transport'],
                ride['notify_time_delta'],
            )
            count += 1
        # answer += "\n\nЧтобы редактировать поездку, введите номер поездки"
        reply_kb = kb.edit_delete_back
        await state.set_state(choose_mode)
    await message.answer(answer, reply_markup=reply_kb)

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
    ride_id = int(message.text)
    user_id = message.from_user.id
    if ride_id < 0 or ride_id > len(rides[user_id]):
        await message.answer("Неправильный номер поездки")
    else:
        await state.update_data(ride_id = ride_id)
        state_data = await state.get_data()
        if state_data["choose_mode"] == "delete":
             del rides[user_id][ride_id - 1]
             if len(rides[user_id]) == 0:
                  del rides[user_id]
             await state.clear()
             await message.answer(f"Поездка номер {ride_id} удалена.", reply_markup=kb.main)
        else:
            await state.set_state(EditStates.parameter_to_edit)
            await message.answer("Какой параметр поездки вы хотите изменить? Выберите в меню", reply_markup=kb.ride_params)


@router.message(F.text == "Место отправления", EditStates.parameter_to_edit)
async def edit_location(message: Message, state: FSMContext):
    await state.set_state(EditStates.location)
    await message.answer("Для изменения начальной точки отправьте геолокацию, нажав на кнопку внизу.", reply_markup=kb.location)

@router.message(EditStates.location)
async def process_new_location(message: Message, state: FSMContext):
    await state.update_data(location=(message.location.latitude, message.location.longitude))
    user_id = message.from_user.id
    state_data = await state.get_data()
    user_ride = rides[user_id][state_data["ride_id"] - 1]
    user_ride["location"] = state_data["location"]
    await state.clear()
    await message.answer("Изменения сохранены. \n\nМесто отправления: {}\nМесто назначения: {}\nВремя прибытия: {}\nТранспортное средство: {}\nВремя до уведомления: {} минут".format(
        user_ride['location'],
        user_ride['destination'],
        user_ride['arrival_time'],
        user_ride['transport'],
        user_ride['notify_time_delta'],
    ), reply_markup=kb.main)


@router.message(F.text == "Место назначения", EditStates.parameter_to_edit)
async def edit_destination(message: Message, state: FSMContext):
    await state.set_state(EditStates.destination)
    await message.answer("Введите новое место назначения.", reply_markup=ReplyKeyboardRemove())

@router.message(EditStates.destination)
async def process_new_destination(message: Message, state: FSMContext):
        await state.update_data(destination=message.text)
        user_id = message.from_user.id
        state_data = await state.get_data()
        user_ride = rides[user_id][state_data["ride_id"] - 1]
        user_ride["destination"] = state_data["destination"]
        await state.clear()
        await message.answer("Изменения сохранены. \n\nМесто отправления: {}\nМесто назначения: {}\nВремя прибытия: {}\nТранспортное средство: {}\nВремя до уведомления: {} минут".format(
            user_ride['location'],
            user_ride['destination'],
            user_ride['arrival_time'],
            user_ride['transport'],
            user_ride['notify_time_delta'],
        ), reply_markup=kb.main)



@router.message(F.text == "Время прибытия", EditStates.parameter_to_edit)
async def edit_arrival_time(message: Message, state: FSMContext):
    await state.set_state(EditStates.arrival_time)
    await message.answer("Введите новое время прибытия.", reply_markup=ReplyKeyboardRemove())

@router.message(EditStates.arrival_time)
async def process_new_arrival_time(message: Message, state: FSMContext):
        await state.update_data(arrival_time=message.text)
        user_id = message.from_user.id
        state_data = await state.get_data()
        user_ride = rides[user_id][state_data["ride_id"] - 1]
        user_ride["arrival_time"] = state_data["arrival_time"]
        await state.clear()
        await message.answer("Изменения сохранены. \n\nМесто отправления: {}\nМесто назначения: {}\nВремя прибытия: {}\nТранспортное средство: {}\nВремя до уведомления: {} минут".format(
            user_ride['location'],
            user_ride['destination'],
            user_ride['arrival_time'],
            user_ride['transport'],
            user_ride['notify_time_delta'],
        ), reply_markup=kb.main)


@router.message(F.text == "Транспортное средство", EditStates.parameter_to_edit)
async def edit_transport(message: Message, state: FSMContext):
    await state.set_state(EditStates.transport)
    await message.answer("Введите новое транспортное средство", reply_markup=kb.transport_types)

@router.message(EditStates.transport)
async def process_new_transport(message: Message, state: FSMContext):
        await state.update_data(transport=message.text)
        user_id = message.from_user.id
        state_data = await state.get_data()
        user_ride = rides[user_id][state_data["ride_id"] - 1]
        user_ride["transport"] = state_data["transport"]
        await state.clear()
        await message.answer("Изменения сохранены. \n\nМесто отправления: {}\nМесто назначения: {}\nВремя прибытия: {}\nТранспортное средство: {}\nВремя до уведомления: {} минут".format(
            user_ride['location'],
            user_ride['destination'],
            user_ride['arrival_time'],
            user_ride['transport'],
            user_ride['notify_time_delta'],
        ), reply_markup=kb.main)



@router.message(F.text == "Время до уведомления", EditStates.parameter_to_edit)
async def edit_notify_time_delta(message: Message, state: FSMContext):
    await state.set_state(EditStates.notify_time_delta)
    await message.answer("Введите новое время до уведомления", reply_markup=ReplyKeyboardRemove())

@router.message(EditStates.notify_time_delta)
async def process_new_notify_time_delta(message: Message, state: FSMContext):
        await state.update_data(notify_time_delta=message.text)
        user_id = message.from_user.id
        state_data = await state.get_data()
        user_ride = rides[user_id][state_data["ride_id"] - 1]
        user_ride["notify_time_delta"] = state_data["notify_time_delta"]
        await state.clear()
        await message.answer("Изменения сохранены. \n\nМесто отправления: {}\nМесто назначения: {}\nВремя прибытия: {}\nТранспортное средство: {}\nВремя до уведомления: {} минут".format(
            user_ride['location'],
            user_ride['destination'],
            user_ride['arrival_time'],
            user_ride['transport'],
            user_ride['notify_time_delta'],
        ), reply_markup=kb.main)




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
    await state.update_data(arrival_time=message.text)
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
    if user_id not in rides:
        rides[user_id] = []
    rides[user_id].append(state_data)
    await state.clear()
    await message.answer("Поездка создана!\n\nМесто отправления: {}\nМесто назначения: {}\nВремя прибытия: {}\nТранспортное средство: {}\nВремя до уведомления: {} минут".format(
        state_data['location'],
        state_data['destination'],
        state_data['arrival_time'],
        state_data['transport'],
        state_data['notify_time_delta'],
    ), reply_markup=kb.main)


@router.message()
async def unknown_command(message: Message):
    await message.answer("Извините, но я не знаю такую команду. Вы можете посмотреть список доступных команд в меню.", reply_markup=kb.main)
