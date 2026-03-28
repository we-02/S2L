"""Cellpose segmentation engine."""
import os
import time
import threading
import logging

import numpy as np
import tqdm

from s2l.utils.sam_utils import SAMModelManager, SAMPreprocessor, SAMPostprocessor

logger = logging.getLogger(__name__)

# Try to import cellpose, handle gracefully if not available
try:
    from cellpose import io, models, transforms
    CELLPOSE_AVAILABLE = True
    logger.info("Cellpose imported successfully")
except ImportError as e:
    CELLPOSE_AVAILABLE = False
    logger.warning(f"Cellpose not available: {e}")

    class _DummyModels:
        class CellposeModel:
            def __init__(self, *args, **kwargs):
                raise ImportError("Cellpose is not installed")
    models = _DummyModels()

    class _DummyIO:
        @staticmethod
        def imread(path):
            raise ImportError("Cellpose is not installed")
    io = _DummyIO()

    class _DummyTransforms:
        @staticmethod
        def normalize99(img, lower=1, upper=99):
            return img
    transforms = _DummyTransforms()

IMAGE_EXTENSIONS = {'.tif', '.tiff', '.png', '.jpg', '.jpeg', '.bmp', '.gif'}
SAVE_TIMEOUT_SECONDS = 30


class CellposeSegmenter:
    """Wrapper around Cellpose models for cell segmentation."""

    def __init__(self, model_type='cpsam', use_sam=True, custom_model_path=None):
        self.model_type = model_type
        self.use_sam = use_sam
        self.custom_model_path = custom_model_path
        self.sam_manager = SAMModelManager()
        self.preprocessor = SAMPreprocessor()
        self.postprocessor = SAMPostprocessor()

        if not CELLPOSE_AVAILABLE:
            raise ImportError("Cellpose is required but not installed. Install with: pip install cellpose[gui]")

        self._init_model(model_type, use_sam, custom_model_path)

    def _init_model(self, model_type, use_sam, custom_model_path):
        import torch
        gpu = torch.cuda.is_available()

        if custom_model_path and os.path.exists(custom_model_path):
            try:
                logger.info(f"Loading custom model from {custom_model_path}")
                self.model = models.CellposeModel(pretrained_model=custom_model_path, gpu=gpu)
                self.model_type = 'custom'
                self.use_sam = False
                logger.info("Custom model loaded successfully")
                return
            except Exception as e:
                logger.error(f"Failed to load custom model: {e}, falling back to default")

        if use_sam and model_type == 'cpsam':
            try:
                self.model = models.CellposeModel(gpu=gpu, model_type='cpsam')
                logger.info("Initialized Cellpose-SAM model")
                return
            except Exception as e:
                logger.error(f"Failed to initialize SAM model: {e}, falling back")

        # Traditional or fallback
        for fallback in [model_type, 'cyto3', 'cyto']:
            try:
                self.model = models.CellposeModel(gpu=gpu, model_type=fallback)
                self.model_type = fallback
                self.use_sam = False
                logger.info(f"Initialized Cellpose model: {fallback}")
                return
            except Exception as e:
                logger.error(f"Failed to initialize {fallback}: {e}")

        raise RuntimeError("Unable to initialize any Cellpose model")

    def segment(self, directory, diameter, flow_threshold=0.4, cellprob_threshold=0.0,
                max_iter=None, max_resize=1000, progress_callback=None):
        """Run segmentation on all images in a directory."""
        start_time = time.time()

        files = [
            entry.path for entry in os.scandir(directory)
            if entry.is_file() and os.path.splitext(entry.name)[1].lower() in IMAGE_EXTENSIONS
        ]
        total_files = len(files)

        if total_files == 0:
            logger.warning("No image files to process.")
            if progress_callback:
                progress_callback(100)
            return

        logger.info(f"Starting segmentation of {total_files} files using {self.model_type} model")

        for idx, filepath in enumerate(tqdm.tqdm(files, desc="Processing images")):
            try:
                img = io.imread(filepath)
                if img is None:
                    logger.error(f"Failed to read image: {filepath}")
                    continue

                img_processed = self._preprocess(img)

                eval_params = {
                    'flow_threshold': flow_threshold,
                    'cellprob_threshold': cellprob_threshold,
                }
                if diameter > 0:
                    eval_params['diameter'] = diameter
                if max_iter is not None:
                    eval_params['niter'] = max_iter

                # Cellpose v4 returns 3 values: masks, flows, styles
                result = self.model.eval(img_processed, **eval_params)
                masks = result[0]
                flows = result[1]

                if self.use_sam and self.model_type == 'cpsam':
                    masks = self.postprocessor.filter_small_masks(masks, min_size=15)
                    masks = self.postprocessor.relabel_masks(masks)

                n_objects = len(np.unique(masks)) - 1
                logger.info(f"{os.path.basename(filepath)}: {n_objects} objects")

                img_normalized = transforms.normalize99(img, lower=1, upper=99)
                self._save_masks_with_timeout(img_normalized, masks, flows, filepath)

            except Exception as e:
                logger.error(f"Error processing {filepath}: {e}")
                continue

            if progress_callback:
                progress_callback(((idx + 1) / total_files) * 100)

        if progress_callback:
            progress_callback(100)

        logger.info(f"Segmentation completed in {time.time() - start_time:.2f} seconds")

    def _preprocess(self, img):
        if self.use_sam and self.model_type == 'cpsam':
            return self.preprocessor.preprocess_for_sam(img, normalize=True)
        return self.preprocessor.preprocess_for_traditional(img, smooth_radius=1, sharpen_radius=0)

    def segment_files(self, file_list, output_dir, diameter=0, flow_threshold=0.4,
                      cellprob_threshold=0.0, max_iter=None, progress_callback=None):
        """Run segmentation on an explicit list of files, saving masks to output_dir."""
        from pathlib import Path
        start_time = time.time()
        total = len(file_list)
        if total == 0:
            if progress_callback:
                progress_callback(100)
            return

        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        logger.info(f"Segmenting {total} files → {out}")

        for idx, filepath in enumerate(tqdm.tqdm(file_list, desc="Processing")):
            try:
                img = io.imread(filepath)
                if img is None:
                    continue
                img_processed = self._preprocess(img)
                eval_params = {'flow_threshold': flow_threshold, 'cellprob_threshold': cellprob_threshold}
                if diameter > 0:
                    eval_params['diameter'] = diameter
                if max_iter is not None:
                    eval_params['niter'] = max_iter

                result = self.model.eval(img_processed, **eval_params)
                masks, flows = result[0], result[1]

                if self.use_sam and self.model_type == 'cpsam':
                    masks = self.postprocessor.filter_small_masks(masks, min_size=15)
                    masks = self.postprocessor.relabel_masks(masks)

                stem = Path(filepath).stem
                img_normalized = transforms.normalize99(img, lower=1, upper=99)
                # Save masks to output_dir instead of next to original
                mask_path = out / f"{stem}_cp_masks.tif"
                from skimage.io import imsave as sk_imsave
                sk_imsave(str(mask_path), masks.astype(np.uint16), check_contrast=False)
                logger.info(f"{stem}: {len(np.unique(masks)) - 1} objects → {mask_path.name}")
            except Exception as e:
                logger.error(f"Error processing {filepath}: {e}")
            if progress_callback:
                progress_callback(((idx + 1) / total) * 100)

        if progress_callback:
            progress_callback(100)
        logger.info(f"Segmentation completed in {time.time() - start_time:.2f}s")

    @staticmethod
    def _save_masks_with_timeout(img, masks, flows, filepath):
        def _save():
            io.save_masks(img, masks, flows, filepath, save_txt=False)

        thread = threading.Thread(target=_save)
        thread.start()
        thread.join(timeout=SAVE_TIMEOUT_SECONDS)
        if thread.is_alive():
            logger.warning(f"Saving masks timed out for {filepath}")
