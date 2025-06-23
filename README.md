# EEG Paradox Viewer v2.0

A professional EEG analysis tool designed for EEG professionals, featuring specialized viewing aids, live screen capture capabilities, and comprehensive analysis tools.

## 🎯 Purpose

This tool helps clinicians efficiently view, analyze, and interpret EEG-related images, PDFs, and live EEG displays from tools like NeuroGuide, Wineeg, or BioExplorer. It serves as a comprehensive digital analysis platform with specialized tools for EEG interpretation.

## ✅ Features

### 🗂 File Support
- Open PDFs (multi-page navigation)
- Open images (.png, .jpg, .bmp, .tif)

### 🔍 Visual Accessibility
- **Enhanced Mode**: One-click setting that auto-zooms to 250% and enables high-contrast display
- **Zoom Controls**: 10% to 400% zoom with + and - buttons
- **Contrast Modes**: 
  - Normal
  - Enhanced Color
  - High-Contrast Color
  - Smart Invert
  - Inverted Gray
  - High-Contrast Gray
  - Inverted High-Contrast Gray
  - Binary

### 🧠 Professional Analysis Tools
- **Analysis Mode**: Comprehensive annotation and measurement tools
  - **Note Tool**: Add text annotations to specific points
  - **Ruler Tool**: Measure distances with color selection and notes
  - **ROI Tool**: Highlight regions of interest with annotations
- **Measurement Grid**: Floating, draggable measurement tool with calibration
- **Trace Enhancement Mode**: Enhances thin EEG traces for better visibility
- **Position Memory**: Save and recall specific zoom/position combinations
- **Live Screen Capture**: Real-time viewing of EEG displays with adjustable FPS

### ⌨️ Keyboard Shortcuts
- `Z` / `X`: Zoom in/out
- `R`: Reset zoom to 100%
- `C`: Cycle contrast modes
- `←` / `→`: Flip PDF pages
- `Space`: Quick screen capture
- `T`: Toggle trace enhancement
- `A`: Toggle analysis mode
- `M`: Toggle measurement grid
- `P`: Save current position
- `Ctrl + Mouse Wheel`: Zoom in/out

### 📄 PDF Viewer Features
- Next/Previous Page buttons
- Jump to Specific Page
- Auto-remembers last page and file opened

### 🎥 Live Capture Features
- **Selectable FPS**: Choose from 10-120 FPS or match screen refresh rate
- **Source Selection**: Capture full screen, specific monitor, or application window
- **Real-time Processing**: Apply all viewing aids to live capture

### 📤 Exporting
- Export current view as .png image (including zoom, contrast, and annotations)
- Export analysis overlays to JSON format

### 💾 Session Memory
Remembers:
- Last opened file
- Last zoom level
- Enhanced Mode on/off
- Contrast mode
- Last page viewed
- Saved positions
- Capture source settings
- Analysis overlays and annotations
- Measurement grid calibration

## 🧰 Installation

### Prerequisites
- Python 3.8 or higher
- Windows 10/11 (for screen capture features)

### Setup
1. Install required libraries:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python eeg_paradox_viewer_v2_live.py
```

## 🏗️ Building Executable

### Quick Build
Run the automated build script:
```bash
build_EEG_viewer.bat
```

### Manual Build with auto-py-to-exe
1. Install auto-py-to-exe:
```bash
pip install auto-py-to-exe
```

2. Run auto-py-to-exe:
```bash
auto-py-to-exe
```

3. Configure:
   - Script Location: `eeg_paradox_viewer_v2_live.py`
   - Onefile: Yes
   - Console Window: No
   - Icon: (optional)
   - Additional Files: None needed

## 🎯 How to Use

### Basic Viewing
1. **Loading a file**: Click "Open File" and choose an EEG-related PDF or image
2. **Zooming**: Use the + and - buttons or press `Z` and `X` to zoom
3. **Enhanced Mode**: Check the "Enable Enhanced Mode" checkbox for auto-zoom and high contrast
4. **Contrast modes**: Press `C` to cycle through contrast options

### Professional Analysis Tools
1. **Analysis Mode**: Click "Analysis Mode" or press `A` to enable analysis tools
2. **Note Tool**: Select "Note" from the dropdown, then click anywhere to add text annotations
3. **Ruler Tool**: Select "Ruler" from the dropdown, choose a color, then click and drag to measure
4. **ROI Tool**: Select "ROI" from the dropdown, then click and drag to create selection boxes
5. **Manage Overlays**: Click "Manage Overlays" to view, edit, and delete all annotations
6. **Measurement Grid**: Click "Toggle Grid" to show the floating measurement tool
7. **Trace Enhancement**: Click "Trace Mode" or press `T` to enhance EEG traces
8. **Save Position**: Click "Save Pos" or press `P` to remember current view
9. **Load Position**: Use the dropdown to return to saved positions

### Live Capture
1. **Select Source**: Click "Select Source" to choose capture area
2. **Set FPS**: Choose desired frame rate from dropdown
3. **Start Live**: Check "Live Capture" to begin real-time viewing
4. **Apply Aids**: Use all viewing aids on live capture

### Page navigation (PDFs): Use the Next/Previous buttons or arrow keys
### Export: Click "Export View" to save a .png snapshot

## 🧠 Use Cases

- Professional EEG analysis and interpretation
- Reading dense EEG printouts or Z-score maps
- Reviewing multi-page reports in high zoom
- Live monitoring of EEG displays during analysis
- Measuring distances and marking important areas on EEG traces
- Creating annotated reports with measurements and notes
- Clinicians with visual impairments or those requiring enhanced viewing
- Portable tool to run on any Windows system

## 🔧 Troubleshooting

If you get a `ModuleNotFoundError`, make sure you've installed all dependencies:
```bash
pip install -r requirements.txt
```

For screen capture issues:
- Ensure you're running on Windows
- Check that `mss` and `pygetwindow` are installed
- Try running as administrator if capture fails

## 📝 Version History

### v2.0 (Professional Edition)
- Added comprehensive analysis tools (Notes, Rulers, ROIs)
- Professional measurement grid with calibration
- Live screen capture with adjustable FPS
- Enhanced contrast modes and viewing aids
- Improved keyboard shortcuts
- Session memory for all settings and annotations

### v1.0
- Basic PDF and image viewing
- Enhanced Mode accessibility features
- Session memory

## 📄 License

This tool is designed for professional EEG analysis and clinical use. 