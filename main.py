"""Main bot code."""

import asyncio
from pathlib import Path
from uuid import uuid4

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.filters.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger

from app import config
from app import messages
from app.meme import create_meme

logger.add("logs.log", rotation="500 MB")

(IMAGES_PATH := Path("images")).mkdir(exist_ok=True)
(MEMES_PATH := Path("memes")).mkdir(exist_ok=True)

ERROR_IMAGE = "goose.jpeg"

bot = Bot(config.BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


class Form(StatesGroup):
    """
    States for meme generation.

    Attributes:
        language: language to make a meme in
        theme: theme of the meme
    """

    language = State()
    theme = State()


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """
    Handle /start command – print start message.

    Args:
        message: received message
    """
    await message.answer(messages.START_MSG)


@dp.message(Command("cancel"))
async def command_cancel_handler(message: Message, state: FSMContext) -> None:
    """
    Allow user to cancel action via the /cancel command.

    Args:
        message: received message
        state: current state
    """
    current_state = await state.get_state()

    if current_state is None:
        return

    logger.info(f"Cancelling state {current_state}...")
    await state.clear()
    await message.reply(messages.CANCEL_MSG)


@dp.message(Form.language)
async def process_language(message: Message, state: FSMContext) -> None:
    """
    Set language to generate meme in. Ask user for meme theme.

    Args:
        message: received message with language name
        state: current state
    """
    await state.update_data(language=message.text)
    await state.set_state(Form.theme)
    await message.reply(messages.THEME_MSG)


@dp.message(Form.theme)
async def process_theme(message: Message, state: FSMContext) -> None:
    """
    Set theme of the meme.

    Args:
        message: received message with meme theme
        state: current state
    """
    await state.update_data(theme=message.text)


@dp.message(F.photo)
async def image_handler(message: Message, state: FSMContext) -> None:
    """
    Handle received image – generate a meme with the image and send it to user.

    Args:
        message: received message
        state: current state
    """
    filename = f"{uuid4()}.jpg"
    input_path, output_path = IMAGES_PATH / filename, MEMES_PATH / filename
    file = await bot.get_file(message.photo[-1].file_id)  # type: ignore
    await bot.download_file(file.file_path, input_path)  # type: ignore
    await state.set_state(Form.language)
    await message.reply(messages.LANGUAGE_MSG)
    data = await state.get_data()
    language = data["language"] if data["language"] else "English"

    try:
        create_meme(input_path, output_path, language, data["theme"])
    except Exception as exc:
        logger.error(f"{exc} happened during meme creation.")
        await message.answer(messages.ERROR_MSG)
        await bot.send_photo(message.chat.id, ERROR_IMAGE)
    else:
        await bot.send_photo(message.chat.id, str(output_path))
    finally:
        input_path.unlink(missing_ok=True)
        await state.clear()


async def main() -> None:
    """Run bot."""
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
