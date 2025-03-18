# Real-Time Window Monitor for ROI Analyzer

This functionality allows you to monitor any application window in real-time, apply your predefined ROIs, and perform automated analysis including OCR and template matching.

## Requirements

- Windows OS (required for window capture)
- Python 3.8+
- ROI Analyzer with configured ROIs

## Additional Dependencies

These are automatically installed when you run `pip install -r requirements.txt`:
- pywin32 (for Windows GUI access)
- pygetwindow (for window management)

## Features

- **Window Selection**: Select any visible window on your system to monitor
- **Real-time Monitoring**: Capture window content at configurable intervals
- **ROI Analysis**: Apply your pre-configured ROIs to the captured window 
- **OCR Recognition**: Extract text from ROIs
- **Target Image Detection**: Detect target images within ROIs
- **Debug Mode**: Save captures and analysis results for debugging
- **Background Operation**: Monitor windows even when they're not in focus

## How to Use

1. Start the ROI Analyzer application
2. Set up your ROIs on a reference image
3. Click "Real-Time Monitor" button
4. In the monitor window:
   - Click "Select Window" to choose a window to monitor
   - Set your desired capture interval (in seconds)
   - Click "Start Monitoring" to begin continuous monitoring
   - Or use "Capture Once" for a single capture

## Monitoring Options

- **Capture Interval**: Time between captures (0.1-10 seconds)
- **Debug Mode**: Enable to save captures and analysis results to the `monitor_output` directory

## Troubleshooting

- If no windows appear in the selection list, try clicking "Refresh Window List"
- If capture fails, ensure the target window is not minimized
- For OCR issues, try adjusting ROI positions or using the "Numbers Only Mode" in main settings

## Notes

- For the best results, define your ROIs on a screenshot of the target application first
- Performance may vary depending on the window size and complexity
- Some applications with hardware acceleration may not be captured correctly 