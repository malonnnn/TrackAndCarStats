import sys
import ac
import acsys

l_lapcount = 0
lapcount = 0
finished_cars = set()  # Track which cars we've logged finishes for

def format_time(ms):
    """Convert milliseconds to formatted time string"""
    if ms <= 0:
        return "invalid"
    s = ms / 1000
    hours = int(s // 3600)
    minutes = int((s % 3600) // 60)
    seconds = s % 60
    return "{:d}:{:02d}:{:06.3f}".format(hours, minutes, seconds)

def acMain(ac_version):
    try:
        global l_lapcount
        appWindow = ac.newApp("LapLogger")
        ac.setSize(appWindow, 200, 200)
        
        l_lapcount = ac.addLabel(appWindow, "Laps: 0")
        ac.setPosition(l_lapcount, 3, 30)
        
        ac.log("LapLogger: Window created successfully")
        return "LapLogger"
    except Exception as e:
        ac.log("LapLogger Error: {}".format(str(e)))
        return "LapLogger"

def acUpdate(deltaT):
    try:
        global l_lapcount, lapcount, finished_cars
        
        # Update lap counter
        current_laps = ac.getCarState(0, acsys.CS.LapCount)
        if current_laps > lapcount:
            lapcount = current_laps
            ac.setText(l_lapcount, "Laps: {}".format(lapcount))
            ac.log("LapLogger: Lap completed: {}".format(lapcount))
        
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
                lap_time = ac.getCarState(car_id, acsys.CS.LastLap)  # Try getting last lap time instead
                position = ac.getCarRealTimeLeaderboardPosition(car_id)
                
                msg = "P{} - {} in {} finished at {} with time {}".format(
                    position, driver, car, track, format_time(lap_time)
                )
                ac.log("LapLogger: {}".format(msg))
                ac.console("LapLogger: {}".format(msg))
                
                finished_cars.add(car_id)
                
    except Exception as e:
        ac.log("LapLogger Error in update: {}".format(str(e)))

def acShutdown():
    ac.log("LapLogger: Shutting down")
