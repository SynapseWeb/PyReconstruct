"""Alignments > Import alignments gains a ".jser" source, with an overwrite prompt.

Importing a colleague's alignment used to be reachable only through
``Series > Import > from series``, the seven-tab whole-series merge dialog, while
``Alignments > Import alignments`` offered ".txt" and SWiFT only. The three
sources now sit together, behind ``MainWindow.importAlignmentsFromSeries``.

Three things get guards, because each one is a claim the change makes:

1. The menu row exists, sits in the Alignments import submenu, and is wired to
   the new handler. Read out of the real ``return_menubar`` tree, so deleting
   the row fails the test.
2. The handler runs the import it advertises: it opens the chosen series, honors
   a cancelled calibration check and a cancelled dialog, hands
   ``Series.importTransforms`` exactly the ``(source, target)`` pairs the dialog
   returned, and closes the other series on every exit path including the
   cancelled ones (a leaked open Series holds a temp directory).
3. The overwrite prompt fires if and only if a target name is already taken,
   names the colliding alignments, and a declined prompt imports nothing.

``MainWindow(...)`` cannot be constructed without a real series on disk, so the
handler tests call the unbound method against a stub carrying just the surface
it touches.

The overwrite decision itself lives in ``collidingImportNames``, which is Qt-free
on purpose: "warn only when a same-named alignment actually exists" is a set
question, and pinning it as one keeps the prompt tests about the prompt.
"""

import types

import pytest

from PyReconstruct.modules.gui.dialog.import_series import (
    ImportAlignmentsDialog,
    ImportAs,
    MultiImportAs,
    collidingImportNames,
)


# --------------------------------------------------------------------------- #
# stubs
# --------------------------------------------------------------------------- #
class _Anything:
    """Any attribute access yields a callable returning an empty list."""

    def __init__(self, **kw):
        self.__dict__.update(kw)

    def __getattr__(self, name):
        return lambda *a, **k: []


class _SeriesStub(_Anything):
    def __init__(self, alignments=(), jser_fp="/nonexistent/other.jser"):
        super().__init__(
            jser_fp=jser_fp,
            object_groups=_Anything(groups={}),
            groups_visibility={},
            user_columns={},
            alignments=set(alignments),
        )

        self.opts = {"recently_opened_series": []}

    def getOption(self, name, get_default=False):
        return self.opts.get(name, "")

    def setOption(self, name, value):
        self.opts[name] = value


@pytest.fixture(scope="module")
def qapp():
    """A QApplication for the widget tests, reused across the module."""
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication(["test"])


def _menubar(series=None):
    from PyReconstruct.modules.gui.main.menubar import return_menubar

    mw = _Anything(
        series=series if series is not None else _SeriesStub(),
        field=_Anything(),
        mouse_palette=_Anything(),
    )
    return return_menubar(mw)


def _submenu(items, attr_name):
    for item in items:
        if isinstance(item, dict):
            if item["attr_name"] == attr_name:
                return item["opts"]
            found = _submenu(item["opts"], attr_name)
            if found is not None:
                return found
    return None


# --------------------------------------------------------------------------- #
# 1. the menu row
# --------------------------------------------------------------------------- #
def test_jser_source_sits_in_the_alignments_import_submenu():
    opts = _submenu(_menubar(), "importalignmentsmenu")
    assert opts is not None, "importalignmentsmenu is gone"
    names = [entry[0] for entry in opts if isinstance(entry, tuple)]
    assert "import_jser_alignments_act" in names, (
        "Alignments > Import alignments has no .jser source"
    )


def test_all_three_alignment_sources_are_siblings_and_jser_is_first():
    """The point of the change: one place to look, .jser at the top."""
    opts = _submenu(_menubar(), "importalignmentsmenu")
    names = [entry[0] for entry in opts if isinstance(entry, tuple)]
    assert names == [
        "import_jser_alignments_act",
        "importtransforms_act",
        "import_swift_transforms_act",
    ]


def test_jser_source_label_names_the_format():
    opts = _submenu(_menubar(), "importalignmentsmenu")
    labels = {entry[0]: entry[1] for entry in opts if isinstance(entry, tuple)}
    assert labels["import_jser_alignments_act"] == "From another series (.jser)..."


def test_jser_source_is_wired_to_the_new_handler():
    """The callback must be MainWindow.importAlignmentsFromSeries, not a lambda
    that quietly reopens the whole-series merge dialog."""
    from PyReconstruct.modules.gui.main.main_window import MainWindow

    assert hasattr(MainWindow, "importAlignmentsFromSeries")

    called = []

    class _Recorder(_Anything):
        def __init__(self):
            super().__init__(series=_SeriesStub(), field=_Anything(),
                             mouse_palette=_Anything())

        def importAlignmentsFromSeries(self, *a, **k):
            called.append(True)

    from PyReconstruct.modules.gui.main.menubar import return_menubar

    opts = _submenu(return_menubar(_Recorder()), "importalignmentsmenu")
    callbacks = {e[0]: e[3] for e in opts if isinstance(e, tuple)}
    callbacks["import_jser_alignments_act"]()
    assert called == [True]


# --------------------------------------------------------------------------- #
# 2. collidingImportNames: the overwrite decision, Qt-free
# --------------------------------------------------------------------------- #
def test_no_collision_when_every_target_name_is_new():
    assert collidingImportNames([("a", "a"), ("b", "b")], {"c"}) == []


def test_collision_reported_for_a_taken_target_name():
    assert collidingImportNames([("a", "existing")], {"existing"}) == ["existing"]


def test_collision_follows_the_target_name_not_the_source_name():
    """Renaming on import is how a user avoids the overwrite, so a taken SOURCE
    name with a free target must not warn."""
    assert collidingImportNames([("existing", "fresh")], {"existing"}) == []


def test_collisions_are_deduped_in_first_seen_order():
    entries = [("a", "y"), ("b", "x"), ("c", "x")]
    assert collidingImportNames(entries, {"x", "y"}) == ["y", "x"]


# --------------------------------------------------------------------------- #
# 3. MultiImportAs: overwrite is opt-in, prompted, and refusable
# --------------------------------------------------------------------------- #
def _multi(qapp, monkeypatch, allow_overwrite, entries, self_items,
           confirm=True):
    """Build a MultiImportAs whose rows are fixed, with the modals recorded."""
    import PyReconstruct.modules.gui.dialog.import_series as mod

    notices, prompts = [], []
    monkeypatch.setattr(mod, "notify", lambda msg, *a, **k: notices.append(msg))
    monkeypatch.setattr(
        mod, "notifyConfirm",
        lambda msg, *a, **k: (prompts.append(msg), confirm)[1],
    )

    widget = MultiImportAs(
        None,
        [source for source, _target in entries],
        set(self_items),
        "alignment",
        allow_overwrite=allow_overwrite,
    )
    monkeypatch.setattr(widget, "getEntries", lambda: list(entries))
    return widget, notices, prompts


def test_overwrite_is_rejected_outright_when_not_allowed(qapp, monkeypatch):
    """The behavior kept for palettes and brightness/contrast profiles."""
    widget, notices, prompts = _multi(
        qapp, monkeypatch, False, [("a", "taken")], {"taken"}
    )
    assert widget.getResponse() == (None, False)
    assert prompts == []
    assert notices == ["Alignment name already exists in current series."]


def test_no_prompt_when_nothing_would_be_overwritten(qapp, monkeypatch):
    """Only warn when a same-named alignment actually exists."""
    widget, notices, prompts = _multi(
        qapp, monkeypatch, True, [("a", "fresh")], {"taken"}
    )
    response, confirmed = widget.getResponse()
    assert (response, confirmed) == ([("a", "fresh")], True)
    assert prompts == []
    assert notices == []


def test_prompt_names_the_alignments_and_says_they_are_replaced(qapp, monkeypatch):
    widget, _notices, prompts = _multi(
        qapp, monkeypatch, True, [("a", "taken"), ("b", "fresh")], {"taken"}
    )
    response, confirmed = widget.getResponse()
    assert confirmed is True
    assert response == [("a", "taken"), ("b", "fresh")]

    assert len(prompts) == 1
    message = prompts[0]
    assert "taken" in message
    assert "fresh" not in message, "the prompt named an alignment that is not at risk"
    assert "replace" in message.lower()


def test_declining_the_prompt_cancels_the_import(qapp, monkeypatch):
    widget, _notices, prompts = _multi(
        qapp, monkeypatch, True, [("a", "taken")], {"taken"}, confirm=False
    )
    assert widget.getResponse() == (None, False)
    assert len(prompts) == 1


def test_prompt_is_singular_or_plural_to_match_the_collisions(qapp, monkeypatch):
    _w, _n, one = _multi(qapp, monkeypatch, True, [("a", "x")], {"x", "y"})
    _w.getResponse()
    assert "alignments:" not in one[0]

    _w2, _n2, two = _multi(
        qapp, monkeypatch, True, [("a", "x"), ("b", "y")], {"x", "y"}
    )
    _w2.getResponse()
    assert "alignments:" in two[0]


def test_prompt_makes_no_claim_about_undo(qapp, monkeypatch):
    """Importing alignments is undoable, so the prompt must not say otherwise.

    The wording is pinned in full because the claim it must not carry is one
    sentence long: warning that the old transforms are gone for good would be
    wrong, and a hedge about undo would be no better. Say what the import
    replaces and stop.
    """
    widget, _notices, prompts = _multi(
        qapp, monkeypatch, True, [("a", "taken")], {"taken"}
    )
    widget.getResponse()

    assert prompts == [
        "This series already has the following alignment:\n"
        "\n"
        "    taken\n"
        "\n"
        "Importing under this name will replace the existing alignment on "
        "every section.\n"
        "\n"
        "Continue?"
    ]
    assert "undo" not in prompts[0].lower()


# --------------------------------------------------------------------------- #
# ImportAs: the target name prefills from the source
# --------------------------------------------------------------------------- #
def test_target_name_prefills_from_source_when_asked(qapp):
    row = ImportAs(None, ["align-a", "align-b"], default_to_source=True)
    assert row.input_2.text() == "align-a"
    row.input_1.setCurrentIndex(1)
    assert row.input_2.text() == "align-b"


def test_target_name_stops_following_once_the_user_types(qapp):
    row = ImportAs(None, ["align-a", "align-b"], default_to_source=True)
    row.input_2.setText("mine")
    row.input_2.textEdited.emit("mine")  # setText alone does not signal an edit
    row.input_1.setCurrentIndex(1)
    assert row.input_2.text() == "mine"


def test_target_name_is_blank_by_default(qapp):
    """The whole-series merge dialog's other tabs are untouched."""
    assert ImportAs(None, ["align-a"]).input_2.text() == ""


# --------------------------------------------------------------------------- #
# ImportAlignmentsDialog
# --------------------------------------------------------------------------- #
def test_dialog_offers_the_other_series_alignments_and_allows_overwrite(qapp):
    other = _SeriesStub(alignments={"default", "swift"})
    current = _SeriesStub(alignments={"default"})
    dialog = ImportAlignmentsDialog(None, current, other)

    widget = dialog.import_widget
    assert set(widget.other_items) == {"default", "swift"}
    assert set(widget.self_items) == {"default"}
    assert widget.allow_overwrite is True
    assert widget.default_to_source is True


def test_whole_series_dialog_allows_overwrite_for_alignments_only(qapp):
    """The Alignments tab of the merge dialog takes the same prompt.

    Palettes and brightness/contrast profiles keep rejecting a taken name,
    because neither import records an undo state.
    """
    from PyReconstruct.modules.gui.dialog.import_series import ImportSeriesDialog

    def _series(alignments):
        series = _SeriesStub(alignments=alignments)
        series.sections = {1: "series.1", 2: "series.2"}
        series.data = {"objects": {}}
        series.ztraces = {}
        series.palette_traces = {"palette": []}
        series.bc_profiles = {"profile": (0, 0)}
        return series

    dialog = ImportSeriesDialog(
        None, _series({"default"}), _series({"default", "swift"})
    )
    widgets = dialog.import_widgets

    assert widgets["alignments"].allow_overwrite is True
    assert widgets["palettes"].allow_overwrite is False
    assert widgets["brightness/contrast profiles"].allow_overwrite is False


# --------------------------------------------------------------------------- #
# 4. MainWindow.importAlignmentsFromSeries
# --------------------------------------------------------------------------- #
class _OtherSeries:
    def __init__(self):
        self.closed = 0

    def close(self):
        self.closed += 1


def _handler_stub(import_calls):
    """The MainWindow surface importAlignmentsFromSeries touches."""

    class _Stub(_Anything):
        def __init__(self):
            super().__init__()
            self.series = types.SimpleNamespace(
                importTransforms=lambda *a, **k: import_calls.append((a, k))
            )
            self.field = _Anything(
                series_states={"states": True},
                table_manager=_Anything(),
            )
            self.saved = 0
            self.menus_rebuilt = 0

        def saveAllData(self):
            self.saved += 1

        def createContextMenus(self):
            self.menus_rebuilt += 1

    return _Stub()


def _patch_handler(monkeypatch, other, *, mag_ok=True, dialog=(None, False)):
    """Replace the three modals the handler drives, and record notifications."""
    import PyReconstruct.modules.gui.main.main_window as mw

    notices = []
    monkeypatch.setattr(mw, "Series", types.SimpleNamespace(
        openJser=lambda fp, *a, **k: other
    ))
    monkeypatch.setattr(mw, "checkMag", lambda *a, **k: mag_ok)
    monkeypatch.setattr(mw, "notify", lambda msg, *a, **k: notices.append(msg))
    monkeypatch.setattr(
        mw, "ImportAlignmentsDialog",
        lambda *a, **k: types.SimpleNamespace(exec=lambda: dialog),
    )
    return notices


def test_handler_passes_the_dialog_pairs_to_import_transforms(monkeypatch):
    from PyReconstruct.modules.gui.main.main_window import MainWindow

    other = _OtherSeries()
    pairs = [("swift", "swift"), ("default", "theirs")]
    notices = _patch_handler(monkeypatch, other, dialog=(pairs, True))

    calls = []
    stub = _handler_stub(calls)
    MainWindow.importAlignmentsFromSeries(stub, "/tmp/other.jser")

    assert len(calls) == 1
    args, _kwargs = calls[0]
    assert args[0] is other
    assert args[1] == pairs
    assert args[2] == {"states": True}  # the undo states, positional as elsewhere

    assert stub.saved == 1, "the current series was not saved before the import"
    assert stub.menus_rebuilt == 1, "the alignment submenus were not rebuilt"
    assert notices == ["Alignments imported successfully."]
    assert other.closed == 1


def test_handler_does_nothing_without_a_file(monkeypatch):
    """FileDialog returning "" is a cancelled file picker."""
    import PyReconstruct.modules.gui.main.main_window as mw
    from PyReconstruct.modules.gui.main.main_window import MainWindow

    monkeypatch.setattr(
        mw.FileDialog, "get", staticmethod(lambda *a, **k: ""),
    )
    calls = []
    stub = _handler_stub(calls)
    MainWindow.importAlignmentsFromSeries(stub)
    assert calls == []
    assert stub.saved == 0, "a cancelled picker still saved the series"


def test_handler_aborts_and_closes_on_a_calibration_mismatch(monkeypatch):
    other = _OtherSeries()
    _patch_handler(monkeypatch, other, mag_ok=False)

    from PyReconstruct.modules.gui.main.main_window import MainWindow

    calls = []
    MainWindow.importAlignmentsFromSeries(_handler_stub(calls), "/tmp/other.jser")
    assert calls == []
    assert other.closed == 1, "the other series was left open"


def test_handler_aborts_and_closes_on_a_cancelled_dialog(monkeypatch):
    other = _OtherSeries()
    _patch_handler(monkeypatch, other, dialog=(None, False))

    from PyReconstruct.modules.gui.main.main_window import MainWindow

    calls = []
    MainWindow.importAlignmentsFromSeries(_handler_stub(calls), "/tmp/other.jser")
    assert calls == []
    assert other.closed == 1, "the other series was left open"


def test_handler_treats_an_empty_selection_as_a_cancel(monkeypatch):
    """confirmed with no pairs must not run a no-op import that still notifies."""
    other = _OtherSeries()
    notices = _patch_handler(monkeypatch, other, dialog=([], True))

    from PyReconstruct.modules.gui.main.main_window import MainWindow

    calls = []
    MainWindow.importAlignmentsFromSeries(_handler_stub(calls), "/tmp/other.jser")
    assert calls == []
    assert notices == []
    assert other.closed == 1
