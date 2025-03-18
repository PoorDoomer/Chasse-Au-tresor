import tkinter as tk
from tkinter import ttk, messagebox
import json
import logging
import re

class ROIManager:
    def __init__(self, parent, canvas, callback_on_roi_change=None):
        self.parent = parent
        self.canvas = canvas
        self.callback_on_roi_change = callback_on_roi_change
        self.roi_rectangles = []  # Will be set from the main application
        
        # Create a new window
        self.window = tk.Toplevel(parent)
        self.window.title("ROI Manager")
        self.window.geometry("600x700")  # Increased size for new options
        self.window.protocol("WM_DELETE_WINDOW", self.hide_window)  # Hide instead of destroy
        
        # Initialize filtering options
        self.filter_options = {
            "numbers": tk.BooleanVar(value=True),
            "numbers_decimal": tk.BooleanVar(value=True),
            "numbers_negative": tk.BooleanVar(value=True),
            "numbers_thousand_sep": tk.BooleanVar(value=False),
            "letters": tk.BooleanVar(value=True),
            "special_chars": tk.BooleanVar(value=False),
            "target_images": tk.BooleanVar(value=True)
        }
        
        self.setup_ui()
        self.window.withdraw()  # Initially hidden
    
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.window, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="ROI Manager", font=("Segoe UI", 16, "bold"))
        title_label.pack(pady=(0, 10))
        
        # ROI list with scrollbar
        list_frame = ttk.LabelFrame(main_frame, text="Regions of Interest")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.roi_list = ttk.Treeview(list_frame, columns=("Name", "Coordinates"), 
                                     show="headings", selectmode="browse")
        self.roi_list.heading("Name", text="Name")
        self.roi_list.heading("Coordinates", text="Coordinates")
        self.roi_list.column("Name", width=100)
        self.roi_list.column("Coordinates", width=250)
        self.roi_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.roi_list.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        self.roi_list.configure(yscrollcommand=scrollbar.set)
        
        # Bind selection event
        self.roi_list.bind("<<TreeviewSelect>>", self.on_roi_selected)
        self.roi_list.bind("<Double-1>", self.on_roi_double_click)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        self.rename_btn = ttk.Button(button_frame, text="Rename ROI", command=self.rename_roi)
        self.rename_btn.pack(side=tk.LEFT, padx=5)
        
        self.select_btn = ttk.Button(button_frame, text="Select on Canvas", command=self.select_on_canvas)
        self.select_btn.pack(side=tk.LEFT, padx=5)
        
        self.delete_btn = ttk.Button(button_frame, text="Delete ROI", command=self.delete_roi)
        self.delete_btn.pack(side=tk.LEFT, padx=5)
        
        # Properties section
        props_frame = ttk.LabelFrame(main_frame, text="ROI Properties")
        props_frame.pack(fill=tk.X, pady=10)
        
        # Grid for properties
        props_grid = ttk.Frame(props_frame)
        props_grid.pack(fill=tk.X, padx=10, pady=10)
        
        # ROI ID
        ttk.Label(props_grid, text="ID:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.id_var = tk.StringVar()
        id_entry = ttk.Entry(props_grid, textvariable=self.id_var, state="readonly", width=10)
        id_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        
        # ROI Name
        ttk.Label(props_grid, text="Name:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=2)
        self.name_var = tk.StringVar()
        self.name_entry = ttk.Entry(props_grid, textvariable=self.name_var, width=20)
        self.name_entry.grid(row=0, column=3, sticky=tk.W, padx=5, pady=2)
        self.name_entry.bind("<Return>", lambda e: self.update_roi_name())
        
        # ROI Coordinates
        ttk.Label(props_grid, text="Coordinates:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.coords_var = tk.StringVar()
        coords_entry = ttk.Entry(props_grid, textvariable=self.coords_var, state="readonly", width=30)
        coords_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2, columnspan=3)
        
        # ROI Size
        ttk.Label(props_grid, text="Size:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.size_var = tk.StringVar()
        size_entry = ttk.Entry(props_grid, textvariable=self.size_var, state="readonly", width=20)
        size_entry.grid(row=2, column=1, sticky=tk.W, padx=5, pady=2, columnspan=2)
        
        # Apply button for name change
        self.apply_btn = ttk.Button(props_grid, text="Apply", command=self.update_roi_name)
        self.apply_btn.grid(row=2, column=3, sticky=tk.E, padx=5, pady=2)
        
        # Output Filtering Options section
        filter_frame = ttk.LabelFrame(main_frame, text="Output Type Filtering")
        filter_frame.pack(fill=tk.X, pady=10)
        
        # Create filter options
        filter_grid = ttk.Frame(filter_frame)
        filter_grid.pack(fill=tk.X, padx=10, pady=10)
        
        # Numerical options
        num_frame = ttk.LabelFrame(filter_grid, text="Numbers")
        num_frame.grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        
        ttk.Checkbutton(num_frame, text="Extract Numbers", 
                      variable=self.filter_options["numbers"]).pack(anchor=tk.W, padx=5)
        ttk.Checkbutton(num_frame, text="Include Decimal Points (0.123)", 
                      variable=self.filter_options["numbers_decimal"]).pack(anchor=tk.W, padx=5)
        ttk.Checkbutton(num_frame, text="Include Negative Signs (-123)", 
                      variable=self.filter_options["numbers_negative"]).pack(anchor=tk.W, padx=5)
        ttk.Checkbutton(num_frame, text="Include Thousand Separators (1,000)", 
                      variable=self.filter_options["numbers_thousand_sep"]).pack(anchor=tk.W, padx=5)
        
        # Text and Target options
        text_frame = ttk.LabelFrame(filter_grid, text="Text & Targets")
        text_frame.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Checkbutton(text_frame, text="Extract Letters", 
                      variable=self.filter_options["letters"]).pack(anchor=tk.W, padx=5)
        ttk.Checkbutton(text_frame, text="Include Special Characters", 
                      variable=self.filter_options["special_chars"]).pack(anchor=tk.W, padx=5)
        ttk.Checkbutton(text_frame, text="Include Target Images", 
                      variable=self.filter_options["target_images"]).pack(anchor=tk.W, padx=5)
        
        # Format option
        format_frame = ttk.LabelFrame(filter_grid, text="Output Format")
        format_frame.grid(row=1, column=0, columnspan=2, sticky=tk.W+tk.E, padx=5, pady=5)
        
        self.output_format = tk.StringVar(value="json")
        ttk.Radiobutton(format_frame, text="JSON", variable=self.output_format, 
                       value="json").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(format_frame, text="CSV", variable=self.output_format, 
                       value="csv").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(format_frame, text="Plain Text", variable=self.output_format, 
                       value="text").pack(side=tk.LEFT, padx=10)
        
        # JSON Preview section
        json_frame = ttk.LabelFrame(main_frame, text="JSON Preview")
        json_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.json_text = tk.Text(json_frame, wrap=tk.WORD, height=8, 
                               bg="#f8f8f8", font=("Consolas", 9))
        self.json_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Disable editing on JSON preview
        self.json_text.config(state=tk.DISABLED)
        
        # Apply styling
        self.apply_styling()
    
    def apply_styling(self):
        """Apply styling to make the UI more attractive"""
        style = ttk.Style()
        
        # Configure Treeview
        style.configure("Treeview", 
                        background="#f0f0f0",
                        foreground="black",
                        rowheight=25,
                        fieldbackground="#f0f0f0",
                        font=("Segoe UI", 9))
        style.map('Treeview', background=[('selected', '#0078d7')])
        
        # Configure Treeview headings
        style.configure("Treeview.Heading",
                        background="#e0e0e0",
                        foreground="black",
                        font=('Segoe UI', 10, 'bold'))
        
        # Configure buttons
        style.configure("TButton", 
                        font=('Segoe UI', 10),
                        background="#e0e0e0",
                        padding=5)
        
        # Configure labels
        style.configure("TLabel",
                        font=('Segoe UI', 10),
                        background="#f0f0f0")
        
        # Configure frames
        style.configure("TFrame", background="#f0f0f0")
        style.configure("TLabelframe", background="#f0f0f0")
        style.configure("TLabelframe.Label", background="#f0f0f0", font=('Segoe UI', 10, 'bold'))
        
        # Make checkbuttons more readable
        style.configure("TCheckbutton", background="#f0f0f0", font=('Segoe UI', 9))
        style.configure("TRadiobutton", background="#f0f0f0", font=('Segoe UI', 9))
    
    def show_window(self):
        """Show the ROI manager window"""
        self.window.deiconify()
        self.window.lift()
        self.update_roi_list()
    
    def hide_window(self):
        """Hide the ROI manager window"""
        self.window.withdraw()
    
    def set_roi_data(self, roi_rectangles):
        """Set ROI data from the main application"""
        self.roi_rectangles = roi_rectangles
        self.update_roi_list()
    
    def update_roi_list(self):
        """Update the ROI list with current data"""
        # Clear current list
        self.roi_list.delete(*self.roi_list.get_children())
        
        # Add ROIs to the list
        for roi in self.roi_rectangles:
            roi_id = str(roi['roi_num'])
            roi_name = roi.get('name', f"ROI {roi_id}")
            
            # Format coordinates
            x1, y1, x2, y2 = roi['original_coords']
            coords_str = f"({x1}, {y1}) to ({x2}, {y2})"
            
            # Add to the list
            self.roi_list.insert("", "end", iid=roi_id, values=(roi_name, coords_str))
        
        # Update JSON preview
        self.update_json_preview()
    
    def get_filter_pattern(self):
        """Get regex pattern based on filter options"""
        patterns = []
        
        # Number patterns
        if self.filter_options["numbers"].get():
            num_pattern = r'\d+'
            if self.filter_options["numbers_decimal"].get():
                num_pattern = r'\d+(?:\.\d+)?'
            if self.filter_options["numbers_negative"].get():
                num_pattern = r'-?' + num_pattern
            if self.filter_options["numbers_thousand_sep"].get():
                num_pattern = r'(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?'
            patterns.append(f"({num_pattern})")
        
        # Text patterns
        if self.filter_options["letters"].get():
            letter_pattern = r'[a-zA-Z]+'
            patterns.append(f"({letter_pattern})")
        
        # Special characters
        if self.filter_options["special_chars"].get():
            special_pattern = r'[!@#$%^&*()_+\-=\[\]{}|;:\'",.<>?/\\]+'
            patterns.append(f"({special_pattern})")
        
        # Combine patterns
        if patterns:
            return '|'.join(patterns)
        return None
    
    def filter_roi_text(self, text):
        """Filter ROI text based on active options"""
        if not text:
            return None
            
        pattern = self.get_filter_pattern()
        if not pattern:
            return text
            
        # Find all matches
        matches = re.findall(pattern, text)
        
        # Flatten list of tuples if needed
        result = []
        for match in matches:
            if isinstance(match, tuple):
                # Get the first non-empty group
                for group in match:
                    if group:
                        result.append(group)
                        break
            else:
                result.append(match)
                
        return result if result else None
    
    def update_json_preview(self):
        """Update the JSON preview with current ROI data including filter options"""
        # Create a simplified JSON representation of ROIs
        roi_data = []
        
        for roi in self.roi_rectangles:
            roi_dict = {
                "id": roi['roi_num'],
                "name": roi.get('name', f"ROI {roi['roi_num']}"),
                "coordinates": roi['original_coords'],
                "output_filters": {
                    "numbers": self.filter_options["numbers"].get(),
                    "include_decimal": self.filter_options["numbers_decimal"].get(),
                    "include_negative": self.filter_options["numbers_negative"].get(),
                    "include_thousand_sep": self.filter_options["numbers_thousand_sep"].get(),
                    "letters": self.filter_options["letters"].get(),
                    "special_chars": self.filter_options["special_chars"].get(),
                    "target_images": self.filter_options["target_images"].get()
                },
                "output_format": self.output_format.get()
            }
            roi_data.append(roi_dict)
        
        # Format as JSON
        json_str = json.dumps({"regions_of_interest": roi_data}, indent=2)
        
        # Update the text widget
        self.json_text.config(state=tk.NORMAL)
        self.json_text.delete(1.0, tk.END)
        self.json_text.insert(tk.END, json_str)
        self.json_text.config(state=tk.DISABLED)
    
    def on_roi_selected(self, event):
        """Handle selection of a ROI in the list"""
        selected = self.roi_list.selection()
        if not selected:
            # Clear property fields
            self.id_var.set("")
            self.name_var.set("")
            self.coords_var.set("")
            self.size_var.set("")
            return
        
        roi_id = selected[0]
        
        # Find the ROI
        roi = next((r for r in self.roi_rectangles if str(r['roi_num']) == roi_id), None)
        if not roi:
            return
        
        # Update property fields
        self.id_var.set(roi_id)
        self.name_var.set(roi.get('name', f"ROI {roi_id}"))
        
        x1, y1, x2, y2 = roi['original_coords']
        self.coords_var.set(f"({x1}, {y1}) to ({x2}, {y2})")
        
        width = abs(x2 - x1)
        height = abs(y2 - y1)
        area = width * height
        self.size_var.set(f"{width}x{height} px ({area} px²)")
    
    def on_roi_double_click(self, event):
        """Handle double click on ROI list item"""
        self.rename_roi()
    
    def rename_roi(self):
        """Rename the selected ROI"""
        selected = self.roi_list.selection()
        if not selected:
            messagebox.showinfo("Information", "No ROI selected")
            return
        
        roi_id = selected[0]
        
        # Find the ROI
        roi = next((r for r in self.roi_rectangles if str(r['roi_num']) == roi_id), None)
        if not roi:
            return
        
        # Show dialog for new name
        new_name = self.name_var.get()
        if not new_name:
            new_name = f"ROI {roi_id}"
        
        # Update the ROI name
        roi['name'] = new_name
        
        # Update the list
        self.roi_list.item(roi_id, values=(new_name, self.coords_var.get()))
        
        # Update canvas
        self.update_roi_label(roi)
        
        # Notify the main application
        if self.callback_on_roi_change:
            self.callback_on_roi_change()
        
        logging.info(f"Renamed ROI {roi_id} to '{new_name}'")
        
        # Update JSON preview
        self.update_json_preview()
    
    def update_roi_name(self):
        """Update the name of the selected ROI"""
        selected = self.roi_list.selection()
        if not selected:
            return
        
        # Get the ROI ID (same as the item ID in the tree)
        roi_id = selected[0]
        
        # Find the corresponding ROI
        roi_index = None
        for i, roi in enumerate(self.roi_rectangles):
            if str(roi['roi_num']) == roi_id:
                roi_index = i
                break
        
        if roi_index is None:
            return
        
        # Get the new name from the entry
        new_name = self.name_var.get().strip()
        if not new_name:
            new_name = f"ROI {roi_id}"
        
        # Update the ROI
        self.roi_rectangles[roi_index]['name'] = new_name
        
        # Update the list
        self.roi_list.item(roi_id, values=(new_name, self.roi_list.item(roi_id, "values")[1]))
        
        # Update the JSON preview
        self.update_json_preview()
        
        # Update the label on the canvas
        self.update_roi_label(self.roi_rectangles[roi_index])
        
        # Notify main application of the change
        if self.callback_on_roi_change:
            self.callback_on_roi_change(roi_index)
    
    def select_on_canvas(self):
        """Select the ROI on the canvas"""
        selected = self.roi_list.selection()
        if not selected:
            return
        
        # Get the ROI ID
        roi_id = selected[0]
        
        # Find the corresponding ROI index
        roi_index = None
        for i, roi in enumerate(self.roi_rectangles):
            if str(roi['roi_num']) == roi_id:
                roi_index = i
                break
        
        if roi_index is not None and self.callback_on_roi_change:
            self.callback_on_roi_change(roi_index)
    
    def delete_roi(self):
        """Delete the selected ROI"""
        selected = self.roi_list.selection()
        if not selected:
            return
        
        # Ask for confirmation
        if not messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this ROI?"):
            return
        
        # Get the ROI ID
        roi_id = selected[0]
        
        # Find the corresponding ROI index
        roi_index = None
        for i, roi in enumerate(self.roi_rectangles):
            if str(roi['roi_num']) == roi_id:
                roi_index = i
                break
        
        if roi_index is not None:
            # Notify parent application to delete the ROI
            if self.callback_on_roi_change:
                self.callback_on_roi_change(roi_index, delete=True)
            else:
                # If no callback, try to delete from our local list
                del self.roi_rectangles[roi_index]
                self.update_roi_list()
    
    def update_roi_label(self, roi):
        """Update the ROI label on the canvas"""
        canvas_rect = roi.get('canvas_rect')
        text_id = roi.get('text_id')
        
        if canvas_rect and text_id and self.canvas:
            try:
                self.canvas.itemconfig(text_id, text=roi.get('name', f"ROI {roi['roi_num']}"))
            except:
                pass
    
    def get_output_config(self):
        """Get the output configuration options"""
        return {
            "format": self.output_format.get(),
            "filters": {k: v.get() for k, v in self.filter_options.items()}
        }
    
    def get_selected_roi_index(self):
        """Get the index of the selected ROI in the roi_rectangles list"""
        selected = self.roi_list.selection()
        if not selected:
            return None
        
        # Get the ROI ID
        roi_id = selected[0]
        
        # Find the corresponding ROI index
        for i, roi in enumerate(self.roi_rectangles):
            if str(roi['roi_num']) == roi_id:
                return i
        
        return None
    
    def _get_parent_app(self):
        """Get a reference to the parent application (ROIAnalyzerApp)"""
        # This is a bit of a hack to get access to the parent application
        # It assumes the parent of this manager is the ROIAnalyzerApp
        try:
            # Check if parent is the main app (has the needed attributes)
            if hasattr(self.parent, 'image') and hasattr(self.parent, 'roi_rectangles'):
                return self.parent
            
            # If not, it might be another window, try to get its parent
            if hasattr(self.parent, 'master'):
                if hasattr(self.parent.master, 'image') and hasattr(self.parent.master, 'roi_rectangles'):
                    return self.parent.master
            
            # Last resort: try to find through the canvas
            if hasattr(self.canvas, 'master'):
                if hasattr(self.canvas.master, 'image') and hasattr(self.canvas.master, 'roi_rectangles'):
                    return self.canvas.master
                
                if hasattr(self.canvas.master, 'master'):
                    if hasattr(self.canvas.master.master, 'image') and hasattr(self.canvas.master.master, 'roi_rectangles'):
                        return self.canvas.master.master
            
            # Nothing found
            return None
        except:
            return None 