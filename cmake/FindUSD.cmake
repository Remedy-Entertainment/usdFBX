# Simple module to find USD.
find_file(USD_CONFIG_FILE
    NAMES
    pxrConfig.cmake
    PATHS
    ${PXR_USD_LOCATION}
    $ENV{PXR_USD_LOCATION}
)

# Force PXR_USD_LOCATION to always be the parent directory of the pxrConfig.cmake file
get_filename_component(PXR_USD_LOCATION "${USD_CONFIG_FILE}" DIRECTORY)
include(${USD_CONFIG_FILE})

# Wrap PXR_INCLUDE_DIRS
set(USD_INCLUDE_DIR ${PXR_INCLUDE_DIRS})
set(USD_VERSION ${PXR_MAJOR_VERSION}.${PXR_MINOR_VERSION}.${PXR_PATCH_VERSION})
set(USD_LIB_PREFIX "${CMAKE_SHARED_LIBRARY_PREFIX}usd_")

# Get /lib dir
if(WIN32)
    set(USD_LIB_SUFFIX ${CMAKE_STATIC_LIBRARY_SUFFIX})
else()
    set(USD_LIB_SUFFIX ${CMAKE_SHARED_LIBRARY_SUFFIX})
endif()
find_library(USD_LIBRARY
    NAMES
    ${USD_LIB_PREFIX}usd${USD_LIB_SUFFIX}
    HINTS
    ${PXR_USD_LOCATION}
    $ENV{PXR_USD_LOCATION}
    ${PXR_USD_LOCATION}/lib
    $ENV{PXR_USD_LOCATION}/lib
    PATH_SUFFIXES
    lib
)
get_filename_component(USD_LIBRARY_DIR ${USD_LIBRARY} DIRECTORY)

message(STATUS "USD include dir: ${USD_INCLUDE_DIR}")
message(STATUS "USD library dir: ${USD_LIBRARY_DIR}")
message(STATUS "USD version: ${USD_VERSION}")

if(NOT DEFINED ENV{BOOST_ROOT})
    set(ENV{BOOST_ROOT} ${PXR_USD_LOCATION})
endif()

include(FindPackageHandleStandardArgs)
find_package_handle_standard_args(USD
    REQUIRED_VARS
    PXR_USD_LOCATION
    USD_INCLUDE_DIR
    USD_LIBRARY_DIR
    USD_CONFIG_FILE
    USD_VERSION
    PXR_VERSION
)