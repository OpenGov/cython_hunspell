cdef extern from "thread.hpp":
    ctypedef void *thread_t

    void dealloc_threads(thread_t **threads, int num_threads)
    thread_t *thread_create(void *(*worker)(void *), void *data)
    int thread_join(thread_t *thread)
