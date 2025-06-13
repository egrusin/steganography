import os
import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
from stego import embed_message, extract_message

# Загружаем переменные из .env
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_CATS_URL = 'https://api.thecatapi.com/v1/images/search'

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot=bot, storage=storage)

# Определяем состояния для FSM
class EmbedMessage(StatesGroup):
    waiting_for_image = State()
    waiting_for_message = State()

class ExtractMessage(StatesGroup):
    waiting_for_image = State()

@dp.message(Command("start"))
async def start_command(message: types.Message):
    """
    Обработчик команды /start.
    """
    await message.answer(
        "Привет! Я стеганографический бот (https://ru.wikipedia.org/wiki/Стеганография). Я могу зашифровать сообщение в изображении или извлечь его.\n\n"
        "Команды:\n"
        "/embed_message - Встрою сообщение в изображение, комар носа не подточит.\n"
        "/extract_message (или просто оправь изображение) - Извлеку из изображения сообщение, которое сам туда положил.\n"
        "/random_image - Фоток нет, а попробовать хочется? Дам тебе картинку котика.\n"
    )

@dp.message(Command("help"))
async def start_command(message: types.Message):
    """
    Обработчик команды /help.
    """
    await message.answer(
        "Ок"
    )

@dp.message(Command("embed_message"))
async def embed_message_command(message: types.Message, state: FSMContext):
    """
    Обработчик команды /embed_message. Запрашивает изображение.
    """
    await message.answer("Отправьте изображение (JPG, PNG или HEIC формата), в которое нужно встроить сообщение.")
    await state.set_state(EmbedMessage.waiting_for_image)

@dp.message(EmbedMessage.waiting_for_image)
async def process_image_for_embed(message: types.Message, state: FSMContext):
    """
    Обрабатывает загруженное изображение и запрашивает сообщение.
    """
    if not message.photo and not message.document:
        await message.answer("Пожалуйста, отправьте изображение.")
        return

    if message.document:
        if not message.document.mime_type.startswith("image/"):
            await message.answer("Файл должен быть изображением.")
            return
        file_id = message.document.file_id
        file_name = message.document.file_name
    else:
        file_id = message.photo[-1].file_id
        file_name = f"{file_id}.png"

    file = await bot.get_file(file_id)
    input_path = f"temp_{file_id}.png"
    await bot.download_file(file.file_path, input_path)

    await state.update_data(image_path=input_path)
    await message.answer("Введите сообщение для встраивания.")
    await state.set_state(EmbedMessage.waiting_for_message)

@dp.message(EmbedMessage.waiting_for_message)
async def process_message_for_embed(message: types.Message, state: FSMContext):
    """
    Встраивает сообщение в изображение и отправляет результат.
    """
    if not message.text:
        await message.answer("Пожалуйста, отправьте текстовое сообщение.")
        return

    user_data = await state.get_data()
    input_path = user_data["image_path"]
    output_path = f"stego_{os.path.basename(input_path)}"
    text = message.text

    try:
        embed_message(input_path, text, output_path)
        with open(output_path, "rb") as f:
            await message.reply_document(
                types.BufferedInputFile(f.read(), filename="stego.png")
            )
        await message.answer("Сообщение успешно встроено.")
    except Exception as e:
        await message.answer(f"Ошибка: {str(e)}")
    finally:
        if os.path.exists(input_path):
            os.remove(input_path)
        if os.path.exists(output_path):
            os.remove(output_path)

    await state.clear()

@dp.message(Command("extract_message"))
async def extract_message_command(message: types.Message, state: FSMContext):
    """
    Обработчик команды /extract_message. Запрашивает изображение.
    """
    await message.answer("Отправьте изображение со скрытым сообщением (без сжатия!).")
    await state.set_state(ExtractMessage.waiting_for_image)

@dp.message(ExtractMessage.waiting_for_image)
async def process_image_for_extract(message: types.Message, state: FSMContext):
    """
    Извлекает сообщение из изображения и отправляет его пользователю.
    """
    if not message.photo and not message.document:
        await message.answer("Пожалуйста, отправьте изображение.")
        return

    if message.document:
        if not message.document.mime_type.startswith("image/"):
            await message.answer("Файл должен быть изображением.")
            return
        file_id = message.document.file_id
    else:
        file_id = message.photo[-1].file_id

    file = await bot.get_file(file_id)
    input_path = f"temp_{file_id}.png"
    await bot.download_file(file.file_path, input_path)

    try:
        extracted_message = extract_message(input_path)
        await message.reply(f"Извлечённое сообщение: {extracted_message}")
    except Exception as e:
        await message.reply(f"Ошибка: {str(e)}")
    finally:
        if os.path.exists(input_path):
            os.remove(input_path)

    await state.clear()

@dp.inline_query()
async def inline_embed_message(inline_query: InlineQuery):
    """
    Обработчик inline-запросов для предложения встраивания.
    """
    result = InlineQueryResultArticle(
        id="embed_instruction",
        title="Встроить сообщение в изображение",
        # url=f"https://t.me/steganozavr_bot",
        input_message_content=InputTextMessageContent(
            message_text="Хотите встроить сообщение в изображение? Это можно сделать в чате с ботом @steganozavr_bot"
        )
    )
    await inline_query.answer([result], cache_time=1)


# Автоматическая обработка изображения с текстом для встраивания
@dp.message(lambda message: (message.photo or (message.document and message.document.mime_type.startswith("image/"))) and (message.text or message.caption))
async def auto_embed_message(message: types.Message, state: FSMContext):
    """
    Автоматически встраивает сообщение в изображение, если отправлено изображение с текстом.
    """
    if message.document:
        if not message.document.mime_type.startswith("image/"):
            return
        file_id = message.document.file_id
    else:
        file_id = message.photo[-1].file_id

    file = await bot.get_file(file_id)
    input_path = f"temp_{file_id}.png"
    await bot.download_file(file.file_path, input_path)

    try:
        output_path = f"stego_{os.path.basename(input_path)}"
        embed_message(input_path, message.text or message.caption, output_path)
        with open(output_path, "rb") as f:
            await message.reply_document(
                types.BufferedInputFile(f.read(), filename="stego.png")
            )
        await message.answer("Сообщение успешно встроено.")
    except Exception as e:
        await message.reply(f"Не удалось встроить сообщение: {str(e)}")
    finally:
        if os.path.exists(input_path):
            os.remove(input_path)
        if os.path.exists(output_path):
            os.remove(output_path)


# Автоматическая обработка изображений для извлечения
@dp.message(lambda message: message.photo or (message.document and message.document.mime_type.startswith("image/")))
async def auto_extract_message(message: types.Message):
    """
    Автоматически извлекает сообщение из любого полученного изображения.
    """
    if message.document:
        if not message.document.mime_type.startswith("image/"):
            return
        file_id = message.document.file_id
    else:
        file_id = message.photo[-1].file_id

    file = await bot.get_file(file_id)
    input_path = f"temp_{file_id}.png"
    await bot.download_file(file.file_path, input_path)

    try:
        extracted_message = extract_message(input_path)
        await message.reply(f"Извлечённое сообщение: {extracted_message}")
    except Exception as e:
        await message.reply(f"Извление не удалось: {str(e)}")
    finally:
        if os.path.exists(input_path):
            os.remove(input_path)


# Обработчик текстовых сообщений вне протокола
@dp.message(lambda message: not message.text or not message.text.startswith('/'))
async def handle_non_command_messages(message: types.Message):
    """
    Блокирует текстовые сообщения вне команд.
    """
    print(message.text, message.caption, message.photo)
    await message.answer("Я не могу отвечать на сообщения вне протокола. Воспользуйтесь меню.")

# Обработчик команды /random_image
@dp.message(Command("random_image"))
async def random_image_command(message: types.Message):
    """
    Отправляет случайное изображение котика из TheCatAPI.
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(API_CATS_URL) as response:
            if response.status == 200:
                data = await response.json()
                cat_link = data[0]["url"]
                await bot.send_photo(chat_id=message.chat.id, photo=cat_link)
            else:
                await message.answer("Не удалось получить изображение котика. Попробуйте позже.")

async def main():
    """
    Запуск бота.
    """
    print("Бот запущен")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        print(f"Ошибка в работе приложения: {e}")
        print("Бот остановлен.")

if __name__ == "__main__":
    asyncio.run(main())