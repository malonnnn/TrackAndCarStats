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
        # This path assumes the script is run from the `TrackAndCarStats` folder.
        script_dir = os.path.dirname(__file__)
        records_dir = normalize_path(os.path.join(script_dir, "records"))
        self.all_records = []
        
        if not os.path.exists(records_dir) or not os.listdir(records_dir):
            messagebox.showwarning("No Records Found", 
                                   "The 'records' directory is empty or missing.\n\n"
                                   "Please ensure this script is in the 'TrackAndCarStats' app folder and that you have completed some laps in Assetto Corsa.")
            return
        
        try:
            for filename in os.listdir(records_dir):
                if filename.endswith(".csv"):
                    track_name = filename[:-4]  # Remove .csv extension
                    track_file = normalize_path(os.path.join(records_dir, filename))
                    
                    with open(track_file, 'r', newline='') as f:
                        reader = csv.reader(f)
                        try:
                            header = next(reader)  # Skip header
                        except StopIteration:
                            continue # Skip empty files

                        # This logic correctly parses the CSV from the AC app
                        for row in reader:
                            if len(row) >= 3:
                                technical_name, time_ms_str, display_name = row[:3]
                                car_name = display_name.strip() if display_name.strip() else technical_name
                                try:
                                    self.all_records.append({
                                        'track': track_name,
                                        'car': car_name,
                                        'time_ms': int(time_ms_str)
                                    })
                                except ValueError:
                                    # Skip rows with invalid time
                                    continue
            
            # Update track list in the combobox
            track_names = sorted(list(set(r['track'] for r in self.all_records)))
            track_names.insert(0, "All Tracks")
            self.track_combo['values'] = track_names
            
            # Initial filter and display
            self.filter_records()
        
        except Exception as e:
            messagebox.showerror("Error Loading Records", "An error occurred while reading the record files:\n\n{}".format(e))

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