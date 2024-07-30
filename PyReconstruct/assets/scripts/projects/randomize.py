#!/usr/bin/env python
# -*- mode: python -*-

import sys
import uuid
from pathlib import Path
from typing import Union

from PyReconstruct.modules.datatypes import Series


def randomize_images(project_dir):
    """Randomize and collect images."""

    decode_file = project_dir / "decode.txt"

    for series in project_dir.iterdir():

        if series.name == "images" or not series.is_dir():

            continue

        for image in series.iterdir():

            ## Generate coded name
            new_name = f"{str(uuid.uuid4())}.{image.suffix[1:]}"

            ## Write decoding info
            with decode_file.open("a") as text:
                text.write(
                    f"{image.relative_to(project_dir)} -> {new_name}\n"
                )

            ## Rename and move image
            image.rename(project_dir / f"images/{new_name}")

        ## Remove empty directories
        series.rmdir()


def sort_images(image_dir):
    """Sort images by name."""

    patterns = ["*.png", "*.tif", "*.tiff", "*.jpg", "*.jpeg", "*.bmp"]
    images = [file for pattern in patterns for file in image_dir.glob(pattern)]
    
    images_sorted = [
        str(elem)
        for elem
        in sorted(
            images, key=lambda p: p.name
        )
    ]
    
    return images_sorted


def create_new(img_dir):
    """Create a new series."""

    images_list = sort_images(img_dir)
    mag = 0.00254
    th = 0.05

    with Series.new(images_list, "coded", mag, th) as series:

        fp = img_dir / "../coded.jser"
        series.saveJser(str(fp))

    return fp.resolve()


def main(project_dir: Union[str, Path]) -> Path:
    """Main."""

    if not isinstance(project_dir, Path):
        project_dir = Path(project_dir)
    
    new_img_dir = project_dir / "images"
    new_img_dir.mkdir()
    
    randomize_images(project_dir)

    return create_new(new_img_dir)


if __name__ == '__main__':

    args = sys.argv

    if not len(args) == 2:
        print("Provide a single directory as an argument.")
        sys.exit(1)
        
    project_dir = Path(args[1])

    fp = main(project_dir)

    print(f"Jser ready in {fp}")
