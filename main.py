#!/usr/bin/env python3

import time
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
from tzlocal import get_localzone


# TODO will i just need to install one (which, and which name to use to install via
# pip?), in order to have the option for interactive plots?
# trying `pip install PyQt5`
# ipdb> matplotlib.use('test')
# *** ValueError: 'test' is not a valid value for backend; supported values are
# ['GTK3Agg', 'GTK3Cairo', 'GTK4Agg', 'GTK4Cairo', 'MacOSX', 'nbAgg', 'QtAgg',
# 'QtCairo', 'Qt5Agg', 'Qt5Cairo', 'TkAgg', 'TkCairo', 'WebAgg', 'WX', 'WXAgg',
# 'WXCairo', 'agg', 'cairo', 'pdf', 'pgf', 'ps', 'svg', 'template']

# <stdin>:1: UserWarning: FigureCanvasAgg is non-interactive, and thus cannot be shown
#mpl.use('agg')


# TODO TODO turn this whole thing into a website, where people can upload CSV (+ input
# goal weights / date, etc) and it will show them this output in a report
def main():
    # Example file name: crimpd-logs-2024-02-11T232609.716Z.csv
    csvs = list(Path('.').glob('crimpd-logs-*.csv'))

    # TODO load most recent one in the input dir
    # just getting one example CSV for now
    csv = csvs[0]

    # Columns I'm seeing as of 2024-02-11, in my one export so far:
    # DATE, WORKOUT_NAME, TYPE, TARGET, WORKLOAD, INTENSITY, COMPLETION, EST_DURATION,
    # EST_WORK_DURATION, AVG_GRADE, RESISTANCE, LB_CIRCUIT, LB_ANGLE, ATTEMPTS, NOTES
    #
    # RESISTANCE seems to contain the weight value added for the max hang protocol I've
    # been using (in units of lbs).
    #
    # INTENSITY column seems to have a number (not sure which range, maybe 1-5? 1 seems
    # to be easy and 3 seems to be hard) for the "Easy", "Moderate", "Hard", etc scale
    # to rate difficulty of each workout.
    df = pd.read_csv(csv)
    df.columns = [c.lower() for c in df.columns]

    # DATE column starts in a format like this:
    # "Fri Dec 29 2023 09:12:59 GMT+0000 (Coordinated Universal Time)"
    # "Tue Jan 02 2024 18:53:57 GMT+0000 (Coordinated Universal Time)"
    #
    # TODO also include ' GMT+0000' in suffix if it's not useful / complicates parsing
    suffix = ' (Coordinated Universal Time)'
    assert df.date.str.endswith(suffix).all()
    df.date = df.date.str.replace(suffix, '')

    # %a: "weekday as locale’s abbreviated name"
    # %b: "month as locale’s abbreviated name"
    #
    # TODO is using both %Z and %z together like i am reasonable? just assert UTC offset
    # always "+0000" and ignore?
    #datetime_format = '%a %b %d %Y %H:%M:%S %Z%z'
    # (no, pandas throws `ValueError: Cannot parse both %Z and %z`)
    # TODO space between %S and %Z cause issues if timezone is absent (in general)?
    # %Z: "time zone name (empty string if the object is naive)"
    #     e.g. (empty), UTC, GMT
    #
    # %z: "UTC offset in the form ±HHMM[SS[.ffffff]] (empty string if the object is
    #     naive)"
    #     e.g. (empty), +0000, -0400, +1030
    #
    # TODO check timezone info in CSV is actually correct (and that time aren't local to
    # begin with, or something like that)
    #
    # up to the ' GMT+0000 (Coordinated Universal Time)' part
    # TODO assert last part (split on whitespace) of each date str startswith GMT+
    tz_prefix = 'GMT'
    assert df.date.str.split().apply(lambda x: x[-1].startswith(tz_prefix)).all()
    datetime_format = f'%a %b %d %Y %H:%M:%S {tz_prefix}%z'

    # TODO weekday (%a) ever cause issues w/ parsing? strip out in advance?
    # timezone dependent?

    df.date = pd.to_datetime(df.date, format=datetime_format)

    # TODO 'PDT' redundant w/ 'PST', or relevant depending on daylight savings?
    # >>> time.tzname
    # ('PST', 'PDT')
    # >>> time.localtime().tm_zone
    # 'PST'
    # TODO this approach work regardless of daylight savings state?
    # this gives me 'PST' (2024-02-11)
    #tz_name = time.localtime().tm_zone
    #df.date = df.date.dt.tz_convert('PDT')
    #
    # above fails with these errors:
    # ipdb> df.date.dt.tz_convert(tz_name)
    # *** pytz.exceptions.UnknownTimeZoneError: 'PST'
    # ipdb> df.date.dt.tz_convert('PDT')
    # *** pytz.exceptions.UnknownTimeZoneError: 'PDT'

    # even tho pandas docs don't seem to explicitly say they work with a ZoneInfo input,
    # (from the new (>=3.9?) stdlib zoneinfo, and what get_localzone() gives us)
    # it does seem to work.
    #
    # could also use tz.key, which seems to be the str I would want
    # (e.g. 'America/Los_Angeles')
    tz = get_localzone()
    df.date = df.date.dt.tz_convert(tz)

    # new column for the day within which each timestamp (df.date) occurs
    df['day'] = df.date.dt.floor('d')

    # TODO is there something that indicates a workout was logged after the fact?
    # (so we could exclude if we wanted to analyze workout times)

    # TODO cases where mass unit in resistance col is something else?
    # (workout dependent?)
    # other places besides this col where mass units can be something else?
    # TODO does it explicitly say units in app?
    mass_unit = 'lb'

    # WORKOUT_NAME for the max hang protocol I've been using is:
    # "Max Hangs - One Arm 90%"
    # The Emil Abrahaamson one is "Emil's Sub-max Daily Fingerboard Routine"
    workout = 'Max Hangs - One Arm 90%'

    # depending on the workout, may want to use this for something different
    resistance_means = 'max rep'
    # also workout dependent
    goal = 180
    want_goal_by = pd.Timestamp('2025-01-01', tz=tz)

    # TODO iterate over workouts and plot results for each?
    wdf = df[df.workout_name == workout]
    assert len(wdf) > 0

    # The NOTES column contains the manually entered notes for each protocol.
    # For the max hang protocol, I've often been entering per-rep weight information in
    # formats such as these:
    # "115, 110, 110, 3x 105"
    # "125x2-3, 120x3-4"
    # TODO parse such that the smaller number is assumed to be rep? warning / dropping
    # if # reps don't add up?
    # TODO parse notes in format as above -> use to get average weight for the day
    # -> analyze separately from max weight i already have

    start_date = wdf.day.min()
    end_date = wdf.day.max()

    print(f'{workout=}')
    dt = end_date - start_date
    # TODO print days until present instead? or clarify what we mean in wording?
    print(f'data for {dt.days} days')

    n_workouts = len(wdf)
    n_weeks = dt.days / 7
    avg_workouts_per_week = n_workouts / n_weeks
    print(f'logged {n_workouts} workouts (avg of {avg_workouts_per_week:.1f}/week)')

    # periods is the number of ticks we want
    # seems to include start_date and end_date, at least if periods>=2.
    # without the .round('d'), intermediate ticks will also have hour/etc info i don't
    # want.
    date_ticks = pd.date_range(start_date, end_date, periods=5).round('d')

    # TODO align each to day, rather than specific time within each day?
    # just also parse date to only the day (/ process it into another col for that?)?
    fig, ax = plt.subplots(layout='constrained')

    # TODO shorter date format then don't rotate?

    # TODO why does rot=90 seem to only apply to xticks? how to specify explicitly?
    # (it is what i want, but i am uneasy i'm not sure why it's doing that...)
    # (seems to apply to either xticks or yticks depending on plot type, so prob fine)
    wdf.plot(ax=ax, x='day', y='resistance', kind='scatter', rot=45, xticks=date_ticks,
        ylabel=f'{resistance_means} ({mass_unit})', title=workout
    )

    ax.axhline(goal, linestyle='dashed', color='grey', label='goal')

    xticks = ax.get_xticks()
    assert np.array_equal(xticks,
        [mpl.dates.date2num(x) for x in date_ticks.to_pydatetime()]
    )
    start_date_float = mpl.dates.date2num(start_date.to_pydatetime())

    # TODO delete. no longer need now that we have mpl.dates.date2num(x.to_pydatetime())
    #assert np.array_equal(np.diff(xticks), date_ticks.diff().dropna().days)
    #assert start_date == date_ticks[0]
    #start_date_float = xticks[0]
    # Timestamp work for x here? (no) how else to convert as pandas does inside
    # DataFrame.plot call?
    # (using start_date directly for x in xy1, rather than start_date_float, got this in
    # the ax.axline call below)
    # TypeError: ufunc 'isfinite' not supported for the input types, and the inputs
    # could not be safely coerced to any supported types according to the casting rule
    # ''safe''
    #xy1 = (start_date, initial)

    # assuming first row is from first date (should be true)
    initial = wdf.resistance.iloc[0]

    # TODO TODO try setting initial weight (for xy1 below) from fit (extrapolating fit
    # to date of first point, to denoise a bit?)?
    xy1 = (start_date_float, initial)

    days_to_goal_date = (want_goal_by - start_date).days
    slope_to_hit_goal = (goal - initial) / days_to_goal_date
    # TODO report in terms of required gain per month?
    #print(f'{slope_to_hit_goal=}')

    # TODO label appropriately (+ add legend) (or just annotate line via text, w/o
    # legend?)
    # TODO somehow compare  slope of this line to slope of one fit to data?
    ax.axline(xy1, slope=slope_to_hit_goal, linestyle='dashed', color='grey')


    # TODO TODO regress and report when we should expect to reach a certain goal
    # resistance?
    # TODO say .05, .95 CI values for estimate on when we reach goal
    # TODO and on values of weight/month progress we are making

    # TODO report weight/month progress we are making


    # TODO report (current?) streak in terms of how many weeks been doing the workout
    # some min # of times?
    plt.show()
    import ipdb; ipdb.set_trace()


if __name__ == '__main__':
    main()

