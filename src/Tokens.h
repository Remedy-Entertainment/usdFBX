// Copyright (C) Remedy Entertainment Plc.

#pragma once

#include "pxr/base/tf/staticTokens.h"
#include "pxr/pxr.h"

PXR_NAMESPACE_OPEN_SCOPE
#define USD_FBX_PRIM_TYPE_NAMES                                                                                                  \
	( BasisCurves )( Camera )(                                                                                                   \
		HermiteCurves )( Mesh )( SkelRoot )( Skeleton )( SkelAnimation )( NurbsCurves )( Points )( PolyMesh )( PseudoRoot )( Scope )( Xform )( GeomSubset )( Material )( Shader )
TF_DECLARE_PUBLIC_TOKENS( UsdFbxPrimTypeNames, USD_FBX_PRIM_TYPE_NAMES );

#define USD_FBX_DISPLAYGROUP_TOKENS                                                                                              \
	( ( geometry, "Geometry" ) )( ( skeleton, "Skeleton" ) )( ( shading, "Shading" ) )( ( user, "User" ) )(                      \
		( skelanimation, "SkelAnimation" ) )( ( camera, "Camera" ) )( ( imageable, "Imageable" ) )(                              \
		( generated,                                                                                                             \
		  "Generated" ) ) // For properties/prims that must be retained from FBX but have no default schema representation.
TF_DECLARE_PUBLIC_TOKENS( UsdFbxDisplayGroupTokens, USD_FBX_DISPLAYGROUP_TOKENS );

PXR_NAMESPACE_CLOSE_SCOPE
