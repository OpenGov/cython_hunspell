import os
from cacheman.cachewrap import NonPersistentCache
from cacheman.cacher import get_cache_manager
from cacheman.autosync import TimeCount, AutoSyncCache

from libc.stdlib cimport *
from libc.string cimport *
from libc.stdio cimport *
from cython.operator cimport dereference as deref

# Use full path for cimport ONLY!
from hunspell.thread cimport *

#//////////////////////////////////////////////////////////////////////////////
# General Utilities
#//////////////////////////////////////////////////////////////////////////////

# Detects the number of CPUs on a system. Cribbed from pp.
def detectCPUs():
    # Linux, Unix and MacOS:
    if hasattr(os, "sysconf"):
        if "SC_NPROCESSORS_ONLN" in os.sysconf_names:
            # Linux & Unix:
            ncpus = os.sysconf("SC_NPROCESSORS_ONLN")
            if isinstance(ncpus, int) and ncpus > 0:
                return ncpus
        else: # OSX:
            return int(os.popen2("sysctl -n hw.ncpu")[1].read())
    # Windows:
    if "NUMBER_OF_PROCESSORS" in os.environ:
        ncpus = int(os.environ["NUMBER_OF_PROCESSORS"])
        if ncpus > 0:
            return ncpus
    return 1 # Default

#//////////////////////////////////////////////////////////////////////////////

cdef int copy_to_c_string(basestring py_unicode_string, char **holder) except -1:
    cdef size_t str_len = len(py_unicode_string)
    py_byte_string = py_unicode_string.encode('UTF-8', 'strict')
    cdef char *c_raw_string = py_byte_string
    holder[0] = <char *>malloc((str_len + 1) * sizeof(char)) # deref doesn't support left-hand assignment
    if deref(holder) is NULL:
        raise MemoryError()
    strncpy(deref(holder), c_raw_string, str_len)
    holder[0][str_len] = 0
    del py_byte_string
    return 1

# Convert c_string to python unicode
cdef unicode c_string_to_unicode_no_except(char* s):
    try:
        return s.decode('UTF-8', 'strict')
    except UnicodeDecodeError:
        return u""

#
# Structure for defining worker args
#
cdef struct ThreadWorkerArgs:
    # Thread ID
    int tid

    # Pointer to Hunspell Dictionary
    Hunspell *hspell

    # Number of words that this thread will check
    int n_words

    # Array of C strings, length of Array is n_words
    char **word_list

    # Array (of length n_words) of arrays of C strings
    char ***output_array_ptr

    # Array (of length n_words) of integers, each the length of the corresponding C string array
    int *output_counts

#//////////////////////////////////////////////////////////////////////////////
# Thread Worker Functions
#//////////////////////////////////////////////////////////////////////////////

cdef void *hunspell_suggest_worker(void *argument) nogil:
    cdef ThreadWorkerArgs args
    cdef int i
    args = deref(<ThreadWorkerArgs *>argument)

    for i from 0 <= i < args.n_words:
        args.output_counts[i] = args.hspell.suggest(args.output_array_ptr + i, deref(args.word_list + i))

    return NULL

cdef void *hunspell_stem_worker(void *argument) nogil:
    cdef ThreadWorkerArgs args
    cdef int i
    args = deref(<ThreadWorkerArgs *>argument)

    for i from 0 <= i < args.n_words:
        args.output_counts[i] = args.hspell.stem(args.output_array_ptr + i, deref(args.word_list + i))

    return NULL

#//////////////////////////////////////////////////////////////////////////////
cdef class HunspellWrap(object):
    # C-realm properties
    cdef Hunspell *_cxx_hunspell
    cdef public int n_cpus
    cdef public basestring lang
    cdef public basestring _cache_manager_name
    cdef public basestring _hunspell_dir
    cdef public object _suggest_cache
    cdef public object _stem_cache
    cdef char *affpath
    cdef char *dpath

    # C-realm Create Hunspell Instance
    cdef Hunspell *_create_hspell_inst(self, basestring lang) except +:
        if self.affpath:
            free(self.affpath)
        self.affpath = NULL
        if self.dpath:
            free(self.dpath)
        self.dpath = NULL
        cdef Hunspell *holder = NULL

        pyaffpath = os.path.join(self._hunspell_dir, '{}.aff'.format(lang))
        pydpath = os.path.join(self._hunspell_dir, '{}.dic'.format(lang))
        for fpath in (pyaffpath, pydpath):
            if not os.path.isfile(fpath) or not os.access(fpath, os.R_OK):
                raise IOError("File '{}' not found or accessible".format(fpath))

        if (copy_to_c_string(pyaffpath, &self.affpath) <= 0 or
            copy_to_c_string(pydpath, &self.dpath) <= 0):
                raise MemoryError()
        holder = new Hunspell(self.affpath, self.dpath)
        if holder is NULL:
            raise MemoryError()

        return holder

    # C-realm Constructor
    def __init__(self, basestring lang='en_US', basestring cache_manager="hunspell",
            basestring disk_cache_dir=None, basestring hunspell_data_dir=None):
        # TODO - make these LRU caches so that you don't destroy your memory!
        if hunspell_data_dir is None:
            hunspell_data_dir = os.environ.get("HUNSPELL_DATA")
        if hunspell_data_dir is None:
            hunspell_data_dir = os.path.join(os.path.dirname(__file__), '..', 'dictionaries')
        self._hunspell_dir = os.path.abspath(hunspell_data_dir)

        self.lang = lang
        self._cxx_hunspell = self._create_hspell_inst(lang)
        self.n_cpus = detectCPUs()

        self._cache_manager_name = cache_manager
        manager = get_cache_manager(self._cache_manager_name)
        if disk_cache_dir:
            manager.cache_directory = disk_cache_dir
        if not manager.cache_registered("hunspell_suggest"):
            if disk_cache_dir:
                custom_time_checks = [TimeCount(60, 1000000), TimeCount(300, 10000), TimeCount(900, 1)]
                AutoSyncCache("hunspell_suggest", cache_manager=manager, time_checks=custom_time_checks)
            else:
                NonPersistentCache("hunspell_suggest", cache_manager=manager)
        if not manager.cache_registered("hunspell_stem"):
            if disk_cache_dir:
                custom_time_checks = [TimeCount(60, 1000000), TimeCount(300, 10000), TimeCount(900, 1)]
                AutoSyncCache("hunspell_stem", cache_manager=manager, time_checks=custom_time_checks)
            else:
                NonPersistentCache("hunspell_stem", cache_manager=manager)
        self._suggest_cache = manager.retrieve_cache("hunspell_suggest")
        self._stem_cache = manager.retrieve_cache("hunspell_stem")

    # Python Destructor
    def __dealloc__(self):
        del self._cxx_hunspell
        free(self.affpath)
        free(self.dpath)

    # Python individual word spellcheck
    def spell(self, basestring word):
        cdef char *c_word = NULL
        if copy_to_c_string(word, &c_word) <= 0:
            raise MemoryError()

        try:
            return self._cxx_hunspell.spell(c_word) != 0
        finally:
            free(c_word)

    # Python individual word suggestions
    def suggest(self, basestring word):
        if word in self._suggest_cache:
            return self._suggest_cache[word]

        cdef char **s_list = NULL
        cdef char *c_word = NULL
        if copy_to_c_string(word, &c_word) <= 0:
            raise MemoryError()

        try:
            count = self._cxx_hunspell.suggest(&s_list, c_word)
            try:
                suggestion_list = []
                for i from 0 <= i < count:
                    suggestion_list.append(c_string_to_unicode_no_except(s_list[i]))

                suggestion_list = tuple(suggestion_list)
                self._suggest_cache[word] = suggestion_list
                return suggestion_list
            finally:
                self._cxx_hunspell.free_list(&s_list, count)
        finally:
            free(c_word)

    # Python individual word stemming
    def stem(self, basestring word):
        if word in self._stem_cache:
            return self._stem_cache[word]

        cdef char **s_list = NULL
        cdef char *c_word = NULL
        if copy_to_c_string(word, &c_word) <= 0:
            raise MemoryError()

        try:
            count = self._cxx_hunspell.stem(&s_list, c_word)
            try:
                stem_list = []
                for i from 0 <= i < count:
                    stem_list.append(c_string_to_unicode_no_except(s_list[i]))

                stem_list = tuple(stem_list)
                self._stem_cache[word] = stem_list
                return stem_list
            finally:
                self._cxx_hunspell.free_list(&s_list, count)
        finally:
            free(c_word)

    def save_cache(self):
        get_cache_manager(self._cache_manager_name).save_all_cache_contents()

    def set_concurrency(self, n_cpus):
        self.n_cpus = n_cpus

    ###################
    # Bulk Operations #
    ###################

    #
    # C realm thread dispatcher
    #
    cdef int _c_bulk_action(self, basestring action, char **word_array, char ***output_array, int n_words, int *output_counts) except +:
        # Allocate all memory per thread
        cdef thread_t **threads = <thread_t **>calloc(self.n_cpus, sizeof(thread_t *))
        cdef ThreadWorkerArgs *thread_args = <ThreadWorkerArgs *>calloc(self.n_cpus, sizeof(ThreadWorkerArgs))
        cdef int rc, i, stride

        if thread_args is NULL or threads is NULL:
            raise MemoryError()

        try:
            # Divide workload between threads
            words_per_thread = n_words / self.n_cpus
            words_distributed = 0
            # If uneven, round down on workers per thread (but the last thread will have extra work to do)
            if n_words % self.n_cpus != 0:
                words_per_thread = (n_words - (n_words % self.n_cpus)) / self.n_cpus

            for i from 0 <= i < self.n_cpus:
                stride = i * words_per_thread
                thread_args[i].tid = i

                # Allocate one Hunspell Dict per thread since it isn't safe.
                thread_args[i].hspell = self._create_hspell_inst(self.lang)

                # Account for leftovers
                if i == self.n_cpus - 1:
                    thread_args[i].n_words = n_words - words_distributed
                else:
                    thread_args[i].n_words = words_per_thread
                    words_distributed += words_per_thread

                # Find the stride into each array
                thread_args[i].word_list = &word_array[stride]
                thread_args[i].output_array_ptr = &output_array[stride]
                thread_args[i].output_counts = &output_counts[stride]

                # Create thread
                if action == "stem":
                    threads[i] = thread_create(&hunspell_stem_worker, <void *> &thread_args[i])
                else: # suggest
                    threads[i] = thread_create(&hunspell_suggest_worker, <void *> &thread_args[i])
                if threads[i] is NULL:
                    raise OSError("Could not create thread")

            # wait for each thread to complete
            for i from 0 <= i < self.n_cpus:
                # block until thread i completes
                rc = thread_join(threads[i])
                if rc:
                    raise OSError(rc, "Could not join thread")

                # Free Hunspell Dict
                del thread_args[i].hspell
            return 1
        finally:
            # Free top level stuff
            free(thread_args)
            dealloc_threads(threads, self.n_cpus)

    # Parse the return of a bulk action
    cdef void _parse_bulk_results(self, dict ret_dict, list unknown_words, int *output_counts, char ***output_array) except +:
        cdef int i, j
        try:
            for i from 0 <= i < len(unknown_words):
                for j from 0 <= j < output_counts[i]:
                    ret_dict[unknown_words[i]].append(c_string_to_unicode_no_except(output_array[i][j]))
        finally:
            for i from 0 <= i < len(unknown_words):
                # Free each suggestion list
                self._cxx_hunspell.free_list(output_array + i, output_counts[i])

    #
    # Python API - Accepts a list of words, returns a dict of words mapped to a list of their hunspell suggestions
    #
    def bulk_action(self, basestring action, list words):
        if not isinstance(words, list) or not words:
            raise TypeError()

        cdef int i = 0
        ret_dict = {}
        unknown_words = []

        # No need to check correctly spelled words
        if action == "stem":
            for i from 0 <= i < len(words):
                if words[i] in self._stem_cache:
                    ret_dict[words[i]] = self._stem_cache[words[i]]
                else:
                    ret_dict[words[i]] = []
                    unknown_words.append(words[i])
        else: # suggest
            for i from 0 <= i < len(words):
                if self.spell(words[i]):
                    ret_dict[words[i]] = [words[i]]
                elif words[i] in self._suggest_cache:
                    ret_dict[words[i]] = self._suggest_cache[words[i]]
                else:
                    ret_dict[words[i]] = []
                    unknown_words.append(words[i])

        # Initialize C word list
        # C version of: ["foo", "bar", "baz"]
        cdef char ***output_array = NULL
        cdef int *output_counts = NULL
        cdef char **word_array = <char **>calloc(len(unknown_words), sizeof(char *))
        if word_array is NULL:
            raise MemoryError()
        for i, unknown_word in enumerate(unknown_words):
            if copy_to_c_string(unknown_word, &word_array[i]) <= 0:
                raise MemoryError()

        try:
            # Create output arrays
            # Array of arrays of C strings (e.g. [["food", ...], ["bar"], ["bad", ...]])
            # This array will be divided evenly amongst the threads for the return values
            # of Hunspell.suggest(), each call returns an array of C strings
            output_array = <char ***>calloc(len(unknown_words), sizeof(char **))

            # Array of integers, each the length of the corresponding C string array
            # This array will be divided evenly amongst the threads for the length of the
            # arrays returned by each call to Hunspell.suggest()
            output_counts = <int *>calloc(len(unknown_words), sizeof(int))
            if output_counts is NULL or output_array is NULL:
                raise MemoryError()

            try:
                # Schedule bulk job
                self._c_bulk_action(action, word_array, output_array, len(unknown_words), output_counts)

                # Parse the return
                self._parse_bulk_results(ret_dict, unknown_words, output_counts, output_array)

                # Add ret_dict words to cache
                if action == "stem":
                    for i from 0 <= i < len(unknown_words):
                        self._stem_cache[unknown_words[i]] = ret_dict[unknown_words[i]]
                else:
                    for i from 0 <= i < len(unknown_words):
                        self._suggest_cache[unknown_words[i]] = ret_dict[unknown_words[i]]
                return ret_dict
            finally:
                # Free top level stuff
                free(output_array)
                free(output_counts)
        finally:
            self._cxx_hunspell.free_list(&word_array, len(unknown_words))
