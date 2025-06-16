import sys
import ac
import acsys
import os
import csv
from datetime import datetime

l_lapcount = 0
l_current_time = 0
l_best_time = 0
l_record_holder = 0
l_last_lap = 0
l_relative = 0
lapcount = 0
finished_cars = set()  # Track which cars we've logged finishes for
records_file = "apps/python/LapLogger/track_records.csv"

def format_time(ms):
    """Convert milliseconds to formatted time string"""
    if ms <= 0:
        return "invalid"
    
    total_seconds = ms / 1000
    minutes = int(total_seconds // 60)
    seconds = total_seconds % 60
    
    # For lap times, we typically don't need hours, just MM:SS.mmm
    return "{:d}:{:06.3f}".format(minutes, seconds)

def load_records():
    """Load existing track records"""
    records = {}  # Format: {(track, car): time_ms}
    try:
        if os.path.exists(records_file):
            with open(records_file, 'r') as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                for row in reader:
                    track, car, time_ms = row
                    records[(track, car)] = int(time_ms)
    except Exception as e:
        ac.log("LapLogger Error loading records: {}".format(str(e)))
    return records

def save_records(records):
    """Save track records to file"""
    try:
        with open(records_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Track', 'Car', 'Time_ms'])
            for (track, car), time_ms in records.items():
                writer.writerow([track, car, time_ms])
    except Exception as e:
        ac.log("LapLogger Error saving records: {}".format(str(e)))

def check_record(track, car, driver, time_ms):
    """Check if this is a new record and update if so"""
    try:
        records = load_records()
        current_key = (track, car)
        
        # First check if this is a track record (best time for this track across all cars)
        track_best_time = float('inf')
        track_best_car = None
        for (rec_track, rec_car), rec_time in records.items():
            if rec_track == track and rec_time < track_best_time:
                track_best_time = rec_time
                track_best_car = rec_car
        
        # Now check if we've beaten the track record
        is_track_record = track_best_time == float('inf') or time_ms < track_best_time
        
        # Update the car-specific record
        if current_key not in records or time_ms < records[current_key]:
            old_time = format_time(records[current_key]) if current_key in records else "none"
            records[current_key] = time_ms
            save_records(records)
            
            # Only announce if it's a track record
            if is_track_record:
                msg = "NEW TRACK RECORD: {} on {}! Time: {} (Previous: {})".format(
                    car, track, format_time(time_ms), format_time(track_best_time) if track_best_time != float('inf') else "none"
                )
                ac.log("LapLogger: {}".format(msg))
                ac.console("LapLogger: {}".format(msg))
                ac.console("LapLogger: View all records in: apps/python/LapLogger/viewer.html")
                
                # Update the display immediately
                ac.setText(l_record_holder, "Track Record: {} by {}".format(format_time(time_ms), car))
            
            return is_track_record
    except Exception as e:
        ac.log("LapLogger Error checking record: {}".format(str(e)))
    return False

def get_current_record():
    """Get the current record for the active track"""
    try:
        track = ac.getTrackName(0)
        records = load_records()
        best_time = float('inf')
        best_car = None
        
        # Find the best time for this track across all cars
        for (rec_track, rec_car), time_ms in records.items():
            if rec_track == track and time_ms < best_time:
                best_time = time_ms
                best_car = rec_car
        
        if best_time != float('inf'):
            return best_time, best_car
    except Exception as e:
        ac.log("LapLogger Error getting current record: {}".format(str(e)))
    return None, None

def acMain(ac_version):
    try:
        global l_lapcount, l_current_time, l_best_time, l_sector1, l_sector2, l_sector3, l_record_holder, l_relative
        appWindow = ac.newApp("LapLogger")
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
        l_last_lap = ac.addLabel(appWindow, "Last Lap: --:--.---")
        ac.setPosition(l_last_lap, 3, 100)
        ac.setFontSize(l_last_lap, 13)
        
        # Record holder info
        l_record_holder = ac.addLabel(appWindow, "Track Record: None")
        ac.setPosition(l_record_holder, 3, 130)
        ac.setFontSize(l_record_holder, 13)
        ac.setSize(l_record_holder, 290, 20)  # Make label use full width
        
        # Relative timing info
        l_relative = ac.addLabel(appWindow, "")
        ac.setPosition(l_relative, 3, 160)
        ac.setFontSize(l_relative, 13)
        ac.setSize(l_relative, 290, 20)  # Make label use full width
          # Create records file if it doesn't exist
        if not os.path.exists(records_file):
            save_records({})
              # Display current record if it exists
        time_ms, driver = get_current_record()
        if time_ms:
            ac.setText(l_record_holder, "Track Record: {} by {}".format(format_time(time_ms), driver))
        
        ac.log("LapLogger: Window created successfully")
        return "LapLogger"
    except Exception as e:
        ac.log("LapLogger Error: {}".format(str(e)))
        return "LapLogger"

def acUpdate(deltaT):
    try:
        global l_lapcount, l_current_time, l_best_time, l_sector1, l_sector2, l_sector3, lapcount, best_sector1, best_sector2, best_sector3, finished_cars, l_relative
        
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
            # Show both gaps in format: "↑Car1 +1.234 ↓Car2 -0.567"
            relative_text = "↑ {} +{} ↓ {} -{}".format(
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
        current_time = ac.getCarState(0, acsys.CS.LapTime)
        if current_time > 0:
            ac.setText(l_current_time, "Current: {}".format(format_time(current_time)))
        
        # Update best lap time
        best_time = ac.getCarState(0, acsys.CS.BestLap)
        if best_time > 0:
            ac.setText(l_best_time, "Best: {}".format(format_time(best_time)))
        
        # Update last lap time
        last_time = ac.getCarState(0, acsys.CS.LastLap)
        if last_time > 0:
            ac.setText(l_last_lap, "Last Lap: {}".format(format_time(last_time)))
        
        # Update lap counter
        current_laps = ac.getCarState(0, acsys.CS.LapCount)
        if current_laps > lapcount:
            lapcount = current_laps
            ac.setText(l_lapcount, "Laps: {}".format(lapcount))
            ac.log("LapLogger: Lap completed: {}".format(lapcount))
            
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
                    ac.log("LapLogger: {}".format(msg))
                    ac.console("LapLogger: {}".format(msg))
                    
                    # Check if this is a new record
                    if check_record(track, car, driver, time_ms):
                        # Update the display with the new record
                        ac.setText(l_record_holder, "Track Record: {} by {}".format(format_time(time_ms), car))
                    
                    finished_cars.add(car_id)
    
    except Exception as e:
        ac.log("LapLogger Error in update: {}".format(str(e)))

def acShutdown():
    ac.log("LapLogger: Shutting down")
