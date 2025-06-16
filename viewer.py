import tkinter as tk
from tkinter import ttk
import csv
import os
from datetime import datetime

class LapLoggerViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("LapLogger Records Viewer")
        
        # Data storage
        self.records = []
        self.filtered_records = []
        
        # Create filters frame
        filters_frame = ttk.Frame(root, padding="5")
        filters_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Track filter
        self.track_var = tk.StringVar()
        self.track_filter = ttk.Combobox(filters_frame, textvariable=self.track_var)
        ttk.Label(filters_frame, text="Track:").grid(row=0, column=0, padx=5)
        self.track_filter.grid(row=0, column=1, padx=5)
        
        # Car filter
        ttk.Label(filters_frame, text="Car:").grid(row=0, column=2, padx=5)
        self.car_filter = ttk.Entry(filters_frame)
        self.car_filter.grid(row=0, column=3, padx=5)
        
        # Refresh button
        ttk.Button(filters_frame, text="Refresh", command=self.load_data).grid(row=0, column=4, padx=5)
        
        # Create treeview
        self.tree = ttk.Treeview(root, columns=('Track', 'Car', 'Time'), show='headings')
        self.tree.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure treeview columns
        self.tree.heading('Track', text='Track', command=lambda: self.sort_records('Track'))
        self.tree.heading('Car', text='Car', command=lambda: self.sort_records('Car'))
        self.tree.heading('Time', text='Time', command=lambda: self.sort_records('Time'))
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(root, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.grid(row=1, column=1, sticky=(tk.N, tk.S))
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Configure grid weights
        root.grid_columnconfigure(0, weight=1)
        root.grid_rowconfigure(1, weight=1)
        
        # Bind events
        self.track_var.trace('w', lambda *args: self.filter_records())
        self.car_filter.bind('<KeyRelease>', lambda e: self.filter_records())
        
        # Initial load
        self.load_data()
    
    def format_time(self, ms):
        if ms <= 0:
            return "invalid"
        total_seconds = ms / 1000
        minutes = int(total_seconds // 60)
        seconds = total_seconds % 60
        return f"{minutes}:{seconds:06.3f}"
    
    def load_data(self):
        csv_path = os.path.join(os.path.dirname(__file__), 'track_records.csv')
        try:
            with open(csv_path, 'r') as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                self.records = []
                for row in reader:
                    if len(row) == 3:  # Ensure row has all required fields
                        track, car, time = row
                        self.records.append({
                            'Track': track,
                            'Car': car,
                            'Time': int(time),
                            'TimeFormatted': self.format_time(int(time))
                        })
            
            # Update track filter options
            tracks = sorted(list(set(record['Track'] for record in self.records)))
            self.track_filter['values'] = [''] + tracks
            
            self.filter_records()
            
        except Exception as e:
            tk.messagebox.showerror("Error", f"Failed to load track_records.csv: {str(e)}")
    
    def filter_records(self):
        track_filter = self.track_var.get()
        car_filter = self.car_filter.get().lower()
        
        self.filtered_records = self.records.copy()
        
        if track_filter:
            self.filtered_records = [r for r in self.filtered_records if r['Track'] == track_filter]
        
        if car_filter:
            self.filtered_records = [r for r in self.filtered_records if car_filter in r['Car'].lower()]
        
        self.update_treeview()
    
    def sort_records(self, column):
        is_time = column == 'Time'
        self.filtered_records.sort(key=lambda x: x[column] if not is_time else x['Time'])
        self.update_treeview()
    
    def update_treeview(self):
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Add filtered records
        for record in self.filtered_records:
            self.tree.insert('', 'end', values=(
                record['Track'],
                record['Car'],
                record['TimeFormatted']
            ))

if __name__ == '__main__':
    root = tk.Tk()
    app = LapLoggerViewer(root)
    root.mainloop()
