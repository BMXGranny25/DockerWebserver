import io
from PIL import Image

# Assume 'response_content' is the binary data received from a request
response_content = ''
image_data = io.BytesIO(response_content) # will come from esp32 client

# need to save image into a folder as a png
image = Image.open(image_data)
image.save('TempImage/image.png')
#image = Image.open(image_data)
#image.show()
