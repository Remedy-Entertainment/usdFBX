// Copyright (C) Remedy Entertainment Plc.

#include "DebugCodes.h"

#include "PrecompiledHeader.h"

#include <pxr/base/tf/debug.h>
#include <pxr/base/tf/registryManager.h>

PXR_NAMESPACE_USING_DIRECTIVE

TF_REGISTRY_FUNCTION( TfDebug )
{
	TF_DEBUG_ENVIRONMENT_SYMBOL( USDFBX, "UsdFbx debug logging for generic operations" )
	TF_DEBUG_ENVIRONMENT_SYMBOL( USDFBX_FBX_READERS, "UsdFbx debug logging for any FbxNode readers" )
}
