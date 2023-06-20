cmake_minimum_required(VERSION 3.12)
project(usdFbx VERSION 1.0.0)

include(CTest)
enable_testing()

set(CMAKE_MODULE_PATH
    ${CMAKE_MODULE_PATH}
    ${CMAKE_CURRENT_SOURCE_DIR}/cmake
)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(WIN32)
    # Necessary to ensure that MSVC does not optimize away the SdfFileFormat registration callback
    set(CMAKE_CXX_FLAGS "/Zc:inline- /EHsc")
endif()

find_package(USD 0.22.08 REQUIRED)
find_package(FBX 2020.0.0 REQUIRED)
find_package(Python 3.7 COMPONENTS Interpreter Development REQUIRED)
find_package(Boost REQUIRED)

if(DEFINED SIDEFX_HDK_LOCATION)
    list( APPEND CMAKE_PREFIX_PATH "${SIDEFX_HDK_LOCATION}/cmake" )
    find_package(Houdini REQUIRED)
endif()

add_subdirectory(src)

set(CPACK_PROJECT_NAME ${PROJECT_NAME})
set(CPACK_PROJECT_VERSION ${PROJECT_VERSION})
include(CPack)
