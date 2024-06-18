from PySide6.QtWidgets import (
    QInputDialog,
    QToolButton,
    QMessageBox,
    QWidget,
    QScrollArea
)
from PySide6.QtCore import Qt

from PyReconstruct.modules.datatypes import Series, Trace
from PyReconstruct.modules.gui.utils import notify

from .quick_dialog import QuickTabDialog, getLayout

class TracePaletteDialog(QuickTabDialog):

    def __init__(self, parent, series : Series):
        """Create a multi-tabbed trace palette dialog."""
        self.series = series
        structures = {}
        for name, palette in self.series.palette_traces.items():
            structures[name] = self.getStructure(palette)
        
        QuickTabDialog.__init__(self, parent, structures, "Trace Palette", grid=True)

        # set up the tab widget
        self.tab_widget.mousePressEvent = self.editTab  # allow tabs to be edited

        for index in range(self.tab_widget.count()):  # select the current tab widget
            if self.tab_widget.tabText(index) == self.series.palette_index[0]:
                self.tab_widget.setCurrentIndex(index)
                break
        
        # allow tabs to be added
        self.add_bttn = QToolButton(self)
        self.add_bttn.setText('+')
        font = self.add_bttn.font()
        font.setBold(True)
        self.add_bttn.setFont(font)
        self.tab_widget.setCornerWidget(self.add_bttn)
        self.add_bttn.clicked.connect(self.addPalette)

        # allow tabs to be removed
        if self.tab_widget.count() > 1:
            self.tab_widget.setTabsClosable(True)
        else:
            self.tab_widget.setTabsClosable(False)
        self.tab_widget.tabCloseRequested.connect(self.removePalette)
    
    def getStructure(self, trace_list : list):
        """Create a dialog from a trace list.
        
            Params:
                trace_list (list): the list of traces to create the dialog
        """
        structure = [["Name", "Color", "Shape", "Tags", "Fill Mode", "Fill Condition", "Stamp Radius"]]
        for t in trace_list:
            t_copy = t.copy()
            t_copy.resize(1)
            shape = t_copy.points
            entry = [
                (True, "text", t.name),
                (True, "color", t.color),
                (True, "shape", shape),
                ("text", ", ".join(t.tags)),
                (True, "combo", ["none", "transparent", "solid"], t.fill_mode[0]),
                (True, "combo", ["none", "selected", "unselected", "always"], t.fill_mode[1]),
                (True, "float", round(t.getRadius(), 7))
            ]
            structure.append(entry)
        return structure
    
    def editTab(self, event):
        """Overwritten from QTabWidget: allows user to edit tab names."""
        super().mousePressEvent(event)

        if event.buttons() == Qt.RightButton:
            index = self.tab_widget.tabBar().tabAt(event.pos())
            text = self.tab_widget.tabText(index)
            if not text:
                return

            new_text, confirmed = QInputDialog.getText(
                self,
                "Rename",
                "Enter new palette name:",
                text=text
            )
            if not confirmed or not new_text or new_text == text:
                return
            
            if new_text in self.inputs:
                notify("Palette name already exists.")
                return

            # iterate to preserve order
            new_inputs = {}
            for key in self.inputs:
                if key == text:
                    new_inputs[new_text] = self.inputs[text]
                else:
                    new_inputs[key] = self.inputs[key]
            self.inputs = new_inputs

            self.tab_widget.setTabText(index, new_text)
    
    def addPalette(self):
        """Add a palette."""
        new_text, confirmed = QInputDialog.getText(
            self,
            "New palette",
            "Enter new palette name:"
        )
        if not confirmed or not new_text:
            return
        
        if new_text in self.inputs:
            notify("This palette name already exists.")
            return

        structure = self.getStructure(Series.getDefaultPaletteTraces())
        layout, inputs = getLayout(self, structure, grid=True)
        self.inputs[new_text] = inputs

        w = QWidget(self)
        w.setLayout(layout)
        self.tab_widget.addTab(w, new_text)

        if self.tab_widget.count() > 1:
            self.tab_widget.setTabsClosable(True)
        else:
            self.tab_widget.setTabsClosable(False)
    
    def removePalette(self, index):
        """Remove a palette."""
        text = self.tab_widget.tabText(index)
        response = QMessageBox.warning(
            self,
            "",
            f"WARNING: Are you sure you would like to remove {text}?",
            QMessageBox.Ok,
            QMessageBox.Cancel
        )
        if not response == QMessageBox.Ok:
            return
        
        del(self.inputs[text])
        self.tab_widget.removeTab(index)

        if self.tab_widget.count() > 1:
            self.tab_widget.setTabsClosable(True)
        else:
            self.tab_widget.setTabsClosable(False)

    def exec(self):
        """Run the dialog."""
        response, confirmed = super().exec()
        if not confirmed:
            return None, False
        
        # modify the series directly
        self.series.palette_index[0] = response["current_tab_text"]
        del(response["current_tab_text"])
        
        self.series.palette_traces = {}
        for palette_name, inputs in response.items():
            palette_traces = []
            while inputs:
                (
                    name,
                    color,
                    shape,
                    tags,
                    fill_mode,
                    fill_condition,
                    stamp_radius
                ) = inputs[:7]
                inputs = inputs[7:]

                x = [p[0] for p in shape]
                y = [p[1] for p in shape]
                tags = tags.split(", ")

                t = Trace.fromList([
                    name, x, y, color, True, False, False,
                    (fill_mode, fill_condition), tags
                ])
                t.resize(stamp_radius)
                
                palette_traces.append(t)
            
            self.series.palette_traces[palette_name] = palette_traces
        
        return None, True