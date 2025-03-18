import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import cv2
import os
import json
from PIL import Image, ImageTk
import logging

class TargetImage:
    def __init__(self, path, description, image=None):
        self.path = path
        self.description = description
        self.image = image if image is not None else cv2.imread(path)
        self.filename = os.path.basename(path)
    
    def to_dict(self):
        """Convert target image to dictionary for JSON serialization"""
        return {
            "path": self.path,
            "description": self.description,
            "filename": self.filename
        }

class TargetImageManager:
    def __init__(self, parent):
        self.parent = parent
        self.target_images = []
        self.current_preview = None
        
        # Create a new window
        self.window = tk.Toplevel(parent)
        self.window.title("Target Image Manager")
        self.window.geometry("600x500")
        self.window.protocol("WM_DELETE_WINDOW", self.hide_window)  # Hide instead of destroy
        
        self.setup_ui()
        self.window.withdraw()  # Initially hidden
    
    def setup_ui(self):
        # Main frame
        main_frame = tk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel: Target list and controls
        left_panel = tk.Frame(main_frame, width=300)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Target list with scrollbar
        list_frame = tk.Frame(left_panel)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        self.target_list = ttk.Treeview(list_frame, columns=("Description",), 
                                         show="headings", selectmode="browse")
        self.target_list.heading("Description", text="Description")
        self.target_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.target_list.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.target_list.configure(yscrollcommand=scrollbar.set)
        
        # Bind selection event
        self.target_list.bind("<<TreeviewSelect>>", self.on_target_selected)
        
        # Control buttons
        controls_frame = tk.Frame(left_panel)
        controls_frame.pack(fill=tk.X, pady=10)
        
        add_btn = tk.Button(controls_frame, text="Add Target", command=self.add_target)
        add_btn.pack(side=tk.LEFT, padx=5)
        
        remove_btn = tk.Button(controls_frame, text="Remove Target", command=self.remove_target)
        remove_btn.pack(side=tk.LEFT, padx=5)
        
        edit_btn = tk.Button(controls_frame, text="Edit Description", command=self.edit_description)
        edit_btn.pack(side=tk.LEFT, padx=5)
        
        # Save/Load buttons
        io_frame = tk.Frame(left_panel)
        io_frame.pack(fill=tk.X, pady=5)
        
        save_btn = tk.Button(io_frame, text="Save Target Set", command=self.save_target_set)
        save_btn.pack(side=tk.LEFT, padx=5)
        
        load_btn = tk.Button(io_frame, text="Load Target Set", command=self.load_target_set)
        load_btn.pack(side=tk.LEFT, padx=5)
        
        # Right panel: Preview
        right_panel = tk.LabelFrame(main_frame, text="Target Preview", width=300)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        self.preview_label = tk.Label(right_panel, text="No target selected")
        self.preview_label.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.description_label = tk.Label(right_panel, text="")
        self.description_label.pack(fill=tk.X, padx=10, pady=5)
    
    def show_window(self):
        """Show the target manager window"""
        self.window.deiconify()
        self.window.lift()
    
    def hide_window(self):
        """Hide the target manager window"""
        self.window.withdraw()
    
    def add_target(self):
        """Add a new target image"""
        # Ask for image file
        path = filedialog.askopenfilename(
            title="Select Target Image",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp *.tif *.tiff")]
        )
        
        if not path:
            return
        
        # Ask for description
        description_dialog = tk.Toplevel(self.window)
        description_dialog.title("Target Description")
        description_dialog.geometry("300x150")
        description_dialog.transient(self.window)
        description_dialog.grab_set()
        
        tk.Label(description_dialog, text="Enter a description for this target image:").pack(padx=10, pady=10)
        
        description_var = tk.StringVar()
        entry = tk.Entry(description_dialog, textvariable=description_var, width=30)
        entry.pack(padx=10, pady=5)
        entry.focus_set()
        
        def on_ok():
            description = description_var.get().strip()
            if not description:
                messagebox.showwarning("Warning", "Please enter a description")
                return
            
            # Load the image
            try:
                image = cv2.imread(path)
                if image is None:
                    raise Exception("Failed to load image")
                
                # Add to our list
                target = TargetImage(path, description, image)
                self.target_images.append(target)
                
                # Add to listbox with filename as ID and description as display text
                self.target_list.insert("", "end", iid=target.filename, values=(description,))
                
                logging.info(f"Added target image: {description} ({os.path.basename(path)})")
                description_dialog.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load image: {str(e)}")
                logging.error(f"Error adding target: {str(e)}")
                description_dialog.destroy()
        
        def on_cancel():
            description_dialog.destroy()
        
        button_frame = tk.Frame(description_dialog)
        button_frame.pack(pady=10)
        
        ok_btn = tk.Button(button_frame, text="OK", command=on_ok)
        ok_btn.pack(side=tk.LEFT, padx=10)
        
        cancel_btn = tk.Button(button_frame, text="Cancel", command=on_cancel)
        cancel_btn.pack(side=tk.LEFT, padx=10)
        
        # Handle Enter key to submit
        entry.bind("<Return>", lambda event: on_ok())
    
    def remove_target(self):
        """Remove the selected target image"""
        selected = self.target_list.selection()
        if not selected:
            messagebox.showinfo("Information", "No target selected")
            return
        
        filename = selected[0]
        
        # Remove from our list
        for i, target in enumerate(self.target_images):
            if target.filename == filename:
                del self.target_images[i]
                break
        
        # Remove from treeview
        self.target_list.delete(selected)
        
        # Clear preview if it was showing this target
        self.clear_preview()
        
        logging.info(f"Removed target image: {filename}")
    
    def edit_description(self):
        """Edit the description of the selected target"""
        selected = self.target_list.selection()
        if not selected:
            messagebox.showinfo("Information", "No target selected")
            return
        
        filename = selected[0]
        current_description = self.target_list.item(selected, "values")[0]
        
        # Find the target
        target = next((t for t in self.target_images if t.filename == filename), None)
        if not target:
            return
        
        # Show edit dialog
        edit_dialog = tk.Toplevel(self.window)
        edit_dialog.title("Edit Description")
        edit_dialog.geometry("300x150")
        edit_dialog.transient(self.window)
        edit_dialog.grab_set()
        
        tk.Label(edit_dialog, text="Edit the description:").pack(padx=10, pady=10)
        
        description_var = tk.StringVar(value=current_description)
        entry = tk.Entry(edit_dialog, textvariable=description_var, width=30)
        entry.pack(padx=10, pady=5)
        entry.focus_set()
        entry.select_range(0, tk.END)
        
        def on_ok():
            new_description = description_var.get().strip()
            if not new_description:
                messagebox.showwarning("Warning", "Description cannot be empty")
                return
            
            # Update target
            target.description = new_description
            
            # Update listbox
            self.target_list.item(selected, values=(new_description,))
            
            # Update preview if showing this target
            if self.current_preview == filename:
                self.description_label.config(text=f"Description: {new_description}")
            
            logging.info(f"Updated description for {filename}: {new_description}")
            edit_dialog.destroy()
        
        def on_cancel():
            edit_dialog.destroy()
        
        button_frame = tk.Frame(edit_dialog)
        button_frame.pack(pady=10)
        
        ok_btn = tk.Button(button_frame, text="OK", command=on_ok)
        ok_btn.pack(side=tk.LEFT, padx=10)
        
        cancel_btn = tk.Button(button_frame, text="Cancel", command=on_cancel)
        cancel_btn.pack(side=tk.LEFT, padx=10)
        
        # Handle Enter key to submit
        entry.bind("<Return>", lambda event: on_ok())
    
    def on_target_selected(self, event):
        """Handle selection of a target in the list"""
        selected = self.target_list.selection()
        if not selected:
            self.clear_preview()
            return
        
        filename = selected[0]
        
        # Find the target
        target = next((t for t in self.target_images if t.filename == filename), None)
        if not target:
            self.clear_preview()
            return
        
        # Show preview
        self.show_preview(target)
    
    def show_preview(self, target):
        """Show preview of the selected target"""
        # Convert for display
        rgb_image = cv2.cvtColor(target.image, cv2.COLOR_BGR2RGB)
        
        # Resize if needed
        h, w = rgb_image.shape[:2]
        max_size = 200
        if h > max_size or w > max_size:
            scale = min(max_size / w, max_size / h)
            new_w, new_h = int(w * scale), int(h * scale)
            rgb_image = cv2.resize(rgb_image, (new_w, new_h))
        
        # Convert to PhotoImage
        pil_image = Image.fromarray(rgb_image)
        tk_image = ImageTk.PhotoImage(image=pil_image)
        
        # Update preview
        self.preview_label.config(image=tk_image)
        self.preview_label.image = tk_image  # Keep a reference
        
        # Update description
        self.description_label.config(text=f"Description: {target.description}")
        
        # Store current preview
        self.current_preview = target.filename
    
    def clear_preview(self):
        """Clear the preview area"""
        self.preview_label.config(image="", text="No target selected")
        self.description_label.config(text="")
        self.current_preview = None
    
    def save_target_set(self):
        """Save current target set to a JSON file"""
        if not self.target_images:
            messagebox.showinfo("Information", "No targets to save")
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            # Create data structure
            data = {
                "targets": [target.to_dict() for target in self.target_images]
            }
            
            # Save to file
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=4)
            
            logging.info(f"Target set saved to {file_path}")
            messagebox.showinfo("Success", f"Target set saved to {file_path}")
        except Exception as e:
            logging.error(f"Error saving target set: {str(e)}")
            messagebox.showerror("Error", f"Failed to save target set: {str(e)}")
    
    def load_target_set(self):
        """Load target set from a JSON file"""
        file_path = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            # Load from file
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            if "targets" not in data:
                raise ValueError("Invalid target set file format")
            
            # Clear current targets
            self.target_images = []
            self.target_list.delete(*self.target_list.get_children())
            self.clear_preview()
            
            # Load each target
            for target_data in data["targets"]:
                path = target_data.get("path", "")
                description = target_data.get("description", "")
                
                if not os.path.exists(path):
                    logging.warning(f"Image file not found: {path}")
                    continue
                
                try:
                    # Load the image
                    image = cv2.imread(path)
                    if image is None:
                        logging.warning(f"Failed to load image: {path}")
                        continue
                    
                    # Add to our list
                    target = TargetImage(path, description, image)
                    self.target_images.append(target)
                    
                    # Add to listbox
                    self.target_list.insert("", "end", iid=target.filename, values=(description,))
                except Exception as e:
                    logging.error(f"Error loading target {path}: {str(e)}")
            
            logging.info(f"Loaded {len(self.target_images)} targets from {file_path}")
            messagebox.showinfo("Success", f"Loaded {len(self.target_images)} targets")
        except Exception as e:
            logging.error(f"Error loading target set: {str(e)}")
            messagebox.showerror("Error", f"Failed to load target set: {str(e)}")
    
    def get_all_targets(self):
        """Return all target images for analysis"""
        return self.target_images

# Function to check target images in an ROI
def check_target_matches(roi_img, targets, match_method, threshold):
    """Check if any of the target images match in the ROI"""
    matches = []
    
    for target in targets:
        target_img = target.image
        
        # Skip if target is bigger than ROI
        target_h, target_w = target_img.shape[:2]
        roi_h, roi_w = roi_img.shape[:2]
        
        if target_w > roi_w or target_h > roi_h:
            continue
        
        # Template matching
        result = cv2.matchTemplate(roi_img, target_img, match_method)
        
        # Get the maximum correlation value
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        # For TM_SQDIFF methods, the minimum value is the best match
        if match_method in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED]:
            confidence = 1 - min_val  # Invert for consistency
            match_loc = min_loc
        else:
            confidence = max_val
            match_loc = max_loc
        
        # If it's a match, add to results
        if confidence >= threshold:
            matches.append({
                "description": target.description,
                "filename": target.filename,
                "confidence": confidence,
                "location": match_loc
            })
    
    return matches 