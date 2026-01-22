import os
from io import BytesIO
from PIL import Image

def is_allowed_file(filename, allowed_extensions):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def bytes_to_image(image_bytes):
    return Image.open(BytesIO(image_bytes))
