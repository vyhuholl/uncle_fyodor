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
from aiogram.types.input_file import BufferedInputFile
from loguru import logger

from app import config
from app import messages
from app.meme import create_meme, IMAGES_PATH, MEMES_PATH

logger.add("logs.log", rotation="500 MB")

ERROR_IMAGE = Path("goose.jpeg")

bot = Bot(config.BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


class Form(StatesGroup):
    """
    States for meme generation.

    Attributes:
        filename: input and output file name
        language: language to make a meme in
        theme: theme of the meme
    """

    filename = State()
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
        message: received message
        state: current state
    """
    await state.update_data(language=message.text)
    await state.set_state(Form.theme)
    await message.reply(messages.THEME_MSG)


@dp.message(Form.theme)
async def process_theme(message: Message, state: FSMContext) -> None:
    """
    Set meme theme. Generate meme text,

    Args:
        message: received message
        state: current state
    """
    await state.update_data(theme=message.text)
    data = await state.get_data()

    try:
        create_meme(data["filename"], data["language"], data["theme"])
    except Exception as exc:
        logger.error(f"{exc} happened during meme creation.")
        await message.answer(messages.ERROR_MSG)
        photo = BufferedInputFile.from_file(ERROR_IMAGE)
        await bot.send_photo(message.chat.id, photo)
    else:
        photo = BufferedInputFile.from_file(MEMES_PATH / data["filename"])
        await bot.send_photo(message.chat.id, photo)
    finally:
        (IMAGES_PATH / data["filename"]).unlink(missing_ok=True)
        await state.clear()


@dp.message(F.photo)
async def image_handler(message: Message, state: FSMContext) -> None:
    """
    Handle received image – generate a meme with the image and send it to user.

    Args:
        message: received message
        state: current state
    """
    filename = f"{uuid4()}.jpg"
    input_path = IMAGES_PATH / filename
    await state.update_data(filename=filename)
    file = await bot.get_file(message.photo[-1].file_id)  # type: ignore
    await bot.download_file(file.file_path, input_path)  # type: ignore
    await state.set_state(Form.language)
    await message.reply(messages.LANGUAGE_MSG)


async def main() -> None:
    """Run bot."""
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
