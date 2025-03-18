import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import cv2
import numpy as np
import time
import threading
import queue
import os
import logging
import json
import datetime
from typing import List, Dict, Any, Optional, Tuple
import win32gui
import win32ui
import win32con
import win32api
from PIL import Image, ImageTk
import pygetwindow as gw


class RealtimeMonitor:
    """Real-time monitoring of application windows with ROI analysis"""
    def __init__(self, root, roi_manager=None):
        self.root = root
        self.roi_manager = roi_manager
        self.window = None
        self.monitor_thread = None
        self.stop_event = threading.Event()
        self.result_queue = queue.Queue()
        self.target_window_handle = None
        self.capture_interval = 1.0  # Default capture interval in seconds
        self.is_monitoring = False
        self.last_results = []
        self.debug_mode = False
        
        # Create output directory if it doesn't exist
        self.output_dir = "monitor_output"
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Show the monitor window
        self.show_window()
    
    def show_window(self):
        """Show the real-time monitor window"""
        if self.window:
            self.window.destroy()
        
        self.window = tk.Toplevel(self.root)
        self.window.title("Real-Time Monitor")
        self.window.geometry("900x700")
        self.window.minsize(800, 600)
        
        # Handle window close
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Create main frame with padding
        main_frame = ttk.Frame(self.window, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create header with title
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        header_label = ttk.Label(header_frame, text="Real-Time Window Monitor", 
                               font=("Segoe UI", 16, "bold"))
        header_label.pack(side=tk.LEFT)
        
        # Control panel
        control_panel = ttk.LabelFrame(main_frame, text="Monitor Controls")
        control_panel.pack(fill=tk.X, pady=5)
        
        # Window selection
        window_frame = ttk.Frame(control_panel)
        window_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(window_frame, text="Target Window:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        
        self.window_var = tk.StringVar(value="No window selected")
        window_label = ttk.Label(window_frame, textvariable=self.window_var, width=40)
        window_label.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        select_btn = ttk.Button(window_frame, text="Select Window", command=self.select_window)
        select_btn.grid(row=0, column=2, padx=5, pady=5)
        
        refresh_btn = ttk.Button(window_frame, text="Refresh Window List", command=self.refresh_window_list)
        refresh_btn.grid(row=0, column=3, padx=5, pady=5)
        
        # Interval setting
        ttk.Label(window_frame, text="Capture Interval (sec):").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        
        self.interval_var = tk.DoubleVar(value=1.0)
        interval_spinner = ttk.Spinbox(window_frame, from_=0.1, to=10.0, increment=0.1, 
                                     textvariable=self.interval_var, width=5)
        interval_spinner.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        
        # Debug mode checkbox
        self.debug_var = tk.BooleanVar(value=False)
        debug_check = ttk.Checkbutton(window_frame, text="Debug Mode (save captures)", 
                                    variable=self.debug_var)
        debug_check.grid(row=1, column=2, padx=5, pady=5, columnspan=2, sticky=tk.W)
        
        # Control buttons
        btn_frame = ttk.Frame(control_panel)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.start_btn = ttk.Button(btn_frame, text="Start Monitoring", 
                                  command=self.start_monitoring)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(btn_frame, text="Stop Monitoring", 
                                 command=self.stop_monitoring, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        self.capture_btn = ttk.Button(btn_frame, text="Capture Once", 
                                    command=self.capture_once)
        self.capture_btn.pack(side=tk.LEFT, padx=5)
        
        # Split view
        split_frame = ttk.Frame(main_frame)
        split_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Left side: Captured image display
        left_panel = ttk.LabelFrame(split_frame, text="Captured Image")
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        self.image_canvas = tk.Canvas(left_panel, bg="white", highlightthickness=0)
        self.image_canvas.pack(fill=tk.BOTH, expand=True)
        
        # Right side: Results and status
        right_panel = ttk.Frame(split_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # Results panel
        results_frame = ttk.LabelFrame(right_panel, text="Analysis Results")
        results_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        self.results_text = tk.Text(results_frame, wrap=tk.WORD, font=("Consolas", 10))
        self.results_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Log panel
        log_frame = ttk.LabelFrame(right_panel, text="Monitor Log")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        
        self.log_text = tk.Text(log_frame, wrap=tk.WORD, font=("Consolas", 9),
                              bg="#f0f0f0", fg="#333333")
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Status bar
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(status_frame, textvariable=self.status_var,
                               font=("Segoe UI", 9), foreground="#666666")
        status_label.pack(side=tk.LEFT, padx=5, pady=2)
        
        # Initialize window list
        self.refresh_window_list()
        
        # Add custom log handler
        self.log_handler = TextHandler(self.log_text)
        self.log_handler.setLevel(logging.INFO)
        logging.getLogger().addHandler(self.log_handler)
        
        self.log_message("Real-time monitor initialized")
    
    def on_close(self):
        """Handle window close event"""
        if self.is_monitoring:
            self.stop_monitoring()
        
        # Remove log handler
        logging.getLogger().removeHandler(self.log_handler)
        
        self.window.destroy()
    
    def log_message(self, message, level=logging.INFO):
        """Add message to log"""
        logging.log(level, message)
        
        # Also log to the monitor log
        if hasattr(self, 'log_text'):
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
            self.log_text.see(tk.END)
    
    def refresh_window_list(self):
        """Refresh the list of available windows"""
        try:
            self.window_list = []
            
            def callback(hwnd, _):
                if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                    self.window_list.append((hwnd, win32gui.GetWindowText(hwnd)))
                return True
            
            win32gui.EnumWindows(callback, None)
            self.log_message(f"Found {len(self.window_list)} visible windows")
        except Exception as e:
            self.log_message(f"Error refreshing window list: {str(e)}", logging.ERROR)
    
    def select_window(self):
        """Display window selection dialog"""
        if not self.window_list:
            self.refresh_window_list()
        
        # Create a dialog to show a list of windows
        dialog = tk.Toplevel(self.window)
        dialog.title("Select Window to Monitor")
        dialog.geometry("500x400")
        dialog.grab_set()  # Make the dialog modal
        
        # Create a listbox with scrollbar
        frame = ttk.Frame(dialog, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Select a window to monitor:").pack(anchor=tk.W, pady=(0, 5))
        
        list_frame = ttk.Frame(frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, font=("Segoe UI", 10))
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar.config(command=listbox.yview)
        
        # Populate listbox with window titles
        for i, (hwnd, title) in enumerate(self.window_list):
            listbox.insert(tk.END, f"{title} (0x{hwnd:08X})")
        
        # Search box
        search_frame = ttk.Frame(frame)
        search_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=(0, 5))
        
        search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        def filter_list(*args):
            search_text = search_var.get().lower()
            listbox.delete(0, tk.END)
            for i, (hwnd, title) in enumerate(self.window_list):
                if search_text in title.lower():
                    listbox.insert(tk.END, f"{title} (0x{hwnd:08X})")
        
        search_var.trace_add("write", filter_list)
        
        # Buttons
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        def on_confirm():
            selection = listbox.curselection()
            if selection:
                # Get the selected window from the filtered list
                selected_text = listbox.get(selection[0])
                hwnd_hex = selected_text.split("(0x")[1].split(")")[0]
                hwnd = int(hwnd_hex, 16)
                
                # Find the window in the original list
                for window_hwnd, window_title in self.window_list:
                    if window_hwnd == hwnd:
                        self.target_window_handle = window_hwnd
                        self.window_var.set(window_title)
                        self.log_message(f"Selected window: {window_title} (0x{window_hwnd:08X})")
                        break
            
            dialog.destroy()
        
        def on_cancel():
            dialog.destroy()
        
        confirm_btn = ttk.Button(button_frame, text="OK", command=on_confirm)
        confirm_btn.pack(side=tk.RIGHT, padx=5)
        
        cancel_btn = ttk.Button(button_frame, text="Cancel", command=on_cancel)
        cancel_btn.pack(side=tk.RIGHT, padx=5)
    
    def start_monitoring(self):
        """Start the real-time monitoring thread"""
        if self.is_monitoring:
            return
        
        if not self.target_window_handle:
            messagebox.showwarning("Warning", "No window selected. Please select a window first.")
            return
        
        # Update interval
        self.capture_interval = self.interval_var.get()
        self.debug_mode = self.debug_var.get()
        
        # Reset stop event
        self.stop_event.clear()
        
        # Start monitor thread
        self.monitor_thread = threading.Thread(target=self.monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        # Update UI
        self.is_monitoring = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.status_var.set("Monitoring...")
        
        # Start processing results from the queue
        self.window.after(100, self.process_results)
        
        self.log_message(f"Started monitoring with interval: {self.capture_interval}s")
    
    def stop_monitoring(self):
        """Stop the real-time monitoring thread"""
        if not self.is_monitoring:
            return
        
        # Signal thread to stop
        self.stop_event.set()
        
        # Wait for thread to finish
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2.0)
        
        # Update UI
        self.is_monitoring = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.status_var.set("Ready")
        
        self.log_message("Stopped monitoring")
    
    def capture_once(self):
        """Perform a single capture and analysis"""
        if not self.target_window_handle:
            messagebox.showwarning("Warning", "No window selected. Please select a window first.")
            return
        
        try:
            # Capture window
            image = self.capture_window(self.target_window_handle)
            
            if image is None:
                self.log_message("Failed to capture window image", logging.ERROR)
                return
            
            # Display image
            self.display_image(image)
            
            # Analyze if ROI manager is available
            if self.roi_manager and hasattr(self.roi_manager, '_get_parent_app'):
                self.analyze_image(image)
            
            self.log_message("Captured and analyzed window")
        except Exception as e:
            self.log_message(f"Error during capture: {str(e)}", logging.ERROR)
    
    def monitor_loop(self):
        """Background thread for real-time monitoring"""
        try:
            while not self.stop_event.is_set():
                # Capture and analyze
                try:
                    # Capture window
                    image = self.capture_window(self.target_window_handle)
                    
                    if image is not None:
                        # Queue results to be processed in the main thread
                        self.result_queue.put(("image", image))
                        
                        # Analyze if ROI manager is available
                        if self.roi_manager and hasattr(self.roi_manager, '_get_parent_app'):
                            self.analyze_image(image)
                except Exception as e:
                    self.log_message(f"Error in monitor loop: {str(e)}", logging.ERROR)
                
                # Wait for the next interval or until stopped
                if self.stop_event.wait(self.capture_interval):
                    break
        except Exception as e:
            self.log_message(f"Monitor thread error: {str(e)}", logging.ERROR)
        
        self.log_message("Monitor thread exited")
    
    def capture_window(self, hwnd):
        """Capture an image of the window"""
        try:
            # Check if window still exists
            if not win32gui.IsWindow(hwnd):
                self.log_message(f"Window 0x{hwnd:08X} no longer exists", logging.WARNING)
                return None
            
            # Get window dimensions
            try:
                left, top, right, bottom = win32gui.GetWindowRect(hwnd)
                width = right - left
                height = bottom - top
            except Exception as e:
                self.log_message(f"Error getting window rect: {str(e)}", logging.ERROR)
                return None
            
            # Skip if window has no size
            if width <= 0 or height <= 0:
                return None
            
            # Create device contexts and bitmap
            try:
                hwnd_dc = win32gui.GetWindowDC(hwnd)
                mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
                save_dc = mfc_dc.CreateCompatibleDC()
                
                save_bitmap = win32ui.CreateBitmap()
                save_bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
                save_dc.SelectObject(save_bitmap)
                
                # Copy window content to bitmap
                result = win32gui.PrintWindow(hwnd, save_dc.GetSafeHdc(), 2)  # 2 = PW_RENDERFULLCONTENT
                
                # Convert to numpy array
                bmpinfo = save_bitmap.GetInfo()
                bmpstr = save_bitmap.GetBitmapBits(True)
                img = np.frombuffer(bmpstr, dtype=np.uint8).reshape(bmpinfo['bmHeight'], bmpinfo['bmWidth'], 4)
                
                # Clean up
                win32gui.ReleaseDC(hwnd, hwnd_dc)
                mfc_dc.DeleteDC()
                save_dc.DeleteDC()
                save_bitmap.DeleteObject()
                
                # Convert to BGR format and remove alpha channel
                img = img[:, :, :3]
                
                # Save debug image if enabled
                if self.debug_mode:
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    cv2.imwrite(os.path.join(self.output_dir, f"capture_{timestamp}.png"), img)
                
                return img
            except Exception as e:
                self.log_message(f"Error capturing window: {str(e)}", logging.ERROR)
                return None
        except Exception as e:
            self.log_message(f"Window capture error: {str(e)}", logging.ERROR)
            return None
    
    def display_image(self, image):
        """Display the captured image on the canvas"""
        try:
            # Convert BGR to RGB for display
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Resize the image to fit the canvas while maintaining aspect ratio
            canvas_width = self.image_canvas.winfo_width()
            canvas_height = self.image_canvas.winfo_height()
            
            # If canvas size is not determined yet
            if canvas_width <= 1:
                canvas_width = 400
                canvas_height = 300
            
            # Calculate scaling factor
            height, width = rgb_image.shape[:2]
            scale = min(canvas_width / width, canvas_height / height)
            new_width = int(width * scale)
            new_height = int(height * scale)
            
            # Resize image
            resized_image = cv2.resize(rgb_image, (new_width, new_height))
            
            # Convert to PhotoImage for tkinter
            self.photo_image = ImageTk.PhotoImage(image=Image.fromarray(resized_image))
            
            # Update canvas
            self.image_canvas.config(width=new_width, height=new_height)
            self.image_canvas.delete("all")
            self.image_canvas.create_image(0, 0, anchor=tk.NW, image=self.photo_image)
        except Exception as e:
            self.log_message(f"Error displaying image: {str(e)}", logging.ERROR)
    
    def analyze_image(self, image):
        """Analyze the image using ROIs from the ROI manager"""
        try:
            # Get parent app
            parent_app = self.roi_manager._get_parent_app()
            
            if not parent_app or not hasattr(parent_app, 'roi_rectangles'):
                return
            
            # Create a copy of the ROIs
            roi_rectangles = parent_app.roi_rectangles.copy()
            
            if not roi_rectangles:
                return
            
            # Store current image and scale factor
            original_image = parent_app.image
            original_scale = getattr(parent_app, 'scale_factor', 1.0)
            
            # Temporarily set the captured image as the current image
            parent_app.image = image
            
            # Analyze ROIs
            results = []
            
            for roi in roi_rectangles:
                roi_num = roi['roi_num']
                x1, y1, x2, y2 = roi['original_coords']
                
                # Make sure coordinates are in the correct order
                x1, x2 = min(x1, x2), max(x1, x2)
                y1, y2 = min(y1, y2), max(y1, y2)
                
                # Check if coordinates are within image bounds
                height, width = image.shape[:2]
                if x1 >= width or y1 >= height:
                    continue
                
                # Clip coordinates to image bounds
                x2 = min(x2, width - 1)
                y2 = min(y2, height - 1)
                
                # Skip if ROI is too small
                if x2 - x1 < 5 or y2 - y1 < 5:
                    continue
                
                # Extract ROI from image
                roi_img = image[y1:y2, x1:x2]
                
                # Create result object
                result = {
                    "roi_num": roi_num,
                    "name": roi.get('name', f"ROI {roi_num}"),
                    "coordinates": [x1, y1, x2, y2],
                    "timestamp": datetime.datetime.now().isoformat()
                }
                
                # Perform OCR if method is available
                if hasattr(parent_app, 'preprocess_roi_for_ocr'):
                    try:
                        # Preprocess
                        processed_roi = parent_app.preprocess_roi_for_ocr(roi_img)
                        
                        # Check if this is a small ROI
                        height, width = roi_img.shape[:2]
                        is_small_roi = height < 50 or width < 100
                        
                        # Configure OCR
                        if hasattr(parent_app, 'numbers_only') and (is_small_roi or parent_app.numbers_only.get()):
                            custom_config = f'--oem 1 --psm 7 -c tessedit_char_whitelist=0123456789.,-'
                        else:
                            custom_config = f'--oem 1 --psm 6'
                        
                        # Perform OCR
                        import pytesseract
                        text = pytesseract.image_to_string(
                            processed_roi, 
                            lang=parent_app.ocr_lang.get() if hasattr(parent_app, 'ocr_lang') else "eng",
                            config=custom_config
                        )
                        text = text.strip()
                        
                        result["ocr_text"] = text
                        
                        # Save debug image if enabled
                        if self.debug_mode:
                            debug_dir = os.path.join(self.output_dir, "roi_debug")
                            os.makedirs(debug_dir, exist_ok=True)
                            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                            cv2.imwrite(f"{debug_dir}/roi_{roi_num}_{timestamp}.png", roi_img)
                            cv2.imwrite(f"{debug_dir}/roi_{roi_num}_{timestamp}_processed.png", processed_roi)
                    except Exception as e:
                        result["ocr_error"] = str(e)
                
                # Check for target images if method is available
                if hasattr(parent_app, 'target_manager') and hasattr(parent_app.target_manager, 'get_all_targets'):
                    try:
                        targets = parent_app.target_manager.get_all_targets()
                        
                        if targets:
                            from target_manager import check_target_matches
                            
                            match_method = parent_app.match_method.get() if hasattr(parent_app, 'match_method') else cv2.TM_CCOEFF_NORMED
                            match_threshold = parent_app.match_threshold.get() if hasattr(parent_app, 'match_threshold') else 0.7
                            
                            matches = check_target_matches(
                                roi_img, 
                                targets, 
                                match_method, 
                                match_threshold
                            )
                            
                            if matches:
                                result["target_matches"] = matches
                    except Exception as e:
                        result["target_match_error"] = str(e)
                
                results.append(result)
            
            # Restore original image
            parent_app.image = original_image
            
            # Update results
            self.last_results = results
            
            # Update results display in main thread
            self.result_queue.put(("results", results))
            
            # Save results to file if in debug mode
            if self.debug_mode and results:
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                results_file = os.path.join(self.output_dir, f"results_{timestamp}.json")
                
                with open(results_file, 'w') as f:
                    json.dump(results, f, indent=2)
        except Exception as e:
            self.log_message(f"Error analyzing image: {str(e)}", logging.ERROR)
    
    def update_results_display(self, results):
        """Update the results display"""
        self.results_text.delete(1.0, tk.END)
        
        if not results:
            self.results_text.insert(tk.END, "No results available")
            return
        
        self.results_text.insert(tk.END, f"Results ({len(results)} ROIs):\n\n")
        
        for result in results:
            roi_name = result.get('name', f"ROI {result.get('roi_num', '?')}")
            self.results_text.insert(tk.END, f"{roi_name}:\n")
            
            if "ocr_text" in result:
                text = result["ocr_text"]
                self.results_text.insert(tk.END, f"  Text: {text if text else '(none)'}\n")
            
            if "target_matches" in result and result["target_matches"]:
                self.results_text.insert(tk.END, f"  Targets found:\n")
                for match in result["target_matches"]:
                    self.results_text.insert(
                        tk.END, 
                        f"    * {match.get('description', 'Unknown')} ({match.get('confidence', 0):.2f})\n"
                    )
            
            self.results_text.insert(tk.END, "\n")
        
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.results_text.insert(tk.END, f"\nLast update: {timestamp}")
    
    def process_results(self):
        """Process results from the queue"""
        try:
            # Process all pending results
            while not self.result_queue.empty():
                result_type, data = self.result_queue.get_nowait()
                
                if result_type == "image":
                    self.display_image(data)
                elif result_type == "results":
                    self.update_results_display(data)
        except queue.Empty:
            pass
        except Exception as e:
            self.log_message(f"Error processing results: {str(e)}", logging.ERROR)
        
        # Schedule next processing
        if self.is_monitoring and not self.stop_event.is_set():
            self.window.after(100, self.process_results)


class TextHandler(logging.Handler):
    """Handler to log messages to a tkinter Text widget"""
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