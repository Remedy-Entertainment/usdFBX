// Copyright (C) Remedy Entertainment Plc.

// TODO: Rework into cmake precompiled header
#pragma once

// Allow usage of normal std::max/min functions rather than the old school
// windows macros
#if defined( _WIN64 ) || defined( _WIN32 )

#ifndef NOMINMAX
#define NOMINMAX
#endif

#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif

#include <windows.h>
#endif

#if defined( __clang__ ) && !defined( __clang_analyzer__ )
#define CLANG
#endif

#if defined( _MSC_VER )
#define MSVC
#endif

#if defined( __GNUC__ ) || defined( __GNUG__ )
#define GCC
#endif

#define DIAGNOSTIC_CLANG_IGNORE( ... )
#define DIAGNOSTIC_MSVC_IGNORE( ... )
#define DIAGNOSTIC_GCC_IGNORE( ... )

#if defined( CLANG )
#define DO_PRAGMA( x ) _Pragma( #x )
#define DIAGNOSTIC_PUSH _Pragma( "clang diagnostic push" )
#undef DIAGNOSTIC_CLANG_IGNORE
#define DIAGNOSTIC_CLANG_IGNORE( args ) DO_PRAGMA( clang diagnostic ignored args )
#define DIAGNOSTIC_POP _Pragma( "clang diagnostic pop" )
#define IGNORE_USD_WARNINGS                                                                                                      \
	DIAGNOSTIC_GCC_IGNORE( "-Wno-deprecated"                                                                                     \
						   "Wdeprecated-declarations" );
#elif defined( MSVC )
#define DIAGNOSTIC_PUSH __pragma( warning( push ) )
#undef DIAGNOSTIC_MSVC_IGNORE
#define DIAGNOSTIC_MSVC_IGNORE( args ) __pragma( warning( disable : args ) )
#define DIAGNOSTIC_POP __pragma( warning( pop ) )

// 4003: not enough actual parameters for macro 'identifier'
// 4127: conditional expression is constant
// 4201: nonstandard extension used : nameless struct/union
// 4244: 'argument' : conversion from 'type1' to 'type2', possible loss of data
// 4244: non - DLL - interface class 'class_1' used as base for DLL - interface class 'class_2'
// 4245: 'initializing': conversion from 'int' to 'size_t', signed/unsigned mismatch
// 4265: class has virtual functions, but destructor is not virtual
// 4305: 'context' : truncation from 'type1' to 'type2'
// 4619: #pragma warning : there is no warning number 'number'
// 4100: unreferenced formal parameter
#define IGNORE_USD_WARNINGS
DIAGNOSTIC_MSVC_IGNORE( 4003 4127 4201 4244 4245 4265 4267 4275 4305 4619 4100 );

#elif defined( GCC )
#define DO_PRAGMA( x ) _Pragma( #x )
#define DIAGNOSTIC_PUSH _Pragma( "GCC diagnostic push" )
#undef DIAGNOSTIC_GCC_IGNORE
#define DIAGNOSTIC_GCC_IGNORE( args ) DO_PRAGMA( GCC diagnostic ignored args )
#define DIAGNOSTIC_POP _Pragma( "GCC diagnostic pop" )

#define IGNORE_USD_WARNINGS                                                                                                      \
	DIAGNOSTIC_GCC_IGNORE( "-Wno-deprecated"                                                                                     \
						   "Wdeprecated-declarations" );
#else
#define DIAGNOSTIC_PUSH
#define DIAGNOSTIC_POP
#define IGNORE_USD_WARNINGS
#endif

// IGNORE SPECIFIC WARNINGS
DIAGNOSTIC_PUSH

#if defined( MSVC )
DIAGNOSTIC_MSVC_IGNORE( 4619 )
// there is no warning 'x' (fbxsdk is trying to suppress warning 4345, which
// only exists up to VS2012)
#elif defined( CLANG )
DIAGNOSTIC_CLANG_IGNORE( "-Wunknown-warning-option" )
#endif

#include <fbxsdk.h>
DIAGNOSTIC_POP

#include <string>

DIAGNOSTIC_PUSH
IGNORE_USD_WARNINGS
#include <pxr/base/gf/transform.h>
#include <pxr/base/gf/vec3f.h>
#include <pxr/base/gf/vec4f.h>
#include <pxr/base/vt/array.h>
#include <pxr/pxr.h>

DIAGNOSTIC_POP
