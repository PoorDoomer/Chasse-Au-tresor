import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import cv2
import numpy as np
import os
import json
import logging
from PIL import Image, ImageTk
from typing import List, Dict, Any, Optional, Tuple


class Template:
    """Class to represent a UI template with predefined ROIs"""
    def __init__(self, name: str, image_path: str = None):
        self.name = name
        self.image_path = image_path
        self.template_image = None
        self.rois = []  # List of ROIs with positions and descriptors
        self.match_threshold = 0.7  # Default match threshold
        self.match_method = cv2.TM_CCOEFF_NORMED
        self.template_regions = []  # Regions used for template matching
        self.window_size = (0, 0)  # Store window size for scaling
    
    def load_template_image(self) -> bool:
        """Load the template image from path"""
        if not self.image_path or not os.path.exists(self.image_path):
            return False
        
        try:
            self.template_image = cv2.imread(self.image_path)
            return self.template_image is not None
        except Exception as e:
            logging.error(f"Failed to load template image: {str(e)}")
            return False
    
    def add_roi(self, roi_data: Dict[str, Any], is_fixed: bool = True) -> None:
        """Add a ROI to the template
        
        Args:
            roi_data: Dictionary containing ROI information
            is_fixed: Whether this ROI has fixed coordinates (True) or should be transformed (False)
        """
        # Add is_fixed flag to the ROI data
        roi_data["is_fixed"] = is_fixed
        self.rois.append(roi_data)
    
    def add_template_region(self, region: Dict[str, Any]) -> None:
        """Add a region used for template matching"""
        self.template_regions.append(region)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert template to dictionary for serialization"""
        return {
            "name": self.name,
            "image_path": self.image_path,
            "rois": self.rois,
            "match_threshold": self.match_threshold,
            "match_method": int(self.match_method),
            "template_regions": self.template_regions,
            "window_size": self.window_size
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Template':
        """Create a template from dictionary data"""
        template = cls(data["name"], data["image_path"])
        template.rois = data["rois"]
        template.match_threshold = data["match_threshold"]
        template.match_method = data["match_method"]
        template.template_regions = data.get("template_regions", [])
        template.window_size = data.get("window_size", (0, 0))
        return template


class TemplateManager:
    """Manager for UI templates with fixed ROIs and template matching"""
    def __init__(self, root, roi_manager=None):
        self.root = root
        self.roi_manager = roi_manager
        self.templates: List[Template] = []
        self.current_template: Optional[Template] = None
        self.window = None
        self.template_rois = []
        
        # Initialize UI variables to avoid AttributeError
        self.template_name_var = tk.StringVar()
        self.template_path_var = tk.StringVar()
        self.roi_count_var = tk.StringVar()
        self.match_threshold_var = tk.DoubleVar(value=0.7)
        self.match_method_var = tk.StringVar()
        self.threshold_label = None
        self.template_combobox = None
        self.region_tree = None
        self.roi_tree = None
        
        # Create templates directory if it doesn't exist
        self.templates_dir = "templates"
        os.makedirs(self.templates_dir, exist_ok=True)
        
        # Load existing templates
        self.load_templates()
    
    def load_templates(self) -> None:
        """Load all templates from the templates directory"""
        self.templates = []
        
        if not os.path.exists(self.templates_dir):
            return
        
        for filename in os.listdir(self.templates_dir):
            if filename.endswith(".json"):
                try:
                    with open(os.path.join(self.templates_dir, filename), "r") as f:
                        template_data = json.load(f)
                        template = Template.from_dict(template_data)
                        self.templates.append(template)
                        logging.info(f"Loaded template: {template.name}")
                except Exception as e:
                    logging.error(f"Failed to load template {filename}: {str(e)}")
    
    def save_template(self, template: Template) -> bool:
        """Save a template to a JSON file"""
        if not template.name:
            logging.error("Cannot save template with empty name")
            return False
        
        try:
            filename = os.path.join(self.templates_dir, f"{template.name}.json")
            with open(filename, "w") as f:
                json.dump(template.to_dict(), f, indent=4)
            
            logging.info(f"Saved template: {template.name}")
            
            # Reload templates list
            if template not in self.templates:
                self.templates.append(template)
            
            return True
        except Exception as e:
            logging.error(f"Failed to save template {template.name}: {str(e)}")
            return False
    
    def delete_template(self, template_name: str) -> bool:
        """Delete a template from the library"""
        filename = os.path.join(self.templates_dir, f"{template_name}.json")
        if not os.path.exists(filename):
            logging.error(f"Template file not found: {filename}")
            return False
        
        try:
            os.remove(filename)
            
            # Remove from templates list
            self.templates = [t for t in self.templates if t.name != template_name]
            
            logging.info(f"Deleted template: {template_name}")
            return True
        except Exception as e:
            logging.error(f"Failed to delete template {template_name}: {str(e)}")
            return False
    
    def create_new_template(self, image_path: str = None) -> None:
        """Create a new template from the current image and ROIs"""
        if self.roi_manager is None or not self.roi_manager.roi_rectangles:
            messagebox.showwarning("Warning", "No ROIs defined. Please define ROIs first.")
            return
        
        template_name = simpledialog.askstring("Template Name", "Enter a name for this template:")
        if not template_name:
            return
        
        # Check if template name already exists
        if any(t.name == template_name for t in self.templates):
            overwrite = messagebox.askyesno("Template Exists", 
                                           f"A template named '{template_name}' already exists. Overwrite?")
            if not overwrite:
                return
        
        # Get image path from roi_manager parent
        if image_path is None:
            try:
                # Get image path from parent app
                parent_app = self.roi_manager._get_parent_app()
                image_path = parent_app.image_path
                # Get window size for scaling reference
                window_size = (parent_app.canvas.winfo_width(), parent_app.canvas.winfo_height())
            except:
                image_path = None
                window_size = (0, 0)
        else:
            window_size = (0, 0)
        
        # Create new template
        template = Template(template_name, image_path)
        template.window_size = window_size
        
        # Show dialog to ask which ROIs should be fixed vs. transformed
        self.show_roi_type_selection_dialog(template)
        
        # If no template regions were added and ROIs were added, save the template
        if template.rois:
            # Save template
            if self.save_template(template):
                messagebox.showinfo("Success", f"Template '{template_name}' saved successfully.")
                
                # Update template selection if window is open
                if self.window and hasattr(self, "template_combobox"):
                    self.refresh_template_list()
    
    def show_roi_type_selection_dialog(self, template: Template) -> None:
        """Show dialog to select which ROIs should be fixed vs. transformed"""
        if not self.roi_manager or not self.roi_manager.roi_rectangles:
            return
        
        # Create a dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("ROI Type Selection")
        dialog.geometry("600x500")
        dialog.grab_set()  # Make it modal
        
        # Create frame with instructions
        instruction_frame = ttk.Frame(dialog, padding=10)
        instruction_frame.pack(fill=tk.X)
        
        ttk.Label(instruction_frame, text="Choose ROI Types", 
                font=("Segoe UI", 14, "bold")).pack(anchor=tk.W)
        
        ttk.Label(instruction_frame, text="""
        For each ROI, specify whether it should be:
        
        - Fixed Position: ROI will appear exactly where it was defined
        - Template Matched: ROI position will be adjusted based on template matching
            
        You must also define at least one reference region for template matching.
        These regions are used to align the template with new images.
        """, 
                font=("Segoe UI", 10), 
                justify=tk.LEFT).pack(pady=5)
        
        # Create main content frame
        content_frame = ttk.Frame(dialog, padding=10)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left side: ROI selection
        left_frame = ttk.LabelFrame(content_frame, text="ROIs")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Create treeview with checkboxes
        columns = ("select", "name", "type")
        tree = ttk.Treeview(left_frame, columns=columns, show="headings", selectmode="browse")
        tree.heading("select", text="Select")
        tree.heading("name", text="ROI Name")
        tree.heading("type", text="Type")
        
        tree.column("select", width=50, anchor=tk.CENTER)
        tree.column("name", width=150)
        tree.column("type", width=150)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tree.configure(yscrollcommand=scrollbar.set)
        
        # Right side: Reference region selection
        right_frame = ttk.LabelFrame(content_frame, text="Reference Regions (for template matching)")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        ref_columns = ("select", "name")
        ref_tree = ttk.Treeview(right_frame, columns=ref_columns, show="headings", selectmode="browse")
        ref_tree.heading("select", text="Select")
        ref_tree.heading("name", text="ROI Name")
        
        ref_tree.column("select", width=50, anchor=tk.CENTER)
        ref_tree.column("name", width=200)
        
        ref_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        ref_scrollbar = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=ref_tree.yview)
        ref_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        ref_tree.configure(yscrollcommand=ref_scrollbar.set)
        
        # Populate ROI trees
        roi_vars = {}
        ref_vars = {}
        type_vars = {}
        
        for roi in self.roi_manager.roi_rectangles:
            roi_num = roi['roi_num']
            roi_name = roi.get('name', f"ROI {roi_num}")
            
            # Create variables for checkboxes
            roi_vars[roi_num] = tk.BooleanVar(value=True)  # By default, include all ROIs
            ref_vars[roi_num] = tk.BooleanVar(value=False)  # By default, not a reference region
            type_vars[roi_num] = tk.StringVar(value="Fixed")  # By default, fixed position
            
            # Add to ROI tree
            item_id = tree.insert("", "end", values=("✓", roi_name, "Fixed"))
            tree.item(item_id, tags=(str(roi_num),))
            
            # Add to reference tree
            ref_item_id = ref_tree.insert("", "end", values=("□", roi_name))
            ref_tree.item(ref_item_id, tags=(str(roi_num),))
        
        # Handle tree item clicks for selection toggle
        def toggle_roi_selection(event):
            item_id = tree.identify_row(event.y)
            if not item_id:
                return
                
            roi_num = int(tree.item(item_id, "tags")[0])
            current_val = roi_vars[roi_num].get()
            roi_vars[roi_num].set(not current_val)
            
            # Update UI
            tree.item(item_id, values=("✓" if not current_val else "□", 
                                     tree.item(item_id, "values")[1],
                                     tree.item(item_id, "values")[2]))
        
        def toggle_ref_selection(event):
            item_id = ref_tree.identify_row(event.y)
            if not item_id:
                return
                
            roi_num = int(ref_tree.item(item_id, "tags")[0])
            current_val = ref_vars[roi_num].get()
            ref_vars[roi_num].set(not current_val)
            
            # Update UI
            ref_tree.item(item_id, values=("✓" if not current_val else "□", 
                                         ref_tree.item(item_id, "values")[1]))
        
        def toggle_roi_type(event):
            item_id = tree.identify_row(event.y)
            if not item_id:
                return
                
            roi_num = int(tree.item(item_id, "tags")[0])
            current_type = type_vars[roi_num].get()
            new_type = "Template Matched" if current_type == "Fixed" else "Fixed"
            type_vars[roi_num].set(new_type)
            
            # Update UI
            tree.item(item_id, values=(tree.item(item_id, "values")[0], 
                                     tree.item(item_id, "values")[1], 
                                     new_type))
        
        # Bind clicks to toggle selection
        tree.bind("<Button-1>", lambda e: toggle_roi_selection(e) if tree.identify_column(e.x) == "#1" else 
                                        toggle_roi_type(e) if tree.identify_column(e.x) == "#3" else None)
        ref_tree.bind("<Button-1>", lambda e: toggle_ref_selection(e) if ref_tree.identify_column(e.x) == "#1" else None)
        
        # Bottom buttons
        btn_frame = ttk.Frame(dialog, padding=10)
        btn_frame.pack(fill=tk.X)
        
        def confirm_selection():
            # Validate at least one reference region if there are template-matched ROIs
            has_template_matched = any(type_vars[roi_num].get() == "Template Matched" and roi_vars[roi_num].get() 
                                     for roi_num in type_vars)
            has_reference = any(ref_vars[roi_num].get() for roi_num in ref_vars)
            
            if has_template_matched and not has_reference:
                messagebox.showwarning("Warning", 
                                      "You need at least one reference region for template matching.")
                return
            
            # Add selected ROIs to template
            for roi in self.roi_manager.roi_rectangles:
                roi_num = roi['roi_num']
                
                # Skip if not selected
                if not roi_vars[roi_num].get():
                    continue
                
                # Add to template with fixed/template-matched flag
                is_fixed = type_vars[roi_num].get() == "Fixed"
                
                template.add_roi({
                    "name": roi.get("name", f"ROI {roi_num}"),
                    "coordinates": roi["original_coords"],
                    "roi_num": roi_num
                }, is_fixed=is_fixed)
            
            # Add selected reference regions
            for roi in self.roi_manager.roi_rectangles:
                roi_num = roi['roi_num']
                
                # Skip if not selected as reference
                if not ref_vars[roi_num].get():
                    continue
                
                # Add to template as reference region
                template.add_template_region({
                    "name": roi.get("name", f"Reference {roi_num}"),
                    "coordinates": roi["original_coords"]
                })
            
            dialog.destroy()
        
        confirm_btn = ttk.Button(btn_frame, text="Confirm", command=confirm_selection)
        confirm_btn.pack(side=tk.RIGHT, padx=5)
        
        cancel_btn = ttk.Button(btn_frame, text="Cancel", command=dialog.destroy)
        cancel_btn.pack(side=tk.RIGHT, padx=5)
        
        # Wait for the dialog to be closed
        dialog.wait_window()
    
    def show_window(self) -> None:
        """Show the template manager window"""
        if self.window:
            self.window.destroy()
        
        self.window = tk.Toplevel(self.root)
        self.window.title("Template Manager")
        self.window.geometry("800x600")
        self.window.minsize(800, 600)
        
        # Create main frame with padding
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create header
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        header_label = ttk.Label(header_frame, text="Template Manager", 
                                font=("Segoe UI", 16, "bold"))
        header_label.pack(side=tk.LEFT)
        
        # Create split view (templates list on left, template editor on right)
        split_frame = ttk.Frame(main_frame)
        split_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left panel for template list
        left_panel = ttk.LabelFrame(split_frame, text="Templates")
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Template list controls
        controls_frame = ttk.Frame(left_panel)
        controls_frame.pack(fill=tk.X, pady=5)
        
        # Template selection
        select_frame = ttk.Frame(controls_frame)
        select_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(select_frame, text="Select Template:").pack(side=tk.LEFT, padx=5)
        
        self.template_combobox = ttk.Combobox(select_frame, state="readonly")
        self.template_combobox.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.template_combobox.bind("<<ComboboxSelected>>", self.on_template_selected)
        
        # Refresh template list
        self.refresh_template_list()
        
        # Template operations buttons
        btn_frame = ttk.Frame(left_panel)
        btn_frame.pack(fill=tk.X, pady=5)
        
        self.new_btn = ttk.Button(btn_frame, text="New Template", 
                                command=self.create_new_template)
        self.new_btn.pack(side=tk.LEFT, padx=5)
        
        self.delete_btn = ttk.Button(btn_frame, text="Delete Template", 
                                   command=self.delete_selected_template)
        self.delete_btn.pack(side=tk.LEFT, padx=5)
        
        self.apply_btn = ttk.Button(btn_frame, text="Apply to Current Image", 
                                  command=self.apply_template_to_current_image)
        self.apply_btn.pack(side=tk.LEFT, padx=5)
        
        # Right panel for template details
        right_panel = ttk.LabelFrame(split_frame, text="Template Details")
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # Template details sections
        details_frame = ttk.Frame(right_panel)
        details_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Template info
        info_frame = ttk.LabelFrame(details_frame, text="Template Information")
        info_frame.pack(fill=tk.X, pady=5)
        
        info_grid = ttk.Frame(info_frame)
        info_grid.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(info_grid, text="Name:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(info_grid, textvariable=self.template_name_var).grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(info_grid, text="Image:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(info_grid, textvariable=self.template_path_var).grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(info_grid, text="ROIs:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(info_grid, textvariable=self.roi_count_var).grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
        
        # Template match settings
        match_frame = ttk.LabelFrame(details_frame, text="Match Settings")
        match_frame.pack(fill=tk.X, pady=5)
        
        match_settings = ttk.Frame(match_frame)
        match_settings.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(match_settings, text="Match Method:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        
        match_method_combo = ttk.Combobox(match_settings, 
                                        textvariable=self.match_method_var,
                                        values=[m[0] for m in match_methods],
                                        state="readonly")
        match_method_combo.current(0)
        match_method_combo.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        match_method_combo.bind("<<ComboboxSelected>>", lambda e: self.update_match_method(
            match_methods[match_method_combo.current()][1]
        ))
        
        ttk.Label(match_settings, text="Match Threshold:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        
        threshold_frame = ttk.Frame(match_settings)
        threshold_frame.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        
        threshold_slider = ttk.Scale(threshold_frame, from_=0.1, to=1.0,
                                   variable=self.match_threshold_var,
                                   length=150,
                                   command=self.update_threshold_label)
        threshold_slider.pack(side=tk.LEFT)
        
        self.threshold_label = ttk.Label(threshold_frame, text="0.70")
        self.threshold_label.pack(side=tk.LEFT, padx=5)
        
        # Template regions frame
        regions_frame = ttk.LabelFrame(details_frame, text="Template Regions")
        regions_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Template regions list
        self.region_tree = ttk.Treeview(regions_frame, columns=("Name", "Coordinates"), 
                                      show="headings", selectmode="browse")
        self.region_tree.heading("Name", text="Name")
        self.region_tree.heading("Coordinates", text="Coordinates")
        self.region_tree.column("Name", width=150)
        self.region_tree.column("Coordinates", width=250)
        self.region_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        regions_scrollbar = ttk.Scrollbar(regions_frame, orient=tk.VERTICAL, 
                                        command=self.region_tree.yview)
        regions_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.region_tree.configure(yscrollcommand=regions_scrollbar.set)
        
        # ROIs list frame
        rois_frame = ttk.LabelFrame(details_frame, text="Predefined ROIs")
        rois_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # ROIs list
        self.roi_tree = ttk.Treeview(rois_frame, columns=("Number", "Name", "Coordinates", "Type"), 
                                   show="headings", selectmode="browse")
        self.roi_tree.heading("Number", text="#")
        self.roi_tree.heading("Name", text="Name")
        self.roi_tree.heading("Coordinates", text="Coordinates")
        self.roi_tree.heading("Type", text="Type")
        self.roi_tree.column("Number", width=50)
        self.roi_tree.column("Name", width=150)
        self.roi_tree.column("Coordinates", width=250)
        self.roi_tree.column("Type", width=150)
        self.roi_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        rois_scrollbar = ttk.Scrollbar(rois_frame, orient=tk.VERTICAL, 
                                      command=self.roi_tree.yview)
        rois_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.roi_tree.configure(yscrollcommand=rois_scrollbar.set)
        
        # Bottom buttons
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, pady=10)
        
        save_btn = ttk.Button(buttons_frame, text="Save Changes", 
                            command=self.save_current_template)
        save_btn.pack(side=tk.RIGHT, padx=5)
        
        add_region_btn = ttk.Button(buttons_frame, text="Add Region from Selected ROI",
                                   command=self.add_region_from_selected_roi)
        add_region_btn.pack(side=tk.RIGHT, padx=5)
        
        delete_region_btn = ttk.Button(buttons_frame, text="Delete Selected Region",
                                      command=self.delete_selected_region)
        delete_region_btn.pack(side=tk.RIGHT, padx=5)
        
        # Set up the template display if a template is selected
        if self.templates and self.template_combobox.current() >= 0:
            self.on_template_selected(None)
    
    def refresh_template_list(self) -> None:
        """Refresh the list of templates in the combobox"""
        template_names = [t.name for t in self.templates]
        self.template_combobox["values"] = template_names
        
        if template_names:
            self.template_combobox.current(0)
            self.on_template_selected(None)
    
    def on_template_selected(self, event) -> None:
        """Handle template selection event"""
        selected_index = self.template_combobox.current()
        if selected_index < 0 or selected_index >= len(self.templates):
            return
        
        self.current_template = self.templates[selected_index]
        self.update_template_details()
    
    def update_template_details(self) -> None:
        """Update UI with details of the selected template"""
        if not self.current_template:
            return
        
        # Update template info
        self.template_name_var.set(self.current_template.name)
        self.template_path_var.set(self.current_template.image_path or "No image")
        self.roi_count_var.set(str(len(self.current_template.rois)))
        
        # Update match settings
        self.match_threshold_var.set(self.current_template.match_threshold)
        
        # Find match method name from value
        match_methods = [
            ("TM_CCOEFF_NORMED", cv2.TM_CCOEFF_NORMED),
            ("TM_CCORR_NORMED", cv2.TM_CCORR_NORMED),
            ("TM_SQDIFF_NORMED", cv2.TM_SQDIFF_NORMED)
        ]
        
        for name, value in match_methods:
            if value == self.current_template.match_method:
                self.match_method_var.set(name)
                break
        
        # Update threshold label
        self.update_threshold_label(None)
        
        # Update template regions list
        self.region_tree.delete(*self.region_tree.get_children())
        for i, region in enumerate(self.current_template.template_regions):
            coords = f"({region['coordinates'][0]}, {region['coordinates'][1]}, " \
                    f"{region['coordinates'][2]}, {region['coordinates'][3]})"
            self.region_tree.insert("", "end", values=(region.get("name", f"Region {i+1}"), coords))
        
        # Update ROIs list
        self.roi_tree.delete(*self.roi_tree.get_children())
        for roi in self.current_template.rois:
            coords = f"({roi['coordinates'][0]}, {roi['coordinates'][1]}, " \
                    f"{roi['coordinates'][2]}, {roi['coordinates'][3]})"
            roi_type = "Fixed Position" if roi.get("is_fixed", True) else "Template Matched"
            self.roi_tree.insert("", "end", values=(roi["roi_num"], roi["name"], coords, roi_type))
    
    def update_threshold_label(self, event) -> None:
        """Update threshold label when slider is moved"""
        value = self.match_threshold_var.get()
        self.threshold_label.config(text=f"{value:.2f}")
        
        if self.current_template:
            self.current_template.match_threshold = value
    
    def update_match_method(self, method_value: int) -> None:
        """Update match method when selection changes"""
        if self.current_template:
            self.current_template.match_method = method_value
    
    def save_current_template(self) -> None:
        """Save changes to the current template"""
        if not self.current_template:
            return
        
        # Update template with current settings
        self.current_template.match_threshold = self.match_threshold_var.get()
        
        # Save template to file
        if self.save_template(self.current_template):
            messagebox.showinfo("Success", f"Template '{self.current_template.name}' saved successfully.")
    
    def delete_selected_template(self) -> None:
        """Delete the currently selected template"""
        selected_index = self.template_combobox.current()
        if selected_index < 0 or selected_index >= len(self.templates):
            return
        
        template_name = self.templates[selected_index].name
        confirm = messagebox.askyesno("Confirm Delete", 
                                     f"Are you sure you want to delete the template '{template_name}'?")
        
        if confirm:
            if self.delete_template(template_name):
                messagebox.showinfo("Success", f"Template '{template_name}' deleted successfully.")
                self.refresh_template_list()
    
    def add_region_from_selected_roi(self) -> None:
        """Add a template region from a currently selected ROI"""
        if not self.current_template or not self.roi_manager:
            return
        
        selected_roi_index = self.roi_manager.get_selected_roi_index()
        if selected_roi_index is None:
            messagebox.showinfo("Information", "No ROI selected. Please select an ROI first.")
            return
        
        # Get the selected ROI
        roi = self.roi_manager.roi_rectangles[selected_roi_index]
        
        # Ask for region name
        region_name = simpledialog.askstring("Region Name", 
                                          "Enter a name for this template region:",
                                          initialvalue=f"Region {len(self.current_template.template_regions) + 1}")
        
        if not region_name:
            return
        
        # Add region to template
        region = {
            "name": region_name,
            "coordinates": roi["original_coords"]
        }
        
        self.current_template.add_template_region(region)
        
        # Update UI
        self.update_template_details()
        
        # Save changes
        self.save_current_template()
    
    def delete_selected_region(self) -> None:
        """Delete the selected template region"""
        if not self.current_template:
            return
        
        selected_item = self.region_tree.selection()
        if not selected_item:
            return
        
        selected_index = self.region_tree.index(selected_item[0])
        
        # Confirm deletion
        region_name = self.current_template.template_regions[selected_index].get("name", f"Region {selected_index+1}")
        confirm = messagebox.askyesno("Confirm Delete", 
                                     f"Are you sure you want to delete the region '{region_name}'?")
        
        if confirm:
            # Remove region from template
            del self.current_template.template_regions[selected_index]
            
            # Update UI
            self.update_template_details()
            
            # Save changes
            self.save_current_template()
    
    def apply_template_to_current_image(self) -> None:
        """Apply the current template to the current image"""
        if not self.current_template or not self.roi_manager:
            return
        
        try:
            # Get parent app
            parent_app = self.roi_manager._get_parent_app()
            
            if not parent_app.image:
                messagebox.showinfo("Information", "No image loaded. Please load an image first.")
                return
            
            # Confirm application
            confirm = messagebox.askyesno("Confirm Apply", 
                                         f"Apply template '{self.current_template.name}' to the current image? "
                                         f"This will replace any existing ROIs.")
            
            if not confirm:
                return
            
            # Apply template
            success = self.apply_template(parent_app.image, parent_app)
            
            if success:
                messagebox.showinfo("Success", f"Template '{self.current_template.name}' applied successfully.")
            else:
                messagebox.showwarning("Warning", "Failed to apply template. Check the logs for details.")
        
        except Exception as e:
            logging.error(f"Error applying template: {str(e)}")
            messagebox.showerror("Error", f"Failed to apply template: {str(e)}")
    
    def apply_template(self, image, parent_app) -> bool:
        """Apply a template to an image"""
        if not self.current_template or not image:
            return False
        
        # Load template image if not already loaded
        if self.current_template.template_image is None:
            if not self.current_template.load_template_image():
                logging.error("Failed to load template image")
                return False
        
        # Clear existing ROIs
        parent_app.clear_rois()
        
        try:
            # Check if we need to do template matching
            has_template_matched_rois = any(not roi.get("is_fixed", True) for roi in self.current_template.rois)
            
            # Calculate window size scaling if needed
            template_width, template_height = self.current_template.window_size
            current_width, current_height = parent_app.canvas.winfo_width(), parent_app.canvas.winfo_height()
            
            # Default to no scaling if sizes are invalid
            window_scale_x = current_width / template_width if template_width > 0 else 1.0
            window_scale_y = current_height / template_height if template_height > 0 else 1.0
            
            # Find template transform if needed
            transform = None
            if has_template_matched_rois and self.current_template.template_regions:
                # Find the transform using template matching
                transform = self._find_template_transform(image)
                
                if transform is None:
                    logging.warning("Could not find matching regions in the image")
                    messagebox.showwarning("Warning", 
                                         "Could not find matching regions in the image. " +
                                         "Fixed position ROIs will still be applied.")
            
            # Process each ROI based on its type
            for roi_data in self.current_template.rois:
                x1, y1, x2, y2 = roi_data["coordinates"]
                is_fixed = roi_data.get("is_fixed", True)
                
                if is_fixed:
                    # For fixed ROIs, apply only window scaling
                    # This adjusts for changes in window size
                    new_x1 = int(x1 * window_scale_x)
                    new_y1 = int(y1 * window_scale_y)
                    new_x2 = int(x2 * window_scale_x)
                    new_y2 = int(y2 * window_scale_y)
                elif transform:
                    # For template-matched ROIs, apply the full transform
                    scale_x, scale_y, offset_x, offset_y = transform
                    
                    # Apply transform
                    new_x1 = int(x1 * scale_x + offset_x)
                    new_y1 = int(y1 * scale_y + offset_y)
                    new_x2 = int(x2 * scale_x + offset_x)
                    new_y2 = int(y2 * scale_y + offset_y)
                else:
                    # Fall back to fixed positioning if transform is not available
                    new_x1 = int(x1 * window_scale_x)
                    new_y1 = int(y1 * window_scale_y)
                    new_x2 = int(x2 * window_scale_x)
                    new_y2 = int(y2 * window_scale_y)
                
                # Ensure coordinates are within image bounds
                h, w = image.shape[:2]
                new_x1 = max(0, min(new_x1, w-1))
                new_y1 = max(0, min(new_y1, h-1))
                new_x2 = max(0, min(new_x2, w-1))
                new_y2 = max(0, min(new_y2, h-1))
                
                # Add ROI to parent app
                self._add_roi_to_parent(parent_app, (new_x1, new_y1, new_x2, new_y2), roi_data["name"])
            
            return True
        
        except Exception as e:
            logging.error(f"Error applying template: {str(e)}")
            return False
    
    def _find_template_transform(self, image) -> Optional[Tuple[float, float, float, float]]:
        """Find transformation between template and current image using template matching"""
        if not self.current_template or not self.current_template.template_image or not image:
            return None
        
        if not self.current_template.template_regions:
            return 1.0, 1.0, 0, 0  # No transform needed
        
        # Get template image and regions
        template_img = self.current_template.template_image
        regions = self.current_template.template_regions
        
        # Match each region and collect correspondences
        correspondences = []
        
        for region in regions:
            x1, y1, x2, y2 = region["coordinates"]
            region_img = template_img[y1:y2, x1:x2]
            
            # Skip if region is too small
            if region_img.shape[0] < 10 or region_img.shape[1] < 10:
                continue
            
            # Match region in target image
            match_result = cv2.matchTemplate(image, region_img, self.current_template.match_method)
            _, max_val, _, max_loc = cv2.minMaxLoc(match_result)
            
            # If match is good enough, add to correspondences
            if max_val >= self.current_template.match_threshold:
                # Template matching gives top-left corner, calculate center
                template_center_x = (x1 + x2) / 2
                template_center_y = (y1 + y2) / 2
                
                # Target center is the matched location plus half the template size
                target_center_x = max_loc[0] + region_img.shape[1] / 2
                target_center_y = max_loc[1] + region_img.shape[0] / 2
                
                correspondences.append((template_center_x, template_center_y, target_center_x, target_center_y))
        
        # If no good matches found, return None
        if not correspondences:
            return None
        
        # Calculate average scale and offset
        scale_x_sum = 0
        scale_y_sum = 0
        offset_x_sum = 0
        offset_y_sum = 0
        
        # If only one correspondence, use 1.0 scale
        if len(correspondences) == 1:
            template_x, template_y, target_x, target_y = correspondences[0]
            return 1.0, 1.0, target_x - template_x, target_y - template_y
        
        # Calculate pairwise scales and offsets
        pair_count = 0
        
        for i in range(len(correspondences)):
            for j in range(i + 1, len(correspondences)):
                template_x1, template_y1, target_x1, target_y1 = correspondences[i]
                template_x2, template_y2, target_x2, target_y2 = correspondences[j]
                
                # Calculate scale between points
                dx_template = template_x2 - template_x1
                dy_template = template_y2 - template_y1
                dx_target = target_x2 - target_x1
                dy_target = target_y2 - target_y1
                
                # Avoid division by zero
                if abs(dx_template) > 1 and abs(dy_template) > 1:
                    scale_x = dx_target / dx_template
                    scale_y = dy_target / dy_template
                    
                    scale_x_sum += scale_x
                    scale_y_sum += scale_y
                    pair_count += 1
        
        # If no valid pairs, use scale 1.0
        if pair_count == 0:
            scale_x = 1.0
            scale_y = 1.0
        else:
            scale_x = scale_x_sum / pair_count
            scale_y = scale_y_sum / pair_count
        
        # Calculate offsets using the computed scale
        for template_x, template_y, target_x, target_y in correspondences:
            offset_x_sum += target_x - template_x * scale_x
            offset_y_sum += target_y - template_y * scale_y
        
        offset_x = offset_x_sum / len(correspondences)
        offset_y = offset_y_sum / len(correspondences)
        
        return scale_x, scale_y, offset_x, offset_y
    
    def _add_roi_to_parent(self, parent_app, coordinates, name=None) -> None:
        """Add a ROI to the parent application"""
        try:
            # Convert coordinates to canvas coordinates
            x1, y1, x2, y2 = coordinates
            canvas_x1 = int(x1 * parent_app.scale_factor)
            canvas_y1 = int(y1 * parent_app.scale_factor)
            canvas_x2 = int(x2 * parent_app.scale_factor)
            canvas_y2 = int(y2 * parent_app.scale_factor)
            
            # Create rectangle on canvas
            canvas_rect = parent_app.canvas.create_rectangle(
                canvas_x1, canvas_y1, canvas_x2, canvas_y2,
                outline="red", width=2
            )
            
            # Add ROI number to the rectangle
            roi_num = len(parent_app.roi_rectangles) + 1
            text_x = min(canvas_x1, canvas_x2) + 5
            text_y = min(canvas_y1, canvas_y2) + 5
            text_id = parent_app.canvas.create_text(text_x, text_y, text=f"ROI {roi_num}", 
                                                  fill="red", anchor=tk.NW)
            
            # Include template information in the ROI
            template_info = {
                "template_name": self.current_template.name,
                "roi_type": "Fixed" if self._is_fixed_roi(name) else "Template-Matched"
            }
            
            # Store ROI
            parent_app.roi_rectangles.append({
                'canvas_coords': (canvas_x1, canvas_y1, canvas_x2, canvas_y2),
                'original_coords': (x1, y1, x2, y2),
                'canvas_rect': canvas_rect,
                'roi_num': roi_num,
                'text_id': text_id,
                'name': name or f"ROI {roi_num}",
                'template_info': template_info
            })
            
            # Update ROI Manager
            parent_app.roi_manager.set_roi_data(parent_app.roi_rectangles)
            
            logging.info(f"Added ROI {roi_num} from template: {x1}, {y1}, {x2}, {y2}")
        
        except Exception as e:
            logging.error(f"Error adding ROI from template: {str(e)}")
    
    def _is_fixed_roi(self, name: str) -> bool:
        """Determine if ROI is fixed based on its name in the current template"""
        if not self.current_template:
            return True
            
        for roi in self.current_template.rois:
            if roi["name"] == name:
                return roi.get("is_fixed", True)
                
        return True


def find_template_matches(image, template_image, match_method=cv2.TM_CCOEFF_NORMED, threshold=0.7):
    """Find all matches of template_image in image"""
    if image is None or template_image is None:
        return []
    
    # Perform template matching
    result = cv2.matchTemplate(image, template_image, match_method)
    
    # Find all locations where the match exceeds the threshold
    locations = []
    h, w = template_image.shape[:2]
    
    # Different handling based on match method
    if match_method in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED]:
        # For these methods, smaller values indicate better matches
        match_indices = np.where(result <= 1.0 - threshold)
    else:
        # For other methods, larger values indicate better matches
        match_indices = np.where(result >= threshold)
    
    # Get coordinates and match values
    match_points = list(zip(*match_indices[::-1]))
    
    for pt in match_points:
        x, y = pt
        match_val = result[y, x]
        
        # Adjust match value for SQDIFF methods
        if match_method in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED]:
            confidence = 1.0 - match_val
        else:
            confidence = match_val
        
        # Add to locations with confidence value
        locations.append((x, y, w, h, confidence))
    
    return locations 