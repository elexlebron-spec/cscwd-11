"""Monotonic elapsed clock including suspend on macOS.

Apple documents CLOCK_MONOTONIC_RAW as the nanosecond equivalent of
mach_continuous_time; Python's mach_absolute_time-based perf_counter excludes
system sleep. Use the continuous clock for both query accounting and deadlines.
https://developer.apple.com/documentation/kernel/1646199-mach_continuous_time
"""
import sys
import time
if sys.platform == 'darwin' and hasattr(time,'CLOCK_MONOTONIC_RAW'):
    CLOCK_NAME='clock_gettime(CLOCK_MONOTONIC_RAW); includes suspend on macOS'
    def query_clock():return time.clock_gettime(time.CLOCK_MONOTONIC_RAW)
else:
    CLOCK_NAME='time.perf_counter; platform default monotonic clock'
    query_clock=time.perf_counter
