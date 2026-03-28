"""StarDist segmentation engine."""
import os
import time
import logging
from pathlib import Path

import numpy as np
import tqdm

logger = logging.getLogger(__name__)

try:
    from stardist.models import StarDist2D
    from csbdeep.utils import normalize as csbdeep_normalize
    STARDIST_AVAILABLE = True
    logger.info("StarDist imported successfully")
except ImportError as e:
    STARDIST_AVAILABLE = False
    logger.warning(f"StarDist not available: {e}")

IMAGE_EXTENSIONS = {".tif", ".tiff", ".png", ".jpg", ".jpeg", ".bmp", ".gif"}

# Pretrained models shipped with StarDist
STARDIST_PRETRAINED = {
    "2D_versatile_fluo": "Versatile (fluorescent nuclei)",
    "2D_versatile_he":   "Versatile (H&E nuclei)",
    "2D_paper_dsb2018":  "DSB 2018",
    "2D_demo":           "Demo",
}


class StarDistSegmenter:
    """Wrapper around StarDist2D for cell/nuclei segmentation."""

    def __init__(self, model_name: str = "2D_versatile_fluo",
                 custom_model_path: str | None = None,
                 custom_model_name: str | None = None):
        if not STARDIST_AVAILABLE:
            raise ImportError(
                "StarDist is not installed. Install with: pip install stardist"
            )

        self.model_name = model_name
        self._load_model(model_name, custom_model_path, custom_model_name)

    def _load_model(self, model_name, custom_path, custom_name):
        if custom_path and custom_name:
            try:
                logger.info(f"Loading custom StarDist model: {custom_name} from {custom_path}")
                self.model = StarDist2D(None, name=custom_name, basedir=custom_path)
                self.model_name = custom_name
                logger.info("Custom StarDist model loaded")
                return
            except Exception as e:
                logger.error(f"Failed to load custom StarDist model: {e}, falling back")

        for name in self._model_order(model_name):
            try:
                logger.info(f"Loading pretrained StarDist model: {name}")
                self.model = self._load_pretrained_safe(name)
                self.model_name = name
                logger.info(f"StarDist model '{name}' ready")
                return
            except Exception as e:
                logger.error(f"Failed to load {name}: {e}")

        raise RuntimeError("Unable to initialize any StarDist model")

    @staticmethod
    def _model_order(preferred: str) -> list[str]:
        """Return model names to try, preferred first, then fallbacks."""
        order = [preferred] if preferred in STARDIST_PRETRAINED else []
        for fb in ["2D_versatile_fluo", "2D_demo"]:
            if fb not in order:
                order.append(fb)
        return order

    @staticmethod
    def _load_pretrained_safe(name: str):
        """Load a pretrained model, working around Windows symlink errors."""
        import shutil

        # StarDist2D(None, name=X, basedir=B) expects B/X/config.json
        # from_pretrained stores at ~/.keras/models/StarDist2D/<name>/
        # and tries to rename <name>_extracted -> <name> (fails on Windows)
        cache_parent = Path.home() / ".keras" / "models" / "StarDist2D" / name
        model_dir = cache_parent / name
        extracted = cache_parent / f"{name}_extracted"

        # recover from a previous failed symlink attempt
        if extracted.is_dir() and not model_dir.is_dir():
            logger.info(f"Recovering '{name}' from stale _extracted directory")
            inner = extracted / name
            src = str(inner) if inner.is_dir() else str(extracted)
            shutil.copytree(src, str(model_dir))
            shutil.rmtree(str(extracted))

        # if model files already exist locally, load directly
        if model_dir.is_dir() and (model_dir / "config.json").exists():
            logger.info(f"Loading '{name}' from cache")
            return StarDist2D(None, name=name, basedir=str(cache_parent))

        # fresh download
        try:
            return StarDist2D.from_pretrained(name)
        except OSError as e:
            # WinError 1314: symlink privilege not held
            if "1314" not in str(e) and "privilege" not in str(e).lower():
                raise
            logger.warning(f"Windows symlink error for '{name}', fixing manually")
            if extracted.is_dir():
                inner = extracted / name
                src = str(inner) if inner.is_dir() else str(extracted)
                if model_dir.exists():
                    shutil.rmtree(str(model_dir))
                shutil.copytree(src, str(model_dir))
                shutil.rmtree(str(extracted))
                logger.info(f"Fixed model directory for '{name}'")
            return StarDist2D(None, name=name, basedir=str(cache_parent))


    def segment(self, directory: str, prob_thresh: float = 0.5,
                nms_thresh: float = 0.4, n_tiles: tuple | None = None,
                scale: float | None = None,
                progress_callback=None):
        """Run StarDist segmentation on all images in *directory*."""
        start_time = time.time()

        files = sorted([
            entry.path for entry in os.scandir(directory)
            if entry.is_file()
            and os.path.splitext(entry.name)[1].lower() in IMAGE_EXTENSIONS
        ])
        total = len(files)

        if total == 0:
            logger.warning("No image files to process.")
            if progress_callback:
                progress_callback(100)
            return

        logger.info(f"StarDist segmentation: {total} files with model '{self.model_name}'")

        for idx, filepath in enumerate(tqdm.tqdm(files, desc="StarDist")):
            try:
                img = self._read_image(filepath)
                if img is None:
                    continue

                # adapt channels to model, then normalize
                img_ready, axes = self._prepare_for_model(img)
                axis_norm = (0, 1)
                img_norm = csbdeep_normalize(img_ready, 1, 99.8, axis=axis_norm)

                predict_kwargs = dict(
                    prob_thresh=prob_thresh,
                    nms_thresh=nms_thresh,
                )
                if n_tiles is not None:
                    predict_kwargs["n_tiles"] = n_tiles
                if scale is not None:
                    predict_kwargs["scale"] = scale
                predict_kwargs["axes"] = axes

                labels, details = self.model.predict_instances(img_norm, **predict_kwargs)

                n_objects = labels.max()
                logger.info(f"{Path(filepath).name}: {n_objects} objects detected")

                # save label mask as _cp_masks compatible tiff
                self._save_labels(filepath, labels)

            except Exception as e:
                logger.error(f"Error processing {filepath}: {type(e).__name__}: {e}", exc_info=True)
                continue

            if progress_callback:
                progress_callback(((idx + 1) / total) * 100)

        if progress_callback:
            progress_callback(100)

        logger.info(f"StarDist segmentation completed in {time.time() - start_time:.2f}s")

    @staticmethod
    def _read_image(filepath: str):
        """Read an image, return as numpy array or None."""
        try:
            from skimage.io import imread
            img = imread(filepath)
            if img.ndim == 3 and img.shape[2] == 4:
                img = img[..., :3]
            return img
        except Exception as e:
            logger.error(f"Failed to read {filepath}: {e}")
            return None

    def _prepare_for_model(self, img: np.ndarray):
        """Adapt image channels to match model's n_channel_in and return (img, axes).
        
        Call this BEFORE normalization so the normalize step works on the right shape.
        """
        n_in = self.model.config.n_channel_in
        logger.debug(f"  _prepare_for_model: input shape={img.shape}, dtype={img.dtype}, model expects n_channel_in={n_in}")

        if n_in == 1:
            if img.ndim == 3:
                # multi-channel → convert to grayscale (mean across channels)
                img = np.mean(img, axis=-1)
            return img, "YX"
        else:
            if img.ndim == 2:
                img = np.stack([img] * n_in, axis=-1)
            elif img.ndim == 3 and img.shape[2] != n_in:
                if img.shape[2] > n_in:
                    img = img[..., :n_in]
                else:
                    pad = np.zeros((*img.shape[:2], n_in - img.shape[2]), dtype=img.dtype)
                    img = np.concatenate([img, pad], axis=-1)
            return img, "YXC"

    @staticmethod
    def _save_labels(filepath: str, labels: np.ndarray):
        """Save label mask next to the original image with _cp_masks suffix."""
        from skimage.io import imsave
        p = Path(filepath)
        out_name = p.stem + "_cp_masks" + ".tif"
        out_path = p.parent / out_name
        imsave(str(out_path), labels.astype(np.uint16), check_contrast=False)
        logger.info(f"Saved mask: {out_path.name}")

    def segment_files(self, file_list, output_dir, prob_thresh=0.5,
                      nms_thresh=0.4, progress_callback=None):
        """Run segmentation on an explicit list of files, saving masks to output_dir."""
        start_time = time.time()
        total = len(file_list)
        if total == 0:
            if progress_callback:
                progress_callback(100)
            return

        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        logger.info(f"StarDist segmenting {total} files → {out}")

        for idx, filepath in enumerate(tqdm.tqdm(file_list, desc="StarDist")):
            try:
                img = self._read_image(filepath)
                if img is None:
                    continue
                # adapt channels first, then normalize
                img_ready, axes = self._prepare_for_model(img)
                img_norm = csbdeep_normalize(img_ready, 1, 99.8, axis=(0, 1))
                kw = dict(prob_thresh=prob_thresh, nms_thresh=nms_thresh)
                kw["axes"] = axes

                labels, _ = self.model.predict_instances(img_norm, **kw)
                stem = Path(filepath).stem
                mask_path = out / f"{stem}_cp_masks.tif"
                from skimage.io import imsave
                imsave(str(mask_path), labels.astype(np.uint16), check_contrast=False)
                logger.info(f"{stem}: {labels.max()} objects → {mask_path.name}")
            except Exception as e:
                logger.error(f"Error processing {filepath}: {type(e).__name__}: {e}", exc_info=True)
            if progress_callback:
                progress_callback(((idx + 1) / total) * 100)

        if progress_callback:
            progress_callback(100)
        logger.info(f"StarDist segmentation completed in {time.time() - start_time:.2f}s")
