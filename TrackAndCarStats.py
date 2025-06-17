import sys
import ac
import acsys
import os
import csv
import time
from datetime import datetime
import traceback # Import traceback for better error logging

# --- Global UI and State Variables ---
app_window = 0
l_lapcount, l_current_time, l_best_time, l_record_holder, l_last_lap, l_relative = (0,) * 6
l_recent_records = []

# --- Configuration ---
RECORDS_DIR = "apps/python/TrackAndCarStats/records"
UI_UPDATE_INTERVAL = 0.5  # How often to update slower-changing UI elements
MAX_RECORDS_DISPLAY = 6   # Number of recent records to display

# --- Caches and State Management ---
app_state = {
    'full_track_name': None,
    'lap_count': 0,
    'last_ui_update': 0
}
last_lap_times = {}       # {car_id: last_lap_time_ms}
records_cache = {}        # {track_name: {car_tech_name: time_ms}}
last_displayed_text = {}  # {label_widget: "text"} - To prevent redundant ac.setText calls

# --- Helper Functions ---

def update_label_if_changed(label, new_text):
    """Avoids calling ac.setText if the label's text has not changed."""
    global last_displayed_text
    if label not in last_displayed_text or last_displayed_text[label] != new_text:
        ac.setText(label, new_text)
        last_displayed_text[label] = new_text

def normalize_path(path):
    """Normalizes a path to use forward slashes, which is safer across systems."""
    return path.replace('\\', '/')

def format_time(ms):
    """Converts milliseconds to a formatted time string MM:SS.mmm."""
    if not isinstance(ms, (int, float)) or ms <= 0:
        return "N/A"
    
    seconds = ms / 1000.0
    minutes = int(seconds // 60)
    secs = seconds % 60
    return "{:d}:{:06.3f}".format(minutes, secs)

# --- Core Logic Functions ---

def get_track_layout():
    """Gets the current track layout, defaulting to 'default'."""
    try:
        track_config = ac.getTrackConfiguration(0)
        return track_config.lower() if track_config and track_config.strip() else "default"
    except Exception as e:
        ac.log("TACS Warning: Could not get track layout. {}. Defaulting to 'default'".format(e))
        return "default"

def get_full_track_name():
    """Gets the track name including its layout, e.g., 'ks_nordschleife_endurance'."""
    track_name = ac.getTrackName(0)
    layout = get_track_layout()
    return "{}_{}".format(track_name, layout)

def get_track_records_file(track_name):
    """Constructs the full, normalized path to a track's records file."""
    if not os.path.exists(RECORDS_DIR):
        try:
            os.makedirs(RECORDS_DIR)
            ac.log("TACS: Created records directory at {}".format(normalize_path(RECORDS_DIR)))
        except OSError as e:
            ac.log("TACS Error: Could not create records directory: {}".format(e))
            return None
            
    return normalize_path(os.path.join(RECORDS_DIR, "{}.csv".format(track_name)))

def load_track_records(track):
    """Loads records for a specific track. Now uses a simplified {name: time} format."""
    if track in records_cache:
        return records_cache[track]

    records = {}
    records_file = get_track_records_file(track)
    if not records_file:
        return {}

    try:
        if os.path.exists(records_file):
            with open(records_file, 'r', newline='') as f:
                reader = csv.reader(f)
                try:
                    next(reader) 
                except StopIteration:
                    pass
                
                for row in reader:
                    try:
                        if len(row) >= 2:
                            records[row[0]] = int(row[1])
                    except (ValueError, IndexError):
                        pass
        else:
            with open(records_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['CarName', 'Time_ms'])
            ac.log("TACS: Created new records file for {}".format(track))

    except Exception as e:
        ac.log("TACS Error loading records for {}: {}".format(track, traceback.format_exc()))

    records_cache[track] = records
    return records

def save_track_records(track, records):
    """Saves all records for a specific track using the simplified 2-column format."""
    records_file = get_track_records_file(track)
    if not records_file:
        return

    try:
        with open(records_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['CarName', 'Time_ms'])
            sorted_records = sorted(records.items(), key=lambda item: item[1])
            for technical_name, time_ms in sorted_records:
                writer.writerow([technical_name, time_ms])
        
        records_cache[track] = dict(sorted_records)
        ac.log("TACS: Successfully saved {} records for track {}".format(len(records), track))

    except Exception as e:
        ac.log("TACS Error saving records for {}: {}".format(track, traceback.format_exc()))

def update_recent_record_display(message):
    """Updates the recent records display area with a new message at the top."""
    if not l_recent_records: return
    
    try:
        for i in range(len(l_recent_records) - 1, 0, -1):
            text = ac.getText(l_recent_records[i-1])
            update_label_if_changed(l_recent_records[i], text)
        
        update_label_if_changed(l_recent_records[0], message)
        
        for label in l_recent_records:
            if ac.getText(label).strip():
                ac.setVisible(label, False)
                ac.setVisible(label, True)
    except Exception as e:
        ac.log("TACS Error in update_recent_record_display: {}".format(e))

def check_and_update_record(track, car_id, lap_time_ms):
    """Checks if a new lap is a record and updates the files and UI with comparison info."""
    try:
        technical_name = ac.getCarName(car_id)
        if not technical_name: return

        records = load_track_records(track)
        
        previous_car_record = records.get(technical_name, float('inf'))
        previous_track_best_time, previous_track_best_car = get_current_track_record(records)
        
        if lap_time_ms < previous_car_record:
            
            is_track_record = lap_time_ms < previous_track_best_time
            
            msg = ""
            if is_track_record:
                if previous_track_best_time != float('inf'):
                    comparison_info = "(Previous {} by {})".format(format_time(previous_track_best_time), previous_track_best_car)
                    msg = "TRACK RECORD! {} - {} {}".format(technical_name, format_time(lap_time_ms), comparison_info)
                else:
                    msg = "TRACK RECORD! {} - {}".format(technical_name, format_time(lap_time_ms))
            else:
                if previous_car_record != float('inf'):
                    comparison_info = "(Previous {})".format(format_time(previous_car_record))
                    msg = "PB! {} - {} {}".format(technical_name, format_time(lap_time_ms), comparison_info)
                else:
                    msg = "PB! {} - {}".format(technical_name, format_time(lap_time_ms))

            records[technical_name] = lap_time_ms
            save_track_records(track, records)
            
            update_recent_record_display(msg)
            ac.log("TACS: {}".format(msg))
            ac.console("TACS: {}".format(msg))

    except Exception as e:
        ac.log("TACS Error in check_and_update_record: {}".format(traceback.format_exc()))

def get_current_track_record(records):
    """Finds the best time and associated car name from a records dictionary."""
    if not records:
        return float('inf'), "N/A"

    try:
        best_car, best_time = min(records.items(), key=lambda item: item[1])
        return best_time, best_car
    except ValueError:
        return float('inf'), "N/A"

def initialize_session():
    """Sets up all session-specific data and initial UI state."""
    global app_state, last_lap_times, last_displayed_text
    
    app_state['full_track_name'] = get_full_track_name()
    app_state['lap_count'] = 0
    last_lap_times.clear()
    last_displayed_text.clear()

    ac.log("TACS: Initializing session for track: {}".format(app_state['full_track_name']))
    
    records = load_track_records(app_state['full_track_name'])
    best_time, best_car_name = get_current_track_record(records)
    
    record_text = "Track Record: N/A"
    if best_time != float('inf'):
        record_text = "Track Record: {} by {}".format(format_time(best_time), best_car_name)
    
    update_label_if_changed(l_record_holder, record_text)
    
    for label in l_recent_records:
        update_label_if_changed(label, "")


# --- AC Hook Functions ---

def acMain(ac_version):
    """Called by Assetto Corsa to initialize the app."""
    global app_window, l_lapcount, l_current_time, l_best_time, l_last_lap, l_record_holder, l_relative, l_recent_records
    
    try:
        app_window = ac.newApp("TrackAndCarStats")
        ac.setSize(app_window, 300, 340)
        ac.setTitle(app_window, "")
        ac.drawBorder(app_window, 0)
        ac.setBackgroundOpacity(app_window, 0.9)

        y_pos = 10
        l_lapcount = ac.addLabel(app_window, "Laps: 0"); ac.setPosition(l_lapcount, 10, y_pos); y_pos += 22
        l_current_time = ac.addLabel(app_window, "Current: --:--.---"); ac.setPosition(l_current_time, 10, y_pos); y_pos += 22
        l_best_time = ac.addLabel(app_window, "Best: --:--.---"); ac.setPosition(l_best_time, 10, y_pos); y_pos += 22
        l_last_lap = ac.addLabel(app_window, "Last: --:--.---"); ac.setPosition(l_last_lap, 10, y_pos); y_pos += 22
        l_record_holder = ac.addLabel(app_window, "Track Record: N/A"); ac.setPosition(l_record_holder, 10, y_pos); y_pos += 22
        l_relative = ac.addLabel(app_window, "Relative: N/A"); ac.setPosition(l_relative, 10, y_pos); y_pos += 30

        records_title = ac.addLabel(app_window, "Recent Records"); ac.setPosition(records_title, 10, y_pos); y_pos += 22
        for i in range(MAX_RECORDS_DISPLAY):
            label = ac.addLabel(app_window, "")
            ac.setPosition(label, 15, y_pos)
            ac.setFontSize(label, 14)
            ac.setSize(label, 270, 20)
            l_recent_records.append(label)
            y_pos += 20
            
        for label in [l_lapcount, l_current_time, l_best_time, l_last_lap, l_record_holder, l_relative, records_title]:
            ac.setFontSize(label, 16)
            ac.setSize(label, 280, 22)

        initialize_session()
        
        ac.log("TACS: App initialized successfully.")
        return "TACS"

    except Exception as e:
        ac.log("TACS FATAL ERROR in acMain: {}".format(traceback.format_exc()))
        return "TACS"

def update_relative_display(focused_car_id):
    """Calculates and updates the relative time gaps to cars ahead and behind."""
    num_cars = ac.getCarsCount()
    if num_cars < 2:
        update_label_if_changed(l_relative, "")
        return

    leaderboard = []
    for i in range(num_cars):
        pos = ac.getCarRealTimeLeaderboardPosition(i)
        if pos >= 0:
            leaderboard.append((pos, i))
    
    leaderboard.sort()
    
    my_leaderboard_index = -1
    for i, (pos, car_id) in enumerate(leaderboard):
        if car_id == focused_car_id:
            my_leaderboard_index = i
            break
            
    if my_leaderboard_index == -1:
        update_label_if_changed(l_relative, "Relative: N/A")
        return

    my_spline_pos = ac.getCarState(focused_car_id, acsys.CS.NormalizedSplinePosition)
    my_speed = ac.getCarState(focused_car_id, acsys.CS.SpeedMS)
    track_len = ac.getTrackLength(0)

    ahead_text = ""
    if my_leaderboard_index > 0:
        ahead_car_id = leaderboard[my_leaderboard_index - 1][1]
        ahead_spline_pos = ac.getCarState(ahead_car_id, acsys.CS.NormalizedSplinePosition)
        gap = ahead_spline_pos - my_spline_pos
        if gap < -0.5: gap += 1.0
        time_gap = (gap * track_len) / (my_speed or 1)
        # --- MODIFICATION START ---
        car_name = ac.getCarName(ahead_car_id)
        ahead_text = u"{} ↑ -{:.1f}".format(car_name, time_gap)
        # --- MODIFICATION END ---

    behind_text = ""
    if my_leaderboard_index < len(leaderboard) - 1:
        behind_car_id = leaderboard[my_leaderboard_index + 1][1]
        behind_spline_pos = ac.getCarState(behind_car_id, acsys.CS.NormalizedSplinePosition)
        car_behind_speed = ac.getCarState(behind_car_id, acsys.CS.SpeedMS)
        gap = my_spline_pos - behind_spline_pos
        if gap < -0.5: gap += 1.0
        time_gap = (gap * track_len) / (car_behind_speed or 1)
        # --- MODIFICATION START ---
        car_name = ac.getCarName(behind_car_id)
        behind_text = u"{} ↓ +{:.1f}".format(car_name, time_gap)
        # --- MODIFICATION END ---
        
    final_text = "{}   {}".format(ahead_text, behind_text).strip()
    update_label_if_changed(l_relative, final_text)

def acUpdate(deltaT):
    """Called by Assetto Corsa every frame. Hot path for performance."""
    global app_state
    
    try:
        now = time.time()
        should_update_slow_ui = (now - app_state['last_ui_update']) >= UI_UPDATE_INTERVAL

        focused_car = ac.getFocusedCar()
        if focused_car < 0: return

        # --- Fast UI Updates ---
        update_label_if_changed(l_current_time, "Current: {}".format(format_time(ac.getCarState(focused_car, acsys.CS.LapTime))))
        update_label_if_changed(l_last_lap, "Last: {}".format(format_time(ac.getCarState(focused_car, acsys.CS.LastLap))))
        
        current_laps = ac.getCarState(focused_car, acsys.CS.LapCount)
        if current_laps > app_state['lap_count']:
            app_state['lap_count'] = current_laps
        update_label_if_changed(l_lapcount, "Laps: {}".format(app_state['lap_count']))

        # --- Check for new completed laps from ANY car (for records) ---
        num_cars = ac.getCarsCount()
        for car_id in range(num_cars):
            car_last_lap = ac.getCarState(car_id, acsys.CS.LastLap)
            if car_last_lap > 0 and car_last_lap != last_lap_times.get(car_id):
                last_lap_times[car_id] = car_last_lap
                check_and_update_record(app_state['full_track_name'], car_id, car_last_lap)

        # --- Slow UI Updates (Record Holder, Best Lap, Relatives, etc.) ---
        if should_update_slow_ui:
            app_state['last_ui_update'] = now
            
            records = load_track_records(app_state['full_track_name'])

            # Update Best Lap Display
            session_best_lap = ac.getCarState(focused_car, acsys.CS.BestLap)
            car_name = ac.getCarName(focused_car)
            car_all_time_best = records.get(car_name, float('inf'))
            
            true_best = float('inf')
            if session_best_lap > 0:
                true_best = session_best_lap
            if car_all_time_best < true_best:
                true_best = car_all_time_best

            if true_best != float('inf'):
                update_label_if_changed(l_best_time, "Best: {}".format(format_time(true_best)))
            else:
                update_label_if_changed(l_best_time, "Best: N/A")

            # Update Record Holder
            best_time, best_car_name = get_current_track_record(records)
            record_text = "Track Record: N/A"
            if best_time != float('inf'):
                record_text = "Track Record: {} by {}".format(format_time(best_time), best_car_name)
            update_label_if_changed(l_record_holder, record_text)

            # Update Relative Gaps
            update_relative_display(focused_car)

    except Exception as e:
        ac.log("TACS Error in acUpdate: {}".format(traceback.format_exc()))

def acShutdown():
    """Called by Assetto Corsa when the app is being shut down."""
    ac.log("TACS: Shutting down.")