#!/usr/bin/env python
# -*- mode: python -*-

import sys
import json
import shutil
from pathlib import Path
from datetime import datetime as dt
from typing import Union


def get_decoding(project_dir):
    """Get decoding information as a dictionary."""

    with (project_dir / "decode.txt").open("r") as decode:
        lines = map(
            lambda x: tuple(x.strip().split(" -> ")),
            decode.readlines()
        )

        image_decoding = list(lines)

    series_names = set(
        [elem[0].split("/")[0] for elem in image_decoding]
    )

    decoding = {
        "series" : list(series_names),
        "images" : {coded: image for image, coded in image_decoding}
    }
        

    return decoding


def derandomize_project(coded_series_fp: Union[str, Path]) -> Path:
    """Derandomize a project."""

    if not isinstance(coded_series_fp, Path):
        
        coded = Path(coded_series_fp)
        
    else:
        
        coded = coded_series_fp
        
    project_dir = coded.parent

    ## Get decoding information
    decoding = get_decoding(project_dir)

    ## Create series data
    for series in decoding["series"]:

        series_dir = project_dir / series
        series_img_dir = series_dir / "images"
        
        series_dir.mkdir()
        series_img_dir.mkdir()
        
        series_jser = series_dir / f"{series}.jser"
        shutil.copy(coded, series_jser)

        ## Edit new series data
        with series_jser.open("r") as fp:
            data = json.load(fp)

        new_sections = []

        for section in data["sections"]:
            
            img_coded = section["src"]
            img_decoded = decoding["images"][img_coded]

            img_series, img_name = img_decoded.split("/")

            if not img_series == series:
                continue

            section["src"] = img_name

            new_sections.append(section)

            ## Move images
            img_coded_fp = project_dir / "images" / img_coded
            img_decoded_fp = series_img_dir / img_name
            img_coded_fp.rename(img_decoded_fp)
            
        data["sections"] = sorted(new_sections, key=lambda x: x["src"])

        ## Edit series data
        data["series"]["code"] = series
        data["series"]["current_section"] = 0
        data["series"]["src_dir"] = str(series_img_dir)

        date = dt.now().strftime("%y-%m-%d")
        time = dt.now().strftime("%H:%M")
        
        log_info = f"\n{date}, {time}, computer, -, -, Decoded series"
        data["log"] = data["log"] + log_info

        ## Copy coded jser
        with series_jser.open("w") as fp:
            fp.write(json.dumps(data))

    ## Move or rename coded files
    save_coding_dir = project_dir / f"decoded-{dt.now().strftime('%y%m%d')}"
    save_coding_dir.mkdir()
    
    (project_dir / "images").rmdir()
    coded.rename(save_coding_dir / coded.name)
    (project_dir / "decode.txt").rename(save_coding_dir / "decode.txt")

    return project_dir


if __name__ == '__main__':

    args = sys.argv

    if not len(args) == 2 or not args[1].endswith(".jser"):
        print("Provide a single coded jser as an argument.")
        sys.exit(1)
        
    project_dir = Path(args[1])
    
    derandomize_project(project_dir)

    print("Project decoded.")
