#ifndef AGNOSTIC_THREAD_HPP_
#define AGNOSTIC_THREAD_HPP_

typedef void * thread_t;

#ifdef _MSC_VER
#include <windows.h>
void dealloc_threads(thread_t **threads, int num_threads) {
    for (int i = 0; i < num_threads; i++) {
        CloseHandle(threads[i]);
    }
    free(threads);
}

struct WorkerWrapperArgs {
    void *(*worker)(void *);
    void *data;
};

unsigned long __cdecl worker_wrapper(void *args) {
    void *data = ((WorkerWrapperArgs *)args)->data;
    void *(*worker)(void *) = ((WorkerWrapperArgs *)args)->worker;
    free(args);

    void *worker_result = worker(data);
    return worker_result == NULL ? 0 : 1;
}

thread_t *thread_create(void *(*worker)(void *), void *data) {
    unsigned long id_holder;
    WorkerWrapperArgs *args = (WorkerWrapperArgs *)malloc(sizeof(WorkerWrapperArgs));
    args->worker = worker;
    args->data = data;
    return (thread_t *)CreateThread(NULL, 0, &worker_wrapper, args, 0, &id_holder);
}

int thread_join(thread_t *thread) {
    return WaitForSingleObject(thread, INFINITE);
}
#else
#include <pthread.h>
void dealloc_threads(thread_t **threads, int num_threads) {
    for (int i = 0; i < num_threads; i++) {
        free(threads[i]);
    }
    free(threads);
}

thread_t *thread_create(void *(*worker)(void *), void *data) {
    pthread_t *thread = (pthread_t *)malloc(sizeof(pthread_t));
    if (pthread_create(thread, NULL, worker, data)) {
        free(thread);
        thread = NULL;
    }
    return (thread_t *)thread;
}

int thread_join(thread_t *thread) {
    return pthread_join((pthread_t)*thread, NULL);
}
#endif

#endif /* AGNOSTIC_THREAD_HPP_ */
