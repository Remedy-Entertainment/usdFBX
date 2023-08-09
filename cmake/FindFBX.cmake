# TODO set options for STATIC/DYNAMIC linkage of FBX 

IF(WIN32)
    SET(ADSK_FBX_LIB_EXTENSION ".lib")
ELSE(WIN32)
    SET(ADSK_FBX_LIB_EXTENSION ".a")
    IF(ADSK_FBX_SHARED)
        IF(APPLE)
            SET(ADSK_FBX_LIB_EXTENSION ".dylib")
        ELSEIF(LINUX)
            SET(ADSK_FBX_LIB_EXTENSION ".so")
        ENDIF()
    ENDIF()
ENDIF(WIN32)
set(ADSK_FBX_LIB_NAME "libfbxsdk${ADSK_FBX_LIB_EXTENSION}")


set(fbx_arch_name "")
set(compiler_name "")
if(UNIX AND NOT APPLE)
    set(fbx_arch_name "x64")
    set(compiler_name "gcc")
elseif(WIN32)
    set(fbx_arch_name "x64")
    if(MSVC_TOOLSET_VERSION EQUAL 140)
        set(compiler_name "vs2015")
    elseif(MSVC_TOOLSET_VERSION EQUAL 141)
        set(compiler_name "vs2017")

    elseif(MSVC_TOOLSET_VERSION EQUAL 142)
        set(compiler_name "vs2019")
    elseif(MSVC_TOOLSET_VERSION EQUAL 143)
        set(compiler_name "vs2022")
    endif()
elseif(APPLE)
    set(fbx_arch_name "")
    set(compiler_name "clang")
else()
    message(ERROR "Unhandled platform")
endif()

set( ADSK_FBX_LIB_DIR "${ADSK_FBX_LOCATION}/lib/${compiler_name}/${fbx_arch_name}/$<IF:$<CONFIG:Debug>,debug,release>")

message(STATUS "Compiler Name: ${compiler_name}")
message(STATUS "Search path: ${ADSK_FBX_LIB_DIR}")

message(STATUS "Looking for FBX in : ${ADSK_FBX_LOCATION}")

set( ADSK_FBX_LIBRARY "${ADSK_FBX_LIB_DIR}/${ADSK_FBX_LIB_NAME}")
message(STATUS "Fbx Library: ${ADSK_FBX_LIBRARY}")

find_path(ADSK_FBX_INCLUDE_DIR
    fbxsdk.h
    HINTS
    "${ADSK_FBX_LOCATION}/include"
    "$ENV{ADSK_FBX_LOCATION}/include"
    DOC
    "Autodesk FBX SDK headers path"
)

if(ADSK_FBX_INCLUDE_DIR AND EXISTS "${ADSK_FBX_INCLUDE_DIR}/fbxsdk/fbxsdk_version.h")
    file(STRINGS "${ADSK_FBX_INCLUDE_DIR}/fbxsdk/fbxsdk_version.h" TMP REGEX "^#define FBXSDK_VERSION_MAJOR.*$")
    string(REGEX MATCHALL "[0-9]+" MAJOR ${TMP})
    file(STRINGS "${ADSK_FBX_INCLUDE_DIR}/fbxsdk/fbxsdk_version.h" TMP REGEX "^#define FBXSDK_VERSION_MINOR.*$")
    string(REGEX MATCHALL "[0-9]+" MINOR ${TMP})
    file(STRINGS "${ADSK_FBX_INCLUDE_DIR}/fbxsdk/fbxsdk_version.h" TMP REGEX "^#define FBXSDK_VERSION_POINT.*$")
    string(REGEX MATCHALL "[0-9]+" PATCH ${TMP})

    set(ADSK_FBX_VERSION ${MAJOR}.${MINOR}.${PATCH})
endif()

include(FindPackageHandleStandardArgs)

find_package_handle_standard_args(FBX
    REQUIRED_VARS
    ADSK_FBX_INCLUDE_DIR
    ADSK_FBX_LIBRARY
    VERSION_VAR
    ADSK_FBX_VERSION
)
