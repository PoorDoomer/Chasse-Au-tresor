# ROI Analyzer with Multiple Target Images

This application allows you to analyze Regions of Interest (ROIs) in images, perform OCR text extraction, and detect target images within the ROIs.


### Key Features:

- Draw multiple Regions of Interest (ROIs) on any image
- Perform OCR text extraction in each ROI
- Add multiple target images with descriptive labels
- Detect target images in each ROI and include descriptions in output
- Save and load sets of target images
- Export analysis results to JSON

## Requirements

- Python 3.6+
- OpenCV
- Tesseract OCR
- NumPy
- Pillow (PIL)

## Installation

1. Install Python 3.6 or higher
2. Install Tesseract OCR from https://github.com/UB-Mannheim/tesseract/wiki
3. Add Tesseract to your PATH or uncomment and edit the line in `script.py`:
   ```python
   # pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
   ```
4. Install required Python packages:
   ```
   pip install opencv-python numpy pytesseract pillow
   ```

## How to Use

1. Run the application: `python script.py`
2. Click "Load Image" to open your main image
3. Draw ROIs by clicking and dragging on the image
4. Right-click an ROI to select it (turns green)
5. Click "Manage Target Images" to add target images with descriptions:
   - In the Target Manager window, click "Add Target" to select an image
   - Enter a descriptive name for the target (e.g., "arrow_left")
   - Add as many target images as needed
   - Use the "Save Target Set" option to save your target set for future use
6. Click "Analyze ROIs" to perform OCR and detect target images
7. Results will show extracted text and any detected target images with their descriptions
8. Use "Save Results" to export analysis as JSON

## Target Manager Usage

The Target Manager allows you to:

1. **Add Target Images**: Select an image file and give it a descriptive name
2. **Edit Descriptions**: Select a target and click "Edit Description"
3. **Remove Targets**: Select a target and click "Remove Target"
4. **Save/Load Target Sets**: Save your collection of target images for reuse

## Output Format

The JSON output includes:
- Timestamp
- Image file name
- OCR language
- Match threshold 
- Target image descriptions
- Results for each ROI, including:
  - Coordinates
  - Extracted text
  - Detected target images with confidence scores and descriptions

## Testing

Run the included tests to verify functionality:
```
python test_target_manager.py 