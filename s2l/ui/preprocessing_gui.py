"""Image preprocessing / enhancement GUI using Cellpose denoise models."""
import os
import sys
import logging

import numpy as np
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QFileDialog, QComboBox, QMessageBox, QSpinBox, QFrame,
)
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from skimage.io import imread, imsave

from s2l.ui.theme import get_complete_stylesheet, get_primary_button_style, COLORS

logger = logging.getLogger(__name__)

AVAILABLE_MODELS = [
    "denoise_cyto3", "deblur_cyto3", "upsample_cyto3", "oneclick_cyto3",
    "denoise_cyto2", "deblur_cyto2", "upsample_cyto2", "oneclick_cyto2",
    "denoise_nuclei", "deblur_nuclei", "upsample_nuclei", "oneclick_nuclei",
]
CHANNELS = [1, 2]


class _DenoiseWorker(QThread):
    result_ready = pyqtSignal(np.ndarray)
    error_occurred = pyqtSignal(str)

    def __init__(self, image, model_name, diameter):
        super().__init__()
        self.image, self.model_name, self.diameter = image, model_name, diameter

    def run(self):
        try:
            from cellpose import denoise
            mt = self.model_name.split("_")[-1]
            model = denoise.CellposeDenoiseModel(
                gpu=True, model_type=mt, restore_type=self.model_name, chan2_restore=True)
            _, _, _, imgs = model.eval([self.image], channels=CHANNELS, diameter=self.diameter)
            self.result_ready.emit(imgs[0])
        except ImportError:
            self.error_occurred.emit("Cellpose denoise not available. Update to 3.0+")
        except Exception as e:
            self.error_occurred.emit(str(e))


def _card(layout):
    f = QFrame()
    f.setObjectName("Card")
    f.setLayout(layout)
    f.layout().setContentsMargins(22, 20, 22, 20)
    f.layout().setSpacing(16)
    return f


class CellposePreprocessingGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("S2L — Image Enhancer")
        self.image = self.processed_image = self.image_path = self.worker = None
        self._build()

    def _build(self):
        self.setStyleSheet(get_complete_stylesheet())
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(20)

        # header
        title = QLabel("Image Enhancer")
        title.setObjectName("PageTitle")
        sub = QLabel("Denoise, deblur, or upsample images with Cellpose restoration models.")
        sub.setObjectName("PageSubtitle")
        root.addWidget(title)
        root.addWidget(sub)

        # ── card: settings ────────────────────────────────────────────────
        settings = QVBoxLayout()
        row1 = QHBoxLayout()
        row1.setSpacing(16)

        # model
        mcol = QVBoxLayout()
        mcol.setSpacing(5)
        mcol.setContentsMargins(0, 2, 0, 2)
        ml = QLabel("Model")
        ml.setObjectName("FieldLabel")
        self.model_box = QComboBox()
        self.model_box.addItems(AVAILABLE_MODELS)
        mcol.addWidget(ml)
        mcol.addWidget(self.model_box)
        row1.addLayout(mcol, 1)

        # diameter
        dcol = QVBoxLayout()
        dcol.setSpacing(5)
        dcol.setContentsMargins(0, 2, 0, 2)
        dl = QLabel("Diameter")
        dl.setObjectName("FieldLabel")
        self.diameter_input = QSpinBox()
        self.diameter_input.setRange(1, 1000)
        self.diameter_input.setValue(50)
        self.diameter_input.setSuffix(" px")
        dcol.addWidget(dl)
        dcol.addWidget(self.diameter_input)
        row1.addLayout(dcol)

        settings.addLayout(row1)
        root.addWidget(_card(settings))

        # ── buttons ───────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        self.load_btn = QPushButton("Load image")
        self.load_btn.clicked.connect(self._load)
        self.apply_btn = QPushButton("Apply enhancement")
        self.apply_btn.setStyleSheet(get_primary_button_style())
        self.apply_btn.clicked.connect(self._apply)
        self.save_btn = QPushButton("Save result")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self._save)
        btn_row.addWidget(self.load_btn)
        btn_row.addWidget(self.apply_btn)
        btn_row.addWidget(self.save_btn)
        root.addLayout(btn_row)

        # ── image panels ──────────────────────────────────────────────────
        panels = QHBoxLayout()
        panels.setSpacing(16)
        for attr, placeholder in [("orig_label", "No image loaded"), ("proc_label", "No result yet")]:
            col = QVBoxLayout()
            col.setSpacing(6)
            lbl = QLabel(placeholder)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setMinimumSize(320, 320)
            lbl.setStyleSheet(
                f"border: 1px dashed {COLORS['border']}; border-radius: 10px; "
                f"background-color: {COLORS['bg_card']}; color: {COLORS['text_dim']}; font-size: 12px;"
            )
            setattr(self, attr, lbl)
            col.addWidget(lbl)
            panels.addLayout(col)
        root.addLayout(panels)

        # ── status ────────────────────────────────────────────────────────
        self.status = QLabel("Ready")
        self.status.setObjectName("StatusSuccess")
        root.addWidget(self.status)

    # ── actions ───────────────────────────────────────────────────────────

    def _set_status(self, text, kind="StatusSuccess"):
        self.status.setText(text)
        self.status.setObjectName(kind)
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)

    def _load(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select image", "",
            "Images (*.png *.jpg *.jpeg *.tif *.tiff *.bmp);;All (*)")
        if not path:
            return
        try:
            self.image_path = path
            self.image = imread(path)
            px = self._to_pixmap(self.image)
            if px.isNull():
                raise ValueError("Conversion failed")
            self.orig_label.setPixmap(px.scaled(
                320, 320, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))
            self._set_status(f"Loaded: {os.path.basename(path)}")
            self.proc_label.setText("No result yet")
            self.proc_label.setPixmap(QPixmap())
            self.save_btn.setEnabled(False)
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))
            self._set_status("Load failed", "StatusError")

    def _apply(self):
        if self.image is None:
            QMessageBox.warning(self, "Error", "Load an image first.")
            return
        self.apply_btn.setEnabled(False)
        self._set_status("Processing…", "StatusWarning")
        self.worker = _DenoiseWorker(
            self.image, self.model_box.currentText(), float(self.diameter_input.value()))
        self.worker.result_ready.connect(self._on_result)
        self.worker.error_occurred.connect(self._on_error)
        self.worker.start()

    def _on_result(self, img):
        try:
            self.processed_image = img
            px = self._to_pixmap(img)
            if px.isNull():
                raise ValueError("Conversion failed")
            self.proc_label.setPixmap(px.scaled(
                320, 320, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))
            self.save_btn.setEnabled(True)
            self._set_status("Enhancement complete")
        except Exception as e:
            self._on_error(str(e))
        finally:
            self.apply_btn.setEnabled(True)

    def _on_error(self, msg):
        QMessageBox.critical(self, "Error", msg)
        self._set_status("Failed", "StatusError")
        self.apply_btn.setEnabled(True)

    def _save(self):
        if self.processed_image is None:
            return
        suggested = "enhanced.png"
        if self.image_path:
            base = os.path.splitext(os.path.basename(self.image_path))[0]
            suggested = f"{base}_{self.model_box.currentText()}.png"
        path, _ = QFileDialog.getSaveFileName(
            self, "Save", suggested, "PNG (*.png);;TIFF (*.tif);;JPEG (*.jpg);;All (*)")
        if not path:
            return
        try:
            img = self.processed_image
            if img.ndim == 2:
                img = np.stack([img] * 3, axis=-1)
            elif img.shape[2] == 1:
                img = np.repeat(img, 3, axis=2)
            img = (img * 255).astype(np.uint8) if img.max() <= 1.0 else img.astype(np.uint8)
            imsave(path, img)
            self._set_status("Saved successfully")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            self._set_status("Save failed", "StatusError")

    @staticmethod
    def _to_pixmap(img: np.ndarray) -> QPixmap:
        try:
            d = (img * 255).astype(np.uint8) if img.max() <= 1.0 else img.astype(np.uint8)
            if d.ndim == 2:
                h, w = d.shape
                qi = QImage(d.data, w, h, d.strides[0], QImage.Format.Format_Grayscale8)
            elif d.ndim == 3:
                h, w, c = d.shape
                fmt = {4: QImage.Format.Format_RGBA8888, 3: QImage.Format.Format_RGB888}.get(c)
                if fmt:
                    qi = QImage(d.data, w, h, d.strides[0], fmt)
                else:
                    g = d[:, :, 0]
                    qi = QImage(g.data, w, h, g.strides[0], QImage.Format.Format_Grayscale8)
            else:
                return QPixmap()
            return QPixmap.fromImage(qi)
        except Exception:
            return QPixmap()


def main():
    app = QApplication(sys.argv)
    w = CellposePreprocessingGUI()
    w.resize(800, 680)
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
