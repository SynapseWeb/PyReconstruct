from PyReconstruct.modules.gui.utils import getUserColsMenu

def get_context_menu_list(self):

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
                ("editobjradius_act", "Edit radius...", "", self.editRadius),
                ("editobjshape_act", "Edit shape...", "", self.editShape),
                None,
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
