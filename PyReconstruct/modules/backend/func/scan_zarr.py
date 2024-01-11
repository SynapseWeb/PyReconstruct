import os
import json

class ZarrScanner:

    def __init__(self, zarr_fp : str):
        """Scan a zarr file for the proper .zgroup and .zarray/.zattrs files
        
            Params:
                zarr_fp (str): the filepath to the zarr
        """
        self.zarr_fp = zarr_fp
        self.corrupt_files = []
        self.missing_files = []
        self.zarray_files = {}
        self.scanFolder(self.zarr_fp)
    
    def addZarrayFile(self, group_name : str, file_str : str):
        """Keep track of number of specific zarray files.
        
            Params:
                group_name (str): the name of the group containing the zarray file
                file_str (str): the .zarray file in string format
        """
        if group_name not in self.zarray_files:
            self.zarray_files[group_name] = {}
        if file_str in self.zarray_files[group_name]:
            self.zarray_files[group_name][file_str] += 1
        else:
            self.zarray_files[group_name][file_str] = 1

    def scanFolder(self, folder : str):
        """San a folder within a zarr file for missing and corrupt files
        
            Params:
                folder (str): the folder to scan
        """
        is_group = False
        has_zgroup = False
        valid_zgroup = False
        has_zattrs = False
        valid_zattrs = False
        has_zarray = False
        valid_zarray = False

        with os.scandir(folder) as entries:
            for entry in entries:
                f = entry.name
                fp = os.path.join(folder, f)
                if entry.is_dir():
                    is_group = True
                    self.scanFolder(fp)
                elif f == ".zgroup":
                    has_zgroup = True
                    valid_zgroup = True
                    try:
                        with open(fp, "r") as file:
                            json.load(file)
                    except:
                        valid_zgroup = False
                elif f == ".zattrs":
                    has_zattrs = True
                    valid_zattrs = True
                    try:
                        with open(fp, "r") as file:
                            json.load(file)
                    except:
                        valid_zattrs = False
                elif f == ".zarray":
                    has_zarray = True
                    valid_zarray = True
                    try:
                        with open(fp, "r") as file:
                            json.load(file)
                        with open(fp, "r") as file:
                            group_name = os.path.dirname(folder)
                            self.addZarrayFile(group_name, file.read())
                    except:
                        valid_zarray = False
                # if starting to encounter number files, break the loop
                elif f.replace(".", "").isnumeric():
                    break

        if is_group:
            zgroup = os.path.join(folder, ".zgroup")
            if not has_zgroup:
                self.missing_files.append(zgroup)
            if has_zgroup and not valid_zgroup:
                self.corrupt_files.append(zgroup)
        else:
            zarray = os.path.join(folder, ".zarray")
            if not has_zarray:
                self.missing_files.append(zarray)
            elif has_zarray and not valid_zarray:
                self.corrupt_files.append(zarray)
            if has_zattrs and not valid_zattrs:
                self.corrupt_files.append(
                    os.path.join(folder, ".zattrs")
                )
    
    def rectifyZarr(self):
        """Correct the internal files in the zarr."""
        # get the most common zarray formats per group
        zarray_strs = {}
        for group_name, zarray_dict in self.zarray_files.items():
            zarray_strs[group_name] = sorted([
                (n, zstr) for zstr, n in zarray_dict.items()
            ])[-1][1]

        for f in self.corrupt_files + self.missing_files:
            if os.path.basename(f) == ".zgroup":
                print("Correcting zarr file at:", f)
                with open(f, "w") as file:
                    file.write('{\n\t"zarr_format" : 2\n}')
            elif os.path.basename(f) == ".zarray":
                print("Correcting zarr file at:", f)
                group_name = os.path.dirname(os.path.dirname(f))
                with open(f, "w") as file:
                    file.write(zarray_strs[group_name])
            elif os.path.basename(f) == ".zattrs":
                print("Removing corrupt zattrs file at:", f)
                os.remove(f)
        
        removeEmptyFolders(self.zarr_fp)

def removeEmptyFolders(folder):
    """Remove empty folders within a folder.
    
        Params:
            folder (str): the parent folder.
    """
    with os.scandir(folder) as entries:
        for entry in entries:
            if entry.is_dir():
                fp = os.path.join(folder, entry.name)
                removeEmptyFolders(fp)
    try:
        os.rmdir(folder)
        print("Removing empty folder:", folder)
    except OSError:
        pass