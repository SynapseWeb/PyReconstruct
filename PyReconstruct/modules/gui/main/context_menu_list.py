"""Context menus."""


from PyReconstruct.modules.gui.utils import getUserColsMenu, getAlignmentsMenu


def get_field_menu_list(self):

    return [
        {
            "attr_name": "tracemenu",
            "text": "Trace",
            "opts": self.field.getTraceMenu()
        },
        {
            "attr_name": "objectmenu",
            "text": "Object",
            "opts": self.field.getObjMenu()
        },
        {
            "attr_name": "ztracemenu",
            "text": "Ztrace",
            "opts": self.field.getZtraceMenu()
        },
        None,
        {
            "attr_name": "viewmenu",
            "text": "View",
            "opts":
            [
                ("unhideall_act", "Unhide all traces", self.series, self.field.unhideAllTraces),
                None,
                ("hideall_act", "Toggle hide all", self.series, self.field.toggleHideAllTraces),
                ("showall_act", "Toggle show all", self.series, self.field.toggleShowAllTraces),
                None,
                ("hideimage_act", "Toggle hide image", self.series, self.field.toggleHideImage),
                ("blend_act", "Toggle section blend", self.series, self.field.toggleBlend),
            ]
        },
        getAlignmentsMenu(self.series, self.changeAlignment),
        None,
        self.cut_act,
        self.copy_act,
        self.paste_act,
        self.pasteattributes_act,
        None,
        ("selectall_act", "Select all traces", self.series, self.field.selectAllTraces),
        ("deselect_act", "Deselect traces", self.series, self.field.deselectAllTraces),
        None,
        ("delete_act", "Delete", "Del", self.backspace),
    ]


def get_context_menu_list_obj(self):

    return [
        ("editobjattribtues_act", "Edit attributes of traces...", "", self.editAttributes),
        None,
        {
            "attr_name" : "objattrsmenu",
            "text": "Object attributes",
            "opts":
            [
                ("editobjcomment_act", "Comment...", "", self.editComment),
                None,
                ("sethosts_act", "Set host(s)...", "", self.setHosts),
                ("clearhosts_act", "Clear host(s)...", "", self.clearHosts),
                ("displayinhabitants_act", "Display tree of inhabitants", "", lambda : self.displayHostTree(False)),
                ("displayhosts_act", "Display tree of hosts", "", self.displayHostTree),
                None,
                ("addobjgroup_act", "Add to group...", "", self.addToGroup),
                ("removeobjgroup_act", "Remove from group...", "", self.removeFromGroup),
                ("removeobjallgroups_act", "Remove from all groups", "", self.removeFromAllGroups),
                None,
                ("setobjalignment_act", "Change object alignment...", "", self.editAlignment),
                None,
                ("lockobj_act", "Lock", "", self.lockObjects),
                ("unlockobj_act", "Unlock", "", lambda : self.lockObjects(False))
            ]
        },
        {
            "attr_name": "objoperationsmenu",
            "text": "Operations",
            "opts":
            [
                ("copyobj_act", "Create copy of object(s)", "", self.copyObjects),
                ("editobjradius_act", "Edit radius...", "", self.editRadius),
                ("editobjshape_act", "Edit shape...", "", self.editShape),
                None,
                ("smoothtraces_act", "Smooth object traces", "", self.smoothObject),
                ("splitobj_act", "Split traces into individual objects", "", self.splitObject),
                None,
                ("hideobj_act", "Hide", "", self.hideObj),
                ("unhideobj_act", "Unhide", "", lambda : self.hideObj(False)),
                None,
                ("removealltags_act", "Remove all tags", "", self.removeAllTags),
                None,
                ("lockobj_act1", "Lock", "", self.lockObjects),
                ("unlockobj_act1", "Unlock", "", lambda : self.lockObjects(False))
            ]
        },
        getUserColsMenu(self.series, self.addUserCol, self.setUserCol, self.editUserCol),
        {
            "attr_name": "curatemenu",
            "text": "Set curation",
            "opts":
            [
                ("blankcurate_act", "Blank", "", lambda : self.bulkCurate("")),
                ("needscuration_act", "Needs curation", "", lambda : self.bulkCurate("Needs curation")),
                ("curated_act", "Curated", "", lambda : self.bulkCurate("Curated"))
            ]
        },
        {
            "attr_name": "menu_3D",
            "text": "3D",
            "opts":
            [
                ("addobjto3D_act", "Add to scene", "", self.addTo3D),
                ("removeobj3D_act", "Remove from scene", "", self.remove3D),
                {
                    "attr_name": "exportobj3D",
                    "text": "Export",
                    "opts":
                    [
                        ("export3D_act", "Wavefront (.obj)", "", lambda : self.exportAs3D("obj")),
                        ("export3D_act", "Object File Format (.off)", "", lambda : self.exportAs3D("off")),
                        ("export3D_act", "Stanford PLY (.ply)", "", lambda : self.exportAs3D("ply")),
                        ("export3D_act", "Stl (.stl)", "", lambda : self.exportAs3D("stl")),
                        ("export3D_act", "Collada (.dae) - requires collada", "", lambda : self.exportAs3D("dae")),
                    ]
                    
                    },
                None,
                ("editobj3D_act", "Edit 3D settings...", "", self.edit3D)
            ]
        },
        {
            "attr_name": "objztracemenu",
            "text": "Create ztrace",
            "opts":
            [
                ("csztrace_act", "On contour midpoints", "", self.createZtrace),
                ("atztrace_act", "From trace sequence", "", lambda : self.createZtrace(cross_sectioned=False)),
            ]
        },
        None,
        ("objhistory_act", "View history", "", self.viewHistory),
        None,
        ("setpaletteobj_act", "Copy attributes to palette", "", self.setPaletteButtonFromObj),
        None,
        ("deleteobj_act", "Delete", "", self.deleteObjects)
    ]


def get_context_menu_list_trace(self, is_in_field=True):

    # only allow shortcuts to be connected through the field
    
    sc = self.series if is_in_field else ""
    
    context_menu = [
        ("edittrace_act", "Edit attributes...", sc, self.traceDialog),
        None,
        ("smoothtraces_act", "Smooth traces", "", self.smoothTraces),
        ("mergetraces_act", "Merge traces", sc, self.mergeTraces),
        ("mergeobjects_act", "Merge attributes", sc, lambda : self.mergeTraces(merge_attrs=True)),
        None,
        ("makenegative_act", "Make negative", "", self.makeNegative),
        ("makepositive_act", "Make positive", "", lambda : self.makeNegative(False)),
        None,
        ("hidetraces_act", "Hide", sc, self.hideTraces),
    ]
    
    if not is_in_field:
        
        context_menu += [
            ("unhidetraces_act", "Unhide", "", lambda : self.hideTraces(hide=False))
        ]

        context_menu += [
            None,
            ("opentraces_act", "Set open", "", lambda : self.closeTraces(closed=False)),
            ("closedtraces_act", "Set closed", "", self.closeTraces),
            None,
            ("edittraceshape_act", "Edit shape...", "", self.editTraceShape),
            ("edittraceradius_act", "Edit radius...", "", self.editTraceRadius),
            None,
            ("createtraceflag_act", "Create flag...", "", self.createTraceFlag),
        ]
        
        if not is_in_field:
            
            context_menu += [
                None,
                ("deletetrace_act", "Delete", "", self.deleteTraces)  # accessible elswhere in the field context menu
            ]
        
    return context_menu
