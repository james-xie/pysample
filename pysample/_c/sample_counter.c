//
// Created by 谢建 on 2020-06-03.
//

#include "sample_counter.h"


#ifdef MS_WINDOWS
#define PATH_SEPARATOR '\\'
#else
#define PATH_SEPARATOR '/'
#endif

#define DEFAULT_PATH_ARRAY_SIZE 10

#define DEFAULT_OUTPUT_BUFFER_SIZE 4096 // 4kb

#define AVAILABLE_BUFFER_SIZE(buffer) ((buffer)->max_size - (buffer)->size)



size_t filenames_hash(const void *key);
int filenames_compare(const void *key1, const void *key2);
size_t traceback_hash(const void *key);
int traceback_compare(const void *key1, const void *key2);

HashMapType filenames_hash_t = {
        .hash_function = &filenames_hash,
        .key_compare = &filenames_compare,
};


HashMapType points_hash_t = {
        .hash_function = &traceback_hash,
        .key_compare = &traceback_compare,
};


size_t filenames_hash(const void *key) {
    return PyObject_Hash((PyObject *)key);
}

int filenames_compare(const void *key1, const void *key2) {
    return PyUnicode_Compare((PyObject *)key1, (PyObject *)key2);
}


size_t traceback_hash(const void *key) {
    size_t hash_value;
    SampleTraceback *tb = (SampleTraceback *)key;
    if (tb->hash_value) {
        return tb->hash_value;
    }

    hash_value = SampleTraceback_Hash(tb);
    tb->hash_value = hash_value;
    return hash_value;
}

int traceback_compare(const void *key1, const void *key2) {
    return SampleTraceback_Compare((SampleTraceback *)key1, (SampleTraceback *)key2);
}


SampleCounter *SampleCounter_Create(int delta, PyObject *sys_path) {
    SampleCounter *counter = NULL;

    counter = PyMem_Malloc(sizeof(SampleCounter));
    if (counter == NULL) {
        return NULL;
    }
    
    counter->delta = delta;
    Py_INCREF(sys_path);
    counter->sys_path = sys_path;

    counter->filenames = HashMap_Create(&filenames_hash_t);
    if (counter->filenames == NULL) {
        PyMem_Free(counter);
        return NULL;
    }

    counter->short_filenames = HashMap_Create(&filenames_hash_t);
    if (counter->short_filenames == NULL) {
        HashMap_Free(counter->filenames);
        PyMem_Free(counter);
        return NULL;
    }

    counter->points = HashMap_Create(&points_hash_t);
    if (counter->points == NULL) {
        HashMap_Free(counter->filenames);
        HashMap_Free(counter->short_filenames);
        PyMem_Free(counter);
        return NULL;
    }
    return counter;
}


void SampleCounter_Free(SampleCounter *counter) {
    HashMapEntry *entry;
    HashMapIterator iterator;

    Py_DECREF(counter->sys_path);

    HASH_MAP_ITERATOR_INIT(&iterator, counter->filenames);

    while ((entry = HashMap_Next(&iterator)) != NULL) {
        assert(PyUnicode_Check(entry->key));
        assert(PyUnicode_Check(entry->val));
        // key equals value, DECREF key or value
        Py_XDECREF(entry->key);
    }
    HashMap_Free(counter->filenames);

    HASH_MAP_ITERATOR_INIT(&iterator, counter->short_filenames);

    while ((entry = HashMap_Next(&iterator)) != NULL) {
        assert(PyUnicode_Check(entry->key));
        assert(PyUnicode_Check(entry->val));
        Py_XDECREF(entry->key);
        Py_XDECREF(entry->val);
    }
    HashMap_Free(counter->short_filenames);

    HASH_MAP_ITERATOR_INIT(&iterator, counter->points);

    while ((entry = HashMap_Next(&iterator)) != NULL) {
        SampleTraceback_Free(entry->key);
        // free SamplePoint
        PyMem_Free(entry->val);
    }
    HashMap_Free(counter->points);

    PyMem_Free(counter);
}


int SampleCounter_AddTraceback(SampleCounter *counter, SampleTraceback *traceback) {
    int res;
    SamplePoint *point;

    assert(traceback);

    point = HashMap_Get(counter->points, traceback);
    if (point == NULL) {
        point = PyMem_Malloc(sizeof(SamplePoint));
        if (point == NULL) {
            return -1;
        }

        point->traceback = traceback;
        point->count = 0;
        res = HashMap_Set(counter->points, traceback, point);
        if (res == HASH_MAP_ERR) {
            PyMem_Free(point);
            return -1;
        }
    } else {
        SampleTraceback_Free(traceback);
    }

    point->count += counter->delta;
    return 0;
}


int SampleCounter_AddFrame(SampleCounter *counter, PyObject *frame) {
    PyFrameObject *pyframe;
    SampleTraceback *traceback;

    pyframe = (PyFrameObject *)frame;
    traceback = SampleTraceback_Create(pyframe, counter->filenames);
    if (traceback == NULL) {
        return -1;
    }

    return SampleCounter_AddTraceback(counter, traceback);
}


typedef struct {
    int length;
    int max_length;
    PyObject *array[DEFAULT_PATH_ARRAY_SIZE];
} PackagePathArray;


typedef struct {
    int size;
    int max_size;
    char *buf;
} OutputBuffer;


static PackagePathArray *get_path_array() {
    static PackagePathArray *path_array = NULL;

    if (path_array == NULL) {
        path_array = PyMem_Malloc(sizeof(PackagePathArray));
        if (path_array == NULL) {
            return NULL;
        }

        path_array->length = 0;
        path_array->max_length = DEFAULT_PATH_ARRAY_SIZE;
    }

    if (path_array->length >= path_array->max_length) {
        int max_length = path_array->max_length;
        PackagePathArray *tmp = PyMem_Realloc(path_array, max_length * 2);
        if (tmp == NULL) {
            return NULL;
        }
        path_array = tmp;
        path_array->length = max_length;
        path_array->max_length = max_length * 2;
    }

    return path_array;
}


static void add_path_to_array(PackagePathArray *path_array, PyObject *path) {
    int i;
    PyObject *item;
    Py_ssize_t path_len = PyUnicode_GET_LENGTH(path);

    for (i=0; i<path_array->length; i++) {
        item = path_array->array[i];
        if (path_len >= PyUnicode_GET_LENGTH(item)) {
            void* src = (char *)path_array->array + i * sizeof(PyObject *);
            void* dest = (char *)src + sizeof(PyObject *);
            size_t size = (path_array->length - i) * sizeof(PyObject *);
            memmove(dest, src, size);

            Py_INCREF(path);
            path_array->array[i] = path;
            path_array->length++;
            return;
        }
    }

    Py_INCREF(path);
    path_array->array[path_array->length++] = path;
}


static inline PyObject *strip_package_path(PyObject *filename, PyObject *package_path) {
    int len = PyUnicode_GET_LENGTH(package_path);
    int name_len = PyUnicode_GET_LENGTH(filename);

    if (name_len > len) {
        if (PyUnicode_READ_CHAR(filename, len) == PATH_SEPARATOR) {
            len += 1;
        }
    }
    return PyUnicode_Substring(filename, len, name_len);
}


/**
 * Shorten the filename by strip the prefix path that starts with the path in sys.path.
 * The array of sys.path should be sorted by path length, because we traverse the
 * sys.path array in order, if the filename is startswith the path, we will strip
 * the path prefix and return directly.
 *
 * @param filename
 *      full filename
 * @param counter
 *      sampling counter
 * @return
 */
PyObject *shorten_filename(PyObject *filename, SampleCounter *counter) {
    int n, res;
    Py_ssize_t len;
    PyObject *item, *long_item, *short_filename = NULL;
    PyObject *sys_path = counter->sys_path;
    PackagePathArray *path_array = get_path_array();

    if (path_array == NULL) {
        return NULL;
    }

    short_filename = HashMap_Get(counter->short_filenames, filename);
    if (short_filename) {
        Py_INCREF(short_filename);
        return short_filename;
    }

    // The filename starts with the path in the cached path array.
    for (n=0; n<path_array->length; n++) {
        item = path_array->array[n];
        len = PyUnicode_GET_LENGTH(item);
        if (PyUnicode_Find(filename, item, 0, len, 1) >= 0) {
            short_filename = strip_package_path(filename, item);
            res = HashMap_Set(counter->short_filenames, filename, short_filename);
            if (res == 0) {
                // Successfully put short_filename in hashmap
                Py_INCREF(filename);
                Py_INCREF(short_filename);
            }
            return short_filename;
        }
    }

    // The cached path array cannot be used to shorten the file name, so we
    // try to strip the prefix path that starts with the path in sys.path.
    if (sys_path == NULL || sys_path == Py_None) {
        return filename;
    }

    assert(PyList_Check(sys_path));

    for (n=0; n<PyList_GET_SIZE(sys_path); n++) {
        item = PyList_GET_ITEM(sys_path, n);
        len = PyUnicode_GET_LENGTH(item);
        if (len <= 0) {
            continue;
        }

        if (PyUnicode_Find(filename, item, 0, len, 1) >= 0) {
            short_filename = strip_package_path(filename, item);
            res = HashMap_Set(counter->short_filenames, filename, short_filename);
            if (res == 0) {
                // Successfully put short_filename in hashmap
                Py_INCREF(filename);
                Py_INCREF(short_filename);
            }

            // Fix the matching path is too short to strip the complete package path.
            // So traverse the sys_path array again, and if the long path is starts
            // with the matching path, add it to the cached path array.
            while (--n >= 0) {
                long_item = PyList_GET_ITEM(sys_path, n);
                len = PyUnicode_GET_LENGTH(long_item);
                if (PyUnicode_Find(long_item, item, 0, len, 1) >= 0) {
                    add_path_to_array(path_array, long_item);
                }
            }
            add_path_to_array(path_array, item);
            return short_filename;
        }
    }

    return NULL;
}


/**
 * Check whether the available output buffer capacity is greater than the given size,
 * if false, double the output buffer.
 *
 * @param buffer
 * @param size
 * @return
 */
static inline int check_buffer_capacity(OutputBuffer *buffer, int size) {
    char *new_buf;

    if (size > AVAILABLE_BUFFER_SIZE(buffer)) {
        new_buf = PyMem_Realloc(buffer->buf, buffer->max_size * 2);
        if (new_buf == NULL) {
            return -1;
        }

        buffer->buf = new_buf;
        buffer->max_size *= 2;
    }

    return 0;
}


static int write_string_to_output(OutputBuffer *buffer, const char *str) {
    int len;

    assert(str != NULL);

    len = strlen(str);
    if (check_buffer_capacity(buffer, len) == -1) {
        return -1;
    }

    memcpy(buffer->buf + buffer->size, str, len);
    buffer->size += len;
    return 0;
}


static int write_int_to_output(OutputBuffer *buffer, int num) {
    char num_buf[11];

    sprintf(num_buf, "%d", num);
    return write_string_to_output(buffer, num_buf);
}


static int write_eof_to_output(OutputBuffer *buffer) {
    if (check_buffer_capacity(buffer, 1) == -1) {
        return -1;
    }

    buffer->buf[buffer->size] = '\0';
    return 0;
}


/**
 * Dump traceback to output buffer.
 *
 * @param counter
 * @param traceback
 * @param buffer
 * @return
 */
int dump_traceback(SampleCounter *counter, SampleTraceback *traceback, OutputBuffer *buffer) {
    int i, res, n = traceback->nframe;
    const char *utf8_str;
    SampleFrame *frame;
    PyObject *filename;

    for (i=0; i<n; i++) {
        frame = &traceback->frames[n-i-1];

        filename = shorten_filename(frame->filename, counter);
        if (filename == NULL) {
            filename = frame->filename;
            Py_INCREF(filename);
        }

        utf8_str = PyUnicode_AsUTF8(frame->co_name);
        if (utf8_str == NULL) {
            Py_DECREF(filename);
            return -1;
        }
        res = write_string_to_output(buffer, utf8_str);
        Py_DECREF(filename);
        if (res == -1) {
            return -1;
        }

        res = write_string_to_output(buffer, " (");
        if (res == -1) {
            return -1;
        }

        utf8_str = PyUnicode_AsUTF8(filename);
        if (utf8_str == NULL) {
            return -1;
        }
        res = write_string_to_output(buffer, utf8_str);
        if (res == -1) {
            return -1;
        }

        res = write_string_to_output(buffer, ":");
        if (res == -1) {
            return -1;
        }

        res = write_int_to_output(buffer, frame->lineno);
        if (res == -1) {
            return -1;
        }

        res = write_string_to_output(buffer, ");");
        if (res == -1) {
            return -1;
        }
    }

    return 0;
}



/**
 * Generate the collected stacks information.
 * The output stack information will be used as the input of the flame graph.
 *
 * See: https://github.com/brendangregg/FlameGraph
 *
 * @param counter
 * @return
 */
PyObject *SampleCounter_FlameOutput(SampleCounter *counter) {
    int i, res;
    SamplePoint *point;
    HashMapEntry *entry;
    HashMapIterator iterator;
    OutputBuffer *buffer = NULL;
    PyObject *output = NULL;

    if (counter->points->used <= 0) {
        return PyUnicode_FromString("");
    }

    buffer = PyMem_Malloc(sizeof(OutputBuffer));
    if (buffer == NULL) {
        return NULL;
    }

    buffer->size = 0;
    buffer->max_size = DEFAULT_OUTPUT_BUFFER_SIZE;

    buffer->buf = PyMem_Malloc(DEFAULT_OUTPUT_BUFFER_SIZE);
    if (buffer->buf == NULL) {
        PyMem_Free(buffer);
        return NULL;
    }

    HASH_MAP_ITERATOR_INIT(&iterator, counter->points);

    i = 0;
    while ((entry = HashMap_Next(&iterator)) != NULL) {
        point = entry->val;
        res = dump_traceback(counter, point->traceback, buffer);
        if (res == -1) {
            goto error;
        }

        res = write_string_to_output(buffer, " ");
        if (res == -1) {
            goto error;
        }

        res = write_int_to_output(buffer, point->count);
        if (res == -1) {
            goto error;
        }

        res = write_string_to_output(buffer, "\n");
        if (res == -1) {
            goto error;
        }

        i++;
    }

    res = write_eof_to_output(buffer);
    if (res == -1) {
        goto error;
    }

    output = PyUnicode_FromString(buffer->buf);
    PyMem_Free(buffer->buf);
    PyMem_Free(buffer);
    return output;

error:
    if (buffer) {
        PyMem_Free(buffer->buf);
        PyMem_Free(buffer);
    }
    return NULL;
}
