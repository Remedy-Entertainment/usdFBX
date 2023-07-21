
set(TARGET_NAME usdFbx)
set(TARGET_NAME_HOUDINI usdFbx_houdini)

set(SOURCES     
DebugCodes.cpp
Error.cpp
FbxNodeReader.cpp
Tokens.cpp
UsdFbxAbstractData.cpp
UsdFbxDataReader.cpp
UsdFbxFileformat.cpp)

set(PLUGINFO_FILENAME "plugInfo.json")
set(USDFBX_VERSION "1.1.0")

file(WRITE "VERSION" "USDFBX_VERSION_STRINGIFY( ${USDFBX_VERSION} )")

# BASIC MODULE
# ------------
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/plugins/${TARGET_NAME})
add_library(${TARGET_NAME} MODULE)
target_sources(${TARGET_NAME}
    PRIVATE
    ${SOURCES}
)
target_include_directories(${TARGET_NAME}
    PRIVATE
    .
    ${PXR_INCLUDE_DIRS}
    ${Boost_INCLUDE_DIRS}
    ${ADSK_FBX_INCLUDE_DIR}
    ${Python_INCLUDE_DIRS}
)

target_compile_definitions(${TARGET_NAME} PRIVATE USDFBX_EXPORTS)
if(WIN32)
    cmake_path(GET ADSK_FBX_LIBRARY PARENT_PATH FBX_LIB_PATH)
    message( STATUS "FBX_LIB_PATH: ${FBX_LIB_PATH}")
    target_link_libraries(${TARGET_NAME} ${PXR_LIBRARIES} ${ADSK_FBX_LIBRARY})
    target_compile_definitions(${TARGET_NAME} PRIVATE FBXSDK_SHARED=1 )
else()
    target_link_libraries(${TARGET_NAME} ${PXR_LIBRARIES} ${ADSK_FBX_LIBRARY} libxml2.so libz.so)
endif()

target_precompile_headers(${TARGET_NAME}
    PRIVATE
    PrecompiledHeader.h
)

set(TARGET_FILENAME "${CMAKE_SHARED_LIBRARY_PREFIX}${TARGET_NAME}${CMAKE_SHARED_LIBRARY_SUFFIX}")

set(PLUG_INFO_RESOURCE_PATH "resources")
set(PLUG_INFO_ROOT "..")
set(PLUG_INFO_LIBRARY_PATH "${TARGET_FILENAME}")

configure_file(
    ${PLUGINFO_FILENAME}
    ${CMAKE_LIBRARY_OUTPUT_DIRECTORY}/${PLUG_INFO_RESOURCE_PATH}/${PLUGINFO_FILENAME}
)

if(WIN32)
string(REGEX REPLACE "[.]lib$" ".dll" FBX_DLL ${ADSK_FBX_LIBRARY})
message(STATUS "FBX DLL: ${FBX_DLL}")
message(STATUS "POST BUILD COPY TO ${CMAKE_CURRENT_BINARY_DIR}/libfbxsdk.dll")
add_custom_command(TARGET ${TARGET_NAME} POST_BUILD  
    COMMAND ${CMAKE_COMMAND} -E copy_if_different 
        ${FBX_DLL}
        ${CMAKE_LIBRARY_OUTPUT_DIRECTORY}/$<CONFIG>) 

add_custom_command(TARGET ${TARGET_NAME} POST_BUILD  
    COMMAND ${CMAKE_COMMAND} -E copy_if_different 
        ${CMAKE_LIBRARY_OUTPUT_DIRECTORY}/${PLUG_INFO_RESOURCE_PATH}/${PLUGINFO_FILENAME}
        ${CMAKE_LIBRARY_OUTPUT_DIRECTORY}/$<CONFIG>/${PLUG_INFO_RESOURCE_PATH}/${PLUGINFO_FILENAME}) 
endif()

# HOUDINI MODULE
# --------------
if(DEFINED Houdini_FOUND)
    message(STATUS "Houdini Found, configuring another target for Houdini specifically")
    set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/plugins/${TARGET_NAME_HOUDINI})
    add_library(${TARGET_NAME_HOUDINI} MODULE)
    target_sources(${TARGET_NAME_HOUDINI}
        PRIVATE
        ${SOURCES}
    )
    target_include_directories(${TARGET_NAME_HOUDINI}
        PRIVATE
        .
        ${_houdini_include_dir}/fbx
    )
    target_compile_definitions(${TARGET_NAME_HOUDINI} PRIVATE USDFBX_EXPORTS HOUDINI FBXSDK_SHARED)

    target_link_libraries(${TARGET_NAME_HOUDINI} Houdini)

    if(WIN32)
        # libfbxsdk is not listed in houdiniConfig.cmake as an external dep, but we need the symbols in it for this plugin
        set( _houdini_fbx_target_name Houdini::Dep::fbxsdk )
        add_library( ${_houdini_fbx_target_name} SHARED IMPORTED )
        set_target_properties(
            ${_houdini_fbx_target_name}
            PROPERTIES
                IMPORTED_IMPLIB ${_houdini_install_root}/custom/houdini/dsolib/libfbxsdk.lib
        )

        set(extra_deps fbxsdk;python3.9;pxr_usdUtils;pxr_ar;pxr_arch;pxr_gf;pxr_js;pxr_kind;pxr_ndr;pxr_pcp;pxr_plug;pxr_sdf;pxr_sdr;pxr_tf;pxr_trace;pxr_usd;pxr_usdGeom;pxr_usdHydra;pxr_usdLux;pxr_usdRender;pxr_usdRi;pxr_usdShade;pxr_usdSkel;pxr_usdVol;pxr_vt;pxr_work;hboost_python;pxr_usdImaging;pxr_cameraUtil;pxr_hd;pxr_hf;pxr_pxOsd)
        foreach(extra_dep ${extra_deps})
            target_link_libraries(${TARGET_NAME_HOUDINI} Houdini::Dep::${extra_dep})
        endforeach()
    endif()
    target_precompile_headers(${TARGET_NAME_HOUDINI}
        PRIVATE
        PrecompiledHeader.h
    )

    set(TARGET_FILENAME "${CMAKE_SHARED_LIBRARY_PREFIX}${TARGET_NAME_HOUDINI}${CMAKE_SHARED_LIBRARY_SUFFIX}")

    set(PLUG_INFO_RESOURCE_PATH "resources")
    set(PLUG_INFO_ROOT "..")
    set(PLUG_INFO_LIBRARY_PATH "${TARGET_FILENAME}")

    configure_file(
        ${PLUGINFO_FILENAME}
        ${CMAKE_LIBRARY_OUTPUT_DIRECTORY}/${PLUG_INFO_RESOURCE_PATH}/${PLUGINFO_FILENAME}
    )
endif()


# TESTS
# -----
if(USDFBX_BUILD_TESTS)
    set(TEST_CMD python -m pytest)
    execute_process(COMMAND python -m pytest --version
        OUTPUT_VARIABLE PYTEST_output 
        ERROR_VARIABLE  PYTEST_error
        RESULT_VARIABLE PYTEST_result)
    if(NOT ${PYTEST_result} EQUAL 0)
        message(SEND_ERROR "Pytest package not available: ${PYTEST_error}")
    endif()
    message(STATUS "PYTEST has been found")


    add_test(NAME all_tests COMMAND ${TEST_CMD} tests WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}  )

    set(DELIM ":")
    if(WIN32)
        set(DELIM ";")
    endif()

    set(_OUT_DIR ${CMAKE_LIBRARY_OUTPUT_DIRECTORY}/$<CONFIG>)
    set(_PYTHONPATH ${USD_LIBRARY_DIR}/python)
    set(_PATH "${_OUT_DIR}\\${DELIM}${USD_LIBRARY_DIR}\\${DELIM}${PXR_USD_LOCATION}/bin")
    set(_PXR_PLUGINPATH_NAME ${_OUT_DIR}/${PLUG_INFO_RESOURCE_PATH})

    set_tests_properties(all_tests 
        PROPERTIES ENVIRONMENT "PYTHONPATH=${_PYTHONPATH};PATH=${_PATH}\\${DELIM}$ENV{PATH};LD_LIBRARY_PATH=${USD_LIBRARY_DIR};PXR_PLUGINPATH_NAME=${_PXR_PLUGINPATH_NAME}")

    if (CMAKE_CONFIGURATION_TYPES)
        add_custom_target(unit_tests COMMAND ${CMAKE_CTEST_COMMAND} 
            --force-new-ctest-process --output-on-failure 
            --build-config "$<CONFIGURATION>")
    else()
        add_custom_target(unit_tests COMMAND ${CMAKE_CTEST_COMMAND} 
            --force-new-ctest-process --output-on-failure)
    endif()
endif()


# INSTALLING
# ----------


install(
    TARGETS ${TARGET_NAME}
    DESTINATION "${CMAKE_INSTALL_PREFIX}/${TARGET_NAME}"
)

install(
    FILES ${CMAKE_BINARY_DIR}/plugins/${TARGET_NAME}/${PLUG_INFO_RESOURCE_PATH}/${PLUGINFO_FILENAME}
    DESTINATION "${CMAKE_INSTALL_PREFIX}/${TARGET_NAME}/resources"
)

# Only install fbxsdk dynamic library on windows, assuming shared linkage. TODO: Add support for static linking 
if(WIN32)
    install(
        FILES ${CMAKE_BINARY_DIR}/plugins/${TARGET_NAME}/$<CONFIG>/libfbxsdk.dll
        DESTINATION "${CMAKE_INSTALL_PREFIX}/${TARGET_NAME}"
    )
endif()

# INSTALLING HOUDINI MODULE
# --------------
if(DEFINED Houdini_FOUND)
    install(
        TARGETS ${TARGET_NAME_HOUDINI}
        DESTINATION "${CMAKE_INSTALL_PREFIX}/${TARGET_NAME_HOUDINI}"
    )

    install(
        FILES ${CMAKE_BINARY_DIR}/plugins/${TARGET_NAME_HOUDINI}/${PLUG_INFO_RESOURCE_PATH}/${PLUGINFO_FILENAME}
        DESTINATION "${CMAKE_INSTALL_PREFIX}/${TARGET_NAME_HOUDINI}/resources"
    )
endif()
