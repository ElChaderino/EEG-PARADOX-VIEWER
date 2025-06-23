# EEG Paradox Viewer - User Manual

## Table of Contents
1. [Getting Started](#getting-started)
2. [File Operations](#file-operations)
3. [Live Screen Capture](#live-screen-capture)
4. [Navigation and Zoom](#navigation-and-zoom)
5. [Analysis Mode](#analysis-mode)
6. [Measurement Grid](#measurement-grid)
7. [Keyboard Shortcuts](#keyboard-shortcuts)
8. [Settings and Preferences](#settings-and-preferences)
9. [Troubleshooting](#troubleshooting)

---

## Getting Started

### Launching the Application
- Run `python eeg_paradox_viewer_v2_live.py` from the command line
- The application will start with a dark theme optimized for EEG analysis
- Your previous session settings will be automatically restored

### Main Interface
The application features a clean, professional interface with:
- **Main Display Area**: Shows your EEG images, PDFs, or live capture
- **Toolbar**: Quick access to essential functions
- **Status Bar**: Shows current zoom level and file information
- **Analysis Panel**: Professional annotation tools (when enabled)

---

## File Operations

### Opening Files
- **Images**: Supports JPG, PNG, BMP, and other common formats
- **PDFs**: Full PDF support with multi-page navigation
- **Method**: Click "Open File" or use `Ctrl+O`

### PDF Navigation
- **Next Page**: Click "Next" button or press `Page Down`
- **Previous Page**: Click "Prev" button or press `Page Up`
- **Go to Page**: Click "Go to Page" to jump to a specific page number
- **Current Page Display**: Shows "Page X of Y" in the status bar

### Exporting Views
- **Export Current View**: Saves the current display as a PNG image
- **Location**: Exported to the `output/` folder
- **Filename**: Automatically generated with timestamp

---

## Live Screen Capture

### Starting Live Capture
1. Click "Start Live Capture" button
2. Select capture source:
   - **Full Screen**: Captures entire monitor
   - **Specific Window**: Choose from list of open windows
3. Choose monitor if using multiple displays
4. Click "OK" to begin capture

### Live Capture Features
- **Real-time Display**: Updates at your monitor's refresh rate
- **FPS Display**: Shows current capture frame rate
- **Pause/Resume**: Click "Stop Live Capture" to pause, "Start Live Capture" to resume
- **Source Change**: Can switch capture source without restarting

### Capture Settings
- **Multi-monitor Support**: Automatically detects all monitors
- **Window Detection**: Lists all visible application windows
- **Performance**: Optimized for smooth real-time display

---

## Navigation and Zoom

### Zoom Controls
- **Zoom In**: Click "+" button or press `Z`
- **Zoom Out**: Click "-" button or press `X`
- **Reset Zoom**: Click "100%" button or press `R`
- **Mouse Wheel**: Hold `Ctrl` and scroll to zoom in/out
- **Zoom Range**: 10% to 500%

### Panning
- **Mouse Drag**: Click and drag to pan around the image
- **Scroll Bars**: Use horizontal/vertical scroll bars when zoomed in

### Keyboard Navigation
- **Arrow Keys**: Pan the view when zoomed in
- **Home**: Return to top-left of image
- **End**: Go to bottom-right of image

---

## Analysis Mode

### Enabling Analysis Mode
1. Click "Toggle Analysis Mode" button
2. The interface will switch to professional analysis tools
3. Analysis overlays will become visible and interactive

### Analysis Tools

#### Note Tool
- **Purpose**: Add text annotations to specific points
- **Usage**: 
  1. Select "Note" from analysis tools
  2. Click anywhere on the image
  3. Enter your annotation text
  4. Click "OK"
- **Display**: Green circle with your text
- **Editing**: Double-click to edit existing notes

#### Ruler Tool
- **Purpose**: Measure distances between points
- **Usage**:
  1. Select "Ruler" from analysis tools
  2. Choose a color for your ruler
  3. Click and drag to create the measurement line
  4. Enter an optional note for the measurement
  5. Release to complete
- **Features**:
  - Custom colors for each ruler
  - Distance calculation in pixels
  - Optional text notes
  - Calibrated measurements (when grid is calibrated)

#### Region of Interest (ROI) Tool
- **Purpose**: Highlight and annotate specific areas
- **Usage**:
  1. Select "ROI" from analysis tools
  2. Click and drag to create a selection box
  3. Enter a note describing the region
  4. Release to complete
- **Features**:
  - Resizable selection boxes
  - Area calculation
  - Text annotations
  - Color-coded regions

### Managing Overlays
- **Access**: Click "Manage Overlays" button
- **Features**:
  - View all annotations in a table
  - Edit existing overlays
  - Delete individual overlays
  - Clear all overlays
  - Export overlays to file
- **Table Columns**:
  - **Type**: Note, Ruler, or ROI
  - **Position**: Coordinates on the image
  - **Details**: Text content or measurements
  - **Actions**: Edit/Delete buttons

---

## Measurement Grid

### Overview
The Measurement Grid is a professional floating tool for precise EEG measurements.

### Activating the Grid
- Click "Toggle Measurement Grid" button
- A semi-transparent grid will appear over the application
- The grid can be moved and resized

### Grid Features
- **Draggable**: Click and drag to move anywhere on screen
- **Resizable**: Drag edges or corners to change size
- **Semi-transparent**: Won't obstruct your view
- **Always on Top**: Stays visible over other applications

### Calibration
1. Click "Calibrate" button on the grid
2. Enter your calibration values:
   - **X-axis**: Pixels per unit (e.g., pixels per millisecond)
   - **Y-axis**: Pixels per unit (e.g., pixels per microvolt)
   - **Units**: Choose appropriate units (ms, µV, Hz, etc.)
3. Click "OK" to apply calibration

### Real-time Measurements
- **Live Display**: Grid shows current dimensions in real-world units
- **Format**: "Width × Height (calibrated units)"
- **Example**: "150.2ms × 45.8µV"

### Grid Settings
- **Line Color**: Customizable grid line color
- **Line Thickness**: Adjustable line width
- **Opacity**: Control transparency level
- **Auto-save**: Calibration settings are saved between sessions

---

## Keyboard Shortcuts

### File Operations
- `Ctrl+O`: Open file
- `Ctrl+S`: Save current view
- `Ctrl+Q`: Quit application

### Navigation
- `Z`: Zoom in
- `X`: Zoom out
- `R`: Reset zoom to 100%
- `Page Up`: Previous page (PDFs)
- `Page Down`: Next page (PDFs)
- `Home`: Go to top-left
- `End`: Go to bottom-right
- `Ctrl + Mouse Wheel`: Zoom in/out

### Analysis Tools
- `A`: Toggle Analysis Mode
- `M`: Toggle Measurement Grid
- `T`: Toggle Trace Enhancement
- `N`: Toggle Note Tool
- `L`: Toggle Ruler Tool
- `B`: Toggle ROI Tool

### Live Capture
- `L`: Toggle Live Capture
- `C`: Capture single screen shot

### View Controls
- `F`: Toggle fullscreen
- `Ctrl+0`: Fit to window
- `Ctrl+1`: Actual size

---

## Settings and Preferences

### Theme
- **Dark Theme**: Optimized for EEG analysis (default)
- **High Contrast**: Enhanced visibility for professional use
- **Custom Colors**: Adjustable interface colors

### Performance
- **Capture Quality**: Adjustable for performance vs. quality
- **Update Rate**: Configurable live capture refresh rate
- **Memory Management**: Automatic cleanup of old captures

### Session Management
- **Auto-save**: Settings and overlays saved automatically
- **Session Restore**: Previous state restored on startup
- **Position Memory**: Window position and size remembered

---

## Troubleshooting

### Common Issues

#### Application Won't Start
- **Check Python Installation**: Ensure Python 3.7+ is installed
- **Install Dependencies**: Run `pip install -r requirements.txt`
- **Check Permissions**: Ensure write access to the application directory

#### Live Capture Not Working
- **Check Dependencies**: Ensure `mss` or `Pillow` is installed
- **Monitor Detection**: Verify monitor configuration
- **Window Permissions**: Some applications may block capture

#### Analysis Tools Not Visible
- **Enable Analysis Mode**: Click "Toggle Analysis Mode" button
- **Check Zoom Level**: Tools may be hidden if zoomed out too far
- **Refresh Display**: Try zooming in/out to refresh the view

#### Measurement Grid Issues
- **Grid Not Visible**: Click "Toggle Measurement Grid" button
- **Calibration Problems**: Reset calibration in the grid dialog
- **Position Lost**: Grid position is saved automatically

#### Performance Issues
- **Reduce Capture Quality**: Lower the capture resolution
- **Close Other Applications**: Free up system resources
- **Check Available Memory**: Ensure sufficient RAM

### Getting Help
- **Error Messages**: Check the console output for detailed error information
- **Log Files**: Application logs are saved in the output directory
- **Settings Reset**: Delete the settings file to restore defaults

---

## Professional Tips

### EEG Analysis Workflow
1. **Load Your Data**: Open EEG images or PDFs
2. **Enable Analysis Mode**: Switch to professional tools
3. **Add Annotations**: Use notes, rulers, and ROIs to mark important features
4. **Use Measurement Grid**: For precise quantitative measurements
5. **Export Results**: Save your analysis with overlays

### Best Practices
- **Regular Saves**: Export your work frequently
- **Organized Annotations**: Use consistent naming for your overlays
- **Calibration**: Always calibrate the measurement grid for accurate readings
- **Documentation**: Use notes to document your analysis process

### Keyboard Efficiency
- Learn the keyboard shortcuts for faster workflow
- Use `Ctrl+Mouse Wheel` for quick zoom adjustments
- Combine analysis tools with keyboard navigation

---

## Version Information
- **Current Version**: 2.0 Professional Edition
- **Last Updated**: 2024
- **Compatibility**: Windows 10/11, Python 3.7+
- **Dependencies**: PyQt5, OpenCV, PyMuPDF, mss/Pillow

For technical support or feature requests, please refer to the project documentation or contact the development team. 