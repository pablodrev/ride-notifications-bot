from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

main = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="Новая поездка")],
    [KeyboardButton(text="Мои поездки"), KeyboardButton(text="Настройки")]
], resize_keyboard=True)

edit_delete_back = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Редактировать"), KeyboardButton(text="Удалить")],
                                                 [KeyboardButton(text="Назад")]], resize_keyboard=True)

location = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Отправить геолокацию", request_location=True)]], resize_keyboard=True)

destination = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Точка на карте")],
                                            [KeyboardButton(text="Ввести адрес вручную")]], resize_keyboard=True)

transport_types = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="Автомобиль"), KeyboardButton(text="Общественный транспорт")],
    [KeyboardButton(text="Пешком")]
], resize_keyboard=True)

ride_params = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="Место отправления")],
    [KeyboardButton(text="Место назначения")],
    [KeyboardButton(text="Время прибытия")],
    [KeyboardButton(text="Транспортное средство")],
    [KeyboardButton(text="Время до уведомления")],
])
