"""Process-local measurements; Windows limits are explicitly not claimed.

Linux uses resource limits and ru_maxrss. Windows reads the real peak working
set of the current process through GetProcessMemoryInfo, in bytes, then converts
to KiB. Both peaks cover the process lifetime, not just the timed interval.
"""
from __future__ import annotations
import os
import platform
import sys
import time


def configure_limits(cpu_seconds):
    limits = {'cpu_limit_seconds': None, 'virtual_memory_limit_bytes': None,
              'affinity_cpu_count': None}
    if os.name != 'posix':
        return limits
    import resource
    if hasattr(os, 'sched_getaffinity') and hasattr(os, 'sched_setaffinity'):
        available = os.sched_getaffinity(0)
        os.sched_setaffinity(0, {min(available)})
        limits['affinity_cpu_count'] = 1
    resource.setrlimit(resource.RLIMIT_AS, (768 * 1024 * 1024,) * 2)
    resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds,) * 2)
    limits.update(cpu_limit_seconds=cpu_seconds,
                  virtual_memory_limit_bytes=768 * 1024 * 1024)
    return limits


def peak_rss_kib():
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes

        class Counters(ctypes.Structure):
            _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD)] + [
                (name, ctypes.c_size_t) for name in (
                    'PeakWorkingSetSize', 'WorkingSetSize',
                    'QuotaPeakPagedPoolUsage', 'QuotaPagedPoolUsage',
                    'QuotaPeakNonPagedPoolUsage', 'QuotaNonPagedPoolUsage',
                    'PagefileUsage', 'PeakPagefileUsage')]

        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        psapi = ctypes.WinDLL('psapi', use_last_error=True)
        kernel.GetCurrentProcess.argtypes = []
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.GetProcessMemoryInfo.argtypes = [
            wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
        values = Counters()
        values.cb = ctypes.sizeof(values)
        if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(),
                                          ctypes.byref(values), values.cb):
            raise ctypes.WinError(ctypes.get_last_error())
        return values.PeakWorkingSetSize / 1024
    import resource
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return peak / 1024 if sys.platform == 'darwin' else peak


def snapshot(begin_cpu, begin_wall, limits=None, **fields):
    return dict(cpu_seconds=time.process_time() - begin_cpu,
                wall_seconds=time.monotonic() - begin_wall,
                peak_rss_kib=peak_rss_kib(),
                rss_source=('GetProcessMemoryInfo.PeakWorkingSetSize' if os.name == 'nt'
                            else 'resource.getrusage(RUSAGE_SELF).ru_maxrss'),
                rss_scope='process lifetime peak, not a process-tree aggregate',
                python=sys.version, platform=platform.platform(),
                workers=1, child_processes=0,
                **(limits or {}), **fields)
