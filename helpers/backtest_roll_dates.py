import pandas as pd
import numpy as np
import datetime as dt

import os
cur_dir = os.path.dirname(__file__)
import sys
sys.path.append('Z:\\ApolloGX')
if "\\im_dev\\" in cur_dir:
    import im_dev.std_lib.common as common
    import im_dev.std_lib.data_library as data_library
else:
    import im_prod.std_lib.common as common
    import im_prod.std_lib.data_library as data_library

def _calculate_expiry(self, roll_date: dt.date, holidays):
    """
    initial expiry function for day 0, different from rolling expiry date finder which will start on an expiry date
    For dtm = 30 or multiple of 30 we want to get expiry date that is the closest 3rd friday to get liquid rolling later on
    """
    def next_friday(date):
        if date.weekday() == 4:
            candidate = common.workday(date, 5, holidays)
        else:
            candidate = common.workday(date, 4 - date.weekday(), holidays)
        while candidate in holidays or candidate.weekday() > 4:
            candidate = common.workday(candidate, -1, holidays)
        return candidate
    
    def third_friday(year: int, month: int) -> dt.date:
        first_day = dt.date(year, month, 1)
        first_friday_offset = (4 - first_day.weekday()) % 7
        first_friday = first_day + dt.timedelta(days=first_friday_offset)
        return first_friday + dt.timedelta(days=14)

    def next_third_friday(roll_date: dt.date, months: int) -> dt.date:
        
        # Third Friday of roll_date's month
        current_tf = third_friday(roll_date.year, roll_date.month)
        # Determine base month
        if roll_date > current_tf:
            base_month_offset = 1
        else:
            base_month_offset = 0
    
        # Convert year/month to absolute month index
        start_index = roll_date.year * 12 + (roll_date.month - 1)
        target_index = start_index + base_month_offset + months - 1
    
        year = target_index // 12
        month = target_index % 12 + 1
    
        return third_friday(year, month)

    if self.dtm == 5:
        expiry = next_friday(roll_date)
        
    else: # any multiple of 30 (months) will look for the 3rd friday regardless of the date we start on
        months = self.dtm//30
        expiry = next_third_friday(roll_date, months)
        
    while expiry in holidays:
        expiry = expiry - dt.timedelta(days=1)
            
    return expiry

def option_dates_roll(start_date: dt.datetime, holidays: dict, end_date: dt.datetime, dtm: int, tenor: int):
    """
    function for determining option roll dates based on given DTM
    Assumes that start_date is already handled to be a Friday before calling this function
    Could expect you to input the third friday of the month
    """
    d = start_date
    def third_friday(year, month):
        d = dt.date(year, month, 15)  
        while d.weekday() != 4:      
            d += dt.timedelta(days=1)
        return d
    
    output_dates = []
               
    while d.date() <= end_date.date():
        # 1. target date = today + tenor
        if d == end_date:
            target_date = d
        elif d + dt.timedelta(days=tenor) >= end_date:
            target_date = d
        else:
            target_date = d + dt.timedelta(days=tenor)

        # 2. find the closest Friday to target_date
        weekday_target = target_date.weekday()  
        days_until_friday = (4 - weekday_target) % 7
        if days_until_friday == 0:
            days_until_friday = 7 
        closest_friday = target_date + dt.timedelta(days=days_until_friday)

        # 3. adjust if holiday
        if closest_friday is not None:
            if holidays.get(closest_friday.strftime('%Y-%m-%d')):
                adjusted = closest_friday - dt.timedelta(days=1)
                if adjusted.weekday() == 3:
                    expiry = adjusted.date()
                else:
                    expiry = closest_friday.date()
            else:
                expiry = closest_friday.date()

            output_dates.append(expiry)
            d = closest_friday
        else:
            break

    return output_dates

def equity_rebalance_dates(start_date: dt.datetime, end_date: dt.datetime, rule: str, option_rebal_dates: list):
    """
    Generate equity rebalance dates based on rule:
    Q = Quarterly (3rd Friday Mar/Jun/Sep/Dec)
    S = Semi-Annual (3rd Friday Mar/Sep)
    A = Annual (3rd Friday Dec)
    O = Same as option roll schedule (i.e. everytime an option is rolled, the portfolio is rebalanced)
    """
    def third_friday(year, month):
        d = dt.date(year, month, 15)  
        while d.weekday() != 4:      
            d += dt.timedelta(days=1)
        return d

    dates = []

    if rule == "O":
        return [d if isinstance(d, dt.date) else d.date() for d in option_rebal_dates]

    for year in range(start_date.year, end_date.year + 1):
        if rule == "Q":
            months = [3, 6, 9, 12]
        elif rule == "S":
            months = [3, 9]
        elif rule == "A":
            months = [12]
        else:
            raise ValueError("Invalid equity rebalance rule. Use Q, S, A, or O.")

        for m in months:
            d = third_friday(year, m)
            if start_date.date() <= d <= end_date.date():
                dates.append(d)

    return dates


start_date = dt.datetime(2026, 1, 12) # Monday, the third week of Jan 2026
end_date = dt.datetime(2026, 4, 17) # Friday, third week of April 2026
option_rebal_dates = option_dates_roll(start_date, common.tsx_holidays(), end_date, 26)
print(option_rebal_dates)