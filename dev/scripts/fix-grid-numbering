#!/usr/bin/env python

"""
Correct image names based on grids and sections.

Example usage: fix-grid-numbering <directory>

This command will rename images based on grids and sections present in the
specified directory. (Images failing to match a regular expression will be
ignored.)

For example:

123_g3_s17_example.tif

will be renamed to:

123_G003_S017_example.tif

If a jser file is present with the images, a copy with sections sorted by the
new image names will be made.

A log with image name changes will also be output to the specificed directory.
"""

import sys
import re
import json
from pathlib import Path
from typing import Union


class GridFile:

    def __init__(
            self,
            filepath:str,
            regexp:str=r'^(.*?)_(g|G|grid|Grid)(\d+).*?(s|S|section|Section)(\d+)_(.*?)$'
    ) -> None:

        self.filepath = Path(filepath)
        self.name = self.filepath.name
        self.name_original = self.name
        self.grid_pattern = regexp
        self.name_corrected = self.correct_name()

    @property 
    def matches_pattern(self) -> bool:

        regexp = re.compile(self.grid_pattern)
        matches = True if regexp.search(self.name) else False

        return matches

    @property
    def name_parts(self) -> tuple:

        match = re.match(self.grid_pattern, self.name)
    
        before_g  = match.group(1)
        g_number  = match.group(3)
        s_number  = match.group(5)
        end       = match.group(6)

        return before_g, g_number, s_number, end

    def correct_name(self) -> Union[str, None]:
        """Get corrected name."""

        if self.matches_pattern:

            start, grid, section, end = self.name_parts

            return f"{start}_G{grid:0>3}_S{section:0>3}_{end}"
    
        else:

            return None

    def rename_file(self, log: Union[Path, None]=None) -> None:

        if self.matches_pattern and self.name_corrected:

            new_path = self.filepath.with_name(self.name_corrected)
            self.filepath.rename(new_path)

            change = f"{self.name} → {self.name_corrected}"
            print(change)

            if log:

                with log.open("a") as f:
                    
                    f.write(change + "\n")


class ImgDir:

    def __init__(self, directory):

        self.directory = Path(directory)

        if not self.directory.exists():
            
            raise FileNotFoundError(f"The directory {self.directory} does not exist.")
        
        if not self.directory.is_dir():
            
            raise NotADirectoryError(f"{self.directory} is not a directory.")

        self.grid_images = [
            GridFile(f)
            for f
            in self.directory.iterdir()
            if f.suffix != ".jser"
        ]
        
        self.jsers = list(self.directory.glob("*.jser"))

    def correct_grid_naming(self):

        for img in self.grid_images:

            log_name = f"{self.directory.absolute().name}_img_changes.txt"
            log_fp = self.directory / log_name
            
            img.rename_file(log=log_fp)

        if self.jsers:  ## TODO: Correct to allow user to point to specific jser

            Jser(self.jsers[0]).correct_naming()


class Jser:

    def __init__(
            self,
            filepath:Union[Path, str],
            pattern:str=r'^(.*?)_(g|G|grid|Grid)(\d+).*?(s|S|sec_section|Section)(\d+)_(.*?)$'
    ) -> None:

        self.filepath = Path(filepath)
        self.pattern = pattern
        self.regexp = re.compile(pattern)
        self.correct_fp = self.filepath.with_name(self.filepath.stem + "_corrected.jser")

        with self.filepath.open("r") as jser:
            self.data = json.load(jser)

    def make_new_jser(self, output: Path):

        with output.open("w") as jser:
            
            jser.write(json.dumps(self.data))

    def correct_naming(self):

        for sec in self.data["sections"]:
    
            original_src = sec["src"]
    
            if self.regexp.search(original_src):

                match = re.match(self.pattern, original_src)
    
                before_g  = match.group(1)
                g_number  = match.group(3)
                s_number  = match.group(5)
                end       = match.group(6)

                sec["src"] = f"{before_g}_G{g_number:0>3}_S{s_number:0>3}_{end}"

        ## Sort sections by new src names
        self.data["sections"] = sorted(
            self.data["sections"], key=lambda x: x["src"]
        )

        ## Update src_dir
        self.data["series"]["src_dir"] = str(self.filepath.parent.resolve())

        ## Write data to a new jser file
        self.make_new_jser(self.correct_fp)


def usage():

    print(__doc__)
    sys.exit()


if __name__ == "__main__":

    if len(sys.argv) != 2:

        usage()

    my_dir = ImgDir(sys.argv[1])
    my_dir.correct_grid_naming()
    sys.exit(0)
