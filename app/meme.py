"""Meme generation."""

from math import ceil
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

from app import config
from app.prompt import SYSTEM_PROMPT, USER_PROMPT
from app.utils import (
    break_text,
    clean_text,
    completion_with_backoff,
    outline_text,
    post_request_with_backoff,
)

(IMAGES_PATH := Path("images")).mkdir(exist_ok=True)
(MEMES_PATH := Path("memes")).mkdir(exist_ok=True)

HUGGINGFACE_API_URL = "https://api-inference.huggingface.co/models/nlpconnect/vit-gpt2-image-captioning"  # pylint: disable=line-too-long

FONT_FILE = "Lobster-Regular.ttf"


def describe_image(filename: Path) -> str:
    """
    Make a request to HuggingFace Inference API and get image description.

    Args:
        filename: path to image file

    Returns:
        image description
    """
    with open(filename, "rb") as file:
        data = file.read()

    response = post_request_with_backoff(
        HUGGINGFACE_API_URL,
        headers={"Authorization": f"Bearer {config.HUGGINGFACE_API_KEY}"},
        data=data,
        timeout=1200,
    )

    return response.json()[0]["generated_text"].strip()


def generate_text(
    image_description: str, language: str, theme: Optional[str] = None
) -> str:
    """
    Create meme text for image via request to ChatGPT.

    Args:
        image_description: image description
        language: language to generate meme text in
        theme: meme theme
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": USER_PROMPT.format(
                image_description,
                language,
                f"Theme: {theme}" if theme else "",
            ),
        },
    ]

    response = completion_with_backoff(
        model="gpt-3.5-turbo", messages=messages
    )

    return clean_text(response["choices"][0]["message"]["content"])


def add_text(
    input_path: Path, output_path: Path, upper_text: str, lower_text: str
) -> None:
    """
    Add meme text to an image and save the new image.

    Args:
        input_path: path to input image file
        output_path: path to output image file
        upper_text: upper text for the meme
        lower_text: upper text for the meme
    """
    image = Image.open(input_path)
    draw = ImageDraw.Draw(image)
    width, height = image.size[:2]

    upper_font = ImageFont.truetype(
        FONT_FILE, ceil(width / len(upper_text) * 1.5)
    )

    lower_font = ImageFont.truetype(
        FONT_FILE, ceil(width / len(lower_text) * 1.5)
    )

    outline_text(draw, upper_font, upper_text, width // 2, height // 10)

    outline_text(
        draw, lower_font, lower_text, width // 2, height - height // 10
    )

    image.save(output_path)


def create_meme(
    filename: str, language: str = "English", theme: str = "-"
) -> None:
    """
    Generate funny text for a meme and place it on an image.

    Args:
        filename: image file name
        language: language to generate meme text in
        theme: meme theme ('-' for no theme)
    """
    input_path, output_path = IMAGES_PATH / filename, MEMES_PATH / filename
    image_description = describe_image(input_path)

    text = generate_text(
        image_description, language, theme if theme != "-" else None
    )

    upper_text, lower_text = break_text(text)
    add_text(input_path, output_path, upper_text, lower_text)
