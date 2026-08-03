"""云端地图列表面板"""

from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QTreeWidget, QTreeWidgetItem,
    QPushButton, QHBoxLayout, QMessageBox,
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont


class RemotePanel(QGroupBox):
    """云端地图列表（树形结构）"""

    download_requested = Signal(str, str)  # 信号: (dated_wld, original_name)
    refresh_requested = Signal()

    def __init__(self, parent=None):
        super().__init__("☁️ 云端地图（GitHub）", parent)
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["地图 / 版本", "时间", "操作"])
        self.tree.setColumnWidth(0, 240)
        self.tree.setColumnWidth(1, 100)
        self.tree.setColumnWidth(2, 120)
        self.tree.setAlternatingRowColors(True)
        self.tree.setRootIsDecorated(True)
        main_layout.addWidget(self.tree)

        # 按钮栏
        btn_layout = QHBoxLayout()

        self.download_btn = QPushButton("⬇ 下载选中版本")
        self.download_btn.clicked.connect(self._on_download)
        self.download_btn.setEnabled(False)
        btn_layout.addWidget(self.download_btn)

        self.refresh_btn = QPushButton("🔄 刷新")
        self.refresh_btn.clicked.connect(lambda: self.refresh_requested.emit())
        btn_layout.addWidget(self.refresh_btn)

        main_layout.addLayout(btn_layout)

    def refresh_list(self, remote_maps: dict[str, list[dict]]):
        """刷新云端地图列表

        remote_maps: {
            "我的世界": [{"date": "20260802", "wld": "...", "bak": "...", "bak2": "..."}, ...],
            ...
        }
        """
        self.tree.clear()

        if not remote_maps:
            root = QTreeWidgetItem(self.tree, ["（云端暂无地图）", "", ""])
            root.setFlags(root.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.download_btn.setEnabled(False)
            return

        bold_font = QFont()
        bold_font.setBold(True)

        for map_name, versions in remote_maps.items():
            # 一级节点：地图名
            map_item = QTreeWidgetItem(self.tree, [map_name, "", ""])
            map_item.setExpanded(True)

            for i, ver in enumerate(versions):
                # 去掉日期前缀取原名
                original_name = Path(ver["wld"]).name[len(ver["date"]):]
                # 格式化时间: 20260802173025 → 2026年08月02日 17:30:25
                d = ver["date"]
                if len(d) == 14:
                    date_display = f"{d[0:4]}年{d[4:6]}月{d[6:8]}日 {d[8:10]}:{d[10:12]}:{d[12:14]}"
                else:
                    date_display = d
                # 操作栏文字
                op_text = "⬇ 下载(最新)" if i == 0 else "⬇ 下载"

                ver_item = QTreeWidgetItem(map_item, [original_name, date_display, op_text])
                ver_item.setData(0, 1, ver["wld"])   # 存储完整文件名
                ver_item.setData(0, 2, original_name)  # 存储原名

                if i == 0:
                    ver_item.setFont(0, bold_font)
                    ver_item.setFont(1, bold_font)

        self.download_btn.setEnabled(True)

    def _on_download(self):
        """下载当前选中的版本"""
        current = self.tree.currentItem()
        if not current:
            QMessageBox.information(self, "提示", "请先选择一个地图版本")
            return

        # 检查选中的是否是二级节点（版本）
        dated_wld = current.data(0, 1)
        original_name = current.data(0, 2)

        if not dated_wld or not original_name:
            QMessageBox.information(self, "提示", "请选择具体的版本，而不是地图名")
            return

        reply = QMessageBox.question(
            self, "确认下载",
            f"确定要下载 \"{current.text(0)}\" 吗？\n\n"
            f"将覆盖本地地图: {original_name}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.download_requested.emit(dated_wld, original_name)
