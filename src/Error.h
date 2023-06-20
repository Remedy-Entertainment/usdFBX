// Copyright (C) Remedy Entertainment Plc.

#pragma once

enum class UsdFbxError
{
	// FBX related
	FBX_UNABLE_TO_OPEN,
	FBX_INCOMPATIBLE_VERSIONS,

	// USDFBX plugin related
	USDFBX_INVALID_LAYER,
	USDFBX_WRITE_TO_FBX_ERROR
};
