cmake_minimum_required(VERSION 3.14)
project(reverseaffinity_benchmark LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Qt5 REQUIRED COMPONENTS Core Gui)

add_executable(benchmark
    benchmark.cpp
    ../src/simd_ops.cpp
)

target_include_directories(benchmark PRIVATE ../include)
target_link_libraries(benchmark PRIVATE Qt5::Core Qt5::Gui)

# Enable SIMD flags
set_source_files_properties(../src/simd_ops.cpp PROPERTIES
    COMPILE_FLAGS "-msse2 -mavx2"
)

if(CMAKE_SYSTEM_PROCESSOR MATCHES "x86_64|AMD64")
    target_compile_options(benchmark PRIVATE -msse2)
endif()
