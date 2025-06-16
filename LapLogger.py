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
        key = (track, car)
        
        if key not in records or time_ms < records[key]:
            # New record!
            old_time = format_time(records[key]) if key in records else "none"
            records[key] = time_ms
            save_records(records)
            
            msg = "NEW TRACK RECORD: {} at {}! Time: {} (Previous: {})".format(
                car, track, format_time(time_ms), old_time
            )
            ac.log("LapLogger: {}".format(msg))
            ac.console("LapLogger: {}".format(msg))
            ac.console("LapLogger: View all records in: apps/python/LapLogger/viewer.html")
            
            return True
    except Exception as e:
        ac.log("LapLogger Error checking record: {}".format(str(e)))
    return False

def get_current_record():
    """Get the current record for the active car/track combination"""
    try:
        track = ac.getTrackName(0)
        car = ac.getCarName(0)
        records = load_records()
        key = (track, car)
        
        if key in records:
            return records[key], None
    except Exception as e:
        ac.log("LapLogger Error getting current record: {}".format(str(e)))
    return None, None, None

def acMain(ac_version):
    try:
        global l_lapcount, l_current_time, l_best_time, l_sector1, l_sector2, l_sector3, l_record_holder, l_relative
        appWindow = ac.newApp("LapLogger")
        ac.setSize(appWindow, 200, 280)
        
        # Labels for lap info
        l_lapcount = ac.addLabel(appWindow, "Laps: 0")
        ac.setPosition(l_lapcount, 3, 30)
        
        l_current_time = ac.addLabel(appWindow, "Current: --:--.---")
        ac.setPosition(l_current_time, 3, 50)
        
        l_best_time = ac.addLabel(appWindow, "Best: --:--.---")
        ac.setPosition(l_best_time, 3, 70)
          # Last lap time
        l_last_lap = ac.addLabel(appWindow, "Last Lap: --:--.---")
        ac.setPosition(l_last_lap, 3, 100)
          # Record holder info
        l_record_holder = ac.addLabel(appWindow, "Track Record: None")
        ac.setPosition(l_record_holder, 3, 130)
        
        # Relative timing info
        l_relative = ac.addLabel(appWindow, "")
        ac.setPosition(l_relative, 3, 160)
          # Create records file if it doesn't exist
        if not os.path.exists(records_file):
            save_records({})
            
        # Display current record if it exists
        time_ms, _ = get_current_record()
        if time_ms:
            ac.setText(l_record_holder, "Track Record: {}".format(format_time(time_ms)))
        
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
        
        # Clear the label if we're not in a valid state
        if focused_car < 0 or focused_pos < 0:
            ac.setText(l_relative, "")
        else:
            found_car_ahead = False
            
            # Look for the car immediately ahead
            for car_id in range(car_count):
                pos = ac.getCarRealTimeLeaderboardPosition(car_id)
                if pos == focused_pos - 1:  # Car ahead
                    found_car_ahead = True
                    name = ac.getDriverName(car_id)[:12]
                    
                    # Get track positions (0.0 to 1.0)
                    car_pos = ac.getCarState(car_id, acsys.CS.NormalizedSplinePosition)
                    my_pos = ac.getCarState(focused_car, acsys.CS.NormalizedSplinePosition)
                    
                    # Get their speeds in m/s
                    car_speed = ac.getCarState(car_id, acsys.CS.SpeedMS)
                    my_speed = ac.getCarState(focused_car, acsys.CS.SpeedMS)
                    
                    # Calculate the gap
                    track_length = ac.getTrackLength(0)
                    # Handle track position wrapping around from 1.0 to 0.0
                    pos_diff = car_pos - my_pos
                    if pos_diff < -0.5:
                        pos_diff += 1.0
                    elif pos_diff > 0.5:
                        pos_diff -= 1.0
                    pos_diff *= track_length  # convert to meters
                    
                    # Estimate time gap based on average speed
                    if my_speed > 0:  # avoid division by zero
                        avg_speed = (car_speed + my_speed) / 2
                        if avg_speed > 0:  # extra safety check
                            gap = pos_diff / avg_speed * 1000  # convert to milliseconds
                            # Only show gap if it's reasonable (less than 30 seconds)
                            if abs(gap) < 30000:
                                if gap > 0:
                                    ac.setText(l_relative, "{} +{}".format(name, format_time(abs(gap))))
                                else:
                                    ac.setText(l_relative, "{} -{}".format(name, format_time(abs(gap))))
                    break
            
            if not found_car_ahead:
                # We're leading, let's find the gap to the car behind
                found_car_behind = False
                for car_id in range(car_count):
                    pos = ac.getCarRealTimeLeaderboardPosition(car_id)
                    if pos == focused_pos + 1:  # Car behind
                        found_car_behind = True
                        name = ac.getDriverName(car_id)[:12]
                        
                        # Get track positions (0.0 to 1.0)
                        car_pos = ac.getCarState(car_id, acsys.CS.NormalizedSplinePosition)
                        my_pos = ac.getCarState(focused_car, acsys.CS.NormalizedSplinePosition)
                        
                        # Get their speeds in m/s
                        car_speed = ac.getCarState(car_id, acsys.CS.SpeedMS)
                        my_speed = ac.getCarState(focused_car, acsys.CS.SpeedMS)
                        
                        # Calculate the gap
                        track_length = ac.getTrackLength(0)
                        # Handle track position wrapping around from 1.0 to 0.0
                        pos_diff = my_pos - car_pos  # Note: reversed to show positive gap to car behind
                        if pos_diff < -0.5:
                            pos_diff += 1.0
                        elif pos_diff > 0.5:
                            pos_diff -= 1.0
                        pos_diff *= track_length  # convert to meters
                        
                        # Estimate time gap based on average speed
                        if my_speed > 0:  # avoid division by zero
                            avg_speed = (car_speed + my_speed) / 2
                            if avg_speed > 0:  # extra safety check
                                gap = pos_diff / avg_speed * 1000  # convert to milliseconds
                                # Only show gap if it's reasonable (less than 30 seconds)
                                if abs(gap) < 30000:
                                    ac.setText(l_relative, "{} +{}".format(name, format_time(abs(gap))))
                                    break
                
                if not found_car_behind:
                    ac.setText(l_relative, "In Lead")
        
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
        car_count = ac.getCarsCount()
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
                        ac.setText(l_record_holder, "Track Record: {} ({})".format(format_time(time_ms), driver))
                    
                    finished_cars.add(car_id)
    
    except Exception as e:
        ac.log("LapLogger Error in update: {}".format(str(e)))

def acShutdown():
    ac.log("LapLogger: Shutting down")
