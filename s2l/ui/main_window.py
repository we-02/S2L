"""Main GUI application for S2L."""
import sys
import os
import re
import subprocess
import logging
import webbrowser
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFileDialog, QComboBox, QSpinBox, QDoubleSpinBox,
    QCheckBox, QMessageBox, QProgressBar, QScrollArea, QGroupBox, QFrame,
    QStackedWidget, QSizePolicy, QGridLayout, QSpacerItem,
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QSize, QPropertyAnimation, QEasingCurve, pyqtProperty, QRectF, QPointF
from PyQt6.QtGui import QFont, QPainter, QColor, QPen, QBrush

from s2l.core.roi_converter import ROIVisualizer
from s2l.core.summary import generate_summary_sheet
from s2l.utils.sam_utils import SAMModelManager, check_sam_compatibility
from s2l.ui.theme import (
    get_complete_stylesheet, get_primary_button_style,
    get_danger_button_style, COLORS,
)
from s2l.ui.dataset_viewer import DatasetViewerPage
from s2l.core.spreadsheet_parser import parse_fim_sheet

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s")
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def check_cuda_availability() -> bool:
    for mod, fn in [("cupy", "is_available"), ("torch", "cuda.is_available")]:
        try:
            m = __import__(mod)
            parts = fn.split(".")
            obj = m
            for p in parts:
                obj = getattr(obj, p)
            if callable(obj) and obj():
                return True
        except Exception:
            pass
    return False


# ═══════════════════════════════════════════════════════════════════════════
# UI building blocks
# ═══════════════════════════════════════════════════════════════════════════

def _card(inner_layout: QVBoxLayout) -> QFrame:
    """Wrap *inner_layout* in a styled card frame."""
    frame = QFrame()
    frame.setObjectName("Card")
    frame.setLayout(inner_layout)
    frame.layout().setContentsMargins(22, 20, 22, 20)
    frame.layout().setSpacing(16)
    return frame


def _section_header(title: str, description: str = "") -> QVBoxLayout:
    """Return a VBox with a bold title and optional muted description."""
    lay = QVBoxLayout()
    lay.setSpacing(2)
    t = QLabel(title)
    t.setObjectName("SectionTitle")
    lay.addWidget(t)
    if description:
        d = QLabel(description)
        d.setObjectName("SectionDesc")
        d.setWordWrap(True)
        lay.addWidget(d)
    return lay


def _field_row(label_text: str, widget, hint: str = "") -> QVBoxLayout:
    """Label above widget, optional hint below."""
    col = QVBoxLayout()
    col.setSpacing(5)
    col.setContentsMargins(0, 2, 0, 2)
    lbl = QLabel(label_text)
    lbl.setObjectName("FieldLabel")
    col.addWidget(lbl)
    if isinstance(widget, QHBoxLayout):
        col.addLayout(widget)
    else:
        col.addWidget(widget)
    if hint:
        h = QLabel(hint)
        h.setObjectName("Hint")
        col.addWidget(h)
    return col


def _browse_row(line_edit: QLineEdit, button_text: str, callback,
                view_callback=None) -> QHBoxLayout:
    """LineEdit + Browse button side by side, optional View button."""
    row = QHBoxLayout()
    row.setSpacing(8)
    row.addWidget(line_edit, 1)
    btn = QPushButton(button_text)
    btn.setMinimumWidth(90)
    btn.clicked.connect(callback)
    row.addWidget(btn)
    if view_callback:
        vbtn = QPushButton("View")
        vbtn.setMinimumWidth(56)
        vbtn.setToolTip("Open this folder in the dataset viewer")
        vbtn.clicked.connect(view_callback)
        row.addWidget(vbtn)
    return row


def _scrollable(content_widget: QWidget) -> QScrollArea:
    """Wrap a widget in a transparent scroll area."""
    sa = QScrollArea()
    sa.setWidget(content_widget)
    sa.setWidgetResizable(True)
    sa.setFrameShape(QFrame.Shape.NoFrame)
    return sa


# ═══════════════════════════════════════════════════════════════════════════
# Toggle switch  (replaces plain checkboxes for on/off options)
# ═══════════════════════════════════════════════════════════════════════════

class ToggleSwitch(QWidget):
    """Animated pill-shaped toggle switch with a label."""
    toggled = pyqtSignal(bool)

    _TRACK_W = 44
    _TRACK_H = 24
    _KNOB_MARGIN = 3
    _KNOB_D = _TRACK_H - _KNOB_MARGIN * 2  # 18

    def __init__(self, text: str = "", checked: bool = False, parent=None):
        super().__init__(parent)
        self._checked = checked
        self._text = text
        self._knob_x = float(self._on_x() if checked else self._off_x())
        self._enabled = True

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(30)
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        self._anim = QPropertyAnimation(self, b"knob_position", self)
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

    # -- properties --------------------------------------------------------

    def _get_knob_position(self) -> float:
        return self._knob_x

    def _set_knob_position(self, val: float):
        self._knob_x = val
        self.update()

    knob_position = pyqtProperty(float, _get_knob_position, _set_knob_position)

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, on: bool):
        if on == self._checked:
            return
        self._checked = on
        self._animate()
        self.toggled.emit(on)

    def setEnabled(self, enabled: bool):
        self._enabled = enabled
        self.setCursor(
            Qt.CursorShape.PointingHandCursor if enabled
            else Qt.CursorShape.ArrowCursor
        )
        self.update()

    def isEnabled(self) -> bool:
        return self._enabled

    # -- geometry helpers --------------------------------------------------

    def _off_x(self) -> float:
        return float(self._KNOB_MARGIN)

    def _on_x(self) -> float:
        return float(self._TRACK_W - self._KNOB_MARGIN - self._KNOB_D)

    def _animate(self):
        self._anim.stop()
        self._anim.setStartValue(self._knob_x)
        self._anim.setEndValue(self._on_x() if self._checked else self._off_x())
        self._anim.start()

    # -- events ------------------------------------------------------------

    def mousePressEvent(self, ev):
        if self._enabled and ev.button() == Qt.MouseButton.LeftButton:
            self.setChecked(not self._checked)

    def sizeHint(self):
        text_w = self.fontMetrics().horizontalAdvance(self._text) if self._text else 0
        gap = 10 if self._text else 0
        return QSize(self._TRACK_W + gap + text_w, 30)

    # -- paint -------------------------------------------------------------

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        accent = QColor(COLORS["accent"])
        accent_hover = QColor(COLORS["accent_hover"])
        bg_off = QColor(COLORS["bg_elevated"])
        dim = QColor(COLORS["text_dim"])
        knob_color = QColor("#ffffff")

        if not self._enabled:
            accent = dim
            bg_off = QColor(COLORS["bg_input"])
            knob_color = QColor(COLORS["text_dim"])

        # track
        track_rect = QRectF(0, (self.height() - self._TRACK_H) / 2,
                            self._TRACK_W, self._TRACK_H)
        track_color = accent if self._checked else bg_off
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(track_color))
        p.drawRoundedRect(track_rect, self._TRACK_H / 2, self._TRACK_H / 2)

        # knob
        knob_y = (self.height() - self._KNOB_D) / 2
        p.setBrush(QBrush(knob_color))
        p.drawEllipse(QPointF(self._knob_x + self._KNOB_D / 2, knob_y + self._KNOB_D / 2),
                       self._KNOB_D / 2, self._KNOB_D / 2)

        # label
        if self._text:
            p.setPen(QPen(QColor(COLORS["text"] if self._enabled else COLORS["text_dim"])))
            text_x = self._TRACK_W + 10
            p.drawText(int(text_x), 0, self.width() - int(text_x), self.height(),
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                       self._text)

        p.end()


# ═══════════════════════════════════════════════════════════════════════════
# Worker thread  (unchanged logic, just lives here)
# ═══════════════════════════════════════════════════════════════════════════

class WorkerThread(QThread):
    cellpose_progress = pyqtSignal(float)
    labels2rois_progress = pyqtSignal(float)
    finished = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(self, base_dir, output_dir, diameter, run_seg, run_l2r,
                 engine="cellpose",
                 model_type="cpsam", use_sam=True, custom_model_path=None,
                 flow_threshold=0.4, cellprob_threshold=0.0,
                 max_iter=0, max_resize=1000,
                 stardist_model="2D_versatile_fluo",
                 prob_thresh=0.5, nms_thresh=0.4,
                 file_list=None):
        super().__init__()
        self.base_dir = Path(base_dir) if base_dir else None
        self.output_dir = Path(output_dir)
        self.diameter = diameter
        self.run_seg = run_seg
        self.run_l2r = run_l2r
        self.engine = engine
        self.flow_threshold = flow_threshold
        self.cellprob_threshold = cellprob_threshold
        self.max_iter = max_iter if max_iter > 0 else None
        self.max_resize = max_resize
        self.prob_thresh = prob_thresh
        self.nms_thresh = nms_thresh
        self.file_list = file_list  # explicit list of paths (spreadsheet mode)
        self._stop = False

        # instantiate the right segmenter (lazy imports to avoid torch at startup)
        if engine == "stardist":
            from s2l.core.stardist_segmenter import StarDistSegmenter
            self.seg = StarDistSegmenter(model_name=stardist_model)
        elif custom_model_path and os.path.exists(custom_model_path):
            from s2l.core.segmenter import CellposeSegmenter
            self.seg = CellposeSegmenter(model_type=None, custom_model_path=custom_model_path)
        else:
            from s2l.core.segmenter import CellposeSegmenter
            self.seg = CellposeSegmenter(model_type=model_type, use_sam=use_sam)

    def stop(self):
        self._stop = True

    def run(self):
        try:
            if self.run_seg and not self._stop:
                if self.file_list:
                    # spreadsheet mode: segment explicit file list → output_dir
                    if self.engine == "stardist":
                        self.seg.segment_files(
                            self.file_list, str(self.output_dir),
                            prob_thresh=self.prob_thresh, nms_thresh=self.nms_thresh,
                            progress_callback=self.cellpose_progress.emit,
                        )
                    else:
                        self.seg.segment_files(
                            self.file_list, str(self.output_dir),
                            diameter=int(self.diameter),
                            flow_threshold=self.flow_threshold,
                            cellprob_threshold=self.cellprob_threshold,
                            max_iter=self.max_iter,
                            progress_callback=self.cellpose_progress.emit,
                        )
                else:
                    # folder mode: segment all images in base_dir
                    if self.engine == "stardist":
                        self.seg.segment(
                            str(self.base_dir),
                            prob_thresh=self.prob_thresh, nms_thresh=self.nms_thresh,
                            progress_callback=self.cellpose_progress.emit,
                        )
                    else:
                        self.seg.segment(
                            str(self.base_dir), diameter=int(self.diameter),
                            flow_threshold=self.flow_threshold,
                            cellprob_threshold=self.cellprob_threshold,
                            max_iter=self.max_iter, max_resize=self.max_resize,
                            progress_callback=self.cellpose_progress.emit,
                        )
            if self.run_l2r and not self._stop:
                self._labels_to_rois()
        except Exception as e:
            logger.error(f"Worker error: {e}")
            self.error_occurred.emit(str(e))
        finally:
            self.finished.emit()

    def _labels_to_rois(self):
        # In spreadsheet mode, masks are in output_dir. In folder mode, masks are in base_dir.
        mask_search_dir = self.output_dir if self.file_list else self.base_dir
        masks = list(mask_search_dir.glob("*cp_masks*"))
        total = len(masks)
        if not total:
            self.labels2rois_progress.emit(100)
            return
        self.labels2rois_progress.emit(0)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Build originals cache from file_list or base_dir
        if self.file_list:
            cache = {Path(p).stem: p for p in self.file_list}
        else:
            cache = self._originals_cache()

        for i, mp in enumerate(masks):
            if self._stop:
                break
            orig = self._find_original(mp, cache)
            if not orig or not Path(orig).exists():
                logger.warning(f"Original not found for mask: {mp.name}")
                continue
            try:
                stem = mp.stem
                ROIVisualizer(
                    str(mp), str(orig),
                    str(self.output_dir / f"{stem}.xlsx"),
                    str(self.output_dir / f"{stem}_ROI.png"),
                    show_labels=True,
                    progress_callback=self.labels2rois_progress.emit,
                ).save_rois_to_excel()
            except Exception as e:
                logger.error(f"ROI error {mp}: {e}")
            self.labels2rois_progress.emit(((i + 1) / total) * 100)
        if not self._stop:
            sd = self.output_dir / "SummarySheet"
            sd.mkdir(exist_ok=True)
            generate_summary_sheet(str(self.output_dir), str(sd / "Summary.xlsx"))

    def _originals_cache(self):
        exts = {".tif", ".tiff", ".png", ".jpg", ".jpeg"}
        return {p.stem: str(p) for p in self.base_dir.rglob("*")
                if p.suffix.lower() in exts and "_cp_masks" not in p.name}

    @staticmethod
    def _find_original(mask_path, cache):
        pat = re.sub(r"_cp_masks.*", "", mask_path.stem)
        if pat in cache:
            return cache[pat]
        for stem, path in cache.items():
            if pat in stem:
                return path
        return None


# ═══════════════════════════════════════════════════════════════════════════
# Page: Segmentation
# ═══════════════════════════════════════════════════════════════════════════

class SegmentationPage(QWidget):
    open_in_viewer = pyqtSignal(str)  # emits a folder path

    def __init__(self):
        super().__init__()
        self.base_dir = ""
        self.output_dir = ""
        self.diameter = 0
        self.worker_thread = None
        self.cuda_available = check_cuda_availability()
        self.sam_manager = SAMModelManager()
        self._spreadsheet_records = []   # parsed from xlsx
        self._active_tags = set()        # currently selected tag filters
        try:
            self.sam_ok, self.sam_status = check_sam_compatibility()
        except Exception as e:
            self.sam_ok, self.sam_status = False, str(e)
        self._build()

    # ── layout ────────────────────────────────────────────────────────────

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        page = QWidget()
        page.setObjectName("PageContent")
        col = QVBoxLayout(page)
        col.setContentsMargins(36, 32, 36, 32)
        col.setSpacing(24)

        # page header
        title = QLabel("Segmentation")
        title.setObjectName("PageTitle")
        sub = QLabel("Run AI-powered cell segmentation and ROI analysis on your images.")
        sub.setObjectName("PageSubtitle")
        col.addWidget(title)
        col.addWidget(sub)
        col.addSpacing(4)

        # ── card: directories ─────────────────────────────────────────────
        dir_lay = QVBoxLayout()
        dir_lay.addLayout(_section_header("Input"))
        dir_lay.addSpacing(4)

        # Input mode selector
        self.input_mode_combo = QComboBox()
        self.input_mode_combo.addItem("Folder", "folder")
        self.input_mode_combo.addItem("Spreadsheet (xlsx)", "spreadsheet")
        self.input_mode_combo.currentIndexChanged.connect(self._on_input_mode_changed)
        dir_lay.addLayout(_field_row("Input mode", self.input_mode_combo))

        # -- folder mode widgets --
        self._folder_widget = QWidget()
        fw_lay = QVBoxLayout(self._folder_widget)
        fw_lay.setContentsMargins(0, 0, 0, 0)
        fw_lay.setSpacing(10)
        self.base_dir_edit = QLineEdit()
        self.base_dir_edit.setPlaceholderText("Path to folder containing your images…")
        fw_lay.addLayout(_field_row(
            "Input directory",
            _browse_row(self.base_dir_edit, "Browse", self._pick_base_dir,
                        view_callback=lambda: self._view_dir(self.base_dir_edit)),
        ))

        # -- spreadsheet mode widgets --
        self._sheet_widget = QWidget()
        sw_lay = QVBoxLayout(self._sheet_widget)
        sw_lay.setContentsMargins(0, 0, 0, 0)
        sw_lay.setSpacing(10)
        self.xlsx_edit = QLineEdit()
        self.xlsx_edit.setPlaceholderText("Path to experiment .xlsx file…")
        xlsx_row = _browse_row(self.xlsx_edit, "Browse", self._pick_xlsx)
        sw_lay.addLayout(_field_row("Spreadsheet", xlsx_row))

        import_btn = QPushButton("Parse spreadsheet")
        import_btn.setStyleSheet(get_primary_button_style())
        import_btn.clicked.connect(self._parse_spreadsheet)
        sw_lay.addWidget(import_btn)

        self._tag_count_label = QLabel("")
        self._tag_count_label.setObjectName("FieldLabel")
        sw_lay.addWidget(self._tag_count_label)

        # filter panel (hidden until parse)
        self._filter_frame = QFrame()
        self._filter_frame.setObjectName("Card")
        fl = QVBoxLayout(self._filter_frame)
        fl.setContentsMargins(16, 14, 16, 14)
        fl.setSpacing(12)

        fl_title = QLabel("Filters")
        fl_title.setObjectName("SectionTitle")
        fl.addWidget(fl_title)

        def _filter_section(label_text):
            """Create a filter section with label, select/unselect buttons, and grid."""
            lbl = QLabel(label_text)
            lbl.setObjectName("FieldLabel")
            fl.addWidget(lbl)

            btn_row = QHBoxLayout()
            btn_row.setSpacing(6)
            sel_btn = QPushButton("Select All")
            sel_btn.setFixedHeight(24)
            sel_btn.setFixedWidth(90)
            unsel_btn = QPushButton("Unselect All")
            unsel_btn.setFixedHeight(24)
            unsel_btn.setFixedWidth(90)
            btn_row.addWidget(sel_btn)
            btn_row.addWidget(unsel_btn)
            btn_row.addStretch()
            fl.addLayout(btn_row)

            grid = QGridLayout()
            grid.setSpacing(6)
            fl.addLayout(grid)

            return grid, sel_btn, unsel_btn

        self._well_checks_layout, self._well_sel_btn, self._well_unsel_btn = _filter_section("Wells")
        self._stage_checks_layout, self._stage_sel_btn, self._stage_unsel_btn = _filter_section("Stage")
        self._chan_checks_layout, self._chan_sel_btn, self._chan_unsel_btn = _filter_section("Channel")
        self._type_checks_layout, self._type_sel_btn, self._type_unsel_btn = _filter_section("Type")

        self._filter_frame.setVisible(False)
        sw_lay.addWidget(self._filter_frame)

        # input mode stack
        self._input_stack = QStackedWidget()
        self._input_stack.addWidget(self._folder_widget)
        self._input_stack.addWidget(self._sheet_widget)
        self._input_stack.setCurrentIndex(0)
        dir_lay.addWidget(self._input_stack)

        # output dir (shared by both modes)
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setPlaceholderText("Path to save results…")
        dir_lay.addLayout(_field_row(
            "Output directory",
            _browse_row(self.output_dir_edit, "Browse", self._pick_output_dir,
                        view_callback=lambda: self._view_dir(self.output_dir_edit)),
        ))
        col.addWidget(_card(dir_lay))

        # ── card: pipeline options ────────────────────────────────────────
        pipe_lay = QVBoxLayout()
        pipe_lay.addLayout(_section_header("Pipeline", "Choose which steps to run."))
        pipe_lay.addSpacing(4)

        self.chk_seg = ToggleSwitch("Run segmentation")
        self.chk_l2r = ToggleSwitch("Run label → ROI analysis")
        pipe_lay.addWidget(self.chk_seg)
        pipe_lay.addWidget(self.chk_l2r)
        col.addWidget(_card(pipe_lay))

        # ── card: model ───────────────────────────────────────────────────
        model_lay = QVBoxLayout()
        model_lay.addLayout(_section_header("Model", "Select the segmentation engine and model."))
        model_lay.addSpacing(4)

        # engine selector
        self.engine_combo = QComboBox()
        self.engine_combo.addItem("Cellpose", "cellpose")
        self.engine_combo.addItem("StarDist", "stardist")
        self.engine_combo.currentIndexChanged.connect(self._on_engine_changed)
        model_lay.addLayout(_field_row("Engine", self.engine_combo))

        # -- cellpose options (stacked widget index 0) --
        self._cp_widget = QWidget()
        cp_lay = QVBoxLayout(self._cp_widget)
        cp_lay.setContentsMargins(0, 0, 0, 0)
        cp_lay.setSpacing(12)

        self.chk_sam = ToggleSwitch("Use Cellpose-SAM  (recommended)", checked=self.sam_ok)
        self.chk_sam.setEnabled(self.sam_ok)
        self.chk_sam.toggled.connect(self._on_sam_toggled)
        cp_lay.addWidget(self.chk_sam)

        self.model_combo = self._make_model_combo()
        cp_lay.addLayout(_field_row("Cellpose model", self.model_combo))

        self.custom_model_edit = QLineEdit()
        self.custom_model_edit.setPlaceholderText("Optional — path to a custom .pth model")
        cp_lay.addLayout(_field_row(
            "Custom model",
            _browse_row(self.custom_model_edit, "Browse", self._pick_custom_model),
            hint="Leave empty to use the selected model above.",
        ))

        self.diameter_spin = QSpinBox()
        self.diameter_spin.setRange(0, 500)
        self.diameter_spin.setValue(0)
        self.diameter_spin.setSpecialValueText("Auto-detect")
        self.diameter_spin.setSuffix(" px")
        self.diameter_spin.valueChanged.connect(lambda v: setattr(self, "diameter", v))
        cp_lay.addLayout(_field_row(
            "Cell diameter", self.diameter_spin,
            hint="Set to 0 for automatic detection. SAM is diameter-invariant.",
        ))

        # -- stardist options (stacked widget index 1) --
        self._sd_widget = QWidget()
        sd_lay = QVBoxLayout(self._sd_widget)
        sd_lay.setContentsMargins(0, 0, 0, 0)
        sd_lay.setSpacing(12)

        self.sd_model_combo = QComboBox()
        try:
            from s2l.core.stardist_segmenter import STARDIST_PRETRAINED
            for key, label in STARDIST_PRETRAINED.items():
                self.sd_model_combo.addItem(label, key)
        except Exception:
            self.sd_model_combo.addItem("Versatile (fluorescent nuclei)", "2D_versatile_fluo")
        sd_lay.addLayout(_field_row("StarDist model", self.sd_model_combo))

        self.sd_prob_spin = QDoubleSpinBox()
        self.sd_prob_spin.setRange(0.0, 1.0)
        self.sd_prob_spin.setSingleStep(0.05)
        self.sd_prob_spin.setValue(0.5)
        self.sd_prob_spin.setDecimals(2)
        sd_lay.addLayout(_field_row("Probability threshold", self.sd_prob_spin,
                                    hint="Objects below this confidence are discarded."))

        self.sd_nms_spin = QDoubleSpinBox()
        self.sd_nms_spin.setRange(0.0, 1.0)
        self.sd_nms_spin.setSingleStep(0.05)
        self.sd_nms_spin.setValue(0.4)
        self.sd_nms_spin.setDecimals(2)
        sd_lay.addLayout(_field_row("NMS overlap threshold", self.sd_nms_spin,
                                    hint="Overlapping objects above this are merged."))

        _sd_available = False
        try:
            from s2l.core.stardist_segmenter import STARDIST_AVAILABLE
            _sd_available = STARDIST_AVAILABLE
        except Exception:
            pass
        if not _sd_available:
            warn = QLabel("StarDist is not installed. Install with: pip install stardist")
            warn.setObjectName("StatusWarning")
            warn.setWordWrap(True)
            sd_lay.addWidget(warn)

        # engine options stack
        self._engine_stack = QStackedWidget()
        self._engine_stack.addWidget(self._cp_widget)
        self._engine_stack.addWidget(self._sd_widget)
        self._engine_stack.setCurrentIndex(0)
        model_lay.addWidget(self._engine_stack)
        col.addWidget(_card(model_lay))

        # ── card: advanced ────────────────────────────────────────────────
        adv_group = QGroupBox("Advanced parameters")
        adv_group.setCheckable(True)
        adv_group.setChecked(False)
        adv_inner = QVBoxLayout()
        adv_inner.setSpacing(16)
        adv_inner.setContentsMargins(12, 16, 12, 12)

        self.flow_spin = QDoubleSpinBox()
        self.flow_spin.setRange(0.1, 3.0)
        self.flow_spin.setSingleStep(0.1)
        self.flow_spin.setValue(0.4)
        self.flow_spin.setDecimals(1)
        adv_inner.addLayout(_field_row("Flow threshold", self.flow_spin, "Default 0.4 — increase if missing ROIs."))

        self.cellprob_spin = QDoubleSpinBox()
        self.cellprob_spin.setRange(-6.0, 6.0)
        self.cellprob_spin.setSingleStep(0.1)
        self.cellprob_spin.setValue(0.0)
        self.cellprob_spin.setDecimals(1)
        adv_inner.addLayout(_field_row("Cell-probability threshold", self.cellprob_spin, "Default 0.0"))

        self.iter_spin = QSpinBox()
        self.iter_spin.setRange(0, 10000)
        self.iter_spin.setSingleStep(100)
        self.iter_spin.setValue(0)
        self.iter_spin.setSpecialValueText("Auto")
        adv_inner.addLayout(_field_row("Max iterations", self.iter_spin, "0 = auto (diameter-based)."))

        self.resize_spin = QSpinBox()
        self.resize_spin.setRange(100, 5000)
        self.resize_spin.setSingleStep(100)
        self.resize_spin.setValue(1000)
        self.resize_spin.setSuffix(" px")
        adv_inner.addLayout(_field_row("Max resize", self.resize_spin))

        docs_btn = QPushButton("Open Cellpose docs")
        docs_btn.clicked.connect(lambda: webbrowser.open(
            "https://cellpose.readthedocs.io/en/latest/settings.html"))
        adv_inner.addWidget(docs_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        adv_group.setLayout(adv_inner)
        col.addWidget(adv_group)

        # ── action buttons ────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        self.run_btn = QPushButton("Start processing")
        self.run_btn.setStyleSheet(get_primary_button_style())
        self.run_btn.clicked.connect(self._run)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setStyleSheet(get_danger_button_style())
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop)
        btn_row.addWidget(self.run_btn, 3)
        btn_row.addWidget(self.stop_btn, 1)
        col.addLayout(btn_row)

        # ── progress ──────────────────────────────────────────────────────
        prog_lay = QVBoxLayout()
        prog_lay.addLayout(_section_header("Progress"))
        prog_lay.addSpacing(2)

        seg_lbl = QLabel("Segmentation")
        seg_lbl.setObjectName("FieldLabel")
        self.seg_bar = QProgressBar()
        self.seg_bar.setFormat("%p%")
        prog_lay.addWidget(seg_lbl)
        prog_lay.addWidget(self.seg_bar)

        roi_lbl = QLabel("ROI analysis")
        roi_lbl.setObjectName("FieldLabel")
        self.roi_bar = QProgressBar()
        self.roi_bar.setFormat("%p%")
        prog_lay.addWidget(roi_lbl)
        prog_lay.addWidget(self.roi_bar)
        col.addWidget(_card(prog_lay))

        # ── status chips ──────────────────────────────────────────────────
        status_row = QHBoxLayout()
        status_row.setSpacing(16)
        gpu_lbl = QLabel("GPU" if self.cuda_available else "CPU only")
        gpu_lbl.setObjectName("StatusSuccess" if self.cuda_available else "StatusWarning")
        status_row.addWidget(gpu_lbl)
        sam_lbl = QLabel("SAM ready" if self.sam_ok else f"SAM: {self.sam_status}")
        sam_lbl.setObjectName("StatusSuccess" if self.sam_ok else "StatusWarning")
        sam_lbl.setWordWrap(True)
        status_row.addWidget(sam_lbl, 1)
        col.addLayout(status_row)

        col.addStretch()
        root.addWidget(_scrollable(page))

    # ── helpers ───────────────────────────────────────────────────────────

    def _make_model_combo(self):
        c = QComboBox()
        for key, name in [
            ("cpsam", "Cellpose-SAM (latest)"), ("cyto3", "Cytoplasm 3"),
            ("cyto2", "Cytoplasm 2"), ("cyto", "Cytoplasm 1"),
            ("nuclei", "Nuclei"), ("tissuenet_cp3", "TissueNet"),
            ("livecell_cp3", "LiveCell"), ("yeast_PhC_cp3", "Yeast PhC"),
            ("yeast_BF_cp3", "Yeast BF"), ("bact_phase_cp3", "Bacteria Phase"),
            ("bact_fluor_cp3", "Bacteria Fluor"), ("deepbacs_cp3", "DeepBacs"),
        ]:
            c.addItem(name, key)
        return c

    def _on_engine_changed(self, idx):
        self._engine_stack.setCurrentIndex(idx)

    def _on_input_mode_changed(self, idx):
        self._input_stack.setCurrentIndex(idx)
        self._spreadsheet_records.clear()
        self._active_tags.clear()

    def _pick_xlsx(self):
        p, _ = QFileDialog.getOpenFileName(self, "Select spreadsheet", "",
                                           "Excel (*.xlsx *.xls);;All (*)")
        if p:
            self.xlsx_edit.setText(p)

    def _parse_spreadsheet(self):
        xlsx_path = self.xlsx_edit.text().strip()
        if not xlsx_path or not os.path.isfile(xlsx_path):
            QMessageBox.warning(self, "No file", "Select a valid .xlsx file first.")
            return
        try:
            self._spreadsheet_records = parse_fim_sheet(xlsx_path)
            self._active_tags.clear()
            self._rebuild_filters()
            self._update_filter_count()
            self._filter_frame.setVisible(bool(self._spreadsheet_records))
        except Exception as e:
            QMessageBox.critical(self, "Parse error", str(e))

    def _rebuild_filters(self):
        """Build checkbox groups from the parsed records."""
        records = self._spreadsheet_records

        # collect unique values per category
        wells = sorted({r["well"] for r in records if r["well"]})
        stages = sorted({r["stage"] for r in records if r["stage"]})
        channels = sorted({r["channel"] for r in records if r["channel"]})
        types = sorted({r["type"] for r in records if r["type"]})

        self._filter_checks = {}  # (category, value) -> QCheckBox

        COLS = 5  # checkboxes per row

        def _populate(grid, category, values, sel_btn, unsel_btn):
            # clear existing widgets from grid
            while grid.count():
                item = grid.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            cbs = []
            for i, val in enumerate(values):
                cb = QCheckBox(val)
                cb.setChecked(True)
                cb.stateChanged.connect(lambda _, c=category, v=val: self._on_filter_changed())
                self._filter_checks[(category, val)] = cb
                grid.addWidget(cb, i // COLS, i % COLS)
                cbs.append(cb)

            # wire select / unselect buttons
            try:
                sel_btn.clicked.disconnect()
            except TypeError:
                pass
            try:
                unsel_btn.clicked.disconnect()
            except TypeError:
                pass
            sel_btn.clicked.connect(lambda: self._set_all_checks(cbs, True))
            unsel_btn.clicked.connect(lambda: self._set_all_checks(cbs, False))

        _populate(self._well_checks_layout, "well", wells, self._well_sel_btn, self._well_unsel_btn)
        _populate(self._stage_checks_layout, "stage", stages, self._stage_sel_btn, self._stage_unsel_btn)
        _populate(self._chan_checks_layout, "channel", channels, self._chan_sel_btn, self._chan_unsel_btn)
        _populate(self._type_checks_layout, "type", types, self._type_sel_btn, self._type_unsel_btn)

    def _set_all_checks(self, checkboxes, checked: bool):
        """Set all checkboxes in a list to checked/unchecked and update filters."""
        for cb in checkboxes:
            cb.setChecked(checked)
        self._on_filter_changed()

    def _on_filter_changed(self):
        self._update_filter_count()

    def _get_filtered_records(self) -> list[dict]:
        """Return records matching all checked filters (AND across categories)."""
        # collect checked values per category
        checked: dict[str, set[str]] = {}
        for (cat, val), cb in self._filter_checks.items():
            if cb.isChecked():
                checked.setdefault(cat, set()).add(val)

        result = []
        for r in self._spreadsheet_records:
            match = True
            for cat, allowed in checked.items():
                if r.get(cat, "") and r[cat] not in allowed:
                    match = False
                    break
            if match:
                result.append(r)
        return result

    def _update_filter_count(self):
        filtered = self._get_filtered_records()
        total = len(self._spreadsheet_records)
        self._tag_count_label.setText(f"{len(filtered)} / {total} images selected")

    def _on_sam_toggled(self, on):
        if on:
            self.model_combo.setCurrentIndex(0)
        self.model_combo.setEnabled(not on)

    def _pick_base_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Select input directory")
        if d:
            self.base_dir = d
            self.base_dir_edit.setText(d)

    def _pick_output_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Select output directory")
        if d:
            self.output_dir = d
            self.output_dir_edit.setText(d)

    def _pick_custom_model(self):
        p, _ = QFileDialog.getOpenFileName(self, "Select model", "", "Model (*.pth *.pt);;All (*)")
        if p:
            self.custom_model_edit.setText(p)

    def _view_dir(self, line_edit: QLineEdit):
        path = line_edit.text().strip()
        if path and os.path.isdir(path):
            self.open_in_viewer.emit(path)
        else:
            QMessageBox.information(self, "No folder", "Enter or browse a valid directory first.")

    # ── run / stop ────────────────────────────────────────────────────────

    def _run(self):
        input_mode = self.input_mode_combo.currentData()
        is_sheet = input_mode == "spreadsheet"

        if not is_sheet and not self.base_dir:
            QMessageBox.warning(self, "Missing input", "Select an input directory.")
            return
        if is_sheet and not self._spreadsheet_records:
            QMessageBox.warning(self, "No data", "Import a spreadsheet first.")
            return
        if not self.output_dir:
            QMessageBox.warning(self, "Missing output", "Select an output directory.")
            return
        if not self.chk_seg.isChecked() and not self.chk_l2r.isChecked():
            QMessageBox.warning(self, "Nothing selected", "Enable at least one pipeline step.")
            return

        self.seg_bar.setValue(0)
        self.roi_bar.setValue(0)
        self.run_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        use_sam = self.chk_sam.isChecked() and self.sam_ok
        engine = self.engine_combo.currentData()

        # Build file list for spreadsheet mode
        file_list = None
        base_dir = self.base_dir
        if is_sheet:
            filtered = self._get_filtered_records()
            file_list = [r["path"] for r in filtered]
            base_dir = self.output_dir  # masks will be in output_dir

        try:
            self.worker_thread = WorkerThread(
                base_dir, self.output_dir, self.diameter,
                self.chk_seg.isChecked(), self.chk_l2r.isChecked(),
                engine=engine,
                model_type="cpsam" if use_sam else self.model_combo.currentData(),
                use_sam=use_sam,
                custom_model_path=self.custom_model_edit.text() or None,
                flow_threshold=self.flow_spin.value(),
                cellprob_threshold=self.cellprob_spin.value(),
                max_iter=self.iter_spin.value(),
                max_resize=self.resize_spin.value(),
                stardist_model=self.sd_model_combo.currentData(),
                prob_thresh=self.sd_prob_spin.value(),
                nms_thresh=self.sd_nms_spin.value(),
                file_list=file_list,
            )
        except Exception as e:
            QMessageBox.critical(self, "Model error", f"Failed to initialize model:\n{e}")
            self._done()
            return

        self.worker_thread.cellpose_progress.connect(lambda v: self.seg_bar.setValue(int(v)))
        self.worker_thread.labels2rois_progress.connect(lambda v: self.roi_bar.setValue(int(v)))
        self.worker_thread.finished.connect(self._done)
        self.worker_thread.error_occurred.connect(
            lambda m: QMessageBox.critical(self, "Error", m))
        self.worker_thread.start()

    def _stop(self):
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.stop()
            self.worker_thread.wait(5000)
            if self.worker_thread.isRunning():
                self.worker_thread.terminate()
            self._done()

    def _done(self):
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)


# ═══════════════════════════════════════════════════════════════════════════
# Page: Training
# ═══════════════════════════════════════════════════════════════════════════

class TrainingPage(QWidget):
    open_in_viewer = pyqtSignal(str)  # emits a folder path

    def __init__(self):
        super().__init__()
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        page = QWidget()
        page.setObjectName("PageContent")
        col = QVBoxLayout(page)
        col.setContentsMargins(36, 32, 36, 32)
        col.setSpacing(24)

        title = QLabel("Training")
        title.setObjectName("PageTitle")
        sub = QLabel("Fine-tune a Cellpose model on your own labelled data.")
        sub.setObjectName("PageSubtitle")
        col.addWidget(title)
        col.addWidget(sub)
        col.addSpacing(4)

        # ── card: data ────────────────────────────────────────────────────
        data_lay = QVBoxLayout()
        data_lay.addLayout(_section_header("Training data"))
        data_lay.addSpacing(4)

        self.train_dir_edit = QLineEdit()
        self.train_dir_edit.setPlaceholderText("Folder with images + masks…")
        data_lay.addLayout(_field_row(
            "Training directory",
            _browse_row(self.train_dir_edit, "Browse", self._pick_train_dir,
                        view_callback=self._view_train_dir),
        ))

        self.mask_filter = QLineEdit("_cp_masks")
        data_lay.addLayout(_field_row("Mask file suffix", self.mask_filter))

        self.img_filter = QLineEdit("_img")
        data_lay.addLayout(_field_row("Image file suffix", self.img_filter))
        col.addWidget(_card(data_lay))

        # ── card: hyper-parameters ────────────────────────────────────────
        hp_lay = QVBoxLayout()
        hp_lay.addLayout(_section_header("Hyper-parameters"))
        hp_lay.addSpacing(4)

        self.base_model_combo = QComboBox()
        self.base_model_combo.addItems([
            "cyto3", "cyto2", "cyto", "nuclei",
            "tissuenet_cp3", "livecell_cp3", "deepbacs_cp3",
        ])
        hp_lay.addLayout(_field_row("Base model", self.base_model_combo))

        self.channels_edit = QLineEdit("1,2")
        hp_lay.addLayout(_field_row("Channels", self.channels_edit, "e.g. 1,2 for cytoplasm + nuclei"))

        self.epochs_spin = QSpinBox()
        self.epochs_spin.setRange(1, 1000)
        self.epochs_spin.setValue(100)
        hp_lay.addLayout(_field_row("Epochs", self.epochs_spin))

        self.lr_spin = QDoubleSpinBox()
        self.lr_spin.setRange(0.0001, 1.0)
        self.lr_spin.setSingleStep(0.01)
        self.lr_spin.setValue(0.1)
        self.lr_spin.setDecimals(4)
        hp_lay.addLayout(_field_row("Learning rate", self.lr_spin))

        self.norm_chk = ToggleSwitch("Normalize images", checked=True)
        hp_lay.addWidget(self.norm_chk)

        self.model_name_edit = QLineEdit("my_model")
        hp_lay.addLayout(_field_row("Save model as", self.model_name_edit))
        col.addWidget(_card(hp_lay))

        # ── action ────────────────────────────────────────────────────────
        train_btn = QPushButton("Start training")
        train_btn.setStyleSheet(get_primary_button_style())
        train_btn.clicked.connect(self._train)
        col.addWidget(train_btn)

        col.addStretch()
        root.addWidget(_scrollable(page))

    def _pick_train_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Select training directory")
        if d:
            self.train_dir_edit.setText(d)

    def _view_train_dir(self):
        path = self.train_dir_edit.text().strip()
        if path and os.path.isdir(path):
            self.open_in_viewer.emit(path)
        else:
            QMessageBox.information(self, "No folder", "Enter or browse a valid directory first.")

    def _train(self):
        td = self.train_dir_edit.text()
        if not td:
            QMessageBox.warning(self, "Missing input", "Select a training directory.")
            return
        try:
            from s2l.core.trainer import Trainer
            trainer = Trainer(train_dir=td, mask_filter=self.mask_filter.text(),
                              img_filter=self.img_filter.text())
            channels = [int(x.strip()) for x in self.channels_edit.text().split(",")]
            path, tl, _ = trainer.train(
                model_name=self.model_name_edit.text(),
                model_type=self.base_model_combo.currentText(),
                channels=channels, epochs=self.epochs_spin.value(),
                learning_rate=self.lr_spin.value(),
                normalize=self.norm_chk.isChecked(),
            )
            QMessageBox.information(self, "Done",
                                    f"Model saved to:\n{path}\n\nFinal loss: {tl[-1]:.4f}")
        except Exception as e:
            QMessageBox.critical(self, "Training failed", str(e))


# ═══════════════════════════════════════════════════════════════════════════
# Page: Tools
# ═══════════════════════════════════════════════════════════════════════════

class ToolsPage(QWidget):
    def __init__(self):
        super().__init__()
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        page = QWidget()
        page.setObjectName("PageContent")
        col = QVBoxLayout(page)
        col.setContentsMargins(36, 32, 36, 32)
        col.setSpacing(24)

        title = QLabel("Tools")
        title.setObjectName("PageTitle")
        sub = QLabel("Launch external utilities and run system checks.")
        sub.setObjectName("PageSubtitle")
        col.addWidget(title)
        col.addWidget(sub)
        col.addSpacing(4)

        # ── card: external tools ──────────────────────────────────────────
        ext_lay = QVBoxLayout()
        ext_lay.addLayout(_section_header("External tools"))
        ext_lay.addSpacing(4)

        grid = QGridLayout()
        grid.setSpacing(10)
        for i, (text, cmd) in enumerate([
            ("Cellpose GUI", [sys.executable, "-m", "cellpose"]),
            ("Image preprocessor", [sys.executable, "-m", "s2l.ui.preprocessing_gui"]),
            ("Himena viewer", ["himena"]),
        ]):
            btn = QPushButton(text)
            btn.clicked.connect(lambda _, c=cmd: self._launch(c))
            grid.addWidget(btn, i // 2, i % 2)
        ext_lay.addLayout(grid)
        col.addWidget(_card(ext_lay))

        # ── card: system checks ───────────────────────────────────────────
        sys_lay = QVBoxLayout()
        sys_lay.addLayout(_section_header("System checks"))
        sys_lay.addSpacing(4)

        grid2 = QGridLayout()
        grid2.setSpacing(10)
        for i, (text, cmd) in enumerate([
            ("Verify installation", [sys.executable, "verify_installation.py"]),
            ("Test SAM", [sys.executable, "test_sam.py"]),
        ]):
            btn = QPushButton(text)
            btn.clicked.connect(lambda _, c=cmd: self._launch(c))
            grid2.addWidget(btn, 0, i)
        sys_lay.addLayout(grid2)
        col.addWidget(_card(sys_lay))

        col.addStretch()
        root.addWidget(_scrollable(page))

    def _launch(self, cmd):
        try:
            subprocess.Popen(cmd)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not launch:\n{e}")


# ═══════════════════════════════════════════════════════════════════════════
# Sidebar navigation
# ═══════════════════════════════════════════════════════════════════════════

class _SideBar(QWidget):
    """Vertical navigation rail with icon-label buttons."""
    page_changed = pyqtSignal(int)

    NAV_ITEMS = [
        ("Segmentation", "🔬"),
        ("Training",     "🧠"),
        ("Viewer",       "🖼"),
        ("Tools",        "🛠"),
    ]

    def __init__(self):
        super().__init__()
        self.setObjectName("SideBar")
        self.setFixedWidth(190)
        self._buttons: list[QPushButton] = []

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 20, 12, 20)
        lay.setSpacing(4)

        # app branding
        brand = QLabel("S2L")
        brand.setStyleSheet(
            f"font-size: 20px; font-weight: 800; color: {COLORS['accent']}; "
            "letter-spacing: 2px; padding: 0 4px; background: transparent;"
        )
        edition = QLabel("Cell Segmentation & Analysis")
        edition.setStyleSheet(
            f"font-size: 10px; color: {COLORS['text_dim']}; padding: 0 4px; background: transparent;"
        )
        lay.addWidget(brand)
        lay.addWidget(edition)
        lay.addSpacing(28)

        for idx, (label, icon) in enumerate(self.NAV_ITEMS):
            btn = QPushButton(f"  {icon}   {label}")
            btn.setObjectName("NavBtn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setMinimumHeight(38)
            btn.clicked.connect(lambda _, i=idx: self._select(i))
            lay.addWidget(btn)
            self._buttons.append(btn)

        lay.addStretch()

        # version / footer
        ver = QLabel("v2.0")
        ver.setStyleSheet(
            f"font-size: 10px; color: {COLORS['text_dim']}; padding: 0 4px; background: transparent;"
        )
        lay.addWidget(ver)

        self._select(0)

    def _select(self, idx: int):
        for i, b in enumerate(self._buttons):
            b.setProperty("active", "true" if i == idx else "false")
            b.style().unpolish(b)
            b.style().polish(b)
        self.page_changed.emit(idx)


# ═══════════════════════════════════════════════════════════════════════════
# Main window
# ═══════════════════════════════════════════════════════════════════════════

class MainApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("S2L")
        self.setMinimumSize(960, 640)
        self.resize(1200, 780)
        self.setStyleSheet(get_complete_stylesheet())

        # central widget
        central = QWidget()
        h = QHBoxLayout(central)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)

        # sidebar
        self.sidebar = _SideBar()
        h.addWidget(self.sidebar)

        # page stack
        self.stack = QStackedWidget()
        self.stack.setObjectName("PageStack")

        self._seg_page = SegmentationPage()
        self._train_page = TrainingPage()
        self._viewer_page = DatasetViewerPage()
        self._tools_page = ToolsPage()

        self.stack.addWidget(self._seg_page)      # 0
        self.stack.addWidget(self._train_page)     # 1
        self.stack.addWidget(self._viewer_page)    # 2
        self.stack.addWidget(self._tools_page)     # 3
        h.addWidget(self.stack, 1)

        self.sidebar.page_changed.connect(self.stack.setCurrentIndex)

        # connect "open in viewer" signals
        self._seg_page.open_in_viewer.connect(self._open_in_viewer)
        self._train_page.open_in_viewer.connect(self._open_in_viewer)

        self.setCentralWidget(central)

        # centre on screen
        scr = QApplication.primaryScreen()
        if scr:
            g = self.frameGeometry()
            g.moveCenter(scr.geometry().center())
            self.move(g.topLeft())

    def _open_in_viewer(self, folder_path: str):
        """Switch to the Viewer page and load the given folder."""
        viewer_idx = 2
        self.sidebar._select(viewer_idx)
        self.stack.setCurrentIndex(viewer_idx)
        self._viewer_page.open_folder(folder_path)

    def closeEvent(self, event):
        seg = self._seg_page
        if hasattr(seg, "worker_thread") and seg.worker_thread and seg.worker_thread.isRunning():
            reply = QMessageBox.question(
                self, "Confirm exit",
                "Processing is still running. Stop and exit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                seg._stop()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


def main():
    app = QApplication(sys.argv)
    w = MainApp()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
