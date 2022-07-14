import io
from PIL import Image, ImageEnhance, ImageQt
from PyQt5.QtGui import QImage
import numpy as np
from PyQt5.QtCore import QBuffer

def QImage2PILImage(img):
    buffer = QBuffer()
    buffer.open(QBuffer.ReadWrite)
    img.save(buffer, "PNG")
    pil_im = Image.open(io.BytesIO(buffer.data()))
    return pil_im

print("starting")
img = QImage("XHMZJ_064.tif")
print("converting to PIL Image")
pil_img = QImage2PILImage(img)
print("changing brightness")
enh = ImageEnhance.Brightness(pil_img)
new_img = enh.enhance(1.5)
print("converting back to QImage")
img = ImageQt(new_img)
print("finished!")

