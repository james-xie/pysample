cmake_minimum_required(VERSION 3.14)
project(pysample C)

set(CMAKE_C_STANDARD 99)

include_directories(
        ${CMAKE_CURRENT_SOURCE_DIR}/third_party/cpython/include
        ${CMAKE_CURRENT_SOURCE_DIR}/pysample/_c/sample.h
        ${CMAKE_CURRENT_SOURCE_DIR}/pysample/_c/hash_map.h
        ${CMAKE_CURRENT_SOURCE_DIR}/pysample/_c/sample_counter.h
        ${CMAKE_CURRENT_SOURCE_DIR}/pysample/_c/sample_traceback.h)

add_library(pysample STATIC
        ${CMAKE_CURRENT_SOURCE_DIR}/pysample/_c/hash_map.c
        ${CMAKE_CURRENT_SOURCE_DIR}/pysample/_c/sample_counter.c
        ${CMAKE_CURRENT_SOURCE_DIR}/pysample/_c/sample_traceback.c)