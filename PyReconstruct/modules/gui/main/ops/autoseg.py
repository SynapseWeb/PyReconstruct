"""Application autoseg operations."""

from PyReconstruct.modules.gui.dialog import TrainDialog, SegmentDialog, PredictDialog
from PyReconstruct.modules.backend.autoseg import labelsToObjects, seriesToLabels


class AutosegOperations:

    def train(self, retrain=False):
        """Train an autosegmentation model."""
        self.saveAllData()
        self.removeZarrLayer()

        model_paths = {"a":{"b":"a/b/m.py"}}

        opts = self.series.options["autoseg"]

        response, confirmed = TrainDialog(self, self.series, model_paths, opts, retrain).exec()
        if not confirmed: return
        
        (data_fp, iterations, save_every, group, model_path, cdir, \
         pre_cache, min_masked, downsample) = response

        training_opts = {
            'zarr_current': data_fp,
            'iters': iterations,
            'save_every': save_every,
            'group': group,
            'model_path': model_path,
            'checkpts_dir': cdir,
            'pre_cache': pre_cache,
            'min_masked': min_masked,
            'downsample_bool': downsample
        }

        for k, v in training_opts.items():
            opts[k] = v
        self.seriesModified(True)

        print("Exporting labels to zarr directory...")
        
        if retrain:
            group_name = f"labels_{self.series.getRecentSegGroup()}_keep"
            seriesToLabels(self.series, data_fp)
            
        else:
            group_name = f"labels_{group}"
            seriesToLabels(self.series, data_fp, group)

        print("Zarr directory updated with labels!")

        if retrain:
            self.field.reload()
            self.field.table_manager.refresh()

        print("Starting training....")

        print("Importing training modules...")

        from autoseg import train, make_mask, model_paths

        make_mask(data_fp, group_name)
        
        sources = [{
            "raw" : (data_fp, "raw"),
            "labels" : (data_fp, group_name),
            "unlabelled" : (data_fp, "unlabelled")
        }]

        train(
            iterations=iterations,
            save_every=save_every,
            sources=sources,
            model_path=model_path,
            pre_cache=pre_cache,
            min_masked=min_masked,
            downsample=downsample,
            checkpoint_basename=os.path.join(cdir, "model")  # where existing checkpoints
        )

        print("Done training!")
    
    def markKeep(self):
        """Add the selected trace to the most recent "keep" segmentation group."""
        keep_tag = f"{self.series.getRecentSegGroup()}_keep"
        for trace in self.field.section.selected_traces:
            trace.addTag(keep_tag)
        # deselect traces and hide
        self.field.hideTraces()
        self.field.deselectAllTraces()

    def predict(self, data_fp : str = None):
        """Run predictons.
        
            Params:
                data_fp (str): the filepath for the zarr
        """
        self.saveAllData()
        self.removeZarrLayer()

        print("Importing models...")
        
        from autoseg import predict, model_paths
        # model_paths = {"a":{"b":"a/b/m.py"}}

        opts = self.series.options["autoseg"]

        response, dialog_confirmed = PredictDialog(self, model_paths, opts).exec()

        if not dialog_confirmed: return

        data_fp, model_path, cp_path, write_opts, increase, downsample, full_out_roi = response

        predict_opts = {
            'zarr_current': data_fp,
            'model_path': model_path,
            'checkpts_dir': os.path.dirname(cp_path),
            'write': write_opts,
            'increase': increase,
            'downsample_bool': downsample,
            'full_out_roi': full_out_roi
        }

        for k, v in predict_opts.items():
            opts[k] = v
        self.seriesModified(True)
                
        print("Running predictions...")

        zarr_datasets = predict(
            sources=[(data_fp, "raw")],
            out_file=data_fp,
            checkpoint_path=cp_path,
            model_path=model_path,
            write=write_opts,
            increase=increase,
            downsample=downsample,
            full_out_roi=full_out_roi
        )

        # display the affinities
        self.setZarrLayer(data_fp)
        for zg in os.listdir(data_fp):
            if zg.startswith("pred_affs"):
                self.setLayerGroup(zg)
                break

        print("Predictions done.")
        
    def segment(self, data_fp : str = None):
        """Run an autosegmentation.
        
            Params:
                data_fp (str): the filepath for the zarr
        """
        self.saveAllData()
        self.removeZarrLayer()

        print("Importing modules...")
        
        from autoseg import hierarchical

        opts = self.series.options["autoseg"]

        response, dialog_confirmed = SegmentDialog(self, opts).exec()

        if not dialog_confirmed: return

        data_fp, thresholds, downsample, norm_preds, min_seed, merge_fun = response

        segment_opts = {
            "zarr_current": data_fp,
            "thresholds": thresholds,
            "downsample_int": downsample,
            "norm_preds": norm_preds,
            "min_seed": min_seed,
            "merge_fun": merge_fun
        }

        for k, v in segment_opts.items():
            opts[k] = v
        self.seriesModified(True)

        print("Running hierarchical...")

        dataset = None
        for d in os.listdir(data_fp):
            if "affs" in d:
                dataset = d
                break

        print("Segmentation started...")
            
        hierarchical.run(
            data_fp,
            dataset,
            thresholds=list(sorted(thresholds)),
            normalize_preds=norm_preds,
            min_seed_distance=min_seed,
            merge_function=merge_fun
        )

        print("Segmentation done.")

        # display the segmetnation
        self.setZarrLayer(data_fp)
        for zg in os.listdir(data_fp):
            if zg.startswith("seg"):
                self.setLayerGroup(zg)
                break
    
    def importLabels(self, all=False):
        """Import labels from a zarr."""
        if not self.field.zarr_layer or not self.field.zarr_layer.is_labels:
            return
        
        # get necessary data
        data_fp = self.series.zarr_overlay_fp
        group_name = self.series.zarr_overlay_group

        labels = None if all else self.field.zarr_layer.selected_ids
        
        labelsToObjects(
            self.series,
            data_fp,
            group_name,
            labels
        )
        self.field.reload()
        self.removeZarrLayer()
        self.field.table_manager.refresh()

        notify("Labels imported successfully.")
    
    def mergeLabels(self):
        """Merge selected labels in a zarr."""
        if not self.field.zarr_layer:
            return
        
        self.field.zarr_layer.mergeLabels()
        self.field.generateView()
    
    
