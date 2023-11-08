import os
import cv2
import zarr

from PySide6.QtWidgets import QApplication, QFileDialog

input("Press enter to locate the images folder.")
app = QApplication([])
img_dir = QFileDialog.getExistingDirectory(
    caption="Locate Images Folder"
)
if not img_dir:
    exit()

os.chdir(img_dir)

zarr_name = input("\nWhat would you like to name your zarr file?: ")
if not zarr_name.endswith(".zarr"):
    zarr_name = zarr_name + ".zarr"

for fname in os.listdir("."):
    print(f"Working on {fname}...")
    try:
        cvim = cv2.imread(fname, cv2.IMREAD_GRAYSCALE)
        zarr.save(os.path.join(zarr_name, fname), cvim)
    except:
        print("File is not an image.")

print()
print("Images successfully exported as zarr directory to:")
print(f"{img_dir}/{zarr_name}")
print()
print("Open series, then SERIES > FIND IMAGES and point to this zarr directory.")
print()
print("Happy scrolling!")
