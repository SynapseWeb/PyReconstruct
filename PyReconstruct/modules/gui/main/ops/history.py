"""Log history operations."""

from pathlib import Path

from PyReconstruct.modules.gui.utils import notifyConfirm
from PyReconstruct.modules.gui.dialog import FileDialog, QuickDialog
from PyReconstruct.modules.gui.table import HistoryTableWidget


class HistoryOperations:

    def viewSeriesHistory(self):
        """View series history."""
        HistoryTableWidget(
            self.series.getFullHistory(),
            self
        )
    
    def exportLog(self):
        """Export complete log history"""

        pass

    def offloadLog(self):
        """Offload log history to external file for storage."""

        ## Notify user
        note_offloading = (
            f"Log creation in PyReconstruct is still a work in progress. Series with extensive "
            f"log history may become very large. You can reduce series size in some cases by "
            f"offloading and saving log history externally as a CSV file. \n\nClick OK to select "
            f"where to save the log CSV."
        )

        confirm = notifyConfirm(note_offloading)

        if not confirm:
            return

        ## Get filepath

        path_check_ok = False

        while not path_check_ok:

            output_fp = FileDialog.get("save", self, "Save data as CSV file", "*.csv", "log_export.csv")
            if not output_fp:

                return

            elif Path(output_fp).exists():

                notify(
                    f"To prevent accidentally overwriting previously offloaded logs, "
                    f"please provide a filename that does not yet exist."
                )

            else:

                path_check_ok = True

        ## Query for age of exported existing data

        structure = [
            ["Export history older than x days: ", ("int", 10)],
        ]
        response, confirmed = QuickDialog.get(self, structure, "Export log history")
        
        if not confirmed:
            return

        days = response[0]

        ## Export for external storage

        LogSet.exportLogHistory(self.series.hidden_dir, output_fp, days)
        self.series.addLog(None, None, f"Offloaded log to {output_fp}")

        notify(
            f"Log offloaded to external CSV file.\n\n"
            f"Be sure to save offloaded log data in a safe place."
        )

        return None

    def updateCurationFromHistory(self):
        """Update the series curation from the history."""
        self.field.series_states.addState()
        self.series.updateCurationFromHistory()
        self.field.table_manager.recreateTables()
        self.seriesModified()
    

