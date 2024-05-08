import os

default_settings = {
    # user
    "user": os.getlogin(),

    # backup
    # "backup_dir": "",
    # "manual_backup_dir": "",
    # "manual_backup_delimiter": "-",
    # "manual_backup_date_delimiter": "-",
    # "manual_backup_time_delimiter": "-",
    # "manual_backup_name": True,
    # "manual_backup_utc": False,
    # "manual_backup_date": True,
    # "manual_backup_date_str": "%Y-%m-%d",
    # "manual_backup_time": False,
    # "manual_backup_time_str": "%H-%M",
    # "manual_backup_user": True,
    # "manual_backup_comment": True,
    "backup_delimiter": "-",
    "backup_series": True,
    "backup_filename": False,
    "backup_user": True,
    "backup_date": True,
    "backup_date_str": "%Y-%m-%d",
    "backup_time": True,
    "backup_time_str": "%H-%M",
    "backup_prefix" : False,
    "backup_prefix_str": "",
    "backup_suffix": False,
    "backup_suffix_str": "",

    # misc preferences
    "left_handed": False,
    "utc": False,

    # view
    "3D_xy_res": 0,  # 0-100
    "3D_smoothing": "humphrey",
    "smoothing_iterations": 10,
    "show_ztraces": True,
    "fill_opacity": 0.2,
    "find_zoom": 95.0,
    "show_flags": "unresolved",
    "display_closest": True,
    "flag_size": 14,

    # mouse tools
    "pointer": ["lasso", "exc"],
    "auto_merge": False,
    "trace_mode": "combo",  # combo, poly, scribble
    "knife_del_threshold": 1.0,
    "grid": [1, 1, 1, 1, 1, 1],
    "sampling_frame_grid": True,
    "flag_name": "",
    "flag_color": [255, 0, 0],
    
    # table columns
    "object_columns": {
        "Range": True,
        "Count": False,
        "Flat area": False,
        "Volume": False,
        "Radius": False,
        "Groups": True,
        "Trace tags": False,
        "Locked": True,
        "Last user": True,
        "Curate": False,
        "Alignment": False,
        "Comment": True
    },
    "trace_columns": {
        "Index": False,
        "Tags": True,
        "Hidden": True,
        "Closed": True,
        "Length": True,
        "Area": True,
        "Radius": True,
    },
    "flag_columns": {
        "Section": True,
        "Color": True,
        "Flag": True,
        "Resolved": False,
        "Last Comment": True
    },

    # shortcuts 
    "alloptions_act": "Shift+O",
    "flicker_act": "/",
    "hideall_act": "H",
    "showall_act": "A",
    "hideimage_act": "I",
    "decbr_act": "-",
    "incbr_act": "=",
    "deccon_act": "[",
    "inccon_act": "]",
    "blend_act": "Space",
    "homeview_act": "Home",
    "selectall_act": "Ctrl+A",
    "deselect_act": "Ctrl+D",
    "edittrace_act": "Ctrl+E",
    "mergetraces_act": "Ctrl+M",
    "mergeobjects_act": "Ctrl+Shift+M",
    "hidetraces_act": "Ctrl+H",
    "unhideall_act": "Ctrl+U",
    "pastetopalette_act": "Shift+G",
    "pastetopalettewithshape_act": "Ctrl+Shift+G",
    "unlocksection_act": "Ctrl+Shift+U",
    "changetform_act": "Ctrl+T",
    "undo_act": "Ctrl+Z",
    "redo_act": "Ctrl+Y",
    "copy_act": "Ctrl+C",
    "cut_act": "Ctrl+X",
    "paste_act": "Ctrl+V",
    "pasteattributes_act": "Ctrl+B",
    "findobjectfirst_act": "Ctrl+F",
    "findcontour_act": "Shift+F",
    "goto_act": "Ctrl+G",
    "open_act": "Ctrl+O",
    "save_act": "Ctrl+S",
    "manualbackup_act": "Ctrl+Shift+B",
    "newfromimages_act": "Ctrl+N",
    "restart_act": "Ctrl+R",
    "quit_act": "Ctrl+Q",
    "objectlist_act": "Ctrl+Shift+O",
    "togglecuration_act": "Ctrl+Shift+C",
    "tracelist_act": "Ctrl+Shift+T",
    "ztracelist_act": "Ctrl+Shift+Z",
    "sectionlist_act": "Ctrl+Shift+S",
    "flaglist_act": "Ctrl+Shift+F",
    "changealignment_act": "Ctrl+Shift+A",
    "modifytracepalette_act": "Ctrl+Shift+P",

    # palette-specific shortcuts
    "usepointer_act": "P",
    "usepanzoom_act": "Z",
    "useknife_act": "K",
    "usectrace_act": "C",
    "useotrace_act": "O",
    "usestamp_act": "S",
    "usegrid_act": "G",
    "useflag_act": "F",

    # series-related
    "series_code_pattern": "[0-9A-Za-z]+"
}

default_series_settings = {
    # "autoversion": False,
    # "autoversion_dir": "",
    # "manual_backup_dir": ""
    "autobackup": False,
    "backup_dir": "",
}
