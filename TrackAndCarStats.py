import sys
import ac
import acsys
import os
import csv
import time
from datetime import datetime

l_lapcount = 0
l_current_time = 0
l_best_time = 0
l_record_holder = 0
l_last_lap = 0
l_relative = 0
lapcount = 0
finished_cars = set()  # Track which cars we've logged finishes for
records_dir = "apps/python/TrackAndCarStats/records"  # Directory for track record files
last_lap_times = {}  # Format: {car_id: last_lap_time}
records_cache = {}  # Format: {track: {car: time_ms}}
last_load_time = {}  # Format: {track: timestamp}
last_ui_update = 0  # Track when we last updated the UI with record information
UI_UPDATE_INTERVAL = 2.0  # Update UI with record information every 2 seconds
last_displayed_text = {}  # Store last displayed text for each label
cached_record_time = None
cached_record_car = None

def get_track_records_file(track_name):
    """Get the records file path for a specific track"""
    # Ensure records directory exists
    if not os.path.exists(records_dir):
        os.makedirs(records_dir)
        ac.log("TACS: Created records directory at {}".format(records_dir))
    
    records_file = os.path.join(records_dir, "{}.csv".format(track_name))
    ac.log("TACS: Track records file path: {}".format(records_file))
    return records_file

def format_time(ms):
    """Convert milliseconds to formatted time string"""
    if ms <= 0:
        return "invalid"
    
    total_seconds = ms / 1000
    minutes = int(total_seconds // 60)
    seconds = total_seconds % 60
    
    # For lap times, we typically don't need hours, just MM:SS.mmm
    return "{:d}:{:06.3f}".format(minutes, seconds)

def load_track_records(track):
    """Load records for a specific track, using cache if available"""
    global records_cache, last_load_time
    current_time = time.time()
      # Use cache if available and less than 60 seconds old
    if track in records_cache and track in last_load_time:
        if current_time - last_load_time[track] < 60:  # Cache for 60 seconds
            return records_cache[track].copy()  # Return a copy to prevent cache modification
        else:
            ac.log("TACS Debug: Cache expired for track {} (age: {:.1f}s)".format(
                track, current_time - last_load_time[track]))
    
    records = {}  # Format: {car: time_ms}
    try:
        ac.log("TACS: Loading records for track: {}".format(track))
        records_file = get_track_records_file(track)
        
        if os.path.exists(records_file):
            with open(records_file, 'r', newline='') as f:
                reader = csv.reader(f)
                next(reader)  # Skip header row (Car,Time_ms)
                
                for row in reader:
                    try:
                        if len(row) >= 2:  # Make sure we have both car and time
                            car, time_ms = row[0], row[1]  # Use indexing to be safer
                            records[car] = int(time_ms)  # Convert time to integer
                    except (ValueError, IndexError) as e:
                        ac.log("TACS Warning: Skipping invalid row in {}: {}".format(track, str(e)))
            
            ac.log("TACS: Loaded {} records for track {}".format(len(records), track))
        else:
            ac.log("TACS: No existing records file, creating new one")
            # Create directory if it doesn't exist
            records_dir = os.path.dirname(records_file)
            if not os.path.exists(records_dir):
                os.makedirs(records_dir)
                
            with open(records_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Car', 'Time_ms'])  # Write header
            
    except Exception as e:
        ac.log("TACS Error loading records for {}: {}".format(track, str(e)))
    
    # Update cache
    records_cache[track] = records.copy()
    last_load_time[track] = current_time
    
    return records

def save_track_records(track, records):
    """Save records for a specific track"""
    global records_cache, last_load_time
    try:
        records_file = get_track_records_file(track)
        with open(records_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Car', 'Time_ms'])  # Write header
            for car, time_ms in records.items():
                writer.writerow([car, time_ms])
        
        # Update cache with the new records
        records_cache[track] = records.copy()
        last_load_time[track] = time.time()
        
        ac.log("TACS: Saved {} records for track {}".format(len(records), track))
    except Exception as e:
        ac.log("TACS Error saving records for {}: {}".format(track, str(e)))

def check_record(track, car, driver, time_ms):
    """Check if this is a new record and update if so"""
    try:
        ac.log("TACS Debug: Checking record - Track: {}, Car: {}, Time: {}".format(
            track, car, format_time(time_ms)))
        
        records = load_track_records(track)
        
        # First check if this is a track record (best time for this track across all cars)
        track_best_time = float('inf')
        track_best_car = None
        for record_car, rec_time in records.items():
            if rec_time < track_best_time:
                track_best_time = rec_time
                track_best_car = record_car
        
        ac.log("TACS Debug: Current track best - Time: {}, Car: {}".format(
            format_time(track_best_time) if track_best_time != float('inf') else "none",
            track_best_car or "none"))
        
        # Now check if we've beaten the track record
        is_track_record = track_best_time == float('inf') or time_ms < track_best_time
        
        # Update the car-specific record
        if car not in records or time_ms < records[car]:
            old_time = format_time(records[car]) if car in records else "none"
            records[car] = time_ms
            save_track_records(track, records)
            
            # Only announce if it's a track record
            if is_track_record:
                msg = "NEW TRACK RECORD: {} on {}! Time: {} (Previous: {})".format(
                    car, track, format_time(time_ms), format_time(track_best_time) if track_best_time != float('inf') else "none"
                )
                ac.log("TACS: {}".format(msg))
                ac.console("TACS: {}".format(msg))
                ac.console("TACS: View all records in: apps/python/TACS/viewer.html")
                
                # Update the display immediately
                ac.setText(l_record_holder, "Track Record: {} by {}".format(format_time(time_ms), car))
            
            return is_track_record
    except Exception as e:
        ac.log("TACS Error checking record: {}".format(str(e)))
    return False

def get_current_record():
    """Get the current record for the active track"""
    global cached_record_time, cached_record_car, last_ui_update
    current_time = time.time()
    
    # Return cached values if they exist and are fresh
    if cached_record_time is not None and current_time - last_ui_update < UI_UPDATE_INTERVAL:
        return cached_record_time, cached_record_car
    
    try:
        track = ac.getTrackName(0)
        records = load_track_records(track)
        best_time = float('inf')
        best_car = None
        
        # Find the best time for this track
        for car, time_ms in records.items():
            if time_ms < best_time:
                best_time = time_ms
                best_car = car
        
        if best_time != float('inf'):
            # Update cache
            cached_record_time = best_time
            cached_record_car = best_car
            last_ui_update = current_time
            return best_time, best_car
    except Exception as e:
        ac.log("TACS Error getting current record: {}".format(str(e)))
    return None, None

def get_car_best_time(car_id):
    """Get the best time for a specific car on the current track from records"""
    global last_ui_update
    current_time = time.time()
    
    # Only check records periodically
    if current_time - last_ui_update < UI_UPDATE_INTERVAL:
        return None
        
    try:
        track = ac.getTrackName(0)
        car = ac.getCarName(car_id)
        records = load_track_records(track)
        if car in records:
            return records[car]
    except Exception as e:
        ac.log("TACS Error getting car best time: {}".format(str(e)))
    return None

def acMain(ac_version):
    try:
        global l_lapcount, l_current_time, l_best_time, l_sector1, l_sector2, l_sector3, l_record_holder, l_relative

        
        appWindow = ac.newApp("TACS")
        ac.setSize(appWindow, 300, 280)  # Increased width to 300
        ac.setTitle(appWindow, "")  # Remove title bar text to save space
        
        # Labels for lap info
        l_lapcount = ac.addLabel(appWindow, "Laps: 0")
        ac.setPosition(l_lapcount, 3, 30)
        ac.setFontSize(l_lapcount, 13)
        
        l_current_time = ac.addLabel(appWindow, "Current: --:--.---")
        ac.setPosition(l_current_time, 3, 50)
        ac.setFontSize(l_current_time, 13)
        
        l_best_time = ac.addLabel(appWindow, "Best: --:--.---")
        ac.setPosition(l_best_time, 3, 70)
        ac.setFontSize(l_best_time, 13)
          # Last lap time
        global l_last_lap
        l_last_lap = ac.addLabel(appWindow, "Last Lap: --:--.---")
        ac.setPosition(l_last_lap, 3, 100)
        ac.setFontSize(l_last_lap, 13)
        ac.setSize(l_last_lap, 290, 20)  # Make label use full width
        
        # Record holder info
        l_record_holder = ac.addLabel(appWindow, "Track Record: None")
        ac.setPosition(l_record_holder, 3, 130)
        ac.setFontSize(l_record_holder, 13)
        ac.setSize(l_record_holder, 290, 20)  # Make label use full width
        
        # Relative timing info
        l_relative = ac.addLabel(appWindow, "")
        ac.setPosition(l_relative, 3, 160)
        ac.setFontSize(l_relative, 13)
        ac.setSize(l_relative, 290, 20)  # Make label use full width        # Create records directory if it doesn't exist
        if not os.path.exists(records_dir):
            os.makedirs(records_dir)
            ac.log("TACS: Created records directory")
        
        # Display current record if it exists
        time_ms, driver = get_current_record()
        if time_ms:
            ac.setText(l_record_holder, "Track Record: {} by {}".format(format_time(time_ms), driver))
  
        
        ac.log("TACS: Window created successfully")
        return "TACS"
    except Exception as e:
        ac.log("TACS Error: {}".format(str(e)))
        return "TACS"

def acUpdate(deltaT):
    try:
        global l_lapcount, l_current_time, l_best_time, l_sector1, l_sector2, l_sector3, lapcount
        global best_sector1, best_sector2, best_sector3, finished_cars, l_relative, l_last_lap, last_ui_update
        global last_displayed_text
        
        current_time = time.time()
        should_update_ui = current_time - last_ui_update >= UI_UPDATE_INTERVAL
        
        # Get car count first
        car_count = ac.getCarsCount()
        
        # Update relative position
        focused_car = ac.getFocusedCar()
        focused_pos = ac.getCarRealTimeLeaderboardPosition(focused_car)
        
        def calculate_gap(car_id, my_pos, my_speed):
            """Calculate gap to another car"""
            if car_id < 0:
                return None, None
            
            car_pos = ac.getCarState(car_id, acsys.CS.NormalizedSplinePosition)
            car_speed = ac.getCarState(car_id, acsys.CS.SpeedMS)
            name = ac.getCarName(car_id)  # Using car name instead of driver name
            name = name.split('_')[-1][:8]  # Take last part of car name, limit to 8 chars
            
            # Calculate the gap
            track_length = ac.getTrackLength(0)
            pos_diff = car_pos - my_pos
            if pos_diff < -0.5:
                pos_diff += 1.0
            elif pos_diff > 0.5:
                pos_diff -= 1.0
            pos_diff *= track_length
            
            # Calculate time gap
            if my_speed > 0 and car_speed > 0:
                avg_speed = (car_speed + my_speed) / 2
                gap = pos_diff / avg_speed * 1000  # Convert to milliseconds
                if abs(gap) < 30000:  # Only return reasonable gaps (under 30 seconds)
                    return name, gap
            return None, None
        
        # Clear the label if we're not in a valid state
        if focused_car < 0 or focused_pos < 0:
            ac.setText(l_relative, "")
            return
            
        # Get my current state
        my_pos = ac.getCarState(focused_car, acsys.CS.NormalizedSplinePosition)
        my_speed = ac.getCarState(focused_car, acsys.CS.SpeedMS)
        
        # Find cars ahead and behind
        car_ahead = -1
        car_behind = -1
        
        for car_id in range(car_count):
            pos = ac.getCarRealTimeLeaderboardPosition(car_id)
            if pos == focused_pos - 1:
                car_ahead = car_id
            elif pos == focused_pos + 1:
                car_behind = car_id
        
        # Calculate gaps
        ahead_name, ahead_gap = calculate_gap(car_ahead, my_pos, my_speed)
        behind_name, behind_gap = calculate_gap(car_behind, my_pos, my_speed)
        
        # Format display - make it more compact by using a single line
        relative_text = ""
        if ahead_name and behind_name:
            # Show both gaps in format: "↑Car1 -1.234 ↓Car2 +0.567"
            relative_text = "↑ {} -{} ↓ {} +{}".format(
                ahead_name,
                format_time(abs(ahead_gap)),
                behind_name,
                format_time(abs(behind_gap))
            )
        elif ahead_name:
            # Only show car ahead: "↑Car1 -1.234"
            relative_text = "↑ {} -{}".format(
                ahead_name,
                format_time(abs(ahead_gap))
            )
        elif behind_name:
            # Only show car behind: "Lead ↓Car2 +0.567"
            relative_text = "Lead ↓ {} +{}".format(
                behind_name,
                format_time(abs(behind_gap))
            )
        else:
            relative_text = "In Lead"
        
        ac.setText(l_relative, relative_text)
          # Update current lap time
        current_time = ac.getCarState(focused_car, acsys.CS.LapTime)
        if current_time > 0:
            ac.setText(l_current_time, "Current: {}".format(format_time(current_time)))
        else:
            ac.setText(l_current_time, "Current: --:--.---")        # Update best lap time - only check records periodically
        session_best = ac.getCarState(focused_car, acsys.CS.BestLap)
        car_best = None
        if should_update_ui:
            car_best = get_car_best_time(focused_car)
        last_time = ac.getCarState(focused_car, acsys.CS.LastLap)
        
        # Initialize best time to infinity
        best_time = float('inf')
        
        # Check all potential sources for the best time
        if session_best > 0:
            best_time = session_best
        if car_best and car_best < best_time:
            best_time = car_best
        if last_time > 0:  # Include last lap in case it's our first and best lap
            if best_time == float('inf') or last_time < best_time:
                best_time = last_time
        
        # Update display with the best time we found
        if best_time != float('inf'):
            ac.setText(l_best_time, "Best: {}".format(format_time(best_time)))
        
        # Track lap completions and update last lap time
        global l_last_lap, l_record_holder  # Ensure we have access to the labels
        current_laps = ac.getCarState(focused_car, acsys.CS.LapCount)
        last_time = ac.getCarState(focused_car, acsys.CS.LastLap)
        current_time = ac.getCarState(focused_car, acsys.CS.LapTime)
        
        try:
            # Check for new completed laps
            if last_time > 0 and (focused_car not in last_lap_times or last_time != last_lap_times[focused_car]):
                last_lap_times[focused_car] = last_time
                track = ac.getTrackName(0)
                car = ac.getCarName(focused_car)
                driver = ac.getDriverName(focused_car)
                check_record(track, car, driver, last_time)  # Display is updated in check_record if it's a record
            
            # Update last lap display only if needed
            new_lap_text = "Last Lap: {}".format(
                format_time(last_lap_times[focused_car]) if focused_car in last_lap_times and last_lap_times[focused_car] > 0
                else "--:--.---"
            )
            if new_lap_text != last_displayed_text.get('last_lap'):
                last_displayed_text['last_lap'] = new_lap_text
                ac.setText(l_last_lap, new_lap_text)
        except Exception as e:
            ac.log("TACS Error updating last lap: {}".format(str(e)))
        
        # Update lap counter
        if current_laps > lapcount:
            lapcount = current_laps
            ac.setText(l_lapcount, "Laps: {}".format(lapcount))
            ac.log("TACS: Lap completed: {}".format(lapcount))
            
            # Reset best sectors for the new lap
            best_sector1 = float('inf')
            best_sector2 = float('inf')
            best_sector3 = float('inf')
        
        # Check all cars for finishes
        for car_id in range(car_count):
            if car_id in finished_cars:
                continue
            
            # Try to detect finish through various means
            is_finished = (
                ac.getCarState(car_id, acsys.CS.RaceFinished) or
                (ac.getCarState(car_id, acsys.CS.LapCount) > 0 and  # Has completed at least one lap
                 ac.getCarRealTimeLeaderboardPosition(car_id) == 1)  # Is in first position
            )
            
            if is_finished:
                driver = ac.getDriverName(car_id)
                car = ac.getCarName(car_id)
                track = ac.getTrackName(0)
                time_ms = ac.getCarState(car_id, acsys.CS.LastLap)
                
                # Only process valid times
                if time_ms > 0:
                    position = ac.getCarRealTimeLeaderboardPosition(car_id) + 1
                    
                    # Log the finish
                    msg = "P{} - {} in {} finished at {} with time {}".format(
                        position, driver, car, track, format_time(time_ms)
                    )
                    ac.log("TACS: {}".format(msg))
                    ac.console("TACS: {}".format(msg))
                    
                    # Check if this is a new record
                    if check_record(track, car, driver, time_ms):
                        # Update the display with the new record
                        ac.setText(l_record_holder, "Track Record: {} by {}".format(format_time(time_ms), car))
                    
                    finished_cars.add(car_id)
    
    except Exception as e:
        ac.log("TACS Error in update: {}".format(str(e)))

def acShutdown():
    ac.log("TACS: Shutting down")
