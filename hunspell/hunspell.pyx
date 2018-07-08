import os
from .platform import detect_cpus
from cacheman.cachewrap import NonPersistentCache
from cacheman.cacher import get_cache_manager
from cacheman.autosync import TimeCount, AutoSyncCache

from libc.stdlib cimport *
from libc.string cimport *
from libc.stdio cimport *
from cython.operator cimport dereference as deref

# Use full path for cimport ONLY!
from hunspell.thread cimport *

def valid_encoding(basestring encoding):
    try:
        "".encode(encoding, 'strict')
        return encoding
    except LookupError:
        return 'ascii'

cdef int copy_to_c_string(basestring py_string, char **holder, basestring encoding='UTF-8') except -1:
    if isinstance(py_string, bytes):
        return byte_to_c_string(<bytes>py_string, holder, encoding)
    else:
        return byte_to_c_string(<bytes>py_string.encode(encoding, 'strict'), holder, encoding)

cdef int byte_to_c_string(bytes py_byte_string, char **holder, basestring encoding='UTF-8') except -1:
    cdef size_t str_len = len(py_byte_string)
    cdef char *c_raw_string = py_byte_string
    holder[0] = <char *>malloc((str_len + 1) * sizeof(char)) # deref doesn't support left-hand assignment
    if deref(holder) is NULL:
        raise MemoryError()
    strncpy(deref(holder), c_raw_string, str_len)
    holder[0][str_len] = 0
    return str_len

cdef unicode c_string_to_unicode_no_except(char* s, basestring encoding='UTF-8'):
    # Convert c_string to python unicode
    try:
        return s.decode(encoding, 'strict')
    except UnicodeDecodeError:
        return u""

#//////////////////////////////////////////////////////////////////////////////
# Thread Worker
#//////////////////////////////////////////////////////////////////////////////

cdef struct ThreadWorkerArgs:
    # Structure for defining worker args

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
    # Determines if the thread is executing a stem or suggestion callback
    bint stem_action

cdef void *hunspell_worker(void *argument) nogil:
    cdef ThreadWorkerArgs args
    cdef int i
    args = deref(<ThreadWorkerArgs *>argument)

    for i from 0 <= i < args.n_words:
        if args.stem_action:
            args.output_counts[i] = args.hspell.stem(args.output_array_ptr + i, deref(args.word_list + i))
        else:
            args.output_counts[i] = args.hspell.suggest(args.output_array_ptr + i, deref(args.word_list + i))

    return NULL

#//////////////////////////////////////////////////////////////////////////////
cdef class HunspellWrap(object):
    # C-realm properties
    cdef Hunspell *_cxx_hunspell
    cdef public int max_threads
    cdef public basestring lang
    cdef public basestring _cache_manager_name
    cdef public basestring _hunspell_dir
    cdef public basestring _dic_encoding
    cdef public object _suggest_cache
    cdef public object _stem_cache
    cdef char *affpath
    cdef char *dpath

    cdef Hunspell *_create_hspell_inst(self, basestring lang) except *:
        # C-realm Create Hunspell Instance
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

        copy_to_c_string(pyaffpath, &self.affpath)
        copy_to_c_string(pydpath, &self.dpath)
        holder = new Hunspell(self.affpath, self.dpath)
        if holder is NULL:
            raise MemoryError()

        return holder

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
        self._dic_encoding = valid_encoding(c_string_to_unicode_no_except(self._cxx_hunspell.get_dic_encoding()))
        self.max_threads = detect_cpus()

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

    def __dealloc__(self):
        del self._cxx_hunspell
        if self.affpath is not NULL:
            free(self.affpath)
        if self.dpath is not NULL:
            free(self.dpath)

    def spell(self, basestring word):
        # Python individual word spellcheck
        cdef char *c_word = NULL
        copy_to_c_string(word, &c_word, self._dic_encoding)
        try:
            return self._cxx_hunspell.spell(c_word) != 0
        finally:
            if c_word is not NULL:
                free(c_word)

    def suggest(self, basestring word):
        # Python individual word suggestions
        return self.action('suggest', word)

    def stem(self, basestring word):
        # Python individual word stemming
        return self.action('stem', word)

    def action(self, basestring action, basestring word):
        cdef bint stem_action = (action == 'stem')
        cache = self._stem_cache if stem_action else self._suggest_cache
        if word in cache:
            return cache[word]

        cdef char **s_list = NULL
        cdef char *c_word = NULL
        cdef list stem_list
        cdef tuple stem_result
        copy_to_c_string(word, &c_word, self._dic_encoding)

        try:
            if stem_action:
                count = self._cxx_hunspell.stem(&s_list, c_word)
            else:
                count = self._cxx_hunspell.suggest(&s_list, c_word)

            stem_list = []
            for i from 0 <= i < count:
                stem_list.append(c_string_to_unicode_no_except(s_list[i], self._dic_encoding))
            self._cxx_hunspell.free_list(&s_list, count)

            stem_result = tuple(stem_list)
            cache[word] = stem_result
            return stem_result
        finally:
            if c_word is not NULL:
                free(c_word)

    def bulk_suggest(self, words):
        return self.bulk_action('suggest', words)

    def bulk_stem(self, words):
        return self.bulk_action('stem', words)

    def bulk_action(self, basestring action, words):
        '''Accepts a list of words, returns a dict of words mapped to a list
        # of their hunspell suggestions'''
        cdef dict ret_dict = {}
        cdef list unknown_words = []
        cdef bint stem_action = (action == 'stem')
        cache = self._stem_cache if stem_action else self._suggest_cache

        for word in words:
            if not stem_action and self.spell(word):
                # No need to check correctly spelled words
                ret_dict[word] = (word,)
            elif word in cache:
                ret_dict[word] = cache[word]
            else:
                # This will turn into a tuple when completed
                ret_dict[word] = []
                unknown_words.append(word)

        if unknown_words:
            self._bulk_unknown_words(unknown_words, stem_action, ret_dict)

        return ret_dict


    def save_cache(self):
        get_cache_manager(self._cache_manager_name).save_all_cache_contents()

    def set_concurrency(self, max_threads):
        self.max_threads = max_threads

    ###################
    # C-Operations
    ###################

    cdef void _c_bulk_action(self, char **word_array, char ***output_array, int n_words, bint stem_action, int *output_counts) except *:
        '''C realm thread dispatcher'''
        # Allocate all memory per thread
        cdef thread_t **threads = <thread_t **>calloc(self.max_threads, sizeof(thread_t *))
        cdef ThreadWorkerArgs *thread_args = <ThreadWorkerArgs *>calloc(self.max_threads, sizeof(ThreadWorkerArgs))
        cdef int rc, i, stride

        if thread_args is NULL or threads is NULL:
            raise MemoryError()

        try:
            # Divide workload between threads
            words_per_thread = n_words // self.max_threads
            words_distributed = 0
            # If uneven, round down on workers per thread (but the last thread will have extra work to do)
            if n_words == 0 or n_words % self.max_threads != 0:
                words_per_thread = (n_words - (n_words % self.max_threads)) // self.max_threads

            for i from 0 <= i < self.max_threads:
                stride = i * words_per_thread
                thread_args[i].tid = i
                thread_args[i].stem_action = stem_action

                # Allocate one Hunspell Dict per thread since it isn't safe.
                thread_args[i].hspell = self._create_hspell_inst(self.lang)

                # Account for leftovers
                if i == self.max_threads - 1:
                    thread_args[i].n_words = n_words - words_distributed
                else:
                    thread_args[i].n_words = words_per_thread
                    words_distributed += words_per_thread

                # Find the stride into each array
                thread_args[i].word_list = &word_array[stride]
                thread_args[i].output_array_ptr = &output_array[stride]
                thread_args[i].output_counts = &output_counts[stride]

                # Create thread
                threads[i] = thread_create(&hunspell_worker, <void *> &thread_args[i])
                if threads[i] is NULL:
                    raise OSError("Could not create thread")

            # wait for each thread to complete
            for i from 0 <= i < self.max_threads:
                # block until thread i completes
                rc = thread_join(threads[i])
                if rc:
                    raise OSError(rc, "Could not join thread")

                # Free Hunspell Dict
                del thread_args[i].hspell
        finally:
            # Free top level stuff
            if thread_args is not NULL:
                free(thread_args)
            dealloc_threads(threads, self.max_threads)

    cdef void _parse_bulk_results(self, dict ret_dict, list unknown_words, int *output_counts, char ***output_array) except *:
        '''Parse the return of a bulk action'''
        cdef int unknown_len = len(unknown_words)
        cdef int i, j
        for i from 0 <= i < unknown_len:
            for j from 0 <= j < output_counts[i]:
                ret_dict[unknown_words[i]].append(c_string_to_unicode_no_except(output_array[i][j], self._dic_encoding))
            ret_dict[unknown_words[i]] = tuple(ret_dict[unknown_words[i]])
        for i from 0 <= i < unknown_len:
            # Free each suggestion list
            self._cxx_hunspell.free_list(output_array + i, output_counts[i])

    cdef void _bulk_unknown_words(self, list unknown_words, bint stem_action, dict ret_dict) except *:
        cdef int unknown_len = len(unknown_words)
        # C version of: ["foo", "bar", "baz"]
        cdef char ***output_array = NULL
        cdef int *output_counts = NULL
        cdef char **word_array = <char **>calloc(unknown_len, sizeof(char *))
        cache = self._stem_cache if stem_action else self._suggest_cache

        if word_array is NULL:
            raise MemoryError()
        for i, unknown_word in enumerate(unknown_words):
            copy_to_c_string(unknown_word, &word_array[i], self._dic_encoding)

        # Create output arrays
        # Array of arrays of C strings (e.g. [["food", ...], ["bar"], ["bad", ...]])
        # This array will be divided evenly amongst the threads for the return values
        # of Hunspell.suggest(), each call returns an array of C strings
        output_array = <char ***>calloc(unknown_len, sizeof(char **))

        # Array of integers, each the length of the corresponding C string array
        # This array will be divided evenly amongst the threads for the length of the
        # arrays returned by each call to Hunspell.suggest()
        output_counts = <int *>calloc(unknown_len, sizeof(int))
        if output_counts is NULL or output_array is NULL:
            raise MemoryError()

        try:
            # Schedule bulk job
            self._c_bulk_action(word_array, output_array, unknown_len, stem_action, output_counts)

            # Parse the return
            self._parse_bulk_results(ret_dict, unknown_words, output_counts, output_array)

            # Add ret_dict words to cache
            for i from 0 <= i < unknown_len:
                cache[unknown_words[i]] = ret_dict[unknown_words[i]]
            self._cxx_hunspell.free_list(&word_array, unknown_len)
        finally:
            # Free top level stuff
            if output_array is not NULL:
                free(output_array)
            if output_counts is not NULL:
                free(output_counts)

