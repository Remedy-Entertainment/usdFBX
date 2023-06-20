// Copyright (C) Remedy Entertainment Plc.

#include "Error.h"

#include "PrecompiledHeader.h"

#include <pxr/base/tf/enum.h>
#include <pxr/base/tf/registryManager.h>

PXR_NAMESPACE_USING_DIRECTIVE

TF_REGISTRY_FUNCTION( TfEnum )
{
	TF_ADD_ENUM_NAME( UsdFbxError::FBX_UNABLE_TO_OPEN, "Unable to open Fbx file" );
	TF_ADD_ENUM_NAME( UsdFbxError::FBX_INCOMPATIBLE_VERSIONS, "Incompatible versions between the SDK and the file used" );
	TF_ADD_ENUM_NAME( UsdFbxError::USDFBX_INVALID_LAYER, "Invalid target layer" );
	TF_ADD_ENUM_NAME( UsdFbxError::USDFBX_WRITE_TO_FBX_ERROR, "Error Writing Fbx from Usd" );
};
