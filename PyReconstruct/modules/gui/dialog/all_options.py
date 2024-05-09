import os

from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QTabWidget,
    QVBoxLayout,
    QHBoxLayout,
    QDialogButtonBox,
    QPushButton,
    QScrollArea
)
from PySide6.QtGui import (
    QPainter,
    QColor
)
from .quick_dialog import QuickDialog

from PyReconstruct.modules.datatypes import Series

class AllOptionsDialog(QDialog):

    def __init__(self, parent, series : Series):
        """Create the dialog for all series/user options
        
            Params:
                parent (QWidget): the parent widget
                series (Series): the series with optionsto view/modify
        """
        super().__init__(parent)
        self.series = series
        self.tabs = QTabWidget(self)
        self.createWidgets()
        self.placeWidgets()

        full_vlayout = QVBoxLayout()
        full_vlayout.addWidget(self.tabs)    

        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        buttonbox = QDialogButtonBox(QBtn)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)

        reset_defaults_button = QPushButton("Reset Defaults")
        reset_defaults_button.clicked.connect(self.resetDefaults)
        buttonbox.addButton(reset_defaults_button, QDialogButtonBox.ResetRole)

        full_vlayout.addWidget(buttonbox)

        self.setLayout(full_vlayout)
    
    def getWidgetsLayout(self, structure : list):
        """Create a layout from a predifined widget structure

        (Ideally the structure for a full tab)
        
            Params:
                structure (list): the desired layout structure
        """
        vlayout = QVBoxLayout()
        for line in structure:
            hlayout = QHBoxLayout()
            for item in line:
                if type(item) is list:
                    l = self.getWidgetsLayout(item)
                    hlayout.addLayout(l)
                else:
                    w = self.all_widgets[item]
                    hlayout.addWidget(w)
            vlayout.addLayout(hlayout)
        return vlayout

    def placeWidgets(self):
        """"""
        # this is what goes into 
        tab_structure = {
            "Mouse Tools": [
                ["pointer"],
                ["trace"],
                ["knife"],
                ["grid"],
                ["flag_defaults"]
            ],
            "View": [
                ["show_ztraces"],
                ["show_flags"],
                ["fill_opacity"],
                ["find_zoom"],
                ["smoothing_3D"]
            ],
            "User/Series": [
                ["user"],
                # ["auto-versioning"],
                ["step"],
                ["left_handed"],
                ["time"]
            ],
            "Lists": [
                ["object_columns"],
                ["trace_columns"],
                ["flag_columns"]
            ]
        }

        for tab_name, structure, in tab_structure.items():
            widget = QWidget(self)
            vlayout = self.getWidgetsLayout(structure)
            widget.setLayout(vlayout)
            qsa = QScrollArea()
            qsa.setWidgetResizable(True)
            qsa.setWidget(widget)
            self.tabs.addTab(qsa, tab_name)
    
    def createWidgets(self, use_defaults=False):
        """Create the widgets for each of the options
        
            Params:
                use_defaults (bool): True if all values should be set at defaults instead of current settings
        """
        self.all_widgets = {}
        # pointer
        s, t = tuple(self.series.getOption("pointer", use_defaults))
        structure = [
            ["Shape:"],
            [("radio", ("Rectangle", s=="rect"), ("Lasso", s=="lasso"))],
            ["Type:"],
            [("radio", ("Include intersected traces", t=="inc"), ("Exclude intersected traces", t=="exc"))],
            [("check", ("Diplay closest field item", self.series.getOption("display_closest", use_defaults)))]
        ]
        def setOption(response):
            s = "rect" if response[0][0][1] else "lasso"
            t = "inc" if response[1][0][1] else "exc"
            self.series.setOption("pointer", [s, t])
            self.series.setOption("display_closest", response[2][0][1])
        self.addOptionWidget("pointer", structure, setOption)

        # trace
        trace_mode = self.series.getOption("trace_mode")
        structure = [
            ["Mode:"],
            [("radio",
                ("Scribble", trace_mode == "scribble"),
                ("Poly", trace_mode == "poly"),
                ("Combo", trace_mode == "combo")
            )],
            [("check", ("Automatically merge selected traces", self.series.getOption("auto_merge", use_defaults)))]
        ]
        def setOption(response):
            if response[0][0][1]:
                new_mode = "scribble"
            elif response[0][1][1]:
                new_mode = "poly"
            else:
                new_mode = "combo"
            self.series.setOption("trace_mode", new_mode)
            self.series.setOption("auto_merge", response[1][0][1])
        self.addOptionWidget("trace", structure, setOption)

        # grid
        w, h, dx, dy, nx, ny = self.series.getOption("grid", use_defaults)
        structure = [
            [None, "X", "Y"],
            ["Element size:", ("float", w), ("float", h)],
            ["Distance:", ("float", dx), ("float", dy)],
            ["Number", ("int", nx), ("int", ny)],
            [("check", ("Sampling frame", self.series.getOption("sampling_frame_grid")))]
        ]
        def setOption(response):
            self.series.setOption("grid", response[:6])
            self.series.setOption("sampling_frame_grid", response[6][0][1])

        self.addOptionWidget("grid", structure, setOption, grid=True)

        # flag_defaults
        structure = [
            ["Default name:", ("text", self.series.getOption("flag_name", use_defaults)), None],
            ["Default color:", ("color", self.series.getOption("flag_color", use_defaults)), None],
        ]
        def setOption(response):
            self.series.setOption("flag_name", response[0])
            self.series.setOption("flag_color", response[1])
        self.addOptionWidget("flag_defaults", structure, setOption)

        # knife
        structure = [
            ["When using the knife, objects smaller than this percent"],
            ["of the original trace area will be automatically deleted."],
            None,
            ["Knife delete threshold (%):", ("float", self.series.getOption("knife_del_threshold", use_defaults), (0, 100)), None]
        ]
        def setOption(response):
            self.series.setOption("knife_del_threshold", response[0])
        self.addOptionWidget("knife", structure, setOption)

        # 3D
        opt = self.series.getOption("3D_smoothing", use_defaults)
        structure = [
            ["XY Resolution:"],
            ["less detail (fast)", ("slider", self.series.getOption("3D_xy_res")), "more detail (slow)"],
            [" "],
            ["3D smoothing:"],
            [("radio",
                ("Laplacian (smoothest, for visualizations only)", opt == "laplacian"),
                ("Humphrey", opt == "humphrey"),
                ("Mutable Diffusion Laplcian", opt == "mut_dif_laplacian"),
                ("Taubin", opt == "taubin"),
                ("None (least smooth)", opt == "none"))],
            ["Smoothing iterations:", ("int", self.series.getOption("smoothing_iterations"))]
        ]
        def setOption(response):
            self.series.setOption("3D_xy_res", response[0])
            if response[1][0][1]:
                smoothing_alg = "laplacian"
            elif response[1][1][1]:
                smoothing_alg = "humphrey"
            elif response[1][2][1]:
                smoothing_alg = "mut_dif_laplacian"
            elif response[1][3][1]:
                smoothing_alg = "taubin"
            else:
                smoothing_alg = "none"
            self.series.setOption("3D_smoothing", smoothing_alg)
            self.series.setOption("smoothing_iterations", response[2])
        self.addOptionWidget("smoothing_3D", structure, setOption)

        # show_ztraces
        structure = [
            [("check", ("show ztraces in field", self.series.getOption("show_ztraces", use_defaults)))],
        ]
        def setOption(response):
            self.series.setOption("show_ztraces", response[0][0][1])
        self.addOptionWidget("show_ztraces", structure, setOption)

        # show_flags
        show_flags = self.series.getOption("show_flags", use_defaults)
        structure = [
            ["Display flags:"],
            [("radio",
              ("All flags", show_flags == "all"),
              ("Only unresolved flags", show_flags == "unresolved"),
              ("No flags", show_flags == "none")
            )]
        ]
        def setOption(response):
            if response[0][0][1]: show_flags = "all"
            elif response[0 ][2][1]: show_flags = "none"
            else: show_flags = "unresolved"
            self.series.setOption("show_flags", show_flags)
        self.addOptionWidget("show_flags", structure, setOption)

        # flag_size
        structure = [
            ["Flag size:", ("int", self.series.getOption("flag_size", use_defaults))]
        ]
        def setOption(response):
            self.series.setOption("flag_size", response[0])
        self.addOptionWidget("flag_size", structure, setOption)

        # fill_opacity
        structure = [
            ["Transparent fill opacity:", ("float", self.series.getOption("fill_opacity", use_defaults))]
        ]
        def setOption(response):
            self.series.setOption("fill_opacity", response[0])
        self.addOptionWidget("fill_opacity", structure, setOption)

        # find_zoom
        structure = [
            ["Zoom level for finding contours:", ("float", self.series.getOption("find_zoom", use_defaults))]
        ]
        def setOption(response):
            self.series.setOption("find_zoom", response[0])
        self.addOptionWidget("find_zoom", structure, setOption)

        # user
        structure = [
            ["Username:", ("text", self.series.user)]
        ]
        def setOption(response):
            self.series.user = response[0]
        self.addOptionWidget("user", structure, setOption)

        # left_handed
        structure = [
            [("check", ("left-handed", self.series.getOption("left_handed", use_defaults)))]
        ]
        def setOption(response):
            self.series.setOption("left_handed", response[0][0][1])
        self.addOptionWidget("left_handed", structure, setOption)

        # utc
        structure = [
            [("check", ("use UTC time", self.series.getOption("utc", use_defaults)))]
        ]
        def setOption(response):
            self.series.setOption("utc", response[0][0][1])
        self.addOptionWidget("time", structure, setOption)

        # columns
        for table_type in ("object", "trace", "flag"):
            structure = [
                [("check", *tuple(self.series.getOption(table_type + "_columns", use_defaults).items()))]
            ]
            def setOption(response):
                self.series.setOption(table_type + "_columns", dict(response[0]))
            self.addOptionWidget(table_type + "_columns", structure, setOption)
        
        # backup
        # structure = [
        #     [" "],
        #     [("check", ("Use auto-versioning", self.series.getOption("autoversion")))],
        #     [f"Auto-version directory for {self.series.code}:"],
        #     [("dir", self.series.getOption("autoversion_dir", use_defaults))],
        # ]
        # def setOption(response):
        #     if response[0][0][1] and response[1] and os.path.isdir(response[1]):
        #             self.series.setOption("autoversion", True)
        #             self.series.setOption("autoversion_dir", response[1])
        #     else:
        #         self.series.setOption("autoversion", False)
        #         if not response[1] or not os.path.isdir(response[1]):
        #             self.series.setOption("autoversion_dir", "")

        # self.addOptionWidget("auto-versioning", structure, setOption)

        # step
        structure = [
            ["Course step:", ("float", self.series.getOption("big_dist", use_defaults))],
            ["Fine step:", ("float", self.series.getOption("med_dist", use_defaults))],
            ["Finest step:", ("float", self.series.getOption("small_dist", use_defaults))]
        ]
        def setOption(response):
            self.series.setOption("big_dist", response[0])
            self.series.setOption("med_dist", response[1])
            self.series.setOption("small_dist", response[2])
        self.addOptionWidget("step", structure, setOption)
    
    def addOptionWidget(self, name : str, structure : list, setOption, grid=False):
        """Add a widget to the all_widgets dictionary
        
            Params:
                name (str): the desired name for the widget
                structure (list): the QuickDialog structure for the widget
                setOption (function): the function for setting the widget option once accepted
                grid (bool): True if widget structure should be a grid instead of rows
        """
        title = name.replace("_", " ").title()
        self.all_widgets[name] = OptionWidget(self, title, structure, self.series, setOption, grid)
    
    def accept(self):
        """Overwritten--called when OK is pressed"""
        widgets = self.all_widgets.values()
        for w in widgets:
            if not w.accept():
                return False
        for w in widgets:
            w.set()
        super().accept()
        return True

    def resetDefaults(self):
        """Reset the default values for the widget inputs"""
        # keep track of the current tab
        current_tab = self.tabs.currentIndex()
        # reset the widget and use defaults
        self.tabs.clear()
        self.createWidgets(use_defaults=True)
        self.placeWidgets()
        # set the tab
        self.tabs.setCurrentIndex(current_tab)

class OptionWidget(QuickDialog):

    def __init__(
            self, 
            parent, 
            title : str, 
            structure : list, 
            series : Series, 
            setOption, 
            grid=False
        ):
        """Create a widget for a series option
        
            Params:
                parent (QWidget): the parent widget
                title (str): the title of the widget
                structure (list): the structure for the widget
                series (Series): the series lnked to the options
                setOption (function): the function to set the options
                grid (bool): True if structure should be grid instead of rows
        """
        super().__init__(parent, structure, title, grid, include_confirm=False)
        self.series = series
        self.setOption = setOption
    
    def set(self):
        """Set the series option for the widget"""
        self.setOption(self.responses)
    
    def paintEvent(self, event):
        super().paintEvent(event)
        # draw the border manually
        painter = QPainter(self)
        painter.setPen(QColor(0, 0, 0))  # Set the color of the border
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))  # Adjust the rectangle to draw inside the border