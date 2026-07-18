from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QDialogButtonBox,
)

from PyReconstruct.modules.gui.utils import notify


def _to_int(token : str):
    """Convert a token to an int, or return None if it is not a plain decimal
    number.

    str.isdecimal() (not isdigit()) is the correct gate: isdigit() accepts
    characters like superscripts ("5²") and circled digits that int() then
    refuses, which would raise ValueError. The try/except covers any remaining
    edge case so a weird token is reported instead of crashing.
    """
    if not token.isdecimal():
        return None
    try:
        return int(token)
    except ValueError:
        return None


def parse_section_spec(text : str, valid_sections) -> tuple:
    """Parse a section spec string into a set of section numbers.

    Accepts comma/space-separated tokens, each either a single number ("12")
    or an inclusive range ("10-15"). Returns the parsed numbers that exist in
    valid_sections, a list of tokens that were malformed or entirely out of
    range, and a list describing requested sections that do not exist (e.g. a
    range that overhangs the series), so nothing is silently dropped.

        Params:
            text (str): the spec, e.g. "10-15, 20, 22"
            valid_sections (iterable): the section numbers that exist
        Returns:
            (tuple): (set of valid section numbers, list of bad tokens,
                      list of descriptions of nonexistent requested sections)
    """
    valid = set(valid_sections)
    chosen = set()
    bad = []
    missing = []

    for token in text.replace(",", " ").split():
        if "-" in token.strip("-"):  # a range like 10-15
            parts = token.split("-")
            if len(parts) != 2:
                bad.append(token)
                continue
            lo, hi = _to_int(parts[0]), _to_int(parts[1])
            if lo is None or hi is None:
                bad.append(token)
                continue
            if lo > hi:
                lo, hi = hi, lo
            # intersect the range with the existing sections WITHOUT
            # materializing it: iterating range(lo, hi + 1) would hang the UI
            # on a huge upper bound like "1-999999999"
            matched = {n for n in valid if lo <= n <= hi}
            if not matched:
                bad.append(token)
                continue
            chosen.update(matched)
            missing_count = (hi - lo + 1) - len(matched)
            if missing_count:
                missing.append(f"{missing_count} section(s) in {token}")
        else:  # a single section number
            n = _to_int(token)
            if n is None:
                bad.append(token)
                continue
            if n in valid:
                chosen.add(n)
            else:
                bad.append(token)

    return chosen, bad, missing


class CopyToSectionsDialog(QDialog):
    """Pick the target sections to copy the selected trace(s) onto."""

    def __init__(self, parent, series):
        super().__init__(parent)
        self.series = series
        self.valid_sections = set(series.sections.keys())
        self.sections = None

        current = series.current_section
        self.smin, self.smax = min(self.valid_sections), max(self.valid_sections)
        smin, smax = self.smin, self.smax

        self.setWindowTitle("Copy to sections")

        vlayout = QVBoxLayout()

        info = QLabel(self, text=(
            "Copy the selected trace(s) onto other sections at the same "
            "location.\n"
            f"The current section ({current}) is left unchanged.\n"
            f"Enter section numbers or ranges from {smin} to {smax}, "
            "e.g. \"10-20\" or \"5, 8, 11\"."
        ))
        vlayout.addWidget(info)

        self.spec_input = QLineEdit(self)
        self.spec_input.setPlaceholderText("e.g. 10-20 or 5, 8, 11")
        vlayout.addWidget(self.spec_input)

        buttonbox = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)
        vlayout.addSpacing(10)
        vlayout.addWidget(buttonbox)

        self.setLayout(vlayout)

    def accept(self):
        chosen, bad, missing = parse_section_spec(
            self.spec_input.text(), self.valid_sections
        )
        if bad:
            notify("Invalid or out-of-range section(s): " + ", ".join(bad))
            return
        if missing:
            notify(
                "Some requested sections do not exist: "
                + "; ".join(missing) + "\n"
                f"Sections in this series range from {self.smin} to {self.smax}."
            )
            return
        if not chosen:
            notify("Please enter at least one valid section.")
            return
        self.sections = chosen
        super().accept()

    def get(self):
        """Run the dialog.

            Returns:
                (tuple): (set of section numbers, confirmed bool)
        """
        if self.exec():
            return self.sections, True
        return None, False
