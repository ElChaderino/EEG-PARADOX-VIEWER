import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QFileDialog, QPushButton, QVBoxLayout,
    QWidget, QSlider, QHBoxLayout, QCheckBox, QSpinBox, QMessageBox, QScrollArea,
    QDialog, QRadioButton, QComboBox, QListWidget, QDialogButtonBox, QColorDialog,
    QInputDialog, QListWidgetItem, QTextEdit, QGroupBox, QGridLayout, QLineEdit,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView, QSplitter, QFrame, QStatusBar
)
from PyQt5.QtGui import QPixmap, QImage, QKeySequence, QPainter, QPen, QColor, QFont, QBrush
from PyQt5.QtCore import Qt, QSettings, QTimer, QPoint, QRect, QDateTime
import fitz  # PyMuPDF
import cv2
import numpy as np
import os
import mss
import pygetwindow as gw
import json
from datetime import datetime
import math

# Try to import screen capture - use fallback if not available
try:
    from PIL import ImageGrab
    SCREEN_CAPTURE_AVAILABLE = True
    # Although mss is preferred, we keep track that PIL is an option
    SCREEN_CAPTURE_METHOD = "pil" 
except ImportError:
    SCREEN_CAPTURE_AVAILABLE = False
    SCREEN_CAPTURE_METHOD = "none"

# We will prioritize mss if available, as it's better for region capture
try:
    import mss
    SCREEN_CAPTURE_METHOD = "mss"
except ImportError:
    # If mss fails, we rely on the PIL check above
    if SCREEN_CAPTURE_METHOD == "pil":
        print("mss not found, falling back to PIL. For multi-monitor support, please install mss.")
    else:
        print("Screen capture not available. Please install 'mss' or 'Pillow'.")

def get_screen_refresh_rate():
    """Get the primary screen refresh rate in Hz."""
    # For packaging compatibility, we'll use a default value
    # Most modern monitors are 60Hz, which is a good default
    return 60

class CaptureSourceDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Capture Source")
        self.setMinimumWidth(350)
        layout = QVBoxLayout(self)

        # Full screen options
        self.screen_radio = QRadioButton("Capture Full Screen")
        self.screen_radio.setChecked(True)
        self.monitor_combo = QComboBox()
        try:
            with mss.mss() as sct:
                if len(sct.monitors) > 1:
                    for i, monitor in enumerate(sct.monitors[1:], 1):
                         self.monitor_combo.addItem(f"Screen {i}: {monitor['width']}x{monitor['height']}", i)
                else:
                    self.monitor_combo.addItem("Screen 1 (Primary)", 1) # Should not happen, but a fallback
        except Exception as e:
            print(f"Could not list monitors via mss: {e}")
            self.monitor_combo.addItem("Screen 1 (Default)", 1)
        layout.addWidget(self.screen_radio)
        layout.addWidget(self.monitor_combo)

        # Window options
        self.window_radio = QRadioButton("Capture Specific Window")
        self.window_list = QListWidget()
        self.populate_window_list()
        self.window_list.setEnabled(False) # Disabled by default
        layout.addWidget(self.window_radio)
        layout.addWidget(self.window_list)

        # Connect signals
        self.screen_radio.toggled.connect(self.toggle_source)
        self.window_radio.toggled.connect(self.toggle_source)

        # OK/Cancel buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def populate_window_list(self):
        self.window_list.clear()
        app_title = self.parent().windowTitle()
        try:
            for window in gw.getWindowsWithTitle(''):
                try:
                    if window.title and window.title != app_title:
                        # Check if window is visible without using isVisible
                        if hasattr(window, 'isVisible'):
                            if window.isVisible():
                                self.window_list.addItem(window.title)
                        else:
                            # If isVisible not available, just add the window
                            self.window_list.addItem(window.title)
                except Exception:
                    # Window might have been closed while iterating
                    continue
        except Exception as e:
            print(f"Could not get window list: {e}")
            self.window_list.addItem("Error: Could not list windows.")

    def toggle_source(self):
        is_screen = self.screen_radio.isChecked()
        self.monitor_combo.setEnabled(is_screen)
        self.window_list.setEnabled(not is_screen)

    def get_selection(self):
        if self.screen_radio.isChecked():
            return {"type": "screen", "monitor": self.monitor_combo.currentData()}
        else:
            selected_item = self.window_list.currentItem()
            if selected_item:
                return {"type": "window", "title": selected_item.text()}
        # Default fallback
        return {"type": "screen", "monitor": 1}

class AnnotationDialog(QDialog):
    def __init__(self, parent=None, annotation_type="", position=None):
        super().__init__(parent)
        self.setWindowTitle("EEG Annotation")
        self.setMinimumWidth(400)
        self.setMinimumHeight(300)
        
        layout = QVBoxLayout(self)
        
        # Annotation type and timestamp
        header_layout = QHBoxLayout()
        self.type_label = QLabel(f"Type: {annotation_type}")
        self.type_label.setStyleSheet("font-weight: bold; color: #2E86AB;")
        self.timestamp_label = QLabel(f"Time: {QDateTime.currentDateTime().toString('yyyy-MM-dd hh:mm:ss')}")
        header_layout.addWidget(self.type_label)
        header_layout.addStretch()
        header_layout.addWidget(self.timestamp_label)
        layout.addLayout(header_layout)
        
        # Position info
        if position:
            pos_layout = QHBoxLayout()
            pos_layout.addWidget(QLabel(f"Position: ({position.x()}, {position.y()})"))
            pos_layout.addStretch()
            layout.addLayout(pos_layout)
        
        # Description
        layout.addWidget(QLabel("Description:"))
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(80)
        layout.addWidget(self.description_edit)
        
        # Measurement fields (for measurements)
        if annotation_type in ["Amplitude", "Frequency", "Duration", "Latency"]:
            self.measurement_group = QGroupBox("Measurement Details")
            measurement_layout = QGridLayout(self.measurement_group)
            
            measurement_layout.addWidget(QLabel("Value:"), 0, 0)
            self.value_edit = QLineEdit()
            measurement_layout.addWidget(self.value_edit, 0, 1)
            
            measurement_layout.addWidget(QLabel("Unit:"), 0, 2)
            self.unit_combo = QComboBox()
            if annotation_type == "Amplitude":
                self.unit_combo.addItems(["μV", "mV", "V"])
            elif annotation_type == "Frequency":
                self.unit_combo.addItems(["Hz", "cycles/sec"])
            elif annotation_type == "Duration":
                self.unit_combo.addItems(["ms", "s", "min"])
            elif annotation_type == "Latency":
                self.unit_combo.addItems(["ms", "s"])
            measurement_layout.addWidget(self.unit_combo, 0, 3)
            
            measurement_layout.addWidget(QLabel("Channel:"), 1, 0)
            self.channel_edit = QLineEdit()
            measurement_layout.addWidget(self.channel_edit, 1, 1)
            
            measurement_layout.addWidget(QLabel("Notes:"), 1, 2)
            self.notes_edit = QLineEdit()
            measurement_layout.addWidget(self.notes_edit, 1, 3)
            
            layout.addWidget(self.measurement_group)
        
        # Event classification (for events)
        elif annotation_type in ["Seizure", "Artifact", "Normal", "Abnormal"]:
            self.event_group = QGroupBox("Event Classification")
            event_layout = QGridLayout(self.event_group)
            
            event_layout.addWidget(QLabel("Severity:"), 0, 0)
            self.severity_combo = QComboBox()
            self.severity_combo.addItems(["Mild", "Moderate", "Severe", "Critical"])
            event_layout.addWidget(self.severity_combo, 0, 1)
            
            event_layout.addWidget(QLabel("Confidence:"), 0, 2)
            self.confidence_combo = QComboBox()
            self.confidence_combo.addItems(["Low", "Medium", "High", "Certain"])
            event_layout.addWidget(self.confidence_combo, 0, 3)
            
            event_layout.addWidget(QLabel("Channels:"), 1, 0)
            self.channels_edit = QLineEdit()
            event_layout.addWidget(self.channels_edit, 1, 1, 1, 3)
            
            layout.addWidget(self.event_group)
        
        # Color selection
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("Color:"))
        self.color_button = QPushButton()
        self.color_button.setFixedSize(50, 25)
        self.set_annotation_color(QColor(255, 0, 0))  # Default red
        self.color_button.clicked.connect(self.choose_color)
        color_layout.addWidget(self.color_button)
        color_layout.addStretch()
        layout.addLayout(color_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Save Annotation")
        self.save_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
    
    def set_annotation_color(self, color):
        self.annotation_color = color
        self.color_button.setStyleSheet(f"background-color: {color.name()}; border: 1px solid black;")
    
    def choose_color(self):
        color = QColorDialog.getColor(self.annotation_color, self, "Choose Annotation Color")
        if color.isValid():
            self.set_annotation_color(color)
    
    def get_annotation_data(self):
        data = {
            "type": self.type_label.text().replace("Type: ", ""),
            "timestamp": self.timestamp_label.text().replace("Time: ", ""),
            "description": self.description_edit.toPlainText(),
            "color": self.annotation_color.name()
        }
        
        # Add measurement data if applicable
        if hasattr(self, 'measurement_group'):
            data.update({
                "value": self.value_edit.text(),
                "unit": self.unit_combo.currentText(),
                "channel": self.channel_edit.text(),
                "notes": self.notes_edit.text()
            })
        
        # Add event data if applicable
        if hasattr(self, 'event_group'):
            data.update({
                "severity": self.severity_combo.currentText(),
                "confidence": self.confidence_combo.currentText(),
                "channels": self.channels_edit.text()
            })
        
        return data

class AnnotationsPanelDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("EEG Annotations Manager")
        self.setMinimumSize(600, 400)
        
        layout = QVBoxLayout(self)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Annotations table tab
        self.create_annotations_tab()
        
        # Statistics tab
        self.create_statistics_tab()
        
        layout.addWidget(self.tab_widget)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.export_button = QPushButton("Export Annotations")
        self.export_button.clicked.connect(self.export_annotations)
        self.clear_button = QPushButton("Clear All")
        self.clear_button.clicked.connect(self.clear_annotations)
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.accept)
        
        button_layout.addWidget(self.export_button)
        button_layout.addWidget(self.clear_button)
        button_layout.addStretch()
        button_layout.addWidget(self.close_button)
        layout.addLayout(button_layout)
        
        self.refresh_data()
    
    def create_annotations_tab(self):
        """Create the annotations table tab."""
        self.annotations_table = QTableWidget()
        self.annotations_table.setColumnCount(7)
        self.annotations_table.setHorizontalHeaderLabels([
            "Type", "Time", "Position", "Value", "Description", "Channel", "Actions"
        ])
        
        # Set column widths
        header = self.annotations_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        
        self.tab_widget.addTab(self.annotations_table, "Annotations")
    
    def create_statistics_tab(self):
        """Create the statistics tab."""
        self.stats_widget = QWidget()
        stats_layout = QVBoxLayout(self.stats_widget)
        
        # Statistics text
        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        stats_layout.addWidget(self.stats_text)
        
        self.tab_widget.addTab(self.stats_widget, "Statistics")
    
    def refresh_data(self):
        """Refresh the annotations data."""
        if not hasattr(self.parent, 'professional_annotations'):
            return
        
        # Clear table
        self.annotations_table.setRowCount(0)
        
        # Populate table
        for i, annotation in enumerate(self.parent.professional_annotations):
            self.annotations_table.insertRow(i)
            
            # Type
            self.annotations_table.setItem(i, 0, QTableWidgetItem(annotation.type))
            
            # Time
            time_str = annotation.data.get("timestamp", "Unknown")
            self.annotations_table.setItem(i, 1, QTableWidgetItem(time_str))
            
            # Position
            if annotation.position:
                pos_str = f"({annotation.position.x()}, {annotation.position.y()})"
            else:
                pos_str = "N/A"
            self.annotations_table.setItem(i, 2, QTableWidgetItem(pos_str))
            
            # Value
            value = annotation.data.get("value", "")
            unit = annotation.data.get("unit", "")
            value_str = f"{value} {unit}" if value else ""
            self.annotations_table.setItem(i, 3, QTableWidgetItem(value_str))
            
            # Description
            desc = annotation.data.get("description", "")
            self.annotations_table.setItem(i, 4, QTableWidgetItem(desc))
            
            # Channel
            channel = annotation.data.get("channel", "")
            self.annotations_table.setItem(i, 5, QTableWidgetItem(channel))
            
            # Actions
            delete_button = QPushButton("Delete")
            delete_button.clicked.connect(lambda checked, row=i: self.delete_annotation(row))
            self.annotations_table.setCellWidget(i, 6, delete_button)
        
        # Update statistics
        self.update_statistics()
    
    def delete_annotation(self, row):
        """Delete an annotation."""
        if row < len(self.parent.professional_annotations):
            del self.parent.professional_annotations[row]
            self.refresh_data()
            self.parent.update_zoom()
    
    def update_statistics(self):
        """Update the statistics display."""
        if not hasattr(self.parent, 'professional_annotations'):
            return
        
        annotations = self.parent.professional_annotations
        
        # Count by type
        type_counts = {}
        measurement_values = []
        
        for annotation in annotations:
            annotation_type = annotation.type
            type_counts[annotation_type] = type_counts.get(annotation_type, 0) + 1
            
            # Collect measurement values
            if annotation_type in ["Amplitude", "Frequency", "Duration", "Latency"]:
                try:
                    value = float(annotation.data.get("value", 0))
                    measurement_values.append(value)
                except ValueError:
                    pass
        
        # Generate statistics text
        stats_text = f"Total Annotations: {len(annotations)}\n\n"
        stats_text += "By Type:\n"
        for annotation_type, count in type_counts.items():
            stats_text += f"  {annotation_type}: {count}\n"
        
        if measurement_values:
            stats_text += f"\nMeasurement Statistics:\n"
            stats_text += f"  Count: {len(measurement_values)}\n"
            stats_text += f"  Average: {sum(measurement_values)/len(measurement_values):.2f}\n"
            stats_text += f"  Min: {min(measurement_values):.2f}\n"
            stats_text += f"  Max: {max(measurement_values):.2f}\n"
        
        self.stats_text.setPlainText(stats_text)
    
    def export_annotations(self):
        """Export annotations to JSON file."""
        if not hasattr(self.parent, 'professional_annotations'):
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Annotations", "eeg_annotations.json", "JSON Files (*.json)"
        )
        if file_path:
            # Convert annotations to serializable format
            export_data = []
            for annotation in self.parent.professional_annotations:
                annotation_data = {
                    "type": annotation.type,
                    "id": annotation.id,
                    "data": annotation.data
                }
                if annotation.position:
                    annotation_data["position"] = {
                        "x": annotation.position.x(),
                        "y": annotation.position.y()
                    }
                export_data.append(annotation_data)
            
            with open(file_path, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            QMessageBox.information(self, "Export", f"Annotations exported to {file_path}")
    
    def clear_annotations(self):
        """Clear all annotations."""
        reply = QMessageBox.question(
            self, "Clear Annotations", 
            "Are you sure you want to clear all annotations?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.parent.professional_annotations.clear()
            self.refresh_data()
            self.parent.update_zoom()

class MeasurementTool:
    def __init__(self):
        self.start_point = None
        self.end_point = None
        self.measurement_type = "Distance"  # Distance, Amplitude, Frequency, Duration
        self.calibration_factor = 1.0  # pixels per unit
        self.calibration_unit = "μV"
    
    def set_points(self, start, end):
        self.start_point = start
        self.end_point = end
    
    def get_distance(self):
        if self.start_point and self.end_point:
            return ((self.end_point.x() - self.start_point.x())**2 + 
                   (self.end_point.y() - self.start_point.y())**2)**0.5
        return 0
    
    def get_calibrated_value(self):
        distance = self.get_distance()
        return distance * self.calibration_factor
    
    def get_measurement_text(self):
        if self.measurement_type == "Distance":
            return f"{self.get_distance():.1f} px"
        else:
            return f"{self.get_calibrated_value():.2f} {self.calibration_unit}"

class AnalysisOverlay:
    """Base class for all analysis overlays."""
    def __init__(self, overlay_type, data=None):
        self.id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        self.type = overlay_type
        self.data = data if data is not None else {}

    def draw(self, painter, zoom_factor):
        raise NotImplementedError

    def to_dict(self):
        return {
            "id": self.id,
            "type": self.type,
            "data": self.data
        }

    @staticmethod
    def from_dict(d):
        overlay_type = d.get("type")
        if overlay_type == "Note":
            return NoteOverlay.from_dict(d)
        if overlay_type == "Ruler":
            return RulerOverlay.from_dict(d)
        if overlay_type == "ROI":
            return RegionOfInterestOverlay.from_dict(d)
        return None


class NoteOverlay(AnalysisOverlay):
    """An overlay for placing text notes."""
    def __init__(self, position, text, color, data=None):
        super().__init__("Note", data)
        self.position = position
        self.text = text
        self.color = color

    def draw(self, painter, zoom_factor):
        # Scale coordinates from original image space to display space
        scaled_pos = QPoint(int(self.position.x() * zoom_factor), int(self.position.y() * zoom_factor))
        
        painter.setPen(QPen(QColor(self.color), 2))
        painter.setBrush(QColor(self.color))
        painter.drawEllipse(scaled_pos, 4, 4)
        
        font = QFont("Arial", int(10 / zoom_factor))
        painter.setFont(font)
        painter.drawText(scaled_pos + QPoint(8, 8), self.text)

    def to_dict(self):
        d = super().to_dict()
        d['data'].update({
            "position": (self.position.x(), self.position.y()),
            "text": self.text,
            "color": self.color,
        })
        return d

    @staticmethod
    def from_dict(d):
        data = d.get("data", {})
        pos_tuple = data.get("position")
        position = QPoint(pos_tuple[0], pos_tuple[1])
        return NoteOverlay(position, data.get("text"), data.get("color"), data)


class RulerOverlay(AnalysisOverlay):
    """An overlay for measurements."""
    def __init__(self, start_point, end_point, color, data=None):
        super().__init__("Ruler", data)
        self.start_point = start_point
        self.end_point = end_point
        self.color = color

    def draw(self, painter, zoom_factor):
        # Scale coordinates from original image space to display space
        scaled_start = QPoint(int(self.start_point.x() * zoom_factor), int(self.start_point.y() * zoom_factor))
        scaled_end = QPoint(int(self.end_point.x() * zoom_factor), int(self.end_point.y() * zoom_factor))
        
        pen = QPen(QColor(self.color), 2, Qt.DashLine)
        painter.setPen(pen)
        painter.drawLine(scaled_start, scaled_end)

        # Draw endpoints
        painter.setBrush(QColor(self.color))
        painter.drawEllipse(scaled_start, 4, 4)
        painter.drawEllipse(scaled_end, 4, 4)

        # Draw measurement text and note
        distance = math.sqrt((self.end_point.x() - self.start_point.x())**2 + (self.end_point.y() - self.start_point.y())**2)
        mid_point = (scaled_start + scaled_end) / 2
        
        font = QFont("Arial", int(10 / zoom_factor))
        painter.setFont(font)
        
        text = f"{distance:.1f}px"
        if 'calibrated_value' in self.data and 'unit' in self.data:
            text += f" / {self.data['calibrated_value']:.2f} {self.data['unit']}"
            
        # Add note if it exists
        if 'note' in self.data:
            text += f" ({self.data['note']})"
            
        painter.drawText(mid_point, text)

    def to_dict(self):
        d = super().to_dict()
        d['data'].update({
            "start_point": (self.start_point.x(), self.start_point.y()),
            "end_point": (self.end_point.x(), self.end_point.y()),
            "color": self.color,
            "note": self.data.get('note') # Ensure note is saved
        })
        return d

    @staticmethod
    def from_dict(d):
        data = d.get("data", {})
        start_tuple = data.get("start_point")
        end_tuple = data.get("end_point")
        start_point = QPoint(start_tuple[0], start_tuple[1])
        end_point = QPoint(end_tuple[0], end_tuple[1])
        return RulerOverlay(start_point, end_point, data.get("color"), data)

class RegionOfInterestOverlay(AnalysisOverlay):
    """An overlay for highlighting regions of interest."""
    def __init__(self, top_left, bottom_right, color, data=None):
        super().__init__("ROI", data)
        self.top_left = top_left
        self.bottom_right = bottom_right
        self.color = color

    def draw(self, painter, zoom_factor):
        # Scale coordinates from original image space to display space
        scaled_tl = QPoint(int(self.top_left.x() * zoom_factor), int(self.top_left.y() * zoom_factor))
        scaled_br = QPoint(int(self.bottom_right.x() * zoom_factor), int(self.bottom_right.y() * zoom_factor))
        
        # Draw rectangle
        rect = QRect(scaled_tl, scaled_br)
        painter.setPen(QPen(QColor(self.color), 2, Qt.SolidLine))
        painter.setBrush(QColor(self.color + "20"))  # Semi-transparent fill
        painter.drawRect(rect)
        
        # Draw corner markers
        painter.setBrush(QColor(self.color))
        painter.drawEllipse(scaled_tl, 4, 4)
        painter.drawEllipse(scaled_br, 4, 4)
        painter.drawEllipse(QPoint(scaled_br.x(), scaled_tl.y()), 4, 4)
        painter.drawEllipse(QPoint(scaled_tl.x(), scaled_br.y()), 4, 4)
        
        # Draw dimensions
        width = abs(self.bottom_right.x() - self.top_left.x())
        height = abs(self.bottom_right.y() - self.top_left.y())
        mid_point = (scaled_tl + scaled_br) / 2
        
        font = QFont("Arial", int(10 / zoom_factor))
        painter.setFont(font)
        painter.setPen(QPen(QColor(self.color), 1))
        
        text = f"{width:.0f} × {height:.0f}px"
        if 'note' in self.data:
            text += f" - {self.data['note']}"
            
        painter.drawText(mid_point, text)

    def to_dict(self):
        d = super().to_dict()
        d['data'].update({
            "top_left": (self.top_left.x(), self.top_left.y()),
            "bottom_right": (self.bottom_right.x(), self.bottom_right.y()),
            "color": self.color,
        })
        return d

    @staticmethod
    def from_dict(d):
        data = d.get("data", {})
        tl_tuple = data.get("top_left")
        br_tuple = data.get("bottom_right")
        top_left = QPoint(tl_tuple[0], tl_tuple[1])
        bottom_right = QPoint(br_tuple[0], br_tuple[1])
        return RegionOfInterestOverlay(top_left, bottom_right, data.get("color"), data)

class Annotation:
    def __init__(self, annotation_type, position, data=None):
        self.type = annotation_type
        self.position = position
        self.data = data or {}
        self.id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    
    def draw(self, painter, zoom_factor=1.0):
        if not self.position:
            return
        
        # Set color
        color = QColor(self.data.get("color", "#FF0000"))
        painter.setPen(QPen(color, 2))
        
        # Draw based on annotation type
        if self.type in ["Seizure", "Artifact", "Normal", "Abnormal"]:
            # Draw event marker
            x, y = self.position.x(), self.position.y()
            painter.drawEllipse(QPoint(x, y), 8, 8)
            painter.drawText(x + 12, y + 4, self.type[:3])
        
        elif self.type in ["Amplitude", "Frequency", "Duration", "Latency"]:
            # Draw measurement marker
            x, y = self.position.x(), self.position.y()
            painter.drawRect(x - 5, y - 5, 10, 10)
            value = self.data.get("value", "")
            unit = self.data.get("unit", "")
            painter.drawText(x + 12, y + 4, f"{value}{unit}")
        
        else:
            # Draw generic marker
            x, y = self.position.x(), self.position.y()
            painter.drawEllipse(QPoint(x, y), 6, 6)

class MeasurementGridWidget(QWidget):
    """A draggable and resizable grid widget for EEG measurement."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setGeometry(150, 150, 300, 200)
        
        self.drag_position = None
        self.resizing = False
        self.resize_margin = 10

        self.setMouseTracking(True) # Needed for cursor changes

        # Calibration (pixels per unit) - will be configurable later
        self.x_pixels_per_unit = 50  # e.g., 50px = 100ms
        self.y_pixels_per_unit = 50  # e.g., 50px = 50µV
        self.x_unit_name = "ms"
        self.y_unit_name = "µV"
        self.x_val_per_tick = 100
        self.y_val_per_tick = 50

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.resizing = self.is_on_edge(event.pos())
            if self.resizing:
                self.drag_position = event.globalPos()
            else:
                self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.drag_position:
            if self.resizing:
                self.handle_resize(event)
            else:
                self.move(event.globalPos() - self.drag_position)
            event.accept()
        else:
            self.update_cursor(event.pos())

    def mouseReleaseEvent(self, event):
        self.drag_position = None
        self.resizing = False
        event.accept()

    def is_on_edge(self, pos):
        return pos.x() > self.width() - self.resize_margin or \
               pos.y() > self.height() - self.resize_margin

    def update_cursor(self, pos):
        if self.is_on_edge(pos):
            self.setCursor(Qt.SizeFDiagCursor)
        else:
            self.setCursor(Qt.SizeAllCursor)
            
    def handle_resize(self, event):
        delta = event.globalPos() - self.drag_position
        new_width = self.width() + delta.x()
        new_height = self.height() + delta.y()
        
        # Enforce minimum size
        min_width = self.x_pixels_per_unit * 2
        min_height = self.y_pixels_per_unit * 2
        
        self.resize(max(min_width, new_width), max(min_height, new_height))
        self.drag_position = event.globalPos()
        self.update() # Repaint on resize

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Background
        bg_color = QColor(20, 20, 40, 180) # Dark blue, semi-transparent
        painter.setBrush(bg_color)
        painter.setPen(QPen(QColor(150, 150, 255), 1, Qt.DashLine))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))

        # Grid lines
        pen = QPen(QColor(100, 100, 150, 150), 1, Qt.DotLine)
        painter.setPen(pen)
        
        # Horizontal lines
        for i in range(1, self.height() // self.y_pixels_per_unit):
            y = i * self.y_pixels_per_unit
            painter.drawLine(0, y, self.width(), y)
            
        # Vertical lines
        for i in range(1, self.width() // self.x_pixels_per_unit):
            x = i * self.x_pixels_per_unit
            painter.drawLine(x, 0, x, self.height())

        # Measurement Text
        font = QFont("Arial", 10)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(Qt.white)

        # TODO: Update with real calibration values
        width_val = (self.width() / self.x_pixels_per_unit) * self.x_val_per_tick 
        height_val = (self.height() / self.y_pixels_per_unit) * self.y_val_per_tick

        width_text = f"W: {width_val:.1f} {self.x_unit_name}"
        height_text = f"H: {height_val:.1f} {self.y_unit_name}"

        painter.drawText(5, 15, width_text)
        painter.drawText(5, 35, height_text)

class CalibrationDialog(QDialog):
    """Dialog for setting grid calibration."""
    def __init__(self, parent=None, x_px=50, x_val=100, x_unit="ms", y_px=50, y_val=50, y_unit="µV"):
        super().__init__(parent)
        self.setWindowTitle("Grid Calibration")
        layout = QGridLayout(self)
        
        # Horizontal (Time)
        layout.addWidget(QLabel("<b>Horizontal (Time)</b>"), 0, 0, 1, 4)
        self.x_pixels_edit = QLineEdit(str(x_px))
        layout.addWidget(QLabel("pixels ="), 1, 1)
        layout.addWidget(self.x_pixels_edit, 1, 0)
        self.x_value_edit = QLineEdit(str(x_val))
        layout.addWidget(self.x_value_edit, 1, 2)
        self.x_unit_edit = QLineEdit(x_unit)
        layout.addWidget(self.x_unit_edit, 1, 3)
        
        # Vertical (Amplitude)
        layout.addWidget(QLabel("<b>Vertical (Amplitude)</b>"), 2, 0, 1, 4)
        self.y_pixels_edit = QLineEdit(str(y_px))
        layout.addWidget(QLabel("pixels ="), 3, 1)
        layout.addWidget(self.y_pixels_edit, 3, 0)
        self.y_value_edit = QLineEdit(str(y_val))
        layout.addWidget(self.y_value_edit, 3, 2)
        self.y_unit_edit = QLineEdit(y_unit)
        layout.addWidget(self.y_unit_edit, 3, 3)

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box, 4, 0, 1, 4)

    def get_values(self):
        return {
            "x_px": int(self.x_pixels_edit.text()), "x_val": float(self.x_value_edit.text()), "x_unit": self.x_unit_edit.text(),
            "y_px": int(self.y_pixels_edit.text()), "y_val": float(self.y_value_edit.text()), "y_unit": self.y_unit_edit.text()
        }

class ImageZoomViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EEG Paradox Viewer v2.0")
        self.setGeometry(100, 100, 1200, 800)

        # Use QScrollArea for panning
        self.scroll_area = QScrollArea()
        self.scroll_area.setAlignment(Qt.AlignCenter)

        self.image_label = QLabel()
        self.scroll_area.setWidget(self.image_label)

        # Widgets - Restore original zoom slider
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setMinimum(10)
        self.zoom_slider.setMaximum(400)
        self.zoom_slider.setTickPosition(QSlider.TicksBelow)
        self.zoom_slider.setTickInterval(10)
        self.zoom_slider.valueChanged.connect(self.update_zoom)

        self.enhanced_mode_checkbox = QCheckBox("Enable Enhanced Mode")
        self.enhanced_mode_checkbox.stateChanged.connect(self.apply_enhanced_mode)

        open_button = QPushButton("Open File")
        open_button.clicked.connect(self.open_file)

        # Screen capture buttons
        self.select_source_button = QPushButton("Select Source")
        self.select_source_button.clicked.connect(self.select_capture_source)
        self.capture_button = QPushButton("Capture")
        self.capture_button.clicked.connect(self.capture_screen)
        
        self.live_capture_checkbox = QCheckBox("Live Capture")
        self.live_capture_checkbox.stateChanged.connect(self.toggle_live_capture)

        # FPS selection combo box
        self.fps_combo = QComboBox()
        screen_refresh = get_screen_refresh_rate()
        self.fps_combo.addItem(f"Screen Rate ({screen_refresh} Hz)", screen_refresh)
        self.fps_combo.addItem("30 FPS", 30)
        self.fps_combo.addItem("60 FPS", 60)
        self.fps_combo.addItem("120 FPS", 120)
        self.fps_combo.addItem("15 FPS", 15)
        self.fps_combo.addItem("10 FPS", 10)
        self.fps_combo.setCurrentText(f"Screen Rate ({screen_refresh} Hz)")
        self.fps_combo.setToolTip("Select the frame rate for live capture")
        self.fps_combo.currentIndexChanged.connect(self.update_fps)

        self.next_page_button = QPushButton("Next Page")
        self.next_page_button.clicked.connect(self.next_page)
        self.prev_page_button = QPushButton("Previous Page")
        self.prev_page_button.clicked.connect(self.prev_page)

        self.export_button = QPushButton("Export View")
        self.export_button.clicked.connect(self.export_current_view)

        self.page_selector = QSpinBox()
        self.page_selector.setMinimum(1)
        self.page_selector.valueChanged.connect(self.goto_page)

        # Contrast mode label
        self.contrast_label = QLabel("Contrast: Normal")
        self.contrast_label.setStyleSheet("QLabel { background-color: #f0f0f0; padding: 5px; border: 1px solid #ccc; }")

        # EEG Viewing Aid Features
        self.trace_enhance_button = QPushButton("Trace Mode")
        self.trace_enhance_button.setCheckable(True)
        self.trace_enhance_button.setToolTip("Enhance EEG traces for better visibility")
        self.trace_enhance_button.clicked.connect(self.toggle_trace_enhancement)

        # Analysis Tools
        self.analysis_mode_button = QPushButton("Analysis Mode")
        self.analysis_mode_button.setCheckable(True)
        self.analysis_mode_button.setToolTip("Enable/Disable Analysis Overlays (A key)")
        self.analysis_mode_button.clicked.connect(self.toggle_analysis_mode)

        self.analysis_tool_combo = QComboBox()
        self.analysis_tool_combo.addItems(["Note", "Ruler", "ROI"])
        self.analysis_tool_combo.setToolTip("Select Analysis Tool")
        self.analysis_tool_combo.setEnabled(False) # Disabled until analysis mode is on

        # Annotation management
        self.annotations_button = QPushButton("Manage Overlays")
        self.annotations_button.setToolTip("View and manage analysis overlays")
        self.annotations_button.clicked.connect(self.show_annotations_panel)

        self.save_position_button = QPushButton("Save Pos")
        self.save_position_button.setToolTip("Save current zoom/position (P key)")
        self.save_position_button.clicked.connect(self.save_position)

        self.positions_list = QComboBox()
        self.positions_list.setToolTip("Saved positions")
        self.positions_list.currentTextChanged.connect(self.load_position)

        self.measurement_grid_button = QPushButton("Toggle Grid")
        self.measurement_grid_button.setToolTip("Show/Hide the draggable measurement grid")
        self.measurement_grid_button.setCheckable(True)
        self.measurement_grid_button.clicked.connect(self.toggle_measurement_grid)

        self.calibrate_button = QPushButton("Calibrate")
        self.calibrate_button.setToolTip("Calibrate the measurement grid")
        self.calibrate_button.clicked.connect(self.calibrate_grid)

        # Layouts
        top_layout = QHBoxLayout()
        top_layout.addWidget(open_button)
        top_layout.addWidget(self.select_source_button)
        top_layout.addWidget(self.capture_button)
        top_layout.addWidget(self.live_capture_checkbox)
        top_layout.addWidget(self.fps_combo)
        top_layout.addWidget(self.zoom_slider)
        top_layout.addWidget(self.enhanced_mode_checkbox)
        top_layout.addWidget(self.prev_page_button)
        top_layout.addWidget(self.next_page_button)
        top_layout.addWidget(self.page_selector)
        top_layout.addWidget(self.export_button)
        top_layout.addWidget(self.contrast_label)
        top_layout.addWidget(self.trace_enhance_button)
        top_layout.addWidget(self.analysis_mode_button)
        top_layout.addWidget(self.analysis_tool_combo)
        top_layout.addWidget(self.annotations_button)
        top_layout.addWidget(self.save_position_button)
        top_layout.addWidget(self.positions_list)
        top_layout.addWidget(self.measurement_grid_button)
        top_layout.addWidget(self.calibrate_button)

        layout = QVBoxLayout()
        layout.addLayout(top_layout)
        layout.addWidget(self.scroll_area)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # State
        self.current_image = None
        self.original_image = None
        self.center_image_focus = True
        self.default_zoom_enhanced_mode = 250
        self.doc = None
        self.current_page_index = 0
        self.current_file_path = None
        self.contrast_mode = 0  # 0=normal, 1=Enh-Color, 2=Hi-Con-Color, 3=Smart Invert, 4=Inv-Gray
        self.settings = QSettings("EEGParadoxViewer", "ParadoxViewer")
        
        # Default capture source: primary monitor
        self.capture_source = {"type": "screen", "monitor": 1}

        # Screen capture state
        self.live_capture_active = False
        self.capture_timer = None

        # Panning state
        self.panning = False
        self.pan_start_pos = None

        # EEG Viewing Aid state
        self.trace_enhancement_active = False
        self.measurement_active = False
        self.annotation_active = False
        self.measurement_tool = MeasurementTool()
        self.professional_annotations = []  # List of Annotation objects
        self.saved_positions = {}
        self.drawing = False
        self.last_draw_point = None
        self.current_measurement_start = None
        self.current_annotation_type = "Seizure" # Default value
        self.preview_position = None

        # Analysis state
        self.analysis_mode_active = False
        self.current_analysis_tool = "Note"
        self.analysis_overlays = []  # Store all overlay objects
        self.drawing_overlay = None  # Currently being drawn
        self.drawing_start_point = None

        # Mouse tracking for overlays
        self.mouse_tracking_active = False
        self.last_mouse_pos = None

        self.last_mouse_pos = None

        self.static_ruler = None

        # Add a status bar for user feedback
        self.setStatusBar(QStatusBar(self))

        # Restore settings
        self.restore_session()

        self.measurement_grid = None

    def select_capture_source(self):
        if SCREEN_CAPTURE_METHOD != "mss":
            QMessageBox.warning(self, "Feature Unavailable", "Window and multi-monitor selection requires the 'mss' library.")
            return
        dialog = CaptureSourceDialog(self)
        if dialog.exec_():
            selection = dialog.get_selection()
            if selection:
                self.capture_source = selection

    def _get_capture_area(self):
        """Get the capture area for screen capture."""
        try:
            with mss.mss() as sct:
                # Always capture the primary monitor for now
                return sct.monitors[1]  # Primary monitor
        except Exception as e:
            print(f"Error getting capture area: {e}")
            # Fallback to a default area
            return {"left": 0, "top": 0, "width": 1920, "height": 1080}

    def _grab_and_load(self, capture_area):
        """Grabs the image and loads it as BGR."""
        try:
            if SCREEN_CAPTURE_METHOD == "mss":
                with mss.mss() as sct:
                    sct_img = sct.grab(capture_area)
                    # Convert BGRA from MSS to BGR
                    img = cv2.cvtColor(np.array(sct_img), cv2.COLOR_BGRA2BGR)
            elif SCREEN_CAPTURE_METHOD == "pil":
                pil_img = ImageGrab.grab()
                # Convert PIL's RGB to BGR
                img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            else:
                print("No screen capture method available")
                return

            if not self.live_capture_active:
                self.showNormal()
                self.raise_()
                self.activateWindow()

            self.original_image = img
            self.current_image = img.copy()
            self.doc = None
            self.page_selector.setMaximum(1)
            self.update_zoom()
        
        except Exception as e:
            print(f"Capture error: {e}")
            if not self.live_capture_active: 
                self.showNormal()

    def _do_capture(self, live=False):
        """High-level capture command."""
        capture_area = self._get_capture_area()
        if not capture_area:
            print("No capture area available")
            return

        if not live:
            self.showMinimized()
            QApplication.processEvents()
            # Give window time to minimize before capture
            QTimer.singleShot(300, lambda: self._grab_and_load(capture_area))
        else:
            self._grab_and_load(capture_area)

    def capture_screen(self):
        """Button action for single capture."""
        self._do_capture(live=False)

    def test_capture(self):
        """Test capture without minimizing window."""
        print("Testing capture...")
        capture_area = self._get_capture_area()
        if capture_area:
            print(f"Capture area: {capture_area}")
            self._grab_and_load(capture_area)
        else:
            print("No capture area available")

    def toggle_live_capture(self):
        if self.live_capture_checkbox.isChecked():
            self.start_live_capture()
        else:
            self.stop_live_capture()

    def start_live_capture(self):
        """Start live capture mode."""
        print("Starting live capture...")
        self.live_capture_active = True
        self.live_capture_checkbox.setChecked(True)
        self.capture_button.setText("Stop Live")
        
        # Disconnect old signal and connect new one
        try: 
            self.capture_button.clicked.disconnect() 
        except TypeError: 
            pass
        self.capture_button.clicked.connect(self.stop_live_capture)
        
        # Reset to default contrast when starting live view
        self.contrast_mode = 0
        self.contrast_label.setText("Contrast: Normal")
        
        # Show status
        self.statusBar().showMessage("Live capture started")

        # Create and start timer
        self.capture_timer = QTimer()
        self.capture_timer.timeout.connect(self.live_capture_update)
        
        # Get selected FPS and convert to milliseconds
        selected_fps = self.fps_combo.currentData()
        interval_ms = int(1000 / selected_fps)  # Convert FPS to milliseconds
        print(f"Starting timer with {selected_fps} FPS ({interval_ms}ms interval)")
        self.capture_timer.start(interval_ms)

    def stop_live_capture(self):
        """Stop live capture mode."""
        print("Stopping live capture...")
        self.live_capture_active = False
        self.live_capture_checkbox.setChecked(False)
        self.capture_button.setText("Capture")
        
        # Stop timer
        if self.capture_timer:
            self.capture_timer.stop()
            self.capture_timer = None
        
        # Reconnect original signal
        try: 
            self.capture_button.clicked.disconnect()
        except TypeError: 
            pass
        self.capture_button.clicked.connect(self.capture_screen)
        
        # Show status
        self.statusBar().showMessage("Live capture stopped")

    def live_capture_update(self):
        """Update function called by the timer for live capture."""
        if not self.live_capture_active:
            return
        print("Live capture update...")
        self._do_capture(live=True)

    def update_fps(self):
        """Update the FPS if live capture is active."""
        if self.live_capture_active and self.capture_timer:
            selected_fps = self.fps_combo.currentData()
            interval_ms = int(1000 / selected_fps)
            self.capture_timer.setInterval(interval_ms)

    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Image or PDF", "", "Images (*.png *.jpg *.bmp *.tif);;PDF Files (*.pdf)")
        if not file_path:
            return
        self.current_file_path = file_path
        self.settings.setValue("last_file", file_path)

        if file_path.lower().endswith('.pdf'):
            self.doc = fitz.open(file_path)
            self.page_selector.setMaximum(len(self.doc))
            self.current_page_index = 0
            self.load_pdf_page(self.current_page_index)
        else:
            self.doc = None
            # imread already provides BGR, which is our new standard.
            self.original_image = cv2.imread(file_path)
            self.current_image = self.original_image.copy()
            self.page_selector.setMaximum(1)
            self.update_zoom()

    def load_pdf_page(self, page_number):
        if self.doc is None:
            return
        page = self.doc.load_page(page_number)
        pix = page.get_pixmap(dpi=300)
        image = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        
        # PyMuPDF gives BGRA or BGR. Ensure it is BGR.
        if pix.n == 4:
            image = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)

        self.original_image = image
        self.current_image = image.copy()
        self.update_zoom()

    def next_page(self):
        if self.doc and self.current_page_index < len(self.doc) - 1:
            self.current_page_index += 1
            self.page_selector.setValue(self.current_page_index + 1)
            self.load_pdf_page(self.current_page_index)

    def prev_page(self):
        if self.doc and self.current_page_index > 0:
            self.current_page_index -= 1
            self.page_selector.setValue(self.current_page_index + 1)
            self.load_pdf_page(self.current_page_index)

    def goto_page(self):
        index = self.page_selector.value() - 1
        if self.doc and 0 <= index < len(self.doc):
            self.current_page_index = index
            self.load_pdf_page(self.current_page_index)

    def update_zoom(self):
        if self.original_image is None:
            return
        scale_percent = self.zoom_slider.value()
        self.settings.setValue("last_zoom", scale_percent)

        # working_image is now always BGR.
        working_image = self.original_image.copy()

        # All filter logic operates directly on the BGR image.
        if self.enhanced_mode_checkbox.isChecked() and self.contrast_mode != 0:
            mode = self.contrast_mode
            if mode == 1:
                lab = cv2.cvtColor(working_image, cv2.COLOR_BGR2LAB)
                l, a, b = cv2.split(lab)
                clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
                l = clahe.apply(l)
                lab = cv2.merge([l, a, b])
                working_image = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
                hsv = cv2.cvtColor(working_image, cv2.COLOR_BGR2HSV)
                hsv[:, :, 1] = cv2.multiply(hsv[:, :, 1], 1.3)
                hsv[:, :, 1] = np.clip(hsv[:, :, 1], 0, 255)
                working_image = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
            elif mode == 2:
                lab = cv2.cvtColor(working_image, cv2.COLOR_BGR2LAB)
                l, a, b = cv2.split(lab)
                clahe = cv2.createCLAHE(clipLimit=5.0, tileGridSize=(8,8))
                l = clahe.apply(l)
                a = cv2.multiply(a, 1.2)
                b = cv2.multiply(b, 1.2)
                a = np.clip(a, 0, 255)
                b = np.clip(b, 0, 255)
                lab = cv2.merge([l, a, b])
                working_image = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
            elif mode == 3:
                hsv = cv2.cvtColor(working_image, cv2.COLOR_BGR2HSV)
                hsv[:, :, 2] = 255 - hsv[:, :, 2]
                working_image = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
            elif mode == 4:
                gray = cv2.cvtColor(working_image, cv2.COLOR_BGR2GRAY)
                inverted = cv2.bitwise_not(gray)
                working_image = cv2.cvtColor(inverted, cv2.COLOR_GRAY2BGR)
            elif mode == 5:
                gray = cv2.cvtColor(working_image, cv2.COLOR_BGR2GRAY)
                clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8,8))
                enhanced_gray = clahe.apply(gray)
                working_image = cv2.cvtColor(enhanced_gray, cv2.COLOR_GRAY2BGR)
            elif mode == 6:
                gray = cv2.cvtColor(working_image, cv2.COLOR_BGR2GRAY)
                clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8,8))
                enhanced_gray = clahe.apply(gray)
                inverted = cv2.bitwise_not(enhanced_gray)
                working_image = cv2.cvtColor(inverted, cv2.COLOR_GRAY2BGR)
            elif mode == 7:
                gray = cv2.cvtColor(working_image, cv2.COLOR_BGR2GRAY)
                _, thresh = cv2.threshold(gray, 120, 255, cv2.THRESH_BINARY)
                working_image = cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)

        # Apply trace enhancement if enabled
        if self.trace_enhancement_active:
            # Enhance thin lines (like EEG traces)
            gray = cv2.cvtColor(working_image, cv2.COLOR_BGR2GRAY)
            kernel = np.ones((2,2), np.uint8)
            dilated = cv2.dilate(gray, kernel, iterations=1)
            working_image = cv2.cvtColor(dilated, cv2.COLOR_GRAY2BGR)

        width = int(working_image.shape[1] * scale_percent / 100)
        height = int(working_image.shape[0] * scale_percent / 100)
        resized = cv2.resize(working_image, (width, height), interpolation=cv2.INTER_LINEAR)

        # The *only* conversion to RGB happens right here, for display.
        display_image = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)

        h, w, ch = display_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(display_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_image)
        
        # Create a new pixmap to draw overlays on
        final_pixmap = QPixmap(pixmap.size())
        final_pixmap.fill(Qt.transparent)
        
        # Draw the image
        painter = QPainter(final_pixmap)
        painter.drawPixmap(0, 0, pixmap)
        
        # Draw analysis overlays (use zoom_factor for positioning)
        for overlay in self.analysis_overlays:
            overlay.draw(painter, scale_percent / 100.0)
        
        # Draw currently being drawn overlay (preview)
        if self.drawing_overlay:
            self.drawing_overlay.draw(painter, scale_percent / 100.0)
        
        painter.end()
        
        self.image_label.setPixmap(final_pixmap)
        self.image_label.adjustSize()

    def apply_enhanced_mode(self):
        checked = self.enhanced_mode_checkbox.isChecked()
        self.settings.setValue("enhanced_mode", checked)
        if checked:
            # When turning ON, set to the default Enhanced Mode zoom
            self.zoom_percent = self.default_zoom_enhanced_mode
        else:
            # When turning OFF, reset zoom to 100%
            self.zoom_percent = 100
        
        # If not in live mode, force an update.
        if not self.live_capture_active:
            self.update_zoom()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_C:
            self.contrast_mode = (self.contrast_mode + 1) % 8 # Now 8 modes
            self.settings.setValue("contrast_mode", self.contrast_mode)
            
            contrast_names = [
                "Normal", "Enhanced Color", "High-Con Color", "Smart Invert", 
                "Inverted Gray", "HC Gray", "Inv HC Gray", "Binary"
            ]
            self.contrast_label.setText(f"Contrast: {contrast_names[self.contrast_mode]}")
            
            if not self.live_capture_active:
                self.update_zoom()

        elif event.key() == Qt.Key_Plus or event.key() == Qt.Key_Equal:
            self.zoom_slider.setValue(self.zoom_slider.value() + 10)
        elif event.key() == Qt.Key_Minus:
            self.zoom_slider.setValue(self.zoom_slider.value() - 10)
        elif event.key() == Qt.Key_Z:
            # Z key for zoom in
            self.zoom_slider.setValue(self.zoom_slider.value() + 10)
        elif event.key() == Qt.Key_X:
            # X key for zoom out
            self.zoom_slider.setValue(self.zoom_slider.value() - 10)
        elif event.key() == Qt.Key_R:
            # R key for reset zoom
            self.zoom_slider.setValue(100)
        elif event.key() == Qt.Key_Right:
            self.next_page()
        elif event.key() == Qt.Key_Left:
            self.prev_page()
        elif event.key() == Qt.Key_Space:
            # Space bar to capture screen quickly
            self.capture_screen()
        elif event.key() == Qt.Key_T:
            # T key for trace enhancement
            self.trace_enhance_button.setChecked(not self.trace_enhance_button.isChecked())
            self.toggle_trace_enhancement()
        elif event.key() == Qt.Key_A:
            # A key for analysis mode
            self.analysis_mode_button.setChecked(not self.analysis_mode_button.isChecked())
            self.toggle_analysis_mode()
        elif event.key() == Qt.Key_P:
            # P key for save position
            self.save_position()
        elif event.key() == Qt.Key_Delete:
            # Delete key to clear annotations
            self.professional_annotations.clear()
            self.update_zoom()

    def wheelEvent(self, event):
        """Handle mouse wheel scrolling to zoom in and out."""
        if QApplication.keyboardModifiers() == Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_slider.setValue(self.zoom_slider.value() + 10)
            elif delta < 0:
                self.zoom_slider.setValue(self.zoom_slider.value() - 10)
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event):
        """Handle mouse press events for panning and analysis tools."""
        if event.button() == Qt.LeftButton:
            if self.analysis_mode_active:
                self.handle_analysis_mouse_press(event)
            else:
                # Original panning logic
                self.panning = True
                self.pan_start_pos = event.pos()
        elif event.button() == Qt.RightButton:
            # Right click to cancel current drawing
            if self.analysis_mode_active and self.drawing_overlay:
                self.drawing_overlay = None
                self.drawing_start_point = None
                self.update_zoom()

    def mouseMoveEvent(self, event):
        """Handle mouse move events for panning and analysis tools."""
        if self.analysis_mode_active:
            self.handle_analysis_mouse_move(event)
        else:
            # Original panning logic
            if self.panning and self.pan_start_pos:
                delta = event.pos() - self.pan_start_pos
                self.scroll_area.horizontalScrollBar().setValue(
                    self.scroll_area.horizontalScrollBar().value() - delta.x()
                )
                self.scroll_area.verticalScrollBar().setValue(
                    self.scroll_area.verticalScrollBar().value() - delta.y()
                )
                self.pan_start_pos = event.pos()

    def mouseReleaseEvent(self, event):
        """Handle mouse release events for analysis tools."""
        if event.button() == Qt.LeftButton and self.analysis_mode_active:
            self.handle_analysis_mouse_release(event)
        elif event.button() == Qt.LeftButton:
            # Original panning logic
            self.panning = False

    def handle_analysis_mouse_press(self, event):
        """Handle mouse press in analysis mode."""
        pos = self.get_image_coordinates(event.pos())
        if pos is None:
            return
            
        if self.current_analysis_tool == "Note":
            # Create note immediately
            text, ok = QInputDialog.getText(self, "Add Note", "Enter note text:")
            if ok and text:
                color = "#00FF00"  # Green for notes
                note = NoteOverlay(pos, text, color)
                self.analysis_overlays.append(note)
                self.update_zoom()
                
        elif self.current_analysis_tool == "Ruler":
            # Let user pick a color for the ruler first
            color = QColorDialog.getColor(Qt.red, self, "Select Ruler Color")
            if not color.isValid():
                return # User cancelled

            # Start drawing ruler
            self.drawing_start_point = pos
            self.drawing_overlay = RulerOverlay(pos, pos, color.name())
        elif self.current_analysis_tool == "ROI":
            # Start drawing ROI box
            self.drawing_start_point = pos
            self.drawing_overlay = RegionOfInterestOverlay(pos, pos, "#0000FF")  # Blue for ROI

    def handle_analysis_mouse_move(self, event):
        """Handle mouse move in analysis mode."""
        pos = self.get_image_coordinates(event.pos())
        if pos is None:
            return
            
        # Update status bar with coordinates
        self.statusBar().showMessage(f"Position: ({pos.x()}, {pos.y()})")
        
        # Update drawing preview
        if self.drawing_overlay and self.drawing_start_point:
            if isinstance(self.drawing_overlay, RulerOverlay):
                self.drawing_overlay.end_point = pos
            elif isinstance(self.drawing_overlay, RegionOfInterestOverlay):
                self.drawing_overlay.bottom_right = pos
            self.update_zoom()

    def handle_analysis_mouse_release(self, event):
        """Handle mouse release in analysis mode."""
        if self.drawing_overlay and self.drawing_start_point:
            pos = self.get_image_coordinates(event.pos())
            if pos is None:
                return
                
            if isinstance(self.drawing_overlay, RulerOverlay):
                # Complete ruler
                self.drawing_overlay.end_point = pos
                
                # Ask for a note
                note, ok = QInputDialog.getText(self, "Ruler Note", "Enter a note for this ruler (optional):")
                if ok and note:
                    self.drawing_overlay.data['note'] = note
                
                self.analysis_overlays.append(self.drawing_overlay)
            elif isinstance(self.drawing_overlay, RegionOfInterestOverlay):
                # Complete ROI box
                self.drawing_overlay.bottom_right = pos
                
                # Ask for a note
                note, ok = QInputDialog.getText(self, "ROI Note", "Enter a note for this region (optional):")
                if ok and note:
                    self.drawing_overlay.data['note'] = note
                
                self.analysis_overlays.append(self.drawing_overlay)
            
            self.drawing_overlay = None
            self.drawing_start_point = None
            self.update_zoom()

    def get_image_coordinates(self, mouse_pos):
        """Convert mouse position to image coordinates."""
        if not hasattr(self, 'image_label') or not self.image_label.pixmap():
            return None
            
        # Get the image label's position relative to the scroll area
        label_pos = self.image_label.mapFrom(self.scroll_area.viewport(), mouse_pos)
        
        # Check if click is within the image
        pixmap = self.image_label.pixmap()
        if not pixmap:
            return None
            
        # Get the actual image dimensions (before zoom)
        if self.original_image is not None:
            original_width = self.original_image.shape[1]
            original_height = self.original_image.shape[0]
        else:
            return None
            
        # Calculate zoom factor
        zoom_factor = self.zoom_slider.value() / 100.0
        
        # Convert from pixmap coordinates to original image coordinates
        image_x = int(label_pos.x() / zoom_factor)
        image_y = int(label_pos.y() / zoom_factor)
        
        # Check if coordinates are within the original image bounds
        if (0 <= image_x < original_width and 0 <= image_y < original_height):
            return QPoint(image_x, image_y)
        return None

    def export_current_view(self):
        if self.original_image is None:
            return
        save_path, _ = QFileDialog.getSaveFileName(self, "Export View", "exported_view.png", "PNG Files (*.png)")
        if save_path:
            scale_percent = self.zoom_slider.value()
            width = int(self.original_image.shape[1] * scale_percent / 100)
            height = int(self.original_image.shape[0] * scale_percent / 100)
            
            # The final processed image to be saved. It starts as BGR.
            image_to_save = cv2.resize(self.original_image, (width, height), interpolation=cv2.INTER_LINEAR)

            if self.enhanced_mode_checkbox.isChecked() and self.contrast_mode != 0:
                mode = self.contrast_mode
                if mode == 1:
                    lab = cv2.cvtColor(image_to_save, cv2.COLOR_BGR2LAB)
                    l, a, b = cv2.split(lab)
                    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
                    l = clahe.apply(l)
                    lab = cv2.merge([l, a, b])
                    image_to_save = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
                    hsv = cv2.cvtColor(image_to_save, cv2.COLOR_BGR2HSV)
                    hsv[:, :, 1] = cv2.multiply(hsv[:, :, 1], 1.3)
                    hsv[:, :, 1] = np.clip(hsv[:, :, 1], 0, 255)
                    image_to_save = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
                elif mode == 2:
                    lab = cv2.cvtColor(image_to_save, cv2.COLOR_BGR2LAB)
                    l, a, b = cv2.split(lab)
                    clahe = cv2.createCLAHE(clipLimit=5.0, tileGridSize=(8,8))
                    l = clahe.apply(l)
                    a = cv2.multiply(a, 1.2)
                    b = cv2.multiply(b, 1.2)
                    a = np.clip(a, 0, 255)
                    b = np.clip(b, 0, 255)
                    lab = cv2.merge([l, a, b])
                    image_to_save = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
                elif mode == 3:
                    hsv = cv2.cvtColor(image_to_save, cv2.COLOR_BGR2HSV)
                    hsv[:, :, 2] = 255 - hsv[:, :, 2]
                    image_to_save = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
                elif mode == 4:
                    gray = cv2.cvtColor(image_to_save, cv2.COLOR_BGR2GRAY)
                    inverted = cv2.bitwise_not(gray)
                    image_to_save = cv2.cvtColor(inverted, cv2.COLOR_GRAY2BGR)
                elif mode == 5:
                    gray = cv2.cvtColor(image_to_save, cv2.COLOR_BGR2GRAY)
                    clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8,8))
                    enhanced_gray = clahe.apply(gray)
                    image_to_save = cv2.cvtColor(enhanced_gray, cv2.COLOR_GRAY2BGR)
                elif mode == 6:
                    gray = cv2.cvtColor(image_to_save, cv2.COLOR_BGR2GRAY)
                    clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8,8))
                    enhanced_gray = clahe.apply(gray)
                    inverted = cv2.bitwise_not(enhanced_gray)
                    image_to_save = cv2.cvtColor(inverted, cv2.COLOR_GRAY2BGR)
                elif mode == 7:
                    gray = cv2.cvtColor(image_to_save, cv2.COLOR_BGR2GRAY)
                    _, thresh = cv2.threshold(gray, 120, 255, cv2.THRESH_BINARY)
                    image_to_save = cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)
            
            # cv2.imwrite expects BGR, which our image is already in.
            cv2.imwrite(save_path, image_to_save)

    def restore_session(self):
        # Load saved zoom
        last_zoom = self.settings.value("last_zoom", type=int)
        if last_zoom:
            self.zoom_slider.setValue(last_zoom)
        last_enhanced = self.settings.value("enhanced_mode", type=bool)
        if last_enhanced is not None:
            self.enhanced_mode_checkbox.setChecked(last_enhanced)
        self.contrast_mode = self.settings.value("contrast_mode", 0, type=int)
        
        # Clamp contrast mode to valid range
        contrast_names = [
            "Normal", "Enhanced Color", "High-Con Color", "Smart Invert", 
            "Inverted Gray", "HC Gray", "Inv HC Gray", "Binary"
        ]
        if self.contrast_mode >= len(contrast_names):
            self.contrast_mode = 0
        self.contrast_label.setText(f"Contrast: {contrast_names[self.contrast_mode]}")
        
        last_file = self.settings.value("last_file", "")
        if last_file and os.path.exists(last_file):
            self.current_file_path = last_file
            if last_file.lower().endswith('.pdf'):
                self.doc = fitz.open(last_file)
                self.page_selector.setMaximum(len(self.doc))
                self.current_page_index = 0
                self.load_pdf_page(self.current_page_index)
            else:
                self.doc = None
                self.original_image = cv2.imread(last_file)
                self.current_image = self.original_image.copy()
                self.page_selector.setMaximum(1)
                self.update_zoom()

        # Load saved positions
        saved_positions_json = self.settings.value("saved_positions", "")
        if saved_positions_json:
            try:
                self.saved_positions = json.loads(saved_positions_json)
                self.update_positions_list()
            except json.JSONDecodeError:
                self.saved_positions = {}

        # Load saved annotations
        saved_annotations_json = self.settings.value("saved_annotations", "")
        if saved_annotations_json:
            try:
                annotations_data = json.loads(saved_annotations_json)
                self.professional_annotations = []
                for ann_data in annotations_data:
                    position = None
                    if "position" in ann_data:
                        pos_data = ann_data["position"]
                        position = QPoint(pos_data["x"], pos_data["y"])
                    annotation = Annotation(ann_data["type"], position, ann_data["data"])
                    annotation.id = ann_data.get("id", annotation.id)
                    self.professional_annotations.append(annotation)
            except json.JSONDecodeError:
                self.professional_annotations = []

        # Load analysis overlays
        overlays_data = self.settings.value("analysis_overlays", [])
        self.analysis_overlays = []
        for overlay_data in overlays_data:
            overlay = AnalysisOverlay.from_dict(overlay_data)
            self.analysis_overlays.append(overlay)

        # Load analysis mode state
        self.analysis_mode_active = self.settings.value("analysis_mode_active", False, type=bool)
        self.current_analysis_tool = self.settings.value("current_analysis_tool", "Note", type=str)

        # Update analysis tool combo
        self.analysis_tool_combo.clear()
        self.analysis_tool_combo.addItems(["Note", "Ruler", "ROI"])
        self.analysis_tool_combo.setCurrentText(self.current_analysis_tool)
        self.analysis_tool_combo.setEnabled(self.analysis_mode_active)
        
        # Update analysis mode button state to match loaded settings
        self.analysis_mode_button.setChecked(self.analysis_mode_active)

    # EEG Viewing Aid Functions
    def toggle_trace_enhancement(self):
        """Toggle EEG trace enhancement mode."""
        self.trace_enhancement_active = self.trace_enhance_button.isChecked()
        if not self.live_capture_active:
            self.update_zoom()

    def toggle_analysis_mode(self):
        """Toggle analysis mode."""
        self.analysis_mode_active = self.analysis_mode_button.isChecked()
        self.analysis_tool_combo.setEnabled(self.analysis_mode_active)
        
        if self.analysis_mode_active:
            self.setCursor(Qt.CrossCursor)
            self.current_analysis_tool = self.analysis_tool_combo.currentText()
            self.statusBar().showMessage("Analysis Mode: " + self.current_analysis_tool)
        else:
            self.setCursor(Qt.ArrowCursor)
            self.statusBar().showMessage("Analysis Mode disabled")
            # Clear any drawing state
            self.drawing_overlay = None
            self.drawing_start_point = None

    def toggle_measurement(self):
        """Toggle professional measurement mode."""
        self.measurement_active = self.measure_button.isChecked()
        if self.measurement_active:
            self.setCursor(Qt.CrossCursor)
            self.current_measurement_start = None
        else:
            self.setCursor(Qt.ArrowCursor)
            self.current_measurement_start = None

    def toggle_annotation(self):
        """Toggle professional annotation mode."""
        self.annotation_active = self.analysis_mode_button.isChecked()
        if self.annotation_active:
            self.setCursor(Qt.CrossCursor)
        else:
            self.setCursor(Qt.ArrowCursor)

    def show_measurement_dialog(self):
        """Show dialog for measurement details."""
        measurement_type = self.measurement_tool.measurement_type
        distance = self.measurement_tool.get_distance()
        
        # Create a simple dialog for measurement details
        dialog = AnnotationDialog(self, measurement_type)
        if dialog.exec_():
            measurement_data = dialog.get_annotation_data()
            measurement_data["raw_distance"] = distance
            measurement_data["calibrated_value"] = self.measurement_tool.get_calibrated_value()
            
            # Create annotation for the measurement
            annotation = Annotation(measurement_type, self.current_measurement_start, measurement_data)
            self.professional_annotations.append(annotation)
            self.update_zoom()

    def calibrate_measurement(self):
        """Set calibration for measurements."""
        current_factor, ok = QInputDialog.getDouble(
            self, "Calibration", 
            f"Enter calibration factor (pixels per {self.measurement_tool.calibration_unit}):",
            self.measurement_tool.calibration_factor, 0.1, 1000.0, 2
        )
        if ok:
            self.measurement_tool.calibration_factor = current_factor
            QMessageBox.information(self, "Calibration", 
                                  f"Calibration set to {current_factor} pixels per {self.measurement_tool.calibration_unit}")

    def show_annotations_panel(self):
        """Show the analysis overlays management panel."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Analysis Overlays Manager")
        dialog.setModal(True)
        dialog.resize(600, 400)
        
        layout = QVBoxLayout(dialog)
        
        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["Type", "Position", "Details", "Actions"])
        table.horizontalHeader().setStretchLastSection(True)
        
        def refresh_table():
            table.setRowCount(0)
            for i, overlay in enumerate(self.analysis_overlays):
                table.insertRow(i)
                
                # Type
                type_item = QTableWidgetItem(overlay.type)
                type_item.setFlags(type_item.flags() & ~Qt.ItemIsEditable)
                table.setItem(i, 0, type_item)
                
                # Position
                if overlay.type == "Note":
                    pos_text = f"({overlay.position.x()}, {overlay.position.y()})"
                elif overlay.type == "Ruler":
                    pos_text = f"({overlay.start_point.x()}, {overlay.start_point.y()}) to ({overlay.end_point.x()}, {overlay.end_point.y()})"
                elif overlay.type == "ROI":
                    pos_text = f"({overlay.top_left.x()}, {overlay.top_left.y()}) to ({overlay.bottom_right.x()}, {overlay.bottom_right.y()})"
                else:
                    pos_text = "N/A"
                
                pos_item = QTableWidgetItem(pos_text)
                pos_item.setFlags(pos_item.flags() & ~Qt.ItemIsEditable)
                table.setItem(i, 1, pos_item)
                
                # Details
                if overlay.type == "Note":
                    details = overlay.text
                elif overlay.type == "Ruler":
                    distance = math.sqrt((overlay.end_point.x() - overlay.start_point.x())**2 + 
                                       (overlay.end_point.y() - overlay.start_point.y())**2)
                    details = f"Distance: {distance:.1f}px"
                    if 'note' in overlay.data and overlay.data['note']:
                        details += f" - {overlay.data['note']}"
                elif overlay.type == "ROI":
                    width = abs(overlay.bottom_right.x() - overlay.top_left.x())
                    height = abs(overlay.bottom_right.y() - overlay.top_left.y())
                    details = f"Size: {width:.0f} × {height:.0f}px"
                    if 'note' in overlay.data and overlay.data['note']:
                        details += f" - {overlay.data['note']}"
                else:
                    details = "N/A"
                
                details_item = QTableWidgetItem(details)
                table.setItem(i, 2, details_item)

                # Actions
                actions_widget = QWidget()
                actions_layout = QHBoxLayout(actions_widget)
                actions_layout.setContentsMargins(0, 0, 0, 0)
                
                edit_btn = QPushButton("Edit")
                delete_btn = QPushButton("Delete")
                
                # The lambda now passes the table reference to the delete function
                edit_btn.clicked.connect(lambda checked, row=i: self.edit_overlay(row, refresh_table))
                delete_btn.clicked.connect(lambda checked, row=i: self.delete_overlay(row, refresh_table))
                
                actions_layout.addWidget(edit_btn)
                actions_layout.addWidget(delete_btn)
                table.setCellWidget(i, 3, actions_widget)

        refresh_table() # Initial population
        
        layout.addWidget(table)
        
        # Buttons
        clear_all_btn = QPushButton("Clear All")
        export_btn = QPushButton("Export Overlays")
        close_btn = QPushButton("Close")
        
        clear_all_btn.clicked.connect(lambda: (self.clear_all_overlays(), refresh_table()))
        export_btn.clicked.connect(self.export_overlays)
        close_btn.clicked.connect(dialog.accept)
        
        button_layout = QHBoxLayout()
        button_layout.addWidget(clear_all_btn)
        button_layout.addWidget(export_btn)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)
        
        dialog.setLayout(layout)
        
        # Apply dark theme
        dialog.setStyleSheet(self.get_dark_theme_stylesheet())
        
        dialog.exec_()

    def delete_overlay(self, index, refresh_callback):
        """Delete an overlay and refresh the calling table."""
        if 0 <= index < len(self.analysis_overlays):
            del self.analysis_overlays[index]
            self.update_zoom() # Redraw the main view
            refresh_callback() # Refresh the table in the dialog

    def edit_overlay(self, index, refresh_callback):
        """Edit an overlay and refresh the calling table."""
        if 0 <= index < len(self.analysis_overlays):
            overlay = self.analysis_overlays[index]
            if overlay.type == "Note":
                text, ok = QInputDialog.getText(self, "Edit Note", "Enter new text:", text=overlay.text)
                if ok:
                    overlay.text = text
                    self.update_zoom()
                    refresh_callback()
            elif overlay.type == "ROI":
                current_note = overlay.data.get('note', '')
                note, ok = QInputDialog.getText(self, "Edit ROI Note", "Enter note for this region:", text=current_note)
                if ok:
                    if note:
                        overlay.data['note'] = note
                    else:
                        overlay.data.pop('note', None)
                    self.update_zoom()
                    refresh_callback()
            elif overlay.type == "Ruler":
                current_note = overlay.data.get('note', '')
                text, ok = QInputDialog.getText(self, 'Edit Ruler Note', 'Note:', QLineEdit.Normal, current_note)
                if ok:
                    overlay.data['note'] = text
                    self.update_zoom()
                    refresh_callback()
            # Add more edit options for other overlay types as needed

    def clear_all_overlays(self):
        """Clear all overlays."""
        reply = QMessageBox.question(self, "Clear All", 
                                   "Are you sure you want to clear all overlays?",
                                   QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.analysis_overlays.clear()
            self.update_zoom()

    def export_overlays(self):
        """Export overlays to a file."""
        filename, _ = QFileDialog.getSaveFileName(self, "Export Overlays", "", "JSON Files (*.json)")
        if filename:
            overlays_data = []
            for overlay in self.analysis_overlays:
                overlays_data.append(overlay.to_dict())
            
            with open(filename, 'w') as f:
                json.dump(overlays_data, f, indent=2)
            
            QMessageBox.information(self, "Export Complete", f"Overlays exported to {filename}")

    def save_position(self):
        """Save current zoom and scroll position."""
        name, ok = QInputDialog.getText(self, "Save Position", "Enter a name for this position:")
        if ok and name:
            position_data = {
                "zoom": self.zoom_percent,
                "scroll_x": self.scroll_area.horizontalScrollBar().value(),
                "scroll_y": self.scroll_area.verticalScrollBar().value(),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            self.saved_positions[name] = position_data
            self.settings.setValue("saved_positions", json.dumps(self.saved_positions))
            self.update_positions_list()
            QMessageBox.information(self, "Position Saved", f"Position '{name}' saved successfully!")

    def load_position(self, position_name):
        """Load a saved position."""
        if position_name in self.saved_positions:
            pos_data = self.saved_positions[position_name]
            self.zoom_percent = pos_data["zoom"]
            self.scroll_area.horizontalScrollBar().setValue(pos_data["scroll_x"])
            self.scroll_area.verticalScrollBar().setValue(pos_data["scroll_y"])

    def update_positions_list(self):
        """Update the positions combo box."""
        self.positions_list.clear()
        self.positions_list.addItem("Select Position...")
        for name in self.saved_positions.keys():
            self.positions_list.addItem(name)

    def closeEvent(self, event):
        """Save annotations when closing the application."""
        # Save analysis overlays
        overlays_data = []
        for overlay in self.analysis_overlays:
            overlays_data.append(overlay.to_dict())
        self.settings.setValue('analysis_overlays', overlays_data)
        
        # Save analysis mode state
        self.settings.setValue('analysis_mode_active', self.analysis_mode_active)
        self.settings.setValue('current_analysis_tool', self.current_analysis_tool)

        # Save professional annotations
        annotations_data = []
        for annotation in self.professional_annotations:
            ann_data = {
                "type": annotation.type,
                "id": annotation.id,
                "data": annotation.data
            }
            if annotation.position:
                ann_data["position"] = {
                    "x": annotation.position.x(),
                    "y": annotation.position.y()
                }
            annotations_data.append(ann_data)
        
        self.settings.setValue("saved_annotations", json.dumps(annotations_data))
        event.accept()

    def map_event_to_image_coords(self, event):
        """Accurately map a mouse event to the image label's coordinate system."""
        # Map global screen coordinates to the scroll area's viewport
        pos_in_viewport = self.scroll_area.viewport().mapFromGlobal(event.globalPos())
        
        # Add the current scroll bar positions to get the final coordinates on the image
        final_x = pos_in_viewport.x() + self.scroll_area.horizontalScrollBar().value()
        final_y = pos_in_viewport.y() + self.scroll_area.verticalScrollBar().value()
        
        return QPoint(final_x, final_y)

    def calculate_distance(self, point1, point2):
        """Calculate distance between two points in pixels."""
        return ((point2.x() - point1.x())**2 + (point2.y() - point1.y())**2)**0.5

    def draw_measurements(self, painter):
        """Draw measurement lines and current measurement in progress."""
        # Draw current measurement in progress
        if self.measurement_active and self.current_measurement_start:
            painter.setPen(QPen(QColor(0, 255, 0), 2, Qt.DashLine))
            painter.drawLine(self.current_measurement_start, painter.device().rect().center())
        
        # Draw completed measurements from annotations
        for annotation in self.professional_annotations:
            if annotation.type in ["Distance", "Amplitude", "Frequency", "Duration", "Latency"]:
                if hasattr(annotation, 'measurement_points') and annotation.measurement_points:
                    start, end = annotation.measurement_points
                    color = QColor(annotation.data.get("color", "#FF0000"))
                    painter.setPen(QPen(color, 2))
                    painter.drawLine(start, end)
                    
                    # Draw measurement text
                    value = annotation.data.get("value", "")
                    unit = annotation.data.get("unit", "")
                    if value and unit:
                        mid_point = QPoint((start.x() + end.x()) // 2, (start.y() + end.y()) // 2)
                        painter.drawText(mid_point, f"{value} {unit}")

    def draw_annotations(self, painter):
        """Draw professional annotations."""
        for annotation in self.professional_annotations:
            annotation.draw(painter)

    def on_annotation_type_changed(self, text):
        self.current_annotation_type = text

    def toggle_static_ruler(self):
        if not self.static_ruler:
            self.static_ruler = StaticRulerWidget()
        
        if self.static_ruler_button.isChecked():
            self.static_ruler.show()
        else:
            self.static_ruler.hide()

    def get_dark_theme_stylesheet(self):
        return """
        QWidget {
            background-color: #2e2e2e;
            color: #ffffff;
            border: none;
        }
        QMainWindow {
            background-color: #2e2e2e;
        }
        QPushButton {
            background-color: #555555;
            border: 1px solid #666666;
            padding: 5px;
            border-radius: 2px;
        }
        QPushButton:hover {
            background-color: #666666;
        }
        QPushButton:checked {
            background-color: #4CAF50;
        }
        QSlider::groove:horizontal {
            background: #444444;
            height: 8px;
            border-radius: 4px;
        }
        QSlider::handle:horizontal {
            background: #888888;
            border: 1px solid #999999;
            width: 14px;
            margin: -4px 0;
            border-radius: 7px;
        }
        QLabel, QCheckBox, QSpinBox, QComboBox {
            background-color: transparent;
        }
        QSpinBox, QComboBox {
            border: 1px solid #555;
            padding: 2px;
        }
        QDialog {
            background-color: #2e2e2e;
        }
        QTableWidget {
            background-color: #3e3e3e;
            gridline-color: #555555;
        }
        QTableWidget::item {
            padding: 5px;
        }
        QTableWidget::item:selected {
            background-color: #4CAF50;
        }
        QHeaderView::section {
            background-color: #555555;
            padding: 5px;
            border: 1px solid #666666;
        }
        """

    def toggle_measurement_grid(self):
        if not self.measurement_grid:
            self.measurement_grid = MeasurementGridWidget()
            self.load_grid_calibration() # Load saved settings
        
        if self.measurement_grid_button.isChecked():
            self.measurement_grid.show()
        else:
            self.measurement_grid.hide()

    def calibrate_grid(self):
        # Create dialog with current values
        x_px = self.settings.value("cal_x_px", 50, type=int)
        x_val = self.settings.value("cal_x_val", 100, type=float)
        x_unit = self.settings.value("cal_x_unit", "ms", type=str)
        y_px = self.settings.value("cal_y_px", 50, type=int)
        y_val = self.settings.value("cal_y_val", 50, type=float)
        y_unit = self.settings.value("cal_y_unit", "µV", type=str)

        dialog = CalibrationDialog(self, x_px, x_val, x_unit, y_px, y_val, y_unit)
        if dialog.exec_():
            values = dialog.get_values()
            # Save values
            self.settings.setValue("cal_x_px", values["x_px"])
            self.settings.setValue("cal_x_val", values["x_val"])
            self.settings.setValue("cal_x_unit", values["x_unit"])
            self.settings.setValue("cal_y_px", values["y_px"])
            self.settings.setValue("cal_y_val", values["y_val"])
            self.settings.setValue("cal_y_unit", values["y_unit"])
            
            # Apply to grid if it exists
            if self.measurement_grid:
                self.load_grid_calibration()

    def load_grid_calibration(self):
        if self.measurement_grid:
            self.measurement_grid.x_pixels_per_unit = self.settings.value("cal_x_px", 50, type=int)
            x_val = self.settings.value("cal_x_val", 100, type=float)
            self.measurement_grid.x_unit_name = self.settings.value("cal_x_unit", "ms", type=str)
            self.measurement_grid.x_val_per_tick = x_val
            
            self.measurement_grid.y_pixels_per_unit = self.settings.value("cal_y_px", 50, type=int)
            y_val = self.settings.value("cal_y_val", 50, type=float)
            self.measurement_grid.y_unit_name = self.settings.value("cal_y_unit", "µV", type=str)
            self.measurement_grid.y_val_per_tick = y_val
            
            self.measurement_grid.update() # Repaint with new calibration

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet("""
        QWidget {
            background-color: #2e2e2e;
            color: #ffffff;
            border: none;
        }
        QMainWindow, QDialog {
            background-color: #3c3c3c;
            border: 1px solid #555;
        }
        QPushButton {
            background-color: #555555;
            border: 1px solid #666666;
            padding: 5px;
            border-radius: 2px;
        }
        QPushButton:hover {
            background-color: #666666;
        }
        QPushButton:pressed {
            background-color: #4d4d4d;
        }
        QSlider::groove:horizontal {
            background: #444444;
            height: 8px;
            border-radius: 4px;
        }
        QSlider::handle:horizontal {
            background: #888888;
            border: 1px solid #999999;
            width: 14px;
            margin: -4px 0;
            border-radius: 7px;
        }
        QLabel, QCheckBox, QRadioButton {
            background-color: transparent;
        }
        QSpinBox, QLineEdit, QTextEdit, QComboBox {
            border: 1px solid #555;
            padding: 3px;
            background-color: #2e2e2e;
            color: #fff;
            border-radius: 2px;
        }
        QComboBox::drop-down {
            border-left: 1px solid #555;
        }
        QTableWidget {
            gridline-color: #555;
            background-color: #2e2e2e;
            color: #fff;
        }
        QHeaderView::section {
            background-color: #444;
            padding: 4px;
            border: 1px solid #555;
            color: #fff;
        }
        QTabWidget::pane {
            border: 1px solid #555;
            border-top: none;
        }
        QTabBar::tab {
            background: #444;
            border: 1px solid #555;
            border-bottom: none;
            padding: 8px 20px;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
            color: #fff;
            margin-right: 2px;
        }
        QTabBar::tab:selected {
            background: #3c3c3c;
            margin-bottom: -1px;
        }
        QStatusBar {
            background: #2e2e2e;
        }
    """)
    viewer = ImageZoomViewer()
    viewer.show()

    # Close the splash screen
    try:
        import pyi_splash
        pyi_splash.close()
    except ImportError:
        pass  # This will fail when not running from a bundled app, which is fine.

    sys.exit(app.exec_()) 