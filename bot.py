import keyring
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
import asyncio
import aiohttp

BOT_TOKEN = keyring.get_password(r't.me/krivoobot', 'token')
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
logging.basicConfig(level=logging.INFO)
WEATHER_CODES = {
    0: "☀️ Ясно",
    1: "🌤 В основном ясно",
    2: "⛅ Переменная облачность",
    3: "☁️ Пасмурно",
    45: "🌫 Туман",
    61: "🌧 Небольшой дождь",
    63: "🌧 Дождь",
    65: "🌧 Сильный дождь",
    71: "❄️ Небольшой снег",
    73: "❄️ Снег",
    75: "❄️ Сильный снег",
    95: "⛈ Гроза",
}
nazad = KeyboardButton(text="назад")
keyboard2 = ReplyKeyboardMarkup(keyboard=[[nazad]],
                                    resize_keyboard=True,
                                    one_time_keyboard=False
                                    )
b1 = KeyboardButton(text="погода")
b2 = KeyboardButton(text="котеки")
b3 = KeyboardButton(text="егор крит")
b4 = KeyboardButton(text='/inline')
keyboard1 = ReplyKeyboardMarkup(keyboard=
                                   [[b1, b2],
                                    [b3, b4]
                                    ],
                                    resize_keyboard=True, 
                                    one_time_keyboard=False,
                                    )

class InputState(StatesGroup):
    waiting_for_data = State()

async def weather(city: str):
    async with aiohttp.ClientSession() as session:
        # 1. Геокодинг
        geo_url = "https://geocoding-api.open-meteo.com/v1/search"
        geo_params = {
            "name": city,
            "count": 1,
            "language": "ru"
        }

        async with session.get(geo_url, params=geo_params) as response:
            geo_data = await response.json()

        if "results" not in geo_data or not geo_data["results"]:
            return f"Город «{city}» не найден"

        shirota = geo_data["results"][0]["latitude"]
        dolgota = geo_data["results"][0]["longitude"]
        city_name = geo_data["results"][0]["name"]

        weather_url = "https://api.open-meteo.com/v1/forecast"
        weather_params = {
                    "latitude": shirota,
                    "longitude": dolgota,
                    "current": "temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m",
                    "timezone": "auto"
                }

        async with session.get(weather_url, params=weather_params) as response:
            data = await response.json()
    current = data["current"]
    temp = current["temperature_2m"]
    feels = current["apparent_temperature"]
    vlaga = current["relative_humidity_2m"]
    veter = current["wind_speed_10m"]
    code = current["weather_code"]

    weather = WEATHER_CODES.get(code, "Неизвестно")

    text = (
        f"Погода в <b>{city_name}</b>\n\n"
        f"{weather}\n"
        f"Температура: <b>{temp}°C</b>\n"
        f"Ощущается как: {feels}°C\n"
        f"Влажность: {vlaga}%\n"
        f"Ветер: {veter} км/ч"
    )
    return text


@dp.message(CommandStart())
async def start_handler(message: Message):
    user_name = message.from_user.full_name
    
    await message.answer(f"Привет, {user_name}!\n"
                        "Выбери действие:", reply_markup=keyboard1
                        )


 
@dp.message(F.text.in_(['погода', 'котеки', "апи3", "апи4"]))
async def button_handler(message : Message, state: FSMContext):
    button = message.text

    if button not in ['котеки', 'егор крит']:
        await state.update_data(action=button)
        await state.set_state(InputState.waiting_for_data)
    if button == "погода":

        await message.answer(
            text="Введите корректное название города на русском языке: ", reply_markup=keyboard2
        )
        

    elif button == "котеки":
        async with aiohttp.ClientSession() as session:
            async with session.get(r"https://api.thecatapi.com/v1/images/search") as response:
                if response.status != 200:
                    await message.answer(text='koteka ne budet')
                    return
                data = await response.json()
                cat_url = data[0]["url"]
        await message.answer_photo(photo=cat_url,
                                    caption='randomny kotek'
                                    )
    elif button == "егор крит":
        await message.answer_audio(
            audio=r"https://cdn8.sefon.pro/prev/NSTDWk3L8ZyIuCTZF0FCwg/1789151074/1056/%D0%95%D0%B3%D0%BE%D1%80%20%D0%9A%D1%80%D0%B8%D0%B4%20-%20%D0%9C%D0%B0%D0%BB%D0%BE%202.0%20%28192kbps%29.mp3",
            caption="не"
        )   

@dp.message(InputState.waiting_for_data)
async def process_data(message: Message, state: FSMContext):
    data = await state.get_data()
    action = data.get("action")
    user_input = message.text

    if action == "погода" and user_input != "назад":
        text = await weather(user_input)
        await message.answer(text, parse_mode="HTML")


    # elif action == "кнопка3":
    #     result = await your_third_api_function(user_input)
    #     await message.answer(result)

    # elif action == "кнопка4":
    #     result = await your_fourth_api_function(user_input)
    #     await message.answer(result)
    if user_input == "назад":
        await message.answer(text="Возвращаемся в меню...", reply_markup=keyboard1)
        await state.clear()

@dp.message(~F.text.in_(["погода", "котеки", "апи3", "апи4"]))
async def other_messages(message: Message, state: FSMContext):
    current_state = await state.get_state()
    
    if current_state is not None:
        return
    
    await message.answer("нормально общайся")




async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

