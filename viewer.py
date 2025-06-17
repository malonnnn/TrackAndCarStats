import os
import csv
import tkinter as tk
from tkinter import ttk, messagebox
from operator import itemgetter

def normalize_path(path):
    """Normalize a path to use forward slashes for consistency."""
    return path.replace('\\', '/')

class TrackAndCarStatsViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("TACS Records Viewer")
        self.root.geometry("650x450") # Slightly larger for better viewing
        
        # --- Main Frame ---
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        
        # --- Track Selection ---
        track_frame = ttk.Frame(main_frame)
        track_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        ttk.Label(track_frame, text="Filter by Track:").pack(side=tk.LEFT, padx=(0, 5))
        self.track_var = tk.StringVar(value="All Tracks")
        self.track_combo = ttk.Combobox(track_frame, textvariable=self.track_var, state="readonly")
        self.track_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # --- Records Treeview ---
        self.tree = ttk.Treeview(main_frame, columns=("Track", "Time", "Car"), show="headings")
        self.tree.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.grid(row=1, column=1, sticky=(tk.N, tk.S))
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # --- Sorting State Management ---
        self.sort_states = {
            "track": False,  # False = ascending, True = descending
            "time_ms": False,
            "car": False
        }
        
        # Map between internal keys and display columns for clarity
        self.column_map = {
            "track": "Track",
            "time_ms": "Time",
            "car": "Car"
        }
        
        # --- Configure Treeview Columns and Headings ---
        self.tree.heading("Track", text="Track", command=lambda: self.sort_records("track"))
        self.tree.heading("Time", text="Time", command=lambda: self.sort_records("time_ms"))
        self.tree.heading("Car", text="Car", command=lambda: self.sort_records("car"))
        
        self.tree.column("Track", width=220, anchor=tk.W)
        self.tree.column("Time", width=100, anchor=tk.W)
        self.tree.column("Car", width=280, anchor=tk.W)
        
        # Make the treeview expandable
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # --- Data and Initialization ---
        self.all_records = []
        self.displayed_records = []
        self.load_records()
        
        # Bind track selection change to the filter function
        self.track_combo.bind("<<ComboboxSelected>>", self.filter_records)
        
        # --- Style Configuration ---
        style = ttk.Style()
        style.configure("Treeview", rowheight=25, font=("TkDefaultFont", 9))
        style.configure("Treeview.Heading", font=("TkDefaultFont", 10, "bold"))
        
        # Set initial sort
        self.sort_records('track')

    # The following 'def' statements were incorrectly indented. They are now corrected.
    def format_time(self, ms):
        """Convert milliseconds to a formatted time string MM:SS.mmm."""
        if not isinstance(ms, (int, float)) or ms <= 0:
            return "0:00.000"
        
        total_seconds = ms / 1000.0
        minutes = int(total_seconds // 60)
        seconds = total_seconds % 60
        return "{:d}:{:06.3f}".format(minutes, seconds)

    def load_records(self):
        """Load records from all track CSV files located in the 'records' subdirectory."""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        records_dir = os.path.join(script_dir, "records")
        self.all_records = []
        
        if not os.path.exists(records_dir):
            messagebox.showerror("Directory Not Found", 
                             f"The records directory was not found at:\n{records_dir}")
            return
        
        csv_files = [f for f in os.listdir(records_dir) if f.endswith('.csv')]
        if not csv_files:
            messagebox.showwarning("No Records Found", 
                           f"No CSV files found in:\n{records_dir}")
            return
        
        for filename in csv_files:
            # Extract track name from filename (remove rt_ prefix and .csv extension)
            track_name = os.path.splitext(filename)[0]
            if track_name.startswith('rt_'):
                track_name = track_name[3:]  # Remove 'rt_' prefix
            track_name = track_name.replace('_', ' ').title()  # Format for display
            
            track_file = os.path.join(records_dir, filename)
            
            try:
                with open(track_file, 'r', newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)  # Use DictReader to read by column names
                    for row in reader:
                        try:
                            car_name = row['CarName']
                            time_ms = int(row['Time_ms'])
                            
                            if time_ms <= 0:
                                continue
                                
                            self.all_records.append({
                                'track': track_name,
                                'car': car_name,
                                'time_ms': time_ms
                            })
                        except (KeyError, ValueError) as e:
                            print(f"Error processing row in {filename}: {str(e)}")
                            continue
                        
            except Exception as e:
                print(f"Error processing {filename}: {str(e)}")
                continue
    
        if not self.all_records:
            messagebox.showwarning("No Valid Records", 
                           "No valid records were found in any of the CSV files.")
            return
        
        # Update track list in the combobox
        track_names = sorted(list(set(r['track'] for r in self.all_records)))
        track_names.insert(0, "All Tracks")
        self.track_combo['values'] = track_names
        self.track_var.set("All Tracks")
        
        # Initial filter and display
        self.filter_records()
        
    def sort_records(self, key):
        """Sort currently displayed records by the given key and update the treeview."""
        # Toggle sort state for the clicked column
        is_reverse = self.sort_states.get(key, False)
        self.sort_states[key] = not is_reverse
        
        # Reset other columns' sort state
        for col_key in self.sort_states:
            if col_key != key:
                self.sort_states[col_key] = False

        # Sort the currently displayed records
        self.displayed_records.sort(key=itemgetter(key), reverse=self.sort_states[key])
        
        self.update_treeview()

    def filter_records(self, event=None):
        """Filter all records based on the selected track."""
        selected_track = self.track_var.get()
        
        if selected_track == "All Tracks":
            self.displayed_records = list(self.all_records)
        else:
            self.displayed_records = [r for r in self.all_records if r['track'] == selected_track]
            
        # After filtering, re-apply the last known sort or a default one
        # Find the currently active sort key
        active_sort_key = 'track' # Default sort
        for key, is_reversed in self.sort_states.items():
             # If a column was previously sorted descending, its state would be True
             if is_reversed or self.tree.heading(self.column_map[key])['text'].endswith(('↑', '↓')):
                 active_sort_key = key
                 break
        
        self.displayed_records.sort(key=itemgetter(active_sort_key), reverse=self.sort_states.get(active_sort_key, False))
        
        self.update_treeview()
        
    def update_treeview(self):
        """Clear and repopulate the treeview with the records from `self.displayed_records`."""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        # Update column headers to show sort direction
        for col_key, column_name in self.column_map.items():
            text = column_name
            if self.sort_states.get(col_key, False):
                text += " ↑" # Descending
            else:
                # If it's the active sort column but ascending, show down arrow
                if self.tree.heading(column_name, "command") and self.sort_states.get(col_key) is not None:
                     # Check if this column was the one just clicked
                     is_active = any(self.sort_states.values())
                     if is_active and not self.sort_states[col_key]:
                         # Find if this is the active ascending sort
                         active_key = next((k for k, v in self.sort_states.items() if v is False and self.tree.heading(self.column_map[k])['text'].endswith('↓')), None)
                         if active_key == col_key:
                            text += " ↓" # Ascending
        
        # Insert filtered and sorted records
        for record in self.displayed_records:
            time_str = self.format_time(record['time_ms'])
            self.tree.insert("", "end", values=(record['track'], time_str, record['car']))


if __name__ == '__main__':
    try:
        root = tk.Tk()
        app = TrackAndCarStatsViewer(root)
        root.mainloop()
    except Exception as e:
        # A fallback for any unexpected errors during app startup
        messagebox.showerror("Application Error", "A critical error occurred:\n\n{}".format(e))