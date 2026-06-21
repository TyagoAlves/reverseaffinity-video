cmake_minimum_required(VERSION 3.16)
project(reverseaffinity VERSION 0.2.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# ---- Dependency management ----
# Optionally use vcpkg: cmake -DCMAKE_TOOLCHAIN_FILE=.../vcpkg.cmake
# Optionally use conan: conan install . --output-folder=build

# ---- Find Qt5 ----
find_package(Qt5 REQUIRED COMPONENTS Widgets Gui Core OpenGL)

if(NOT Qt5_FOUND)
    message(FATAL_ERROR "Qt5 required (qtbase5-dev). Install:\n"
        "  Debian/Ubuntu: sudo apt install qtbase5-dev\n"
        "  Fedora:        sudo dnf install qt5-qtbase-devel\n"
        "  Arch:          sudo pacman -S qt5-base")
endif()

# Verify Qt5 version >= 5.12
if(Qt5_VERSION VERSION_LESS "5.12")
    message(FATAL_ERROR "Qt5 version ${Qt5_VERSION} is too old. Minimum 5.12 required.")
endif()
message(STATUS "Qt5 found: ${Qt5_VERSION} at ${Qt5_DIR}")

# ---- Find OpenGL ----
find_package(OpenGL REQUIRED)
if(NOT OPENGL_FOUND)
    message(FATAL_ERROR "OpenGL required (libgl1-mesa-dev).")
endif()

# ---- Find MOC ----
find_program(QT_MOC_EXECUTABLE NAMES moc-qt5 moc)
if(NOT QT_MOC_EXECUTABLE)
    message(FATAL_ERROR "moc (Qt5 meta-object compiler) not found. Install qt5-qmake or qt5-qtbase-dev.")
endif()

# ---- MOC headers ----
set(MOC_HEADERS
    include/canvas.h
    include/gl_canvas.h
    include/app_ui.h
    include/panels.h
)

set(MOC_DIR "${CMAKE_BINARY_DIR}/moc")
file(MAKE_DIRECTORY ${MOC_DIR})

foreach(header ${MOC_HEADERS})
    get_filename_component(basename ${header} NAME_WE)
    set(moc_output "${MOC_DIR}/moc_${basename}.cpp")
    set(moc_input "${CMAKE_CURRENT_SOURCE_DIR}/${header}")

    add_custom_command(
        OUTPUT ${moc_output}
        COMMAND ${QT_MOC_EXECUTABLE}
            -I${CMAKE_CURRENT_SOURCE_DIR}/include
            -I${CMAKE_CURRENT_SOURCE_DIR}/include
            -o ${moc_output}
            ${moc_input}
        DEPENDS ${moc_input}
        COMMENT "Generating MOC for ${header}"
    )
    list(APPEND MOC_SOURCES ${moc_output})
endforeach()

# ---- Sources ----
set(SOURCES
    src/main.cpp
    src/layers.cpp
    src/history.cpp
    src/filters.cpp
    src/tools.cpp
    src/canvas.cpp
    src/panels.cpp
    src/app_ui.cpp
    src/simd_ops.cpp
    src/gl_canvas.cpp
    ${MOC_SOURCES}
)

add_executable(reverseaffinity ${SOURCES})

target_include_directories(reverseaffinity PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_link_libraries(reverseaffinity PRIVATE
    Qt5::Widgets
    Qt5::Gui
    Qt5::Core
    Qt5::OpenGL
    OpenGL::GL
)

target_compile_options(reverseaffinity PRIVATE -fPIC -msse2)

set_source_files_properties(src/simd_ops.cpp PROPERTIES
    COMPILE_OPTIONS "-msse2;-mavx2"
)
