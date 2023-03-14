from modules.pyrecon import Series, Transform

def importTransforms(series : Series, tforms_fp : str):
        """Import transforms from a text file.
        
            Params:
                series (Series): the series to import transforms to
                tforms_fp (str): the file path for the transforms file
        """
        # read through file
        with open(tforms_fp, "r") as f:
            lines = f.readlines()
        tforms = {}
        for line in lines:
            nums = line.split()
            if len(nums) != 7:
                print("Incorrect transform file format")
                return
            try:
                if int(nums[0]) not in series.sections:
                    print("Transform file section numbers do not correspond to this series")
                    return
                tforms[int(nums[0])] = [float(n) for n in nums[1:]]
            except ValueError:
                print("Incorrect transform file format")
                return
        
        # set tforms
        for section_num, tform in tforms.items():
            section = series.loadSection(section_num)
            # multiply pixel translations by magnification of section
            tform[2] *= section.mag
            tform[5] *= section.mag
            section.tforms[series.alignment] = Transform(tform)
            section.save()