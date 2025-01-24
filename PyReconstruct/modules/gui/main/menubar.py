from PyReconstruct.modules.gui.utils import getOpenRecentMenu, getGroupsMenu

from PyReconstruct.modules.constants import (
    kh_web,
    kh_wiki,
    kh_atlas,
    gh_repo,
    gh_issues,
    gh_submit,
    developers_mailto_str,
    repo_string
)


def return_file_menu(self):
    """Return file menu."""

    return {
        "attr_name": "filemenu",
        "text": "File",
        "opts":
        [   
            {
                "attr_name": "newseriesmenu",
                "text": "New",
                "opts":
                [
                    ("newfromimages_act", "From images...", self.series, self.newSeries),
                    ("newfromzarr_act", "From scaled images...", "", lambda : self.newSeries(from_zarr=True)),
                    ("newfromxml_act", "From legacy .ser...", "", self.newFromXML),
                    ("newfromngzarr_act", "From neuroglancer zarr...", "", self.newFromNgZarr),
                ]
            },
            ("open_act", "Open", self.series, self.openSeries),
            getOpenRecentMenu(self.series, self.openSeries),
            ("close_act", "Close", "", self.openWelcomeSeries),
            None,  # None acts as menu divider
            ("save_act", "Save", self.series, self.saveToJser),
            ("saveas_act", "Save as...", "", self.saveAsToJser),
            {
                "attr_name": "projectsmenu",
                "text": "Projects",
                "opts":
                [
                    ("random_act", "Randomize images...", "", self.randomizeProject),
                    ("derandom_act", "De-randomize project...", "", self.derandomizeProject)
                ]
            },
            {
                "attr_name": "backupmenu",
                "text": "Backup",
                "opts":
                [
                    ("manualbackup_act", "Backup now...", self.series, self.manualBackup),
                    ("setbackup_act", "Settings...", "", self.setBackup),
                ]
            },
            {
                "attr_name": "exportmenu",
                "text": "Export",
                "opts":
                [
                    ("exportxml_act", "to legacy Reconstruct (XML)...", "", self.exportToXML),
                    ("exportngzarr_act", "to Neuroglancer (Zarr)...", "", self.exportToZarr)
                ]
            },
            None,
            ("username_act", "Change username...", "", self.changeUsername),
            None,
            ("restart_act", "Reload", self.series, self.restart),
            ("quit_act", "Quit", self.series, self.close),
            ##("test_act", "Test", "", self.test),
        ]
    }


def return_edit_menu(self):
    """Return edit menu."""

    return {
        "attr_name": "editmenu",
        "text": "Edit",
        "opts":
        [
            ("undo_act", "Undo", self.series, self.undo),
            ("redo_act", "Redo", self.series, lambda : self.undo(True)),
            None,
            ("cut_act", "Cut", self.series, self.field.cut),
            ("copy_act", "Copy", self.series, self.copy),
            ("paste_act", "Paste", self.series, self.field.paste),
            ("pasteattributes_act", "Paste attributes", self.series, self.field.pasteAttributes),
            None,
            ("pastetopalette_act", "Paste attributes to palette", self.series, self.pasteAttributesToPalette),
            ("pastetopalettewithshape_act", "Paste attributes to palette (+shape)", self.series, lambda : self.pasteAttributesToPalette(True)),
            None,
            {
                "attr_name": "bcmenu",
                "text": "Brightness/contrast",
                "opts":
                [
                    ("incbr_act", "Increase brightness", self.series, lambda : self.editImage(option="brightness", direction="up")),
                    ("decbr_act", "Decrease brightness", self.series, lambda : self.editImage(option="brightness", direction="down")),
                    ("inccon_act", "Increase contrast", self.series, lambda : self.editImage(option="contrast", direction="up")),
                    ("deccon_act", "Decrease contrast", self.series, lambda : self.editImage(option="contrast", direction="down"))
                ]
            }
        ]
    }


def return_series_menu(self):
    """Return series menu."""

    return {
        "attr_name": "seriesmenu",
        "text": "Series",
        "opts":
        [
            ("alloptions_act", "Options...", self.series, self.allOptions),
            {
                "attr_name": "importmenu",
                "text": "Import",
                "opts":
                [
                    ("importfromseries_act", "from series...", "", self.importFromSeries),
                    ("importfromzarrlabels_act", "from neuroglancer zarr labels...", "", self.importFromZarrLabels),
                ]
            },
            {
                "attr_name": "imagesmenu",
                "text": "Images",
                "opts":
                [
                    ("change_src_act", "Find/change image directory", "", self.changeSrcDir),
                    ("zarrimage_act", "Convert to scaled images", "", self.srcToZarr),
                    ("scalezarr_act", "Update image scales", "", lambda : self.srcToZarr(create_new=False)),
                ]
            },
            {
                "attr_name": "serieshidemenu",
                "text": "Hide",
                "opts":
                [
                    ("hidealltraces_act", "Hide all traces", "", self.hideSeriesTraces),
                    ("unhidealltraces_act", "Unhide all traces", "", lambda : self.hideSeriesTraces(hidden=False))
                ]
            },
            {
                "attr_name": "threedeemenu",
                "text": "3D",
                "opts":
                [
                    ("load3Dscene_act", "Load 3D scene...", "", self.load3DScene),
                ]
            },
            {
                "attr_name": "tracepalette_menu",
                "text": "Trace Palette",
                "opts":
                [
                    ("modifytracepalette_act", "Edit all palettes...", self.series, self.mouse_palette.modifyAllPaletteButtons),
                    ("resetpalette_act", "Reset current palette", "", self.resetTracePalette),
                    None,
                    ("exporttracepalette_act", "Export as CSV...", "", self.exportTracePaletteCSV),
                    ("importtracepalettecsv_act", "Import from CSV...", "", self.importTracePaletteCSV),
                ]
            },
            {
                "attr_name": "calibrationmenu",
                "text": "Calibration",
                "opts":
                [
                    ("calibrate_act", "Calibrate pixel size...", "", self.calibrateMag),
                    ("setmag_act", "Manually set pixel mag...", "", self.setSeriesMag),
                ]
            },
            {
                "attr_name": "seriescodemenu",
                "text": "Series Code",
                "opts":
                [
                    ("setseriescode_act", "Set series code", "", self.setSeriesCode),
                    ("seriescodepattern_act", "Modify regex pattern", "", self.editSeriesCodePattern),
                ]
            },
            None,
            ("findobjectfirst_act", "Find first object contour...", self.series, self.findObjectFirst),
            ("removeduplicates_act", "Remove duplicate traces", "", self.deleteDuplicateTraces),
            None,
            ("updatecuration_act", "Update curation from history", "", self.updateCurationFromHistory),
            None,
            ("bcprofiles_act", "Brightness/contrast profiles...", "", self.changeBCProfiles),
            None,
            ("about_act", "About this series...", "", self.displayAbout),
        ]
    }


def return_section_menu(self):

    return {
        "attr_name": "sectionmenu",
        "text": "Section",
        "opts":
        [
            ("nextsection_act", "Next section", "PgUp", self.incrementSection),
            ("prevsection_act", "Previous section", "PgDown", lambda : self.incrementSection(down=True)),
            None,
            ("goto_act", "Go to section", self.series, self.changeSection),
            None,
            ("flicker_act", "Flicker section", self.series, self.flickerSections),
            None,
            ("findcontour_act", "Find contour...", self.series, self.field.findContourDialog),
            ("addscalebar", "Add scalebar...", "", self.addScaleBar),
            {
                "attr_name": "exportsecmenu",
                "text": "Export section",
                "opts":
                [
                    ("exportsvg_act", "As svg...", "", self.exportSectionSVG),
                    ("exportpng_act", "As png...", "", self.exportSectionPNG)
                ]
            }
        ]
    }


def return_list_menu(self):
    """Return list menu."""

    return {
        "attr_name": "listsmenu",
        "text": "Lists",
        "opts":
        [
            ("objectlist_act", "Object list", self.series, lambda : self.field.openList(list_type="object")),
            ("tracelist_act", "Trace list", self.series, lambda : self.field.openList(list_type="trace")),
            ("sectionlist_act", "Section list", self.series, lambda : self.field.openList(list_type="section")),
            ("ztracelist_act", "Z-trace list", self.series, lambda : self.field.openList(list_type="ztrace")),
            ("flaglist_act", "Flag list", self.series, lambda : self.field.openList(list_type="flag")),
            ("history_act", "Series history", "", self.viewSeriesHistory)
        ]
    }


def return_alignments_menu(self):
    """Return alignments menu."""

    return {
        "attr_name": "alignmentsmenu",
        "text": "Alignments",
        "opts":
        [
            ("changealignment_act", "Modify alignments", self.series, self.modifyAlignments),
            None,
            {
                "attr_name": "importmenu",
                "text": "Import alignments",
                "opts":
                [
                    ("importtransforms_act", ".txt file", "", self.importTransforms),
                    ("import_swift_transforms_act", "SWiFT project", "", self.importSwiftTransforms),
                ]
            },
            None,
            {
                "attr_name": "propagatemenu",
                "text": "Propagate transform",
                "opts":
                [
                    ("startpt_act", "Start propagation recording", "", lambda : self.field.setPropagationMode(True)),
                    ("endpt_act", "End propagation recording", "", lambda : self.field.setPropagationMode(False)),
                    None,
                    ("proptostart_act", "Propagate to start", "", lambda : self.field.propagateTo(False)),
                    ("proptoend_act", "Propagate to end", "", lambda : self.field.propagateTo(True))
                ]
            },
            None,
            ("unlocksection_act", "Unlock current section", self.series, self.field.unlockSection),
            ("changetform_act", "Edit transformation", self.series, self.changeTform),
            ("linearalign_act", "Estimate affine transform", "", self.field.affineAlign),
            ("aligncorrelation_act", "Align by correlation", "Ctrl+\\", self.field.corrAlign),
            # ("quickalign_act", "Auto-align", "Ctrl+\\", self.field.quickAlign)
        ]
    }


def return_autoseg_menu(self):
    """Return autoseg menu."""

    return {
        "attr_name": "autosegmenu",
        "text": "Autosegment",
        "opts":
        [
            ("export_zarr_act", "Export to zarr...", "", self.exportToZarr),
            ("trainzarr_act", "Train...", "", self.train),
            ("retrainzarr_act", "Retrain...", "", lambda : self.train(retrain=True)),
            ("predictzarr_act", "Predict (infer)...", "", self.predict),
            ("sementzarr_act", "Segment...", "", self.segment),
            {
                "attr_name": "zarrlayermenu",
                "text": "Zarr layer",
                "opts":
                [
                    ("setzarrlayer_act", "Set zarr layer...", "", self.setZarrLayer),
                    ("removezarrlayer_act", "Remove zarr layer", "", self.removeZarrLayer)
                ]
            }
        ]
    }


def return_view_menu(self):
    """Return view menu."""
    
    view_menu = {
        "attr_name": "viewmenu",
        "text": "View",
        "opts":
        [
            ("copyscreen_act", "Copy view to clipboard", "", lambda : self.saveFieldView(False)),
            ("copyscreen_act", "Save view to file", "", lambda : self.saveFieldView(True)),
            None,
            ("changetheme_act", "Change theme", "", self.setTheme),
            None,
            ("fillopacity_act", "Edit fill opacity...", "", self.setFillOpacity),
            None,
            ("homeview_act", "Set view to image", "Home", self.field.home),
            ("viewmag_act", "View magnification...", "", self.field.setViewMagnification),
            ("findview_act", "Set zoom when finding contours...", "", self.setFindZoom),
            None,
            ("toggleztraces_act", "Toggle show Z-traces", "", self.toggleZtraces),
            None,
            {
                "attr_name": "palettemenu",
                "text": "Palette",
                "opts":
                [
                    {
                        "attr_name": "togglepalettemenu",
                        "text": "Visibility",
                        "opts":
                        [
                            ("togglepalette_act", "Trace palette", "checkbox", self.mouse_palette.togglePalette),
                            ("toggleinc_act",  "Section increment buttons", "checkbox", self.mouse_palette.toggleIncrement),
                            ("togglebc_act", "Brightness/contrast sliders", "checkbox", self.mouse_palette.toggleBC),
                            ("togglesb_act", "Scale bar", "checkbox", self.mouse_palette.toggleSB),
                        ]
                    },
                    {
                        "attr_name": "incpalettemenu",
                        "text": "Increment palette buttons",
                        "opts":
                        [
                            ("incpaletteup_act", "Up", self.series, lambda : self.mouse_palette.incrementPalette(True)),
                            ("incpalettedown_act", "Down", self.series, lambda : self.mouse_palette.incrementPalette(False)),
                        ]
                    },
                    ("resetpalette_act", "Reset palette position", "", self.mouse_palette.resetPos),
                ]
            },
            ("lefthanded_act", "Left handed", "checkbox", self.field.setLeftHanded),
            None,
            ("togglecuration_act", "Toggle curation in object lists", self.series, self.toggleCuration),
        ]
    }

    obj_groups = self.series.object_groups.groups

    if(obj_groups):
        
        view_menu["opts"].append(
            getGroupsMenu(self)

        )

    return view_menu


def return_help_menu(self):
    """Return help menu."""

    return {
        "attr_name": "helpmenu",
        "text": "Help",
        "opts":
        [
            ("repobranch_act", repo_string, "", self.copyCommit),
            None,
            ("shortcutshelp_act", "Shortcuts list", "?", self.displayShortcuts),
            None,
            {
                "attr_name": "onlinemenu",
                "text": "Online resources",
                "opts": [
                    ("openwiki_act", "PyReconstruct user guide", "", lambda : self.openWebsite(kh_wiki)),
                    ("openrepo_act", "PyReconstruct source code", "", lambda : self.openWebsite(gh_repo)),
                    ("openkhlab_act", "KH lab website", "", lambda : self.openWebsite(kh_web)),
                    ("openkhatlast_act", "Atlas of Ultrastructural Neurocytology", "", lambda : self.openWebsite(kh_atlas)),
                    ("download2015", "Harris2015 example images", "", self.downloadExample)
                ]
            },
            {
                "attr_name": "issuemenu",
                "text": "Report issues (GitHub)",
                "opts":
                [
                    ("submitissue_act", "Report bug / Request feature", "", lambda : self.openWebsite(gh_submit)),
                    ("seeissues_act", "See unresolved issues", "", lambda : self.openWebsite(gh_issues))
                ]
            },
            ("emailteam_act", "Email developers", "", lambda : self.openWebsite(developers_mailto_str)),
        ]
    }


def return_menubar(self):
    """Return the complete menubar."""

    return [
        return_file_menu(self),
        return_edit_menu(self),
        return_series_menu(self),
        return_section_menu(self),
        return_list_menu(self),
        return_alignments_menu(self),
        ##return_autoseg_menu(self),
        return_view_menu(self),
        return_help_menu(self)
    ]
