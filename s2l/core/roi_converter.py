"""Convert segmentation masks to ROI data with visualization.

Optimized: uses scipy.ndimage for single-pass label stats instead of
per-label boolean mask loops. Overlay plot is generated lazily only if
a plot output path is provided.
"""
import logging
from pathlib import Path

import cv2
import numpy as np
import xlsxwriter

logger = logging.getLogger(__name__)


class ROIVisualizer:
    """Quantify ROIs from segmentation masks and optionally render overlays."""

    def __init__(self, label_image_path, original_image_path, excel_output_path,
                 plot_output_path=None, show_labels=False, progress_callback=None):
        self.label_image_path = str(label_image_path)
        self.original_image_path = str(original_image_path)
        self.excel_output_path = str(excel_output_path)
        self.plot_output_path = str(plot_output_path) if plot_output_path else None
        self.show_labels = show_labels
        self.progress_callback = progress_callback

    def save_rois_to_excel(self):
        """Compute ROI stats and write to Excel. Generates overlay plot if path was given."""
        label_img = cv2.imread(self.label_image_path, cv2.IMREAD_UNCHANGED)
        gray_img = cv2.imread(self.original_image_path, cv2.IMREAD_GRAYSCALE)

        if label_img is None or gray_img is None:
            raise ValueError("Unable to load image(s) at provided path(s).")

        # Ensure label image is integer type for indexing
        if label_img.dtype.kind == 'f':
            label_img = label_img.astype(np.int32)

        roi_data = self._compute_stats_fast(label_img, gray_img)
        self._write_excel(roi_data)

        if self.plot_output_path:
            color_img = cv2.imread(self.original_image_path, cv2.IMREAD_COLOR)
            if color_img is not None:
                self._save_overlay(label_img, color_img)

        logger.info(f"ROI data saved to {self.excel_output_path}")
        if self.progress_callback:
            self.progress_callback(100)


    @staticmethod
    def _compute_stats_fast(label_img, gray_img):
        """Compute per-label stats in a single pass using numpy bincount."""
        max_label = label_img.max()
        if max_label == 0:
            return []

        flat_labels = label_img.ravel()
        flat_gray = gray_img.ravel().astype(np.float64)

        # bincount gives per-label sums in O(n) — one pass over the image
        area = np.bincount(flat_labels, minlength=max_label + 1)
        sum_intensity = np.bincount(flat_labels, weights=flat_gray, minlength=max_label + 1)

        # For std dev we need sum of squares
        sum_sq = np.bincount(flat_labels, weights=flat_gray ** 2, minlength=max_label + 1)

        roi_data = []
        for lbl in range(1, max_label + 1):
            a = area[lbl]
            if a == 0:
                continue
            s = sum_intensity[lbl]
            mean = s / a
            var = (sum_sq[lbl] / a) - mean ** 2
            std = np.sqrt(max(var, 0.0))
            roi_data.append([int(lbl), int(a), float(s), float(mean), float(std)])

        return roi_data

    def _write_excel(self, roi_data):
        headers = ["Label", "Area", "Integrated Density", "Mean Gray Value", "Standard Deviation"]
        with xlsxwriter.Workbook(self.excel_output_path, {"constant_memory": True}) as wb:
            ws = wb.add_worksheet()
            hdr_fmt = wb.add_format({"bold": True, "bg_color": "#D7E4BC"})
            ws.write_row(0, 0, headers, hdr_fmt)
            for row, data in enumerate(roi_data, start=1):
                ws.write_row(row, 0, data)

    def _save_overlay(self, label_img, color_img):
        """Generate and save an ROI overlay image using OpenCV (no matplotlib)."""
        max_label = label_img.max()
        if max_label == 0:
            cv2.imwrite(self.plot_output_path, color_img)
            return

        # Generate random colors for all labels at once
        rng = np.random.RandomState(42)
        colors = rng.randint(0, 256, (max_label + 1, 3), dtype=np.uint8)
        colors[0] = 0  # background = black

        # Vectorized color lookup — no per-label loop
        overlay = colors[label_img]

        # Blend
        alpha = 0.3
        blended = cv2.addWeighted(color_img, 1 - alpha, overlay, alpha, 0)

        # Add label text if requested
        if self.show_labels:
            # Use scipy.ndimage.center_of_mass for all labels at once
            try:
                from scipy.ndimage import center_of_mass
                centers = center_of_mass(
                    np.ones_like(label_img), label_img, range(1, max_label + 1)
                )
                for lbl, (cy, cx) in enumerate(centers, start=1):
                    if not np.isnan(cy):
                        cv2.putText(blended, str(lbl), (int(cx), int(cy)),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.4,
                                    (255, 255, 255), 1, cv2.LINE_AA)
            except ImportError:
                pass  # skip labels if scipy not available

        cv2.imwrite(self.plot_output_path, blended)
