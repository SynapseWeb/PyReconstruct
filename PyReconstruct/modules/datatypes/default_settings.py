import os

# MFO = modifiable from options dialog

def get_username() -> str:
    """Return username."""
    try:
        user = os.getlogin()
    except FileNotFoundError:
        user = os.environ.get("USER")
    return user

default_settings = {
    # user
    "username": get_username(),  # MFO

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
    "left_handed": False,  # MFO
    "utc": False,  # MFO
    "cpu_max": 100, 

    # view
    "3D_xy_res": 0,  # 0-100  # MFO
    "3D_smoothing": "humphrey",  # MFO
    "smoothing_iterations": 10,  # MFO
    "screenshot_res": 300,
    "show_ztraces": True,  # MFO
    "fill_opacity": 0.2,  # MFO
    "find_zoom": 95.0,  # MFO
    "show_flags": "unresolved",  # MFO
    "display_closest": True,  # MFO
    "flag_size": 14,  # MFO

    # mouse tools
    "pointer": ["lasso", "exc"],  # MFO
    "auto_merge": False,  # MFO
    "roll_average": False,
    "roll_window": 10,
    "roll_knife_average": False,
    "roll_knife_window": 10,
    "trace_mode": "combo",  # combo, poly, scribble  # MFO
    "knife_del_threshold": 1.0,  # MFO
    "grid": [1, 1, 1, 1, 1, 1],  # MFO
    "sampling_frame_grid": True,  # MFO
    "flag_name": "",  # MFO
    "flag_color": [255, 0, 0],  # MFO
    "palette_inc_all": True,

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
    "incpaletteup_act": "Ctrl+=",
    "incpalettedown_act": "Ctrl+-",
    "sethosts_act": "Ctrl+Shift+H",

    # palette-specific shortcuts
    "usepointer_act": "P",
    "usepanzoom_act": "Z",
    "useknife_act": "K",
    "usectrace_act": "C",
    "useotrace_act": "O",
    "usestamp_act": "S",
    "usegrid_act": "G",
    "useflag_act": "F",
    "usehost_act": "Q",

    # series-related
    "series_code_pattern": "[0-9A-Za-z]+",  # MFO

    # theme
    "theme": "default",  # MFO

    # 3D
    "translate_step_3D": 0.1,  # MFO
    "rotate_step_3D": 10,  # MFO

    # recently opened series
    "recently_opened_series": [],

    # scale bar settings
    "scale_bar_width": 25,  # displayed as this percentage of the screen (min should be 20)
    "show_scale_bar_text": True,
    "show_scale_bar_ticks": True,
}

default_series_settings = {
    # "autoversion": False,
    # "autoversion_dir": "",
    # "manual_backup_dir": ""
    "autobackup": False,
    "backup_dir": "",
}
