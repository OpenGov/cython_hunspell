import os

def int_or_zero(value):
    try:
        return int(value)
    except TypeError:
        return 0

def detect_cpus():
    '''Detects the number of CPUs on a system. Cribbed from pp.'''
    # Linux, Unix and MacOS:
    if hasattr(os, "sysconf"):
        if "SC_NPROCESSORS_ONLN" in os.sysconf_names:
            # Linux & Unix:
            ncpus = int_or_zero(os.sysconf("SC_NPROCESSORS_ONLN"))
        else:
            # OSX:
            ncpus = int_or_zero(os.popen2("sysctl -n hw.ncpu")[1].read())
    # Windows:
    if "NUMBER_OF_PROCESSORS" in os.environ:
        ncpus = int_or_zero(os.environ["NUMBER_OF_PROCESSORS"])
    if ncpus > 0:
        return ncpus
    return 1 # Default
