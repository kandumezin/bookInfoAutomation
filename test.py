from PIL import Image
import pyzbar.pyzbar as pyzbar

im = Image.open("tooMuchCodes.jpg")

pre_bcodes = pyzbar.decode(im)

print(pre_bcodes)