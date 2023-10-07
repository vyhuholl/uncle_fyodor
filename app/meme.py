"""Meme generation."""

from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

from app import config
from app.prompt import SYSTEM_PROMPT, USER_PROMPT
from app.utils import (
    break_text,
    clean_text,
    completion_with_backoff,
    post_request_with_backoff,
)

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

    return response.json()[0]["generated_text"]


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
    upper_font = ImageFont.truetype(FONT_FILE, width // len(upper_text))
    lower_font = ImageFont.truetype(FONT_FILE, width // len(lower_text))

    draw.text(
        (width // 2, height // 10),
        upper_text,
        fill="white",
        font=upper_font,
        anchor="ms",
    )

    draw.text(
        (width // 2, height - height // 10),
        lower_text,
        fill="white",
        font=lower_font,
        anchor="ms",
    )

    image.save(output_path)


def create_meme(
    input_path: Path,
    output_path: Path,
    language: str = "English",
    theme: Optional[str] = None,
) -> None:
    """
    Generate funny text for a meme and place it on an image.

    Args:
        input_path: path to input image file
        output_path: path to output image file
        language: language to generate meme text in
        theme: theme of the meme
    """
    image_description = describe_image(input_path)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": USER_PROMPT.format(
                image_description, language, f"Theme: {theme}" if theme else ""
            ),
        },
    ]

    response = completion_with_backoff(
        model="gpt-3.5-turbo", messages=messages
    )

    text = clean_text(response["choices"][0]["message"]["content"])
    upper_text, lower_text = break_text(text)
    add_text(input_path, output_path, upper_text, lower_text)
