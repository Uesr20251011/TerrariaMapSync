"""Shared visual language and optional Windows system backdrop."""

import ctypes
import sys


STYLE_SHEET = """
QWidget { color: #EAF5FA; font-family: "Microsoft YaHei UI", "Segoe UI"; font-size: 13px; }
QMainWindow, QDialog, QWizard { background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 rgba(13,31,50,238), stop:1 rgba(21,27,49,238)); }
QFrame#glassCard, QGroupBox { background-color: rgba(57,84,111,88); border: 1px solid rgba(180,225,245,48); border-radius: 18px; }
QGroupBox { margin-top: 16px; padding: 20px 10px 10px 10px; font-size: 15px; font-weight: 600; }
QGroupBox::title { subcontrol-origin: margin; left: 18px; padding: 0 8px; color: #ECF9FF; }
QWidget#accountBadge { background-color: rgba(126,195,219,28); border: 1px solid rgba(184,227,241,35); border-radius: 14px; }
QLabel#pageTitle { font-size: 27px; font-weight: 700; color: #FFFFFF; }
QLabel#brandTitle { font-size: 24px; font-weight: 700; color: #FFFFFF; }
QLabel#sectionHint, QLabel#mutedText { color: #A8C5D6; font-size: 11px; }
QLabel#accountName { font-weight: 600; font-size: 13px; }
QLabel#statusText { color: #BCD6E2; line-height: 1.5; }
QLineEdit, QPlainTextEdit, QListWidget, QTreeWidget { background-color: rgba(8,20,38,145); border: 1px solid rgba(156,212,238,52); border-radius: 10px; padding: 8px; selection-background-color: rgba(37,206,190,130); }
QLineEdit:focus, QListWidget:focus, QTreeWidget:focus { border: 1px solid #53DCCF; }
QListWidget::item, QTreeWidget::item { min-height: 30px; padding: 3px 7px; border-radius: 7px; }
QListWidget::item:selected, QTreeWidget::item:selected { background-color: #187F83; color: #FFFFFF; }
QHeaderView::section { background-color: rgba(17,38,58,205); color: #A9CDDB; border: none; padding: 9px; }
QPushButton { background-color: rgba(124,171,199,42); border: 1px solid rgba(157,215,238,60); border-radius: 10px; padding: 9px 16px; color: #E9F7FC; font-weight: 600; }
QPushButton:hover { background-color: rgba(121,195,215,80); border-color: rgba(163,233,235,150); }
QPushButton:pressed { background-color: rgba(77,156,172,115); }
QPushButton:disabled { color: #7892A2; background-color: rgba(85,110,130,25); border-color: rgba(140,180,200,28); }
QPushButton[variant="primary"] { background-color: #21B9AA; border-color: #43DACA; color: #061E29; }
QPushButton[variant="primary"]:hover { background-color: #5CE2D4; }
QPushButton[variant="primary"]:disabled { background-color: #3B666E; color: #9CB4BC; }
QStatusBar { background-color: rgba(8,24,40,130); color: #A8D4DD; border-top: 1px solid rgba(175,228,244,38); }
QSplitter::handle { background-color: rgba(147,206,221,26); width: 5px; }
QWizardPage { background: transparent; }
QDialogButtonBox QPushButton { min-width: 100px; }
QScrollBar:vertical { width: 8px; background: transparent; }
QScrollBar::handle:vertical { background: rgba(105,170,195,75); border-radius: 4px; min-height: 28px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
"""


def apply_glass_backdrop(window):
    """Request Windows 11 Acrylic; the translucent Qt cards remain the fallback."""
    if sys.platform != "win32":
        return
    try:
        handle = ctypes.c_void_p(int(window.winId()))
        dark = ctypes.c_int(1)
        acrylic = ctypes.c_int(3)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(handle, 20, ctypes.byref(dark), ctypes.sizeof(dark))
        ctypes.windll.dwmapi.DwmSetWindowAttribute(handle, 38, ctypes.byref(acrylic), ctypes.sizeof(acrylic))
    except (AttributeError, OSError, ValueError):
        pass
