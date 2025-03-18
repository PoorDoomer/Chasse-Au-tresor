import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox, ttk
import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageTk
import logging
import os
import datetime
import json
import asyncio
import aiohttp
from target_manager import TargetImageManager, check_target_matches
from roi_manager import ROIManager
from template_manager import TemplateManager
from json_manager import JSONManager

# Configure logging
log_directory = "logs"
if not os.path.exists(log_directory):
    os.makedirs(log_directory)

log_filename = f"roi_analyzer_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
log_path = os.path.join(log_directory, log_filename)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_path),
        logging.StreamHandler()
    ]
)

class ModernScrollableFrame(ttk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        # Create canvas and scrollbar
        self.canvas = tk.Canvas(self)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        # Configure canvas
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # Pack scrollbar and canvas
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        
        # Bind mouse wheel
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        
        # Bind resize event
        self.bind('<Configure>', self._on_frame_configure)
    
    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    def _on_frame_configure(self, event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

class ROIAnalyzerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ROI Analyzer")
        self.root.geometry("1400x900")
        
        # Initialize variables
        self.image_path = None
        self.target_image_path = None
        self.image = None
        self.image_display = None
        self.displayed_image = None
        self.roi_rectangles = []
        self.current_rectangle = None
        self.drawing = False
        self.start_x, self.start_y = 0, 0
        self.selected_roi_index = None
        
        # OCR and template matching settings
        self.ocr_lang = tk.StringVar(value="eng")
        self.match_method = tk.IntVar(value=cv2.TM_CCOEFF_NORMED)
        self.match_threshold = tk.DoubleVar(value=0.7)
        self.numbers_only = tk.BooleanVar(value=False)
        self.debug_preprocessing = tk.BooleanVar(value=False)
        
        # Initialize managers
        self.target_manager = TargetImageManager(self.root)
        self.roi_manager = None
        self.template_manager = None
        self.json_manager = None
        
        # Set up the UI
        self.setup_ui()
        
        # Apply modern styling
        self.apply_styling()
        
        # Initialize JSON Manager after ROI manager
        self.json_manager = JSONManager(self.root)
        
        # No need to initialize API client here - will create on demand
        self.api_client = None
        
        logging.info("Application started")
    
    def setup_api_client(self):
        """Initialize the API client for real-time updates - not used directly"""
        # This method is kept for backward compatibility but not used
        pass
    
    async def send_update(self, data):
        """Send update to the API server"""
        try:
            # Create a new client session for this request
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.post('http://localhost:8000/update', json=data, timeout=1.0) as response:
                        return await response.json()
                except aiohttp.ClientError as e:
                    logging.warning(f"API server not available: {str(e)}")
                    return None
        except Exception as e:
            logging.error(f"Error sending update to API: {str(e)}")
            return None

    def send_update_sync(self, data):
        """Synchronous wrapper for send_update"""
        try:
            asyncio.run(self.send_update(data))
        except Exception as e:
            logging.error(f"Error in send_update_sync: {str(e)}")
    
    def apply_styling(self):
        """Apply modern styling to the UI"""
        style = ttk.Style()
        
        # Configure colors
        style.configure("TFrame", background="#f0f0f0")
        style.configure("TLabel", background="#f0f0f0", font=("Segoe UI", 10))
        
        # Modern button style
        style.configure("TButton", 
                       font=("Segoe UI", 10, "bold"),
                       padding=5,
                       background="#0078d7",
                       foreground="black")
        
        # Hover effects
        style.map("TButton",
                 foreground=[("active", "black"), ("pressed", "black")],
                 background=[("active", "#00afff"), ("pressed", "#0065b8")])
        
        # Modern LabelFrame style
        style.configure("TLabelframe", 
                       background="#f0f0f0",
                       font=("Segoe UI", 10, "bold"))
        style.configure("TLabelframe.Label", 
                       background="#f0f0f0",
                       font=("Segoe UI", 10, "bold"))
        
        # Modern Combobox style
        style.configure("TCombobox",
                       font=("Segoe UI", 10),
                       background="white",
                       fieldbackground="white",
                       selectbackground="#0078d7",
                       selectforeground="white")
        
        # Modern Scale style
        style.configure("Horizontal.TScale",
                       background="#f0f0f0")
        
        # Modern Treeview style
        style.configure("Treeview",
                       background="white",
                       fieldbackground="white",
                       foreground="black",
                       rowheight=25,
                       font=("Segoe UI", 9))
        style.map("Treeview",
                 background=[("selected", "#0078d7")],
                 foreground=[("selected", "white")])
        
        # Modern Treeview headings
        style.configure("Treeview.Heading",
                       background="#e0e0e0",
                       foreground="black",
                       font=("Segoe UI", 10, "bold"))
        
        # Custom styles for grouped buttons
        style.configure("FileButton.TButton", 
                       background="#4CAF50",
                       foreground="black")
        style.map("FileButton.TButton",
                 background=[("active", "#6FCF7C"), ("pressed", "#3B8E41")])
        
        style.configure("ROIButton.TButton", 
                       background="#2196F3",
                       foreground="black")
        style.map("ROIButton.TButton",
                 background=[("active", "#64B5F6"), ("pressed", "#1976D2")])
        
        style.configure("TargetButton.TButton", 
                       background="#FF9800",
                       foreground="black")
        style.map("TargetButton.TButton",
                 background=[("active", "#FFB74D"), ("pressed", "#F57C00")])
        
        style.configure("AnalyzeButton.TButton", 
                       background="#E91E63",
                       foreground="black")
        style.map("AnalyzeButton.TButton",
                 background=[("active", "#F06292"), ("pressed", "#C2185B")])
    
    def setup_ui(self):
        # Create main scrollable frame
        self.main_frame = ModernScrollableFrame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title with gradient-like effect
        title_frame = ttk.Frame(self.main_frame.scrollable_frame)
        title_frame.pack(fill=tk.X, pady=(0, 20))
        
        title_label = ttk.Label(title_frame, 
                              text="ROI Analyzer", 
                              font=("Segoe UI", 20, "bold"),
                              foreground="#0078d7")
        title_label.pack(side=tk.LEFT, padx=(10, 0))
        
        version_label = ttk.Label(title_frame,
                                text="v2.0",
                                font=("Segoe UI", 10),
                                foreground="#666666")
        version_label.pack(side=tk.LEFT, padx=(5, 0), pady=(8, 0))
        
        # Create a container for the main content
        content_frame = ttk.Frame(self.main_frame.scrollable_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left panel for image and ROI selection
        left_panel = ttk.Frame(content_frame, width=800)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # Canvas for image display with border
        self.canvas_frame = ttk.LabelFrame(left_panel, text="Image View")
        self.canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(self.canvas_frame, bg="white", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Mouse events for drawing ROIs
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_move)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        self.canvas.bind("<ButtonPress-3>", self.on_right_click)
        
        # Initialize ROI Manager after canvas creation
        self.roi_manager = ROIManager(self.root, self.canvas, self.on_roi_change)
        
        # Initialize Template Manager
        self.template_manager = TemplateManager(self.root, self.roi_manager)
        
        # Button panel with modern styling
        button_panel = ttk.Frame(left_panel)
        button_panel.pack(fill=tk.X, pady=10)
        
        # Create button groups
        file_buttons = ttk.Frame(button_panel)
        file_buttons.pack(side=tk.LEFT, padx=5)
        
        self.load_btn = ttk.Button(file_buttons, text="Load Image", 
                                 command=self.load_image, style="FileButton.TButton")
        self.load_btn.pack(side=tk.LEFT, padx=5)
        
        self.save_results_btn = ttk.Button(file_buttons, text="Save Results", 
                                         command=self.save_results, style="FileButton.TButton")
        self.save_results_btn.pack(side=tk.LEFT, padx=5)
        
        roi_buttons = ttk.Frame(button_panel)
        roi_buttons.pack(side=tk.LEFT, padx=5)
        
        self.manage_rois_btn = ttk.Button(roi_buttons, text="Manage ROIs", 
                                         command=self.roi_manager.show_window,
                                         style="ROIButton.TButton")
        self.manage_rois_btn.pack(side=tk.LEFT, padx=5)
        
        self.delete_roi_btn = ttk.Button(roi_buttons, text="Delete Selected ROI", 
                                        command=self.delete_selected_roi,
                                        style="ROIButton.TButton")
        self.delete_roi_btn.pack(side=tk.LEFT, padx=5)
        
        self.clear_roi_btn = ttk.Button(roi_buttons, text="Clear All ROIs", 
                                       command=self.clear_rois,
                                       style="ROIButton.TButton")
        self.clear_roi_btn.pack(side=tk.LEFT, padx=5)
        
        # Template buttons
        template_buttons = ttk.Frame(button_panel)
        template_buttons.pack(side=tk.LEFT, padx=5)
        
        self.manage_templates_btn = ttk.Button(template_buttons, text="Manage Templates",
                                             command=self.template_manager.show_window,
                                             style="ROIButton.TButton")
        self.manage_templates_btn.pack(side=tk.LEFT, padx=5)
        
        self.create_template_btn = ttk.Button(template_buttons, text="Create Template",
                                            command=self.template_manager.create_new_template,
                                            style="ROIButton.TButton")
        self.create_template_btn.pack(side=tk.LEFT, padx=5)
        
        target_buttons = ttk.Frame(button_panel)
        target_buttons.pack(side=tk.LEFT, padx=5)
        
        self.manage_targets_btn = ttk.Button(target_buttons, text="Manage Target Images", 
                                            command=self.target_manager.show_window,
                                            style="TargetButton.TButton")
        self.manage_targets_btn.pack(side=tk.LEFT, padx=5)
        
        self.analyze_btn = ttk.Button(target_buttons, text="Analyze ROIs", 
                                     command=self.analyze_rois,
                                     style="AnalyzeButton.TButton")
        self.analyze_btn.pack(side=tk.LEFT, padx=5)
        
        # Configure JSON Button
        self.json_config_btn = ttk.Button(target_buttons, text="Configure JSON", 
                                        command=self.json_manager.show_window,
                                        style="AnalyzeButton.TButton")
        self.json_config_btn.pack(side=tk.LEFT, padx=5)
        
        # Real-time monitoring button
        self.realtime_btn = ttk.Button(target_buttons, text="Real-Time Monitor",
                                      command=self.open_realtime_monitor,
                                      style="AnalyzeButton.TButton")
        self.realtime_btn.pack(side=tk.LEFT, padx=5)
        
        # Settings panel with modern styling
        settings_panel = ttk.LabelFrame(left_panel, text="Settings")
        settings_panel.pack(fill=tk.X, pady=10)
        
        # OCR language selection
        ocr_frame = ttk.Frame(settings_panel)
        ocr_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(ocr_frame, text="OCR Language:").pack(side=tk.LEFT, padx=5)
        ocr_langs = ["eng", "fra", "deu", "spa", "ita", "jpn", "kor", "chi_sim"]
        ocr_dropdown = ttk.Combobox(ocr_frame, textvariable=self.ocr_lang, 
                                  values=ocr_langs, state="readonly")
        ocr_dropdown.pack(side=tk.LEFT, padx=5)
        
        # Template matching method
        match_frame = ttk.Frame(settings_panel)
        match_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(match_frame, text="Matching Method:").pack(side=tk.LEFT, padx=5)
        methods = [
            ("TM_CCOEFF_NORMED", cv2.TM_CCOEFF_NORMED),
            ("TM_CCORR_NORMED", cv2.TM_CCORR_NORMED),
            ("TM_SQDIFF_NORMED", cv2.TM_SQDIFF_NORMED)
        ]
        
        method_dropdown = ttk.Combobox(match_frame, values=[m[0] for m in methods], 
                                     state="readonly")
        method_dropdown.current(0)
        method_dropdown.pack(side=tk.LEFT, padx=5)
        method_dropdown.bind("<<ComboboxSelected>>", lambda e: self.match_method.set(
            methods[method_dropdown.current()][1]))
        
        # Threshold slider
        ttk.Label(match_frame, text="Match Threshold:").pack(side=tk.LEFT, padx=(15, 5))
        threshold_slider = ttk.Scale(match_frame, from_=0.1, to=1.0, 
                                   variable=self.match_threshold, length=100)
        threshold_slider.pack(side=tk.LEFT, padx=5)
        threshold_label = ttk.Label(match_frame, 
                                  textvariable=tk.StringVar(
                                      value=lambda: f"{self.match_threshold.get():.2f}"))
        threshold_label.pack(side=tk.LEFT, padx=5)
        
        # Update threshold label when slider moves
        def update_threshold_label(*args):
            threshold_label.config(text=f"{self.match_threshold.get():.2f}")
        
        self.match_threshold.trace_add("write", update_threshold_label)
        
        # Add OCR-specific settings
        ocr_settings_frame = ttk.Frame(settings_panel)
        ocr_settings_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Numbers only mode checkbox
        numbers_check = ttk.Checkbutton(
            ocr_settings_frame,
            text="Numbers Only Mode (Improved for small digits)",
            variable=self.numbers_only
        )
        numbers_check.pack(anchor=tk.W)
        
        # Debug preprocessing checkbox
        debug_check = ttk.Checkbutton(
            ocr_settings_frame,
            text="Debug preprocessing (save intermediate images)",
            variable=self.debug_preprocessing
        )
        debug_check.pack(anchor=tk.W)
        
        # Right panel for results and logs
        right_panel = ttk.Frame(content_frame, width=400)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(10, 0))
        
        # Results section with improved styling
        results_frame = ttk.LabelFrame(right_panel, text="Results")
        results_frame.pack(fill=tk.BOTH, expand=True)
        
        # Add JSON view
        json_frame = ttk.LabelFrame(results_frame, text="JSON Output")
        json_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.json_text = scrolledtext.ScrolledText(json_frame, wrap=tk.WORD,
                                                 font=("Consolas", 10),
                                                 background="#ffffff",
                                                 foreground="#000000",
                                                 height=10)
        self.json_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Add results text
        self.results_text = scrolledtext.ScrolledText(results_frame, wrap=tk.WORD,
                                                    font=("Consolas", 10),
                                                    background="#ffffff",
                                                    foreground="#000000")
        self.results_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Log section with improved styling
        log_frame = ttk.LabelFrame(right_panel, text="Logs")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD,
                                                font=("Consolas", 9),
                                                background="#f0f0f0",
                                                foreground="#333333")
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Status bar at the bottom
        status_frame = ttk.Frame(self.main_frame.scrollable_frame)
        status_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(status_frame, textvariable=self.status_var,
                                font=("Segoe UI", 9),
                                foreground="#666666")
        status_label.pack(side=tk.LEFT, padx=5, pady=2)
        
        # Custom log handler to display logs in the UI
        log_handler = TextHandler(self.log_text)
        log_handler.setLevel(logging.INFO)
        log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        log_handler.setFormatter(log_formatter)
        logging.getLogger().addHandler(log_handler)
    
    def on_roi_change(self, roi_index=None, delete=False):
        """Handle ROI changes from the ROI Manager"""
        if delete and roi_index is not None:
            # Delete the ROI
            roi = self.roi_rectangles[roi_index]
            self.canvas.delete(roi['canvas_rect'])
            self.canvas.delete(roi['text_id'])
            del self.roi_rectangles[roi_index]
            self.update_roi_numbers()
        elif roi_index is not None:
            # Select the ROI on canvas
            self.selected_roi_index = roi_index
            for i, roi in enumerate(self.roi_rectangles):
                if i == roi_index:
                    self.canvas.itemconfig(roi['canvas_rect'], outline="green", width=3)
                    self.canvas.itemconfig(roi['text_id'], fill="green")
                else:
                    self.canvas.itemconfig(roi['canvas_rect'], outline="red", width=2)
                    self.canvas.itemconfig(roi['text_id'], fill="red")
        
        # Update ROI Manager data
        self.roi_manager.set_roi_data(self.roi_rectangles)
    
    def load_image(self):
        self.image_path = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp *.tif *.tiff")]
        )
        
        if not self.image_path:
            return
        
        logging.info(f"Loading image: {self.image_path}")
        
        # Load the image
        self.image = cv2.imread(self.image_path)
        if self.image is None:
            logging.error("Failed to load image")
            return
        
        # Convert BGR to RGB for display
        rgb_image = cv2.cvtColor(self.image, cv2.COLOR_BGR2RGB)
        
        # Resize the image to fit the canvas while maintaining aspect ratio
        height, width = rgb_image.shape[:2]
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        # If canvas size is not determined yet (window not fully initialized)
        if canvas_width <= 1:
            canvas_width = 800
            canvas_height = 600
        
        # Calculate scaling factor
        scale = min(canvas_width / width, canvas_height / height)
        new_width = int(width * scale)
        new_height = int(height * scale)
        
        self.displayed_image = cv2.resize(rgb_image, (new_width, new_height))
        self.scale_factor = scale  # Store scale factor for ROI calculations
        
        # Convert to PhotoImage for tkinter
        self.image_display = ImageTk.PhotoImage(image=Image.fromarray(self.displayed_image))
        
        # Update canvas
        self.canvas.config(width=new_width, height=new_height)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.image_display)
        
        # Clear ROIs when loading a new image
        self.roi_rectangles = []
        self.selected_roi_index = None
        
        # Update ROI Manager
        self.roi_manager.set_roi_data(self.roi_rectangles)
        
        logging.info("Image loaded successfully")
    
    def on_mouse_down(self, event):
        if self.image is None:
            return
        
        self.drawing = True
        self.start_x, self.start_y = event.x, event.y
        
        # Start drawing a rectangle
        self.current_rectangle = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y,
            outline="red", width=2
        )
    
    def on_mouse_move(self, event):
        if not self.drawing:
            return
        
        # Update the rectangle as mouse moves
        self.canvas.coords(self.current_rectangle, self.start_x, self.start_y, event.x, event.y)
    
    def on_mouse_up(self, event):
        if not self.drawing:
            return
        
        self.drawing = False
        
        # Get coordinates
        end_x, end_y = event.x, event.y
        
        # Ensure the rectangle has some size
        if abs(self.start_x - end_x) > 5 and abs(self.start_y - end_y) > 5:
            # Convert to the original image coordinates (accounting for scaling)
            original_start_x = int(self.start_x / self.scale_factor)
            original_start_y = int(self.start_y / self.scale_factor)
            original_end_x = int(end_x / self.scale_factor)
            original_end_y = int(end_y / self.scale_factor)
            
            # Store ROI coordinates as (x1, y1, x2, y2)
            roi_num = len(self.roi_rectangles) + 1
            self.roi_rectangles.append({
                'canvas_coords': (self.start_x, self.start_y, end_x, end_y),
                'original_coords': (original_start_x, original_start_y, original_end_x, original_end_y),
                'canvas_rect': self.current_rectangle,
                'roi_num': roi_num,
                'text_id': None  # Will store the ID of the text object
            })
            
            # Add ROI number to the rectangle
            text_x = min(self.start_x, end_x) + 5
            text_y = min(self.start_y, end_y) + 5
            text_id = self.canvas.create_text(text_x, text_y, text=f"ROI {roi_num}", 
                                            fill="red", anchor=tk.NW)
            
            # Store the text ID
            self.roi_rectangles[-1]['text_id'] = text_id
            
            # Update ROI Manager
            self.roi_manager.set_roi_data(self.roi_rectangles)
            
            logging.info(f"ROI {roi_num} selected: {original_start_x}, {original_start_y}, {original_end_x}, {original_end_y}")
        else:
            # If the rectangle is too small, remove it
            self.canvas.delete(self.current_rectangle)
    
    def on_right_click(self, event):
        """Handle right-click to select an ROI"""
        if not self.roi_rectangles:
            return
        
        # Deselect previous selection
        if self.selected_roi_index is not None:
            old_roi = self.roi_rectangles[self.selected_roi_index]
            self.canvas.itemconfig(old_roi['canvas_rect'], outline="red", width=2)
            self.canvas.itemconfig(old_roi['text_id'], fill="red")
        
        # Find if the click is inside any ROI
        for i, roi in enumerate(self.roi_rectangles):
            x1, y1, x2, y2 = roi['canvas_coords']
            x1, x2 = min(x1, x2), max(x1, x2)
            y1, y2 = min(y1, y2), max(y1, y2)
            
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                # Highlight selected ROI
                self.canvas.itemconfig(roi['canvas_rect'], outline="green", width=3)
                self.canvas.itemconfig(roi['text_id'], fill="green")
                self.selected_roi_index = i
                
                # Update ROI Manager selection
                self.roi_manager.roi_list.selection_set(str(roi['roi_num']))
                
                logging.info(f"ROI {roi['roi_num']} selected")
                return
        
        # If click is not in any ROI, clear selection
        self.selected_roi_index = None
        self.roi_manager.roi_list.selection_remove(
            self.roi_manager.roi_list.selection())
    
    def delete_selected_roi(self):
        """Delete the currently selected ROI"""
        if self.selected_roi_index is None:
            messagebox.showinfo("Information", "No ROI selected. Right-click on an ROI to select it.")
            return
        
        # Get the selected ROI
        roi = self.roi_rectangles[self.selected_roi_index]
        
        # Delete the rectangle and text from the canvas
        self.canvas.delete(roi['canvas_rect'])
        self.canvas.delete(roi['text_id'])
        
        # Remove from our list
        del self.roi_rectangles[self.selected_roi_index]
        
        logging.info(f"ROI {roi['roi_num']} deleted")
        
        # Reset selection
        self.selected_roi_index = None
        
        # Update ROI numbers
        self.update_roi_numbers()
        
        # Update ROI Manager
        self.roi_manager.set_roi_data(self.roi_rectangles)
    
    def update_roi_numbers(self):
        """Update ROI numbers after deletion"""
        for i, roi in enumerate(self.roi_rectangles):
            roi_num = i + 1
            roi['roi_num'] = roi_num
            
            # Update text on canvas
            self.canvas.itemconfig(roi['text_id'], text=f"ROI {roi_num}")
    
    def clear_rois(self):
        # Clear all ROIs
        for roi in self.roi_rectangles:
            self.canvas.delete(roi['canvas_rect'])
            self.canvas.delete(roi['text_id'])
        
        self.roi_rectangles = []
        self.selected_roi_index = None
        
        # Redisplay the image if it exists
        self.canvas.delete("all")
        if self.image_display:
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.image_display)
        
        # Update ROI Manager
        self.roi_manager.set_roi_data(self.roi_rectangles)
        
        logging.info("All ROIs cleared")
    
    def preprocess_roi_for_ocr(self, roi_img):
        """Apply custom preprocessing based on ROI size"""
        # Get dimensions
        height, width = roi_img.shape[:2]
        
        # Convert to grayscale
        gray = cv2.cvtColor(roi_img, cv2.COLOR_BGR2GRAY)
        
        # For small ROIs (adjust these thresholds based on your specific use case)
        if height < 50 or width < 100:
            logging.info(f"Using enhanced preprocessing for small ROI: {width}x{height}")
            
            # More aggressive upscaling for very small ROIs
            scale_factor = 4 if height < 30 or width < 60 else 3
            
            # Apply super-resolution or upscaling for small ROIs
            upscaled = cv2.resize(gray, (width*scale_factor, height*scale_factor), interpolation=cv2.INTER_CUBIC)
            
            # Apply bilateral filter to reduce noise while preserving edges
            denoised = cv2.bilateralFilter(upscaled, 9, 75, 75)
            
            # Enhanced contrast with CLAHE (Contrast Limited Adaptive Histogram Equalization)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(denoised)
            
            # Apply unsharp mask for sharpening
            gaussian = cv2.GaussianBlur(enhanced, (0, 0), 3.0)
            sharpened = cv2.addWeighted(enhanced, 1.5, gaussian, -0.5, 0)
            
            # Try different binarization methods and select the best
            # Method 1: Adaptive thresholding 
            thresh1 = cv2.adaptiveThreshold(sharpened, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                          cv2.THRESH_BINARY, 11, 2)
            
            # Method 2: Otsu's thresholding
            _, thresh2 = cv2.threshold(sharpened, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Choose the method that retains more information (more white pixels for dark text on light background)
            if cv2.countNonZero(thresh1) > cv2.countNonZero(thresh2):
                result = thresh1
            else:
                result = thresh2
            
            # Dilate slightly to connect broken character components
            kernel = np.ones((2, 2), np.uint8)
            dilated = cv2.dilate(result, kernel, iterations=1)
            
            # Erode slightly to restore character thickness
            eroded = cv2.erode(dilated, kernel, iterations=1)
            
            return eroded
        else:
            # Regular preprocessing for larger ROIs
            # Denoise with Gaussian blur
            denoised = cv2.GaussianBlur(gray, (3, 3), 0)
            
            # Apply Otsu's thresholding
            _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Apply morphological operations to clean up
            kernel = np.ones((1, 1), np.uint8)
            opening = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
            
            return opening
    
    def analyze_rois(self):
        if self.image is None or not self.roi_rectangles:
            logging.warning("No image or ROIs to analyze")
            messagebox.showinfo("Information", "Please load an image and select at least one ROI.")
            return
        
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, "=== ROI Analysis Results ===\n\n")
        
        logging.info(f"Analyzing {len(self.roi_rectangles)} ROIs...")
        
        # Get all target images from the target manager
        targets = self.target_manager.get_all_targets()
        has_targets = len(targets) > 0
        
        if has_targets:
            logging.info(f"Using {len(targets)} target images for detection")
        
        # Get current window dimensions for metadata
        window_dimensions = {
            "canvas_width": self.canvas.winfo_width(),
            "canvas_height": self.canvas.winfo_height(),
            "scale_factor": self.scale_factor if hasattr(self, 'scale_factor') else 1.0,
            "image_width": self.image.shape[1] if self.image is not None else 0,
            "image_height": self.image.shape[0] if self.image is not None else 0
        }
        
        # Prepare a dictionary to store all results
        self.analysis_results = []
        
        for roi in self.roi_rectangles:
            roi_num = roi['roi_num']
            x1, y1, x2, y2 = roi['original_coords']
            
            # Make sure coordinates are in the correct order
            x1, x2 = min(x1, x2), max(x1, x2)
            y1, y2 = min(y1, y2), max(y1, y2)
            
            # Extract the ROI from the original image
            roi_img = self.image[y1:y2, x1:x2]
            
            roi_result = {
                "roi_num": roi_num,
                "name": roi.get('name', f"ROI {roi_num}"),
                "coordinates": [x1, y1, x2, y2],
                "template_info": roi.get('template_info', None),
                "ocr_text": None,
                "target_matches": []
            }
            
            # Perform OCR on the ROI
            try:
                # Preprocess for better OCR
                processed_roi = self.preprocess_roi_for_ocr(roi_img)
                
                # Check if this is a small ROI
                height, width = roi_img.shape[:2]
                is_small_roi = height < 50 or width < 100
                
                # Configure Tesseract specifically for numbers and small text
                if is_small_roi or self.numbers_only.get():
                    custom_config = f'--oem 1 --psm 7 -c tessedit_char_whitelist=0123456789.,-'
                else:
                    custom_config = f'--oem 1 --psm 6'  # Different PSM mode for regular text
                
                # Perform OCR with selected language and configuration
                text = pytesseract.image_to_string(
                    processed_roi, 
                    lang=self.ocr_lang.get(),
                    config=custom_config
                )
                text = text.strip()
                
                # Display ROI source information if available
                roi_source = ""
                if roi.get('template_info'):
                    template_name = roi['template_info'].get('template_name')
                    roi_type = roi['template_info'].get('roi_type')
                    if template_name and roi_type:
                        roi_source = f" (From template: {template_name}, Type: {roi_type})"
                
                self.results_text.insert(tk.END, f"ROI {roi_num} ({roi.get('name', f'ROI {roi_num}')}{roi_source}):\n")
                self.results_text.insert(tk.END, f"  - Extracted Text: {text if text else 'None detected'}\n")
                
                roi_result["ocr_text"] = text
                
                # Save debug images if enabled
                if self.debug_preprocessing.get():
                    debug_dir = "debug_images"
                    os.makedirs(debug_dir, exist_ok=True)
                    cv2.imwrite(f"{debug_dir}/roi_{roi_num}_original.png", roi_img)
                    cv2.imwrite(f"{debug_dir}/roi_{roi_num}_processed.png", processed_roi)
                
                logging.info(f"OCR completed for ROI {roi_num}")
            except Exception as e:
                error_msg = f"OCR error for ROI {roi_num}: {str(e)}"
                self.results_text.insert(tk.END, f"  - OCR Error: {error_msg}\n")
                logging.error(error_msg)
                roi_result["ocr_error"] = str(e)
            
            # Check for target images if available
            if has_targets:
                try:
                    # Check all target images against this ROI
                    matches = check_target_matches(
                        roi_img, 
                        targets, 
                        self.match_method.get(), 
                        self.match_threshold.get()
                    )
                    
                    if matches:
                        self.results_text.insert(tk.END, f"  - Target Images Found:\n")
                        for match in matches:
                            match_msg = f"    * '{match['description']}' with {match['confidence']:.2f} confidence\n"
                            self.results_text.insert(tk.END, match_msg)
                            logging.info(f"Target '{match['description']}' found in ROI {roi_num}")
                        
                        roi_result["target_matches"] = matches
                    else:
                        self.results_text.insert(tk.END, f"  - No target images found in this ROI\n")
                        logging.info(f"No target images found in ROI {roi_num}")
                        
                except Exception as e:
                    error_msg = f"Image matching error for ROI {roi_num}: {str(e)}"
                    self.results_text.insert(tk.END, f"  - {error_msg}\n")
                    logging.error(error_msg)
                    roi_result["target_match_error"] = str(e)
            
            self.results_text.insert(tk.END, "\n")
            self.analysis_results.append(roi_result)
        
        # Update JSON view
        self.update_json_view()
        
        # Include information about the analysis in results
        analysis_metadata = {
            "timestamp": datetime.datetime.now().isoformat(),
            "image_path": self.image_path,
            "window_dimensions": window_dimensions,
            "settings": {
                "ocr_language": self.ocr_lang.get(),
                "match_threshold": self.match_threshold.get(),
                "match_method": self.match_method.get()
            }
        }
        
        # Complete results including metadata
        self.complete_results = {
            "metadata": analysis_metadata,
            "results": self.analysis_results
        }
        
        # Send update to API server - wrapped in try/except to prevent errors
        try:
            # Try to send the update, but don't let errors affect the application
            try:
                self.send_update_sync(self.complete_results)
            except Exception as e:
                logging.error(f"Failed to send API update: {str(e)}")
        except Exception as e:
            logging.error(f"Error preparing API update: {str(e)}")
        
        logging.info("ROI analysis completed")
    
    def update_json_view(self):
        """Update the JSON view with current results"""
        if hasattr(self, 'analysis_results') and self.analysis_results:
            # Apply JSON filtering if JSON manager exists
            if hasattr(self, 'json_manager') and self.json_manager:
                # Create a complete data structure
                complete_data = {
                    "metadata": {
                        "timestamp": datetime.datetime.now().isoformat(),
                        "image_path": self.image_path,
                        "settings": {
                            "ocr_language": self.ocr_lang.get(),
                            "match_threshold": self.match_threshold.get(),
                            "match_method": self.match_method.get()
                        }
                    },
                    "results": self.analysis_results
                }
                
                # Filter through JSON manager
                filtered_data = self.json_manager.filter_json_output(complete_data)
                
                # Display filtered JSON
                self.json_text.delete(1.0, tk.END)
                self.json_text.insert(tk.END, json.dumps(filtered_data, indent=2))
            else:
                # Original behavior
                self.json_text.delete(1.0, tk.END)
                self.json_text.insert(tk.END, json.dumps(self.analysis_results, indent=2))
        else:
            self.json_text.delete(1.0, tk.END)
            self.json_text.insert(tk.END, "No analysis results available")
    
    def save_results(self):
        """Save analysis results to JSON file"""
        if not hasattr(self, 'analysis_results') or not self.analysis_results:
            messagebox.showinfo("Information", "No analysis results to save. Please analyze ROIs first.")
            return
        
        # Ask for file location
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
        
        # Get target descriptions for metadata
        target_descriptions = []
        targets = self.target_manager.get_all_targets()
        if targets:
            target_descriptions = [
                {"filename": t.filename, "description": t.description} 
                for t in targets
            ]
        
        # Create a results dictionary with metadata
        results_data = {
            "timestamp": datetime.datetime.now().isoformat(),
            "image": os.path.basename(self.image_path) if self.image_path else None,
            "ocr_language": self.ocr_lang.get(),
            "match_threshold": self.match_threshold.get(),
            "target_images": target_descriptions,
            "results": self.analysis_results
        }
        
        # Apply JSON filtering if JSON manager exists
        if hasattr(self, 'json_manager') and self.json_manager:
            complete_data = {
                "metadata": {
                    "timestamp": datetime.datetime.now().isoformat(),
                    "image_path": self.image_path,
                    "image": os.path.basename(self.image_path) if self.image_path else None,
                    "ocr_language": self.ocr_lang.get(),
                    "match_threshold": self.match_threshold.get(),
                    "target_images": target_descriptions,
                    "settings": {
                        "ocr_language": self.ocr_lang.get(),
                        "match_threshold": self.match_threshold.get(),
                        "match_method": self.match_method.get()
                    }
                },
                "results": self.analysis_results
            }
            
            # Filter through JSON manager
            results_data = self.json_manager.filter_json_output(complete_data)
        
        # Save to file
        try:
            with open(file_path, 'w') as f:
                json.dump(results_data, f, indent=4)
            
            logging.info(f"Results saved to {file_path}")
            messagebox.showinfo("Success", f"Results saved to {file_path}")
        except Exception as e:
            logging.error(f"Error saving results: {str(e)}")
            messagebox.showerror("Error", f"Failed to save results: {str(e)}")
    
    def open_realtime_monitor(self):
        """Open the real-time monitoring window"""
        try:
            # Import at function call to avoid circular imports
            from realtime_monitor import RealtimeMonitor
            RealtimeMonitor(self.root, self.roi_manager)
            self.status_var.set("Real-time monitor opened")
        except Exception as e:
            logging.error(f"Error opening real-time monitor: {str(e)}")
            messagebox.showerror("Error", f"Failed to open real-time monitor: {str(e)}")

# Custom log handler to display logs in the tkinter Text widget
class TextHandler(logging.Handler):
    def __init__(self, text_widget):
        logging.Handler.__init__(self)
        self.text_widget = text_widget
    
    def emit(self, record):
        msg = self.format(record)
        
        def append():
            self.text_widget.insert(tk.END, msg + '\n')
            self.text_widget.see(tk.END)  # Auto-scroll to the end
        
        # Append in the main thread to avoid tkinter threading issues
        self.text_widget.after(0, append)

def main():
    # Set path to Tesseract OCR executable if not in PATH
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  
    
    # Create templates directory if it doesn't exist
    os.makedirs("templates", exist_ok=True)
    
    root = tk.Tk()
    app = ROIAnalyzerApp(root)
    
    # Add a small help window at startup
    def show_help():
        help_text = """
        ROI Analyzer Tool Help:
        
        1. Click "Load Image" to open your main image
        2. Draw ROIs by clicking and dragging on the image
        3. Right-click an ROI to select it (turns green)
        4. Use "Manage ROIs" to:
           - Rename ROIs
           - View ROI properties
           - Select ROIs on canvas
           - Delete ROIs
        5. Click "Manage Target Images" to add multiple target images with descriptions
        6. Add target images in the Target Manager window
        7. Click "Manage Templates" to create and apply UI templates with predefined ROIs
        8. Click "Analyze ROIs" to perform OCR and detect target images
        9. Use "Save Results" to export analysis as JSON
        10. Configure JSON output using "JSON Output Manager"
        
        Note: You need Tesseract OCR installed on your system.
        """
        
        help_window = tk.Toplevel(root)
        help_window.title("Help")
        help_window.geometry("500x400")
        
        help_textbox = scrolledtext.ScrolledText(help_window, wrap=tk.WORD, 
                                               font=("Segoe UI", 10))
        help_textbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        help_textbox.insert(tk.END, help_text)
        help_textbox.config(state=tk.DISABLED)
    
    # Add help button to menu
    menu_bar = tk.Menu(root)
    help_menu = tk.Menu(menu_bar, tearoff=0)
    help_menu.add_command(label="Show Help", command=show_help)
    menu_bar.add_cascade(label="Help", menu=help_menu)
    
    # Add templates menu
    templates_menu = tk.Menu(menu_bar, tearoff=0)
    templates_menu.add_command(label="Manage Templates", command=app.template_manager.show_window)
    templates_menu.add_command(label="Create New Template", command=app.template_manager.create_new_template)
    menu_bar.add_cascade(label="Templates", menu=templates_menu)
    
    # Add JSON output menu
    json_menu = tk.Menu(menu_bar, tearoff=0)
    json_menu.add_command(label="Configure JSON Output", command=app.json_manager.show_window)
    menu_bar.add_cascade(label="JSON", menu=json_menu)
    
    root.config(menu=menu_bar)
    
    # Show help on startup
    root.after(500, show_help)
    
    root.mainloop()

if __name__ == "__main__":
    main()

