cmake_minimum_required(VERSION 3.14)
project(reverseaffinity VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find Qt5 using qt_local cmake config (for headers and moc tool)
find_package(Qt5 REQUIRED COMPONENTS Widgets Gui Core OpenGL)

# Override library paths to use system Qt5 .so.5 (avoid ICU version mismatch)
set(QT5_SYS_LIB_DIR "/usr/lib/x86_64-linux-gnu")
set_target_properties(Qt5::Core PROPERTIES IMPORTED_LOCATION_RELEASE "${QT5_SYS_LIB_DIR}/libQt5Core.so.5")
set_target_properties(Qt5::Gui PROPERTIES IMPORTED_LOCATION_RELEASE "${QT5_SYS_LIB_DIR}/libQt5Gui.so.5")
set_target_properties(Qt5::Widgets PROPERTIES IMPORTED_LOCATION_RELEASE "${QT5_SYS_LIB_DIR}/libQt5Widgets.so.5")
set_target_properties(Qt5::OpenGL PROPERTIES IMPORTED_LOCATION_RELEASE "${QT5_SYS_LIB_DIR}/libQt5OpenGL.so.5")

# Find OpenGL
find_package(OpenGL REQUIRED)

# Find moc from qt_local
find_program(QT_MOC_EXECUTABLE moc
    PATHS "${CMAKE_SOURCE_DIR}/qt_local/gcc_64/bin"
    NO_DEFAULT_PATH
)

# MOC headers manually
set(MOC_HEADERS
    include/canvas.h
    include/gl_canvas.h
    include/app_ui.h
    include/panels.h
)

# Create MOC cpp files directory
set(MOC_DIR "${CMAKE_BINARY_DIR}/moc")
file(MAKE_DIRECTORY ${MOC_DIR})

foreach(header ${MOC_HEADERS})
    get_filename_component(basename ${header} NAME_WE)
    set(moc_output "${MOC_DIR}/moc_${basename}.cpp")
    set(moc_input "${CMAKE_SOURCE_DIR}/${header}")

    add_custom_command(
        OUTPUT ${moc_output}
        COMMAND ${QT_MOC_EXECUTABLE}
            -I${CMAKE_SOURCE_DIR}/include
            -I${CMAKE_SOURCE_DIR}/qt_local/gcc_64/include
            -o ${moc_output}
            ${moc_input}
        DEPENDS ${moc_input}
        COMMENT "Generating MOC for ${header}"
    )
    list(APPEND MOC_SOURCES ${moc_output})
endforeach()

# Add the executable
add_executable(reverseaffinity
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

target_include_directories(reverseaffinity PRIVATE include)

target_link_libraries(reverseaffinity PRIVATE
    Qt5::Widgets
    Qt5::Gui
    Qt5::Core
    Qt5::OpenGL
    OpenGL::GL
)

# Qt5 headers require -fPIC (built with -reduce-relocations)
target_compile_options(reverseaffinity PRIVATE -fPIC -msse2)

# Enable SIMD flags for simd_ops.cpp
set_source_files_properties(src/simd_ops.cpp PROPERTIES
    COMPILE_FLAGS "-msse2 -mavx2"
)
