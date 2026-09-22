import keyring
import logging
import ssl
import json
import os
import csv
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart, or_f
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.session.aiohttp import AiohttpSession
import asyncio
import aiohttp

class DisabledSSLAiohttpSession(AiohttpSession):
    async def create_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:

            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            connector = aiohttp.TCPConnector(ssl=ssl_context)
            self._session = aiohttp.ClientSession(
                connector=connector,
                json_serialize=self.json_dumps, 
            )
        return self._session
    
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
logging.basicConfig(level=logging.INFO)
LOG_FILE = 'bot_loggs.csv'
def logger(
    user_id: int,
    username: str | None,
    motion: str,
    api: str = "NONE",
    api_answer: str = "NONE",
) :
    nick = f"@{username}" if username else "None"
    now = datetime.now()
    date_str = now.strftime("%d.%m.%Y")
    time_str = now.strftime("%H:%M:%S")

    api_answer_clean = str(api_answer).replace("\n", " ").replace("\r", " ")[:500]

    file_exists = os.path.exists(LOG_FILE)

    with open(LOG_FILE, "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter=",", quotechar='"', quoting=csv.QUOTE_MINIMAL)
        if not file_exists:
            writer.writerow(
                ["Unic ID", "@TG nick", "Motion", "API", "Date", "Time", "API answer"]
            )
        writer.writerow(
            [user_id, nick, motion, api, date_str, time_str, api_answer_clean]
        )


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
b3 = KeyboardButton(text="конвертер валют")
b4 = KeyboardButton(text='смешнявка')
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


async def currency_convert(s: str):
    parts = s.upper().split()
    if len(parts) != 3:
        return "эмммм"
    url = f"https://v6.exchangerate-api.com/v6/3f90a64e7451ec50582d54b4/pair/{parts[1]}/{parts[2]}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url=url) as response:
            data = await response.json()
    if data.get("result") == "success":
        rate = data["conversion_rate"]
        return f"{float(parts[0]) * rate} {parts[2]}"
    else:
        return r"ошибка"


@dp.message(or_f(CommandStart(), F.text == "назад"))
async def start_handler(message: Message, state: FSMContext):
    motion = "start" if message.text and message.text.startswith("/") else "назад"
    await state.clear()
    logger(
        message.from_user.id,
        message.from_user.username,
        motion=motion,
        api="NONE",
        api_answer="NONE",
    )
    user_name = message.from_user.full_name
    
    await message.answer(f"Привет, {user_name}!\n"
                        "Выбери действие:", reply_markup=keyboard1
                        )

 
@dp.message(F.text.in_(['погода', 'котеки', "конвертер валют", "смешнявка"]))
async def button_handler(message : Message, state: FSMContext):
    button = message.text
    id = message.from_user.id
    username = message.from_user.username
   
    if button in ['погода', 'конвертер валют']:
        api = "NONE"
        api_answer = "NONE"         
        await state.update_data(action=button)
        await state.set_state(InputState.waiting_for_data)
    if button == "погода":      
        await message.answer(
            text="Введите корректное название города на русском языке: ",
              reply_markup=keyboard2
        )
    elif button == "конвертер валют":    
        await message.answer(
            text=f"Введите параметры конвертации.\nпример для перевода 100 USD в BYN:\n<b>100 usd byn</b>",
              parse_mode="HTML",
              reply_markup=keyboard2
        )
        
    elif button == "котеки":
        async with aiohttp.ClientSession() as session:
            async with session.get(r"https://api.thecatapi.com/v1/images/search") as response:
                data = await response.json()
                cat_url = data[0]["url"]
            api = "thecatapi"
            api_answer = cat_url if cat_url else "NONE"

        await message.answer_photo(photo=cat_url,
                                    caption='randomny kotek'
                                    )
    elif button == "смешнявка":
        url = "http://rzhunemogu.ru/RandJSON.aspx?CType=1"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, ssl=False) as response:
                text = await response.text(encoding='cp1251')
                data = json.loads(text, strict=False)
                joke = data.get('content')
        api = "rzhunemogu"
        api_answer = joke if joke else "NONE"
        await message.answer(text=joke.strip())
    logger(id,
        username,
        motion=button, 
        api=api,
        api_answer=api_answer)
    
@dp.message(InputState.waiting_for_data)
async def process_data(message: Message, state: FSMContext):
    data = await state.get_data()
    action = data.get("action")
    user_input = message.text
    id = message.from_user.id
    username = message.from_user.username
    if user_input == "назад":
        await message.answer(text="Возвращаемся в меню...", reply_markup=keyboard1)
        await state.clear()
        logger(id,
               username,
               motion='назад',
               api="NONE",
               api_answer="NONE")
        return

    elif action == "погода":
        text = await weather(user_input)
        await message.answer(text, parse_mode="HTML")
        api = "open-meteo"
        api_answer = text if text else "NONE"

    elif action == "конвертер валют":
        result = await currency_convert(user_input)
        await message.answer(result, parse_mode="HTML")
        api = "exchangerate_api"
        api_answer = result if result else "NONE"

    logger(id,
           username,
           motion=action,
           api=api,
           api_answer=api_answer)

@dp.message(~F.text.in_(["погода", "котеки", "конвертер валют", "смешнявка"]))
async def other_messages(message: Message, state: FSMContext):
    current_state = await state.get_state()
    id = message.from_user.id
    username = message.from_user.username    
    if current_state is None:
        await message.answer("нормально общайся")
    logger(id,
           username,
           motion="non-handle message",
           api="NONE",
           api_answer="NONE")

async def main():
    session = DisabledSSLAiohttpSession()

    BOT_TOKEN = keyring.get_password(r't.me/krivoobot', 'token')
    bot = Bot(token=BOT_TOKEN, session=session)

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

