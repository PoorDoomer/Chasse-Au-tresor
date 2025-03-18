import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
import logging
import os

class JSONManager:
    """Manager for JSON output format and fields"""
    
    def __init__(self, parent):
        self.parent = parent
        
        # Initialize JSON output settings
        self.output_settings = {
            # General metadata
            "include_metadata": tk.BooleanVar(value=True),
            "include_timestamp": tk.BooleanVar(value=True),
            "include_image_path": tk.BooleanVar(value=True),
            "include_settings": tk.BooleanVar(value=True),
            
            # ROI information
            "include_coordinates": tk.BooleanVar(value=True),
            "include_roi_name": tk.BooleanVar(value=True),
            "include_template_info": tk.BooleanVar(value=True),
            
            # Analysis results
            "include_ocr_text": tk.BooleanVar(value=True),
            "include_target_matches": tk.BooleanVar(value=True),
            "include_confidence_scores": tk.BooleanVar(value=True),
            
            # Error handling
            "include_errors": tk.BooleanVar(value=True)
        }
        
        # Create window
        self.window = tk.Toplevel(parent)
        self.window.title("JSON Output Manager")
        self.window.geometry("650x700")
        self.window.protocol("WM_DELETE_WINDOW", self.hide_window)
        
        # Setup UI
        self.setup_ui()
        self.window.withdraw()  # Initially hidden
    
    def setup_ui(self):
        # Main frame with padding
        main_frame = ttk.Frame(self.window, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title label
        title_label = ttk.Label(main_frame, text="JSON Output Manager", 
                             font=("Segoe UI", 14, "bold"))
        title_label.pack(pady=(0, 10))
        
        # Description
        description = ttk.Label(main_frame, 
                             text="Configure which fields to include in the JSON output.", 
                             wraplength=600)
        description.pack(pady=(0, 15))
        
        # Settings frame with checkboxes
        settings_frame = ttk.LabelFrame(main_frame, text="Output Fields")
        settings_frame.pack(fill=tk.BOTH, expand=False, pady=10)
        
        # Create three columns for better organization
        col1 = ttk.Frame(settings_frame)
        col1.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        col2 = ttk.Frame(settings_frame)
        col2.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        col3 = ttk.Frame(settings_frame)
        col3.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Column 1: General metadata
        ttk.Label(col1, text="General Metadata", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W)
        
        ttk.Checkbutton(col1, text="Include Metadata Section", 
                      variable=self.output_settings["include_metadata"]).pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(col1, text="Timestamp", 
                      variable=self.output_settings["include_timestamp"]).pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(col1, text="Image Path", 
                      variable=self.output_settings["include_image_path"]).pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(col1, text="Settings (OCR, threshold)", 
                      variable=self.output_settings["include_settings"]).pack(anchor=tk.W, pady=2)
        
        # Column 2: ROI information
        ttk.Label(col2, text="ROI Information", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W)
        
        ttk.Checkbutton(col2, text="Coordinates", 
                      variable=self.output_settings["include_coordinates"]).pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(col2, text="ROI Names", 
                      variable=self.output_settings["include_roi_name"]).pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(col2, text="Template Information", 
                      variable=self.output_settings["include_template_info"]).pack(anchor=tk.W, pady=2)
        
        # Column 3: Analysis results
        ttk.Label(col3, text="Analysis Results", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W)
        
        ttk.Checkbutton(col3, text="OCR Text", 
                      variable=self.output_settings["include_ocr_text"]).pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(col3, text="Target Matches", 
                      variable=self.output_settings["include_target_matches"]).pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(col3, text="Confidence Scores", 
                      variable=self.output_settings["include_confidence_scores"]).pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(col3, text="Error Messages", 
                      variable=self.output_settings["include_errors"]).pack(anchor=tk.W, pady=2)
        
        # Select/Deselect All buttons
        buttons_frame = ttk.Frame(settings_frame)
        buttons_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(buttons_frame, text="Select All", 
                 command=self.select_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Deselect All", 
                 command=self.deselect_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Reset to Default", 
                 command=self.reset_defaults).pack(side=tk.LEFT, padx=5)
        
        # JSON preview area
        preview_frame = ttk.LabelFrame(main_frame, text="JSON Preview")
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.preview_text = scrolledtext.ScrolledText(preview_frame, wrap=tk.WORD, 
                                                   height=15, font=("Consolas", 10))
        self.preview_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Update preview when any variable changes
        for var in self.output_settings.values():
            var.trace_add("write", self.update_preview)
        
        # Close and Apply buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(button_frame, text="Apply", 
                 command=self.apply_settings).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Close", 
                 command=self.hide_window).pack(side=tk.RIGHT, padx=5)
        
        # Update preview initially
        self.update_preview()
    
    def show_window(self):
        """Show the JSON manager window"""
        self.window.deiconify()
        self.window.lift()
        self.update_preview()
    
    def hide_window(self):
        """Hide the window instead of destroying it"""
        self.window.withdraw()
    
    def select_all(self):
        """Select all output options"""
        for var in self.output_settings.values():
            var.set(True)
    
    def deselect_all(self):
        """Deselect all output options"""
        for var in self.output_settings.values():
            var.set(False)
    
    def reset_defaults(self):
        """Reset to default settings"""
        defaults = {
            "include_metadata": True,
            "include_timestamp": True,
            "include_image_path": True,
            "include_settings": True,
            "include_coordinates": True,
            "include_roi_name": True,
            "include_template_info": True,
            "include_ocr_text": True,
            "include_target_matches": True,
            "include_confidence_scores": True,
            "include_errors": True
        }
        
        for key, value in defaults.items():
            self.output_settings[key].set(value)
    
    def update_preview(self, *args):
        """Update the JSON preview based on current settings"""
        # Create sample data
        sample_data = self.create_sample_data()
        
        # Format as JSON
        json_str = json.dumps(sample_data, indent=2)
        
        # Update the preview
        self.preview_text.delete(1.0, tk.END)
        self.preview_text.insert(tk.END, json_str)
    
    def create_sample_data(self):
        """Create sample data structure based on current settings"""
        data = {}
        
        # Add metadata if enabled
        if self.output_settings["include_metadata"].get():
            metadata = {}
            
            if self.output_settings["include_timestamp"].get():
                metadata["timestamp"] = "2025-03-17T12:34:56"
            
            if self.output_settings["include_image_path"].get():
                metadata["image_path"] = "C:/example/image.png"
            
            if self.output_settings["include_settings"].get():
                metadata["settings"] = {
                    "ocr_language": "eng",
                    "match_threshold": 0.7,
                    "match_method": 5
                }
            
            if metadata:
                data["metadata"] = metadata
        
        # Add ROI data
        roi_data = []
        
        # Sample ROI 1
        roi1 = {"roi_num": 1}
        
        if self.output_settings["include_roi_name"].get():
            roi1["name"] = "Sample ROI 1"
        
        if self.output_settings["include_coordinates"].get():
            roi1["coordinates"] = [10, 20, 100, 50]
        
        if self.output_settings["include_template_info"].get():
            roi1["template_info"] = {
                "template_name": "Sample Template",
                "roi_type": "Fixed"
            }
        
        if self.output_settings["include_ocr_text"].get():
            roi1["ocr_text"] = "Sample text from ROI 1"
        
        if self.output_settings["include_target_matches"].get():
            if self.output_settings["include_confidence_scores"].get():
                roi1["target_matches"] = [
                    {"description": "Target 1", "confidence": 0.95}
                ]
            else:
                roi1["target_matches"] = [
                    {"description": "Target 1"}
                ]
        
        # Sample ROI 2 with error
        roi2 = {"roi_num": 2}
        
        if self.output_settings["include_roi_name"].get():
            roi2["name"] = "Sample ROI 2"
        
        if self.output_settings["include_coordinates"].get():
            roi2["coordinates"] = [150, 30, 200, 70]
        
        if self.output_settings["include_ocr_text"].get():
            roi2["ocr_text"] = None
        
        if self.output_settings["include_errors"].get():
            roi2["ocr_error"] = "Failed to process small ROI"
        
        # Add ROIs to the data
        roi_data.append(roi1)
        roi_data.append(roi2)
        
        data["results"] = roi_data
        
        return data
    
    def apply_settings(self):
        """Apply the current settings and hide the window"""
        messagebox.showinfo("Settings Applied", "JSON output settings have been applied.")
        self.hide_window()
    
    def filter_json_output(self, data):
        """Filter the JSON output based on current settings"""
        filtered_data = {}
        
        # Handle metadata section
        if "metadata" in data and self.output_settings["include_metadata"].get():
            metadata = {}
            
            if self.output_settings["include_timestamp"].get() and "timestamp" in data["metadata"]:
                metadata["timestamp"] = data["metadata"]["timestamp"]
            
            if self.output_settings["include_image_path"].get() and "image_path" in data["metadata"]:
                metadata["image_path"] = data["metadata"]["image_path"]
            
            if self.output_settings["include_settings"].get() and "settings" in data["metadata"]:
                metadata["settings"] = data["metadata"]["settings"]
            
            if metadata:
                filtered_data["metadata"] = metadata
        
        # Handle results section
        if "results" in data:
            filtered_results = []
            
            for roi in data["results"]:
                filtered_roi = {"roi_num": roi.get("roi_num")}
                
                if self.output_settings["include_roi_name"].get() and "name" in roi:
                    filtered_roi["name"] = roi["name"]
                
                if self.output_settings["include_coordinates"].get() and "coordinates" in roi:
                    filtered_roi["coordinates"] = roi["coordinates"]
                
                if self.output_settings["include_template_info"].get() and "template_info" in roi:
                    filtered_roi["template_info"] = roi["template_info"]
                
                if self.output_settings["include_ocr_text"].get() and "ocr_text" in roi:
                    filtered_roi["ocr_text"] = roi["ocr_text"]
                
                if self.output_settings["include_target_matches"].get() and "target_matches" in roi:
                    if self.output_settings["include_confidence_scores"].get():
                        filtered_roi["target_matches"] = roi["target_matches"]
                    else:
                        # Remove confidence scores
                        filtered_matches = []
                        for match in roi["target_matches"]:
                            filtered_match = {"description": match.get("description")}
                            filtered_matches.append(filtered_match)
                        filtered_roi["target_matches"] = filtered_matches
                
                if self.output_settings["include_errors"].get():
                    if "ocr_error" in roi:
                        filtered_roi["ocr_error"] = roi["ocr_error"]
                    if "target_match_error" in roi:
                        filtered_roi["target_match_error"] = roi["target_match_error"]
                
                filtered_results.append(filtered_roi)
            
            filtered_data["results"] = filtered_results
        
        return filtered_data 