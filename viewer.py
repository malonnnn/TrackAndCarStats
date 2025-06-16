import os
import csv
import tkinter as tk
from tkinter import ttk, messagebox
from operator import itemgetter
from collections import defaultdict

def normalize_path(path):
    """Normalize a path to use forward slashes"""
    return path.replace('\\', '/')

class TrackAndCarStatsViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("TNCS Records Viewer")
        self.root.geometry("600x400")
        
        # Create main frame
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        
        # Track selection
        self.track_var = tk.StringVar(value="All Tracks")
        track_frame = ttk.Frame(main_frame)
        track_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        ttk.Label(track_frame, text="Track:").pack(side=tk.LEFT, padx=(0, 5))
        self.track_combo = ttk.Combobox(track_frame, textvariable=self.track_var, state="readonly")
        self.track_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Records treeview
        self.tree = ttk.Treeview(main_frame, columns=("Track", "Time", "Car"), show="headings")
        self.tree.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.grid(row=1, column=1, sticky=(tk.N, tk.S))
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Track sort state
        self.sort_states = {
            "track": False,  # False = ascending, True = descending
            "time_ms": False,
            "car": False
        }
        
        # Map between internal keys and display columns
        self.column_map = {
            "track": "Track",
            "time_ms": "Time",
            "car": "Car"
        }
        
        # Configure treeview columns
        self.tree.heading("Track", text="Track ↓", command=lambda: self.sort_records("track"))
        self.tree.heading("Time", text="Time ↓", command=lambda: self.sort_records("time_ms"))
        self.tree.heading("Car", text="Car ↓", command=lambda: self.sort_records("car"))
        
        self.tree.column("Track", width=200)
        self.tree.column("Time", width=100)
        self.tree.column("Car", width=250)
        
        # Make the treeview expandable
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Load records
        self.records = []
        self.load_records()
        
        # Bind track selection change
        self.track_combo.bind("<<ComboboxSelected>>", self.filter_records)
        
        # Configure style
        style = ttk.Style()
        style.configure("Treeview", rowheight=25)
        style.configure("Treeview.Heading", font=("TkDefaultFont", 9, "bold"))

    def format_time(self, ms):
        """Convert milliseconds to formatted time string"""
        if ms <= 0:
            return "invalid"
        
        total_seconds = ms / 1000
        minutes = int(total_seconds // 60)
        seconds = total_seconds % 60
        return f"{minutes:d}:{seconds:06.3f}"

    def load_records(self):
        """Load records from all track CSV files"""
        records_dir = normalize_path(os.path.join(os.path.dirname(__file__), "records"))
        self.records = []
        
        if not os.path.exists(records_dir):
            messagebox.showwarning("No Records", "No lap records found.")
            return
        
        try:
            # Load records from each track file
            for file in os.listdir(records_dir):
                if file.endswith(".csv"):
                    track_name = file[:-4]  # Remove .csv extension
                    track_file = normalize_path(os.path.join(records_dir, file))
                    
                    with open(track_file, 'r') as f:
                        reader = csv.reader(f)
                        next(reader)  # Skip header (Car, Time_ms)
                        for row in reader:
                            car, time_ms = row
                            self.records.append({
                                'track': track_name,
                                'car': car,
                                'time_ms': int(time_ms)
                            })
            
            # Update track list in combobox
            tracks = sorted(list(set(r['track'] for r in self.records)))
            tracks.insert(0, "All Tracks")
            self.track_combo['values'] = tracks
            
            # Display records
            self.filter_records()
        
        except Exception as e:
            messagebox.showerror("Error", f"Error loading records: {str(e)}")

    def sort_records(self, key):
        """Sort records by the given key"""
        # Toggle sort state for the clicked column
        self.sort_states[key] = not self.sort_states[key]
        
        # Update column headers to show sort direction
        for col_key in ["track", "time_ms", "car"]:
            column_name = self.column_map[col_key]
            if col_key == key:
                direction = "↑" if self.sort_states[col_key] else "↓"
            else:
                direction = "↓"  # Reset other columns
                self.sort_states[col_key] = False  # Reset other columns' state
            self.tree.heading(column_name, text=f"{column_name} {direction}")
        
        # Sort the records
        self.records.sort(key=itemgetter(key), reverse=self.sort_states[key])
        self.display_records()

    def filter_records(self, event=None):
        """Filter records based on selected track"""
        self.display_records()

    def display_records(self):
        """Update the treeview with current records"""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Filter and display records
        selected_track = self.track_var.get()
        for record in self.records:
            if selected_track == "All Tracks" or selected_track == record['track']:
                time_str = self.format_time(record['time_ms'])
                self.tree.insert("", "end", values=(record['track'], time_str, record['car']))

if __name__ == '__main__':
    try:
        root = tk.Tk()
        app = TrackAndCarStatsViewer(root)
        root.mainloop()
    except Exception as e:
        messagebox.showerror("Error", f"Application error: {str(e)}")
