"""Main bot code."""

import asyncio
from pathlib import Path
from uuid import uuid4

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandObject, CommandStart
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


@dp.message(Command("set_language"))
async def set_language(
    message: Message, command: CommandObject, state: FSMContext
) -> None:
    """
    Handle /set_language command – set meme language.

    Args:
        message: received message
        command: received command object
        state: current state
    """
    await state.update_data(language=command.args)
    data = await state.get_data()

    await message.answer(
        messages.LANGUAGE_MSG.format(data["language"], data["language"])
    )


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

    if message.caption:
        await state.update_data(theme=message.caption)
    else:
        await state.update_data(theme=None)

    data = await state.get_data()

    try:
        create_meme(**data)
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


async def main() -> None:
    """Run bot."""
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
