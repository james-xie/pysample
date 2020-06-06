//
// Created by 谢建 on 2020-01-07.
//

#ifndef FUZZLE_HASH_MAP_H
#define FUZZLE_HASH_MAP_H

#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <errno.h>


#define HASH_MAP_FAIL -2

#define LOAD_FACTOR 0.75
#define HASH_MAP_DEFAULT_SIZE 8
#define SIZE_TO_MASK(size) (size-1)
#define HASH_MAP_DEFAULT_SIZE_MASK SIZE_TO_MASK(HASH_MAP_DEFAULT_SIZE)


#define HASH_MAP_ITERATOR_INIT(iterator, mp) do {\
    (iterator)->map = (mp);\
    (iterator)->index = -1;\
    (iterator)->entry = NULL;\
} while (0)

#define HASH_MAP_OK 0
#define HASH_MAP_ERR -1
    

typedef struct _HashMapEntry HashMapEntry;

struct _HashMapEntry {
    void *key;
    void *val;
    HashMapEntry *next;
};

typedef struct {
    size_t (*hash_function)(const void *key);

    // Compare key1 with key2. Returns 0 if the two are equal, otherwise it returns 1
    int (*key_compare)(const void *key1, const void *key2);

    // Copy key to res
    int (*key_copy)(const void *key, void **res);

    int (*val_copy)(const void *val, void **res);

    void (*key_delete)(const void *key);

    void (*val_delete)(const void *val);
} HashMapType;

typedef struct {
    HashMapType *type;
    HashMapEntry **entries;
    size_t size;
    size_t mask;
    size_t used;
} HashMap;

typedef struct {
    HashMap *map;
    size_t index;
    HashMapEntry *entry;
} HashMapIterator;


HashMap *HashMap_Create(HashMapType *type);

void HashMap_Clear(HashMap *map);

void HashMap_Free(HashMap *map);

int HashMap_Set(HashMap *map, void *key, void *val);

void *HashMap_Get(HashMap *map, void *key);

int HashMap_Exists(HashMap *map, void *key);

int HashMap_Delete(HashMap *map, void *key);

int HashMap_Extend(HashMap *dest, HashMap *src);

unsigned long HashMap_NextPower(size_t size);

int HashMap_Resize(HashMap *map, size_t size);

HashMapEntry *HashMap_Next(HashMapIterator *iterator);

#endif //FUZZLE_HASH_MAP_H
