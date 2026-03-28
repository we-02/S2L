"""
Polished dark theme for the S2L application.

Design language:
  - Deep charcoal background with subtle layering
  - Indigo/violet accent (#7c6aef) for interactive elements
  - Card-based layout with soft rounded corners and 1px borders
  - Generous padding and spacing for readability
"""

# ── colour tokens ──────────────────────────────────────────────────────────

COLORS = {
    # accent
    "accent":          "#7c6aef",
    "accent_hover":    "#9585f5",
    "accent_pressed":  "#6455d0",
    "accent_muted":    "rgba(124, 106, 239, 30)",
    "accent_glow":     "rgba(124, 106, 239, 64)",

    # surfaces
    "bg_window":       "#101014",
    "bg_base":         "#16161a",
    "bg_card":         "#1e1e24",
    "bg_input":        "#25252d",
    "bg_hover":        "#2c2c36",
    "bg_elevated":     "#323240",

    # text
    "text":            "#eaeaef",
    "text_secondary":  "#a0a0b0",
    "text_dim":        "#65657a",
    "text_on_accent":  "#ffffff",

    # semantic
    "success":         "#34d399",
    "warning":         "#fbbf24",
    "error":           "#f87171",

    # borders
    "border":          "#2a2a35",
    "border_subtle":   "#222230",
    "border_focus":    "#7c6aef",
}

C = COLORS  # shorthand used inside f-strings

# ── reusable style fragments ──────────────────────────────────────────────

FONT_STACK = "'Segoe UI', 'Inter', 'SF Pro Display', 'Helvetica Neue', Arial, sans-serif"


def get_primary_button_style():
    """Accent-coloured call-to-action button."""
    return f"""
    QPushButton {{
        background-color: {C['accent']};
        color: {C['text_on_accent']};
        border: none;
        border-radius: 6px;
        padding: 6px 20px;
        font-family: {FONT_STACK};
        font-size: 13px;
        font-weight: 600;
        min-height: 30px;
        letter-spacing: 0.3px;
    }}
    QPushButton:hover  {{ background-color: {C['accent_hover']}; }}
    QPushButton:pressed {{ background-color: {C['accent_pressed']}; }}
    QPushButton:disabled {{
        background-color: {C['bg_elevated']};
        color: {C['text_dim']};
    }}
    """


def get_danger_button_style():
    """Red stop / cancel button."""
    return f"""
    QPushButton {{
        background-color: transparent;
        color: {C['error']};
        border: 1px solid {C['error']};
        border-radius: 6px;
        padding: 6px 20px;
        font-family: {FONT_STACK};
        font-size: 13px;
        font-weight: 600;
        min-height: 30px;
    }}
    QPushButton:hover {{
        background-color: rgba(248, 113, 113, 25);
    }}
    QPushButton:disabled {{
        border-color: {C['border']};
        color: {C['text_dim']};
    }}
    """


def get_complete_stylesheet():
    """Master stylesheet applied to the top-level window."""
    return f"""
    /* ── base ─────────────────────────────────────────────── */
    * {{
        font-family: {FONT_STACK};
        outline: none;
    }}
    QMainWindow {{
        background-color: {C['bg_window']};
        color: {C['text']};
    }}
    QWidget {{
        color: {C['text']};
        font-size: 13px;
    }}
    QWidget#SideBar {{
        background-color: {C['bg_base']};
        border-right: 1px solid {C['border']};
    }}
    QWidget#PageStack, QWidget#PageContent {{
        background-color: {C['bg_window']};
    }}

    /* ── sidebar nav buttons ─────────────────────────────── */
    QPushButton#NavBtn {{
        background: transparent;
        color: {C['text_secondary']};
        border: none;
        border-radius: 8px;
        padding: 8px 16px;
        font-size: 13px;
        font-weight: 500;
        text-align: left;
        min-height: 22px;
    }}
    QPushButton#NavBtn:hover {{
        background-color: {C['bg_hover']};
        color: {C['text']};
    }}
    QPushButton#NavBtn[active="true"] {{
        background-color: {C['accent_muted']};
        color: {C['accent']};
        font-weight: 600;
    }}

    /* ── cards ────────────────────────────────────────────── */
    QFrame#Card {{
        background-color: {C['bg_card']};
        border: 1px solid {C['border']};
        border-radius: 12px;
    }}

    /* ── inputs ───────────────────────────────────────────── */
    QLineEdit {{
        background-color: {C['bg_input']};
        color: {C['text']};
        border: 1px solid {C['border']};
        border-radius: 6px;
        padding: 9px 12px;
        font-size: 13px;
        min-height: 20px;
        selection-background-color: {C['accent']};
    }}
    QSpinBox, QDoubleSpinBox {{
        background-color: {C['bg_input']};
        color: {C['text']};
        border: 1px solid {C['border']};
        border-radius: 6px;
        padding: 6px 10px;
        font-size: 13px;
        min-height: 28px;
        selection-background-color: {C['accent']};
    }}
    QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
        border-color: {C['accent']};
    }}
    QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover {{
        border-color: {C['bg_elevated']};
    }}
    QSpinBox::up-button, QDoubleSpinBox::up-button {{
        background: {C['bg_hover']};
        border: none;
        border-top-right-radius: 5px;
        width: 22px;
        margin: 1px 1px 0 0;
    }}
    QSpinBox::down-button, QDoubleSpinBox::down-button {{
        background: {C['bg_hover']};
        border: none;
        border-bottom-right-radius: 5px;
        width: 22px;
        margin: 0 1px 1px 0;
    }}
    QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
    QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
        background: {C['accent']};
    }}
    QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-bottom: 5px solid {C['text_secondary']};
    }}
    QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 5px solid {C['text_secondary']};
    }}

    /* ── combo box ────────────────────────────────────────── */
    QComboBox {{
        background-color: {C['bg_input']};
        color: {C['text']};
        border: 1px solid {C['border']};
        border-radius: 6px;
        padding: 8px 12px;
        font-size: 13px;
        min-height: 20px;
    }}
    QComboBox:hover {{ border-color: {C['bg_elevated']}; }}
    QComboBox:focus {{ border-color: {C['accent']}; }}
    QComboBox::drop-down {{ border: none; width: 28px; }}
    QComboBox::down-arrow {{
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 5px solid {C['text_secondary']};
        margin-right: 8px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {C['bg_card']};
        color: {C['text']};
        border: 1px solid {C['border']};
        border-radius: 6px;
        selection-background-color: {C['accent_muted']};
        selection-color: {C['accent']};
        outline: none;
        padding: 4px;
    }}
    QComboBox QAbstractItemView::item {{
        padding: 8px 12px;
        border-radius: 4px;
    }}
    QComboBox QAbstractItemView::item:hover {{
        background-color: {C['bg_hover']};
    }}

    /* ── check box ────────────────────────────────────────── */
    QCheckBox {{
        color: {C['text']};
        font-size: 13px;
        spacing: 10px;
        padding: 4px 0;
    }}
    QCheckBox::indicator {{
        width: 20px;
        height: 20px;
        border-radius: 6px;
        border: 2px solid {C['border']};
        background-color: {C['bg_input']};
    }}
    QCheckBox::indicator:hover {{
        border-color: {C['accent']};
        background-color: {C['bg_hover']};
    }}
    QCheckBox::indicator:checked {{
        background-color: {C['accent']};
        border-color: {C['accent']};
    }}
    QCheckBox::indicator:checked:hover {{
        background-color: {C['accent_hover']};
        border-color: {C['accent_hover']};
    }}
    QCheckBox:disabled {{
        color: {C['text_dim']};
    }}
    QCheckBox::indicator:disabled {{
        border-color: {C['border_subtle']};
        background-color: {C['bg_base']};
    }}

    /* ── progress bar ─────────────────────────────────────── */
    QProgressBar {{
        background-color: {C['bg_input']};
        border: 1px solid {C['border']};
        border-radius: 6px;
        text-align: center;
        font-size: 11px;
        font-weight: 600;
        color: {C['text_secondary']};
        min-height: 22px;
        max-height: 22px;
    }}
    QProgressBar::chunk {{
        background-color: {C['accent']};
        border-radius: 5px;
        margin: 1px;
    }}

    /* ── labels ───────────────────────────────────────────── */
    QLabel {{
        color: {C['text']};
        font-size: 13px;
        background: transparent;
    }}
    QLabel#SectionTitle {{
        font-size: 15px;
        font-weight: 700;
        color: {C['text']};
        padding: 0;
    }}
    QLabel#SectionDesc {{
        font-size: 12px;
        color: {C['text_secondary']};
        padding: 0;
    }}
    QLabel#FieldLabel {{
        font-size: 12px;
        font-weight: 600;
        color: {C['text_secondary']};
        padding: 0;
    }}
    QLabel#StatusSuccess {{ color: {C['success']}; font-weight: 600; font-size: 12px; }}
    QLabel#StatusWarning {{ color: {C['warning']}; font-weight: 600; font-size: 12px; }}
    QLabel#StatusError   {{ color: {C['error']};   font-weight: 600; font-size: 12px; }}
    QLabel#Hint {{
        color: {C['text_dim']};
        font-size: 11px;
        font-style: italic;
    }}
    QLabel#PageTitle {{
        font-size: 22px;
        font-weight: 700;
        color: {C['text']};
        background: transparent;
    }}
    QLabel#PageSubtitle {{
        font-size: 13px;
        color: {C['text_secondary']};
        background: transparent;
    }}

    /* ── scroll area ──────────────────────────────────────── */
    QScrollArea {{
        border: none;
        background: transparent;
    }}
    QScrollArea > QWidget > QWidget {{
        background: transparent;
    }}
    QScrollBar:vertical {{
        background: transparent;
        width: 8px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {C['bg_elevated']};
        border-radius: 4px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {C['accent']};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar:horizontal {{
        background: transparent;
        height: 8px;
    }}
    QScrollBar::handle:horizontal {{
        background: {C['bg_elevated']};
        border-radius: 4px;
        min-width: 30px;
    }}
    QScrollBar::handle:horizontal:hover {{ background: {C['accent']}; }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

    /* ── group box (advanced settings) ────────────────────── */
    QGroupBox {{
        font-size: 13px;
        font-weight: 600;
        color: {C['text']};
        background-color: {C['bg_card']};
        border: 1px solid {C['border']};
        border-radius: 10px;
        margin-top: 14px;
        padding: 24px 16px 16px 16px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 14px;
        padding: 2px 8px;
        color: {C['accent']};
    }}
    QGroupBox::indicator {{
        width: 16px; height: 16px;
        border-radius: 4px;
        border: 1px solid {C['border']};
        background-color: {C['bg_input']};
    }}
    QGroupBox::indicator:checked {{
        background-color: {C['accent']};
        border-color: {C['accent']};
    }}

    /* ── tooltips ─────────────────────────────────────────── */
    QToolTip {{
        background-color: {C['bg_elevated']};
        color: {C['text']};
        border: 1px solid {C['border']};
        border-radius: 6px;
        padding: 6px 10px;
        font-size: 12px;
    }}

    /* ── message box ──────────────────────────────────────── */
    QMessageBox {{
        background-color: {C['bg_card']};
        color: {C['text']};
    }}
    QMessageBox QPushButton {{
        min-width: 80px;
        padding: 8px 16px;
    }}

    /* ── generic buttons (fallback) ───────────────────────── */
    QPushButton {{
        background-color: {C['bg_hover']};
        color: {C['text']};
        border: 1px solid {C['border']};
        border-radius: 6px;
        padding: 6px 14px;
        font-size: 13px;
        font-weight: 500;
        min-height: 30px;
    }}
    QPushButton:hover {{
        background-color: {C['bg_elevated']};
        border-color: {C['accent']};
    }}
    QPushButton:pressed {{
        background-color: {C['bg_input']};
    }}
    QPushButton:disabled {{
        background-color: {C['bg_base']};
        color: {C['text_dim']};
        border-color: {C['border_subtle']};
    }}
    """
