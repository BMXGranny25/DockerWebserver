import io
import os
from PIL import Image


def save_binary_as_png(binary_data: bytes, output_path: str = "TempImage/image.png"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    image_data = io.BytesIO(binary_data)
    image = Image.open(image_data).convert("RGB")
    image.save(output_path, format="PNG")

    return output_path