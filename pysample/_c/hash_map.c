#include <stdio.h>
#include <string.h>
#include <math.h>
#include <assert.h>
#include <time.h>

#include "hash_map.h"

// (2^30) - 1 || (2^62) - 1
#define MAX_SIZE ((1UL << (sizeof(size_t) * 8 - 2)) - 1)

#define NEED_TO_GROW(map) ((map)->used > (map)->size * LOAD_FACTOR)
#define GROWTH_RATE(map) ((map)->size * 2)
// why do we need to make "LOAD_FACTOR * 0.8"?
// if we frequently call the "HashMap_Delete" and "HashMap_Set" functions at the
// critical point of the hash map shrinking, this will cause the hash map to be
// rehash frequently, so we should make the shrink factor of the hash map smaller
// than the growth factor.
#define NEED_TO_SHRINK(map) ((map)->used < (size_t)((map)->size / 2) * LOAD_FACTOR * 0.8)
#define SHRINK_RATE(map) ((map)->size / 2)


#define GET_INDEX(hash_val, mask) ((hash_val) & (mask))
#define IS_POWER_OF_TWO(n) (((n) & (n-1)) == 0)

#define MUTATED_DURING_ITERATION "hash map mutated during iteration\n"



HashMap *HashMap_Create(HashMapType *type) {
    HashMap *map = malloc(sizeof(HashMap));
    if (map == NULL) {
        return NULL;
    }

    assert(type->key_compare);
    assert(type->hash_function);

    map->type = type;
    map->entries = NULL;
    map->size = 0;
    map->mask = 0;
    map->used = 0;
    return map;
}


static inline int set_key_to_entry(HashMap *map, HashMapEntry *entry, void *key) {
    int res = 0;
    if (map->type->key_copy) {
        res = map->type->key_copy(key, &entry->key);
    } else {
        entry->key = key;
    }
    return res;
}

static inline int set_val_to_entry(HashMap *map, HashMapEntry *entry, void *val) {
    int res = 0;
    if (map->type->val_copy) {
        res = map->type->val_copy(val, &entry->val);
    } else {
        entry->val = val;
    }
    return res;
}

static inline void del_key_from_entry(HashMap *map, HashMapEntry *entry) {
    if (map->type->key_delete) {
        map->type->key_delete(entry->key);
    }
}

static inline void del_val_from_entry(HashMap *map, HashMapEntry *entry) {
    if (map->type->val_delete) {
        map->type->val_delete(entry->val);
    }
}

static inline HashMapEntry *lookup_entry(HashMap *map, size_t index, void *key) {
    HashMapType *type = map->type;
    HashMapEntry *entry;

    entry = map->entries[index];
    while (entry != NULL) {
        if (type->key_compare(key, entry->key) == 0) {
            return entry;
        }
        entry = entry->next;
    }
    return NULL;
}


unsigned long HashMap_NextPower(size_t size) {
    size_t i = HASH_MAP_DEFAULT_SIZE;

    if (size < i)
        return i;

    if (IS_POWER_OF_TWO(size))
        return size;

    for (; i < size; i <<= 1ULL);
    return i;
}


int HashMap_Resize(HashMap *map, size_t size) {
    size_t index;
    size_t mask;
    size_t hash_val;
    HashMapEntry *prev, *next;
    HashMapIterator iterator;
    HashMapEntry **new_entries;
    size_t (*hash_function)(const void *);

    size = HashMap_NextPower(size);
    if (size >= MAX_SIZE) {
        fprintf(stderr, "hash map resize: trying to resize to %ld\n", size);
        return HASH_MAP_ERR;
    } else if (size < HASH_MAP_DEFAULT_SIZE) {
        size = HASH_MAP_DEFAULT_SIZE;
    } else if (size < (map->used / LOAD_FACTOR)) {
        size = ceil(map->used / LOAD_FACTOR);
    }

    mask = SIZE_TO_MASK(size);
    hash_function = map->type->hash_function;
    new_entries = calloc(size, sizeof(HashMapEntry *));
    if (new_entries == NULL) {
        return HASH_MAP_ERR;
    }

    HASH_MAP_ITERATOR_INIT(&iterator, map);

    prev = HashMap_Next(&iterator);
    while (prev != NULL) {
        next = HashMap_Next(&iterator);

        hash_val = hash_function(prev->key);
        index = GET_INDEX(hash_val, mask);
        prev->next = new_entries[index];
        new_entries[index] = prev;

        prev = next;
    }

    if (map->entries)
        free(map->entries);
    map->entries = new_entries;
    map->size = size;
    map->mask = mask;

    return HASH_MAP_OK;
}


static int resize_if_needed(HashMap *map) {
    int res = HASH_MAP_OK;

    if (map->size == 0) {
        map->size = HASH_MAP_DEFAULT_SIZE;
        map->mask = HASH_MAP_DEFAULT_SIZE_MASK;
        map->entries = calloc(map->size, sizeof(HashMapEntry *));
        if (map->entries == NULL) {
            res = HASH_MAP_ERR;
        }
    } else if (NEED_TO_GROW(map)) {
        res = HashMap_Resize(map, GROWTH_RATE(map));
    } else if (NEED_TO_SHRINK(map)) {
        res = HashMap_Resize(map, SHRINK_RATE(map));
    }
    return res;
}


int HashMap_Set(HashMap *map, void *key, void *val) {
    int res;
    size_t index;
    size_t hash_val;
    HashMapEntry *entry;

    res = resize_if_needed(map);
    if (res != HASH_MAP_OK) {
        return res;
    }

    hash_val = map->type->hash_function(key);
    index = GET_INDEX(hash_val, map->mask);
    entry = lookup_entry(map, index, key);

    if (entry == NULL) {
        entry = malloc(sizeof(HashMapEntry));
        if (entry == NULL) {
            return HASH_MAP_ERR;
        }

        res = set_key_to_entry(map, entry, key);
        if (res != 0) {
            free(entry);
            return HASH_MAP_ERR;
        }

        res = set_val_to_entry(map, entry, val);
        if (res != 0) {
            del_key_from_entry(map, key);
            free(entry);
            return HASH_MAP_ERR;
        }

        entry->next = map->entries[index];
        map->entries[index] = entry;
        map->used++;
    } else {
        if (map->type->key_delete && entry->key != key) {
            del_key_from_entry(map, entry);
            res = set_key_to_entry(map, entry, key);
            if (res != 0) {
                return HASH_MAP_ERR;
            }
        }

        del_val_from_entry(map, entry);
        res = set_val_to_entry(map, entry, val);
        if (res != 0) {
            return HASH_MAP_ERR;
        }
    }
    return HASH_MAP_OK;
}


void *HashMap_Get(HashMap *map, void *key) {
    size_t index;
    size_t hash_val;
    HashMapEntry *entry;
    HashMapType *type = map->type;

    if (map->size == 0) {
        return NULL;
    }

    hash_val = type->hash_function(key);
    index = GET_INDEX(hash_val, map->mask);
    entry = lookup_entry(map, index, key);
    if (entry == NULL)
        return NULL;
    return entry->val;
}


HashMapEntry *HashMap_Next(HashMapIterator *iterator) {
    HashMap *map = iterator->map;
    size_t index = iterator->index;
    HashMapEntry *entry = iterator->entry;

    if (entry != NULL && entry->next != NULL) {
        iterator->entry = entry->next;
        return entry->next;
    }

    while (++index < map->size) {
        if ((entry = map->entries[index]) != NULL) {
            iterator->index = index;
            iterator->entry = entry;
            return entry;
        }
    }
    return NULL;
}


void HashMap_Clear(HashMap *map) {
    HashMapEntry *prev, *next;
    HashMapIterator iterator;

    if (map->size == 0) {
        return;
    }

    if (map->used > 0) {
        HASH_MAP_ITERATOR_INIT(&iterator, map);

        prev = HashMap_Next(&iterator);
        while (prev != NULL) {
            next = HashMap_Next(&iterator);

            del_key_from_entry(map, prev);
            del_val_from_entry(map, prev);
            free(prev);

            prev = next;
        }
    }

    if (map->entries) {
        free(map->entries);
    }
    map->entries = NULL;
    map->size = 0;
    map->mask = 0;
    map->used = 0;
}

void HashMap_Free(HashMap *map) {
    HashMap_Clear(map);
    free(map);
}



