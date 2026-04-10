import datetime as dt
import pandas as pd
import os
cur_dir = os.path.dirname(__file__)
import sys
sys.path.append('Z:\\ApolloGX')
if "\\im_dev\\" in cur_dir:
    import im_dev.std_lib.common as common
else:
    import im_prod.std_lib.common as common

country_code = "CN"
start_dt = dt.date(2025, 1, 3)
end_dt = dt.date(2025, 4, 30)
holidays = None
if country_code == "US":
    holidays = common.nyse_holidays()
    holidays = pd.to_datetime(list(holidays.keys()), format='ISO8601').date
    while start_dt in holidays:
        start_dt = common.workday(start_dt, 1, holidays)
    while end_dt in holidays:
        end_dt = common.workday(end_dt, -1, holidays)
else:
    holidays = common.tsx_holidays()
    holidays = pd.to_datetime(list(holidays.keys()), format='ISO8601').date
    while start_dt in holidays:
        start_dt = common.workday(start_dt, 1, holidays)
    while end_dt in holidays:
        end_dt = common.workday(end_dt, -1, holidays)
holidays = dict(enumerate(holidays.flatten(), 1))

def _calculate_expiry(dtm, roll_date: dt.date, holidays):
        def next_friday(date):
            if date.weekday() == 4:
                candidate = common.workday(date, 5, holidays)
            else:
                candidate = common.workday(date, 4 - date.weekday(), holidays)
            while candidate in holidays or candidate.weekday() > 4:
                candidate = common.workday(candidate, -1, holidays)
            return candidate

        if dtm == 5:
            expiry = next_friday(roll_date)
        else:
            target = roll_date + dt.timedelta(days=dtm)
            weekday = target.weekday()
            days_to_friday = 4 - weekday
            expiry = target + dt.timedelta(days=days_to_friday)
            while expiry in holidays:
                expiry = expiry - dt.timedelta(days=7)

        return expiry
    
if __name__ == "__main__":
    exp = _calculate_expiry(5, start_dt, holidays)
    print(exp)