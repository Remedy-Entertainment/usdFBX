// Copyright (C) Remedy Entertainment Plc.

#include "UsdFbxFileformat.h"

#include "DebugCodes.h"
#include "Error.h"
#include "PrecompiledHeader.h"
#include "UsdFbxAbstractData.h"

DIAGNOSTIC_PUSH
IGNORE_USD_WARNINGS
#include "pxr/base/gf/range3f.h"

#include <pxr/base/tf/fileUtils.h>
#include <pxr/base/tf/pathUtils.h>
#include <pxr/base/tf/registryManager.h>
#include <pxr/base/vt/array.h>
#include <pxr/pxr.h>
#include <pxr/usd/sdf/fileFormat.h>
#include <pxr/usd/sdf/layer.h>
#include <pxr/usd/usd/stage.h>
#include <pxr/usd/usd/usdaFileFormat.h>
#include <pxr/usd/usdGeom/mesh.h>
#include <pxr/usd/usdGeom/metrics.h>
#include <pxr/usd/usdGeom/xform.h>
#include <pxr/usd/usdSkel/skeleton.h>

DIAGNOSTIC_POP

#include <filesystem>
#include <fstream>
#include <numeric>
#include <string>

PXR_NAMESPACE_USING_DIRECTIVE

TF_DEFINE_PUBLIC_TOKENS( UsdFbxFileFormatTokens, USDFBX_FILE_FORMAT_TOKENS );

// When using TF_REGISTRY_FUNCTION, you must not have /Zc:inline enabled on MSVC
TF_REGISTRY_FUNCTION( TfType )
{
	SDF_DEFINE_FILE_FORMAT( remedy::UsdFbxFileFormat, SdfFileFormat );
}

remedy::UsdFbxFileFormat::UsdFbxFileFormat()
	: SdfFileFormat(
		UsdFbxFileFormatTokens->Id,
		UsdFbxFileFormatTokens->Version,
		UsdFbxFileFormatTokens->Target,
		UsdFbxFileFormatTokens->Id )
	, m_usda( FindById( UsdUsdaFileFormatTokens->Id ) )
{
}

SdfAbstractDataRefPtr remedy::UsdFbxFileFormat::InitData( const FileFormatArguments& args ) const
{
	if( TfDebug::IsEnabled( USDFBX ) )
	{
		const std::string delimiter = "\n\t- ";
		const std::string args_string = std::accumulate(
			args.cbegin(),
			args.cend(),
			std::string(),
			[ delimiter ]( const std::string& s, const std::pair< std::string, std::string >& p )
			{ return s + ( s.empty() ? std::string() : delimiter ) + p.first + " -> " + p.second; } );
		TF_DEBUG( USDFBX ).Msg( "UsdFbx - remedy::UsdFbxFileFormat::InitData(args={%s})\n", args_string.c_str() );
	}

	return UsdFbxAbstractData::New( args );
}

bool remedy::UsdFbxFileFormat::CanRead( const std::string& file ) const
{
	TF_DEBUG( USDFBX ).Msg( "UsdFbx - remedy::UsdFbxFileFormat::CanRead(file=@%s)\n", file.c_str() );

	const auto extension = TfGetExtension( file );
	TF_DEBUG( USDFBX ).Msg(
		"UsdFbx - Testing file extension (%s) against %s",
		extension.c_str(),
		this->GetFormatId().GetString().c_str() );

	if( extension.empty() )
	{
		TF_DEBUG( USDFBX ).Msg( "UsdFbx - File extension is empty! Unable to read \"%s\"", file.c_str() );
		return false;
	}

	return extension == GetFormatId();
}

bool remedy::UsdFbxFileFormat::Read( SdfLayer* layer, const std::string& resolvedPath, bool metadataOnly ) const
{
	TRACE_FUNCTION()

	if( !TF_VERIFY( layer ) )
	{
		TF_ERROR( UsdFbxError::USDFBX_INVALID_LAYER, "remedy::UsdFbxFileFormat::Read -> Input layer is invalid (nullptr)!" );
		return false;
	}

	TF_DEBUG( USDFBX ).Msg(
		"UsdFbx - remedy::UsdFbxFileFormat::Read(layer=@%s@, "
		"resolvedPath=%s, metadataOnly=%s)\n",
		layer->GetIdentifier().c_str(),
		resolvedPath.c_str(),
		TfStringify( metadataOnly ).c_str() );

	auto data = InitData( layer->GetFileFormatArguments() );
	const auto fbxData = TfStatic_cast< UsdFbxAbstractDataRefPtr >( data );
	if( !fbxData->Open( resolvedPath ) )
	{
		return false;
	}

	_SetLayerData( layer, data );
	return true;
}

bool remedy::UsdFbxFileFormat::ReadFromString( SdfLayer* layer, const std::string& str ) const
{
	return m_usda->ReadFromString( layer, str );
}

// We have no need to really output writing to FBX files from USD. So the WriteX
// methods simply output usda content This is only relevant when you open an fbx
// as a layer and you wish to save into that layer
bool remedy::UsdFbxFileFormat::WriteToString( const SdfLayer& layer, std::string* str, const std::string& comment ) const
{
	TF_WARN( "remedy::UsdFbxFileFormat::WriteToString will only output usda data "
			 "for Fbx layers!" );
	return m_usda->WriteToString( layer, str, comment );
}

bool remedy::UsdFbxFileFormat::WriteToStream( const SdfSpecHandle& spec, std::ostream& out, size_t indent ) const
{
	TF_WARN( "remedy::UsdFbxFileFormat::WriteToStream will only output usda data "
			 "for Fbx layers!" );
	return m_usda->WriteToStream( spec, out, indent );
}

bool remedy::UsdFbxFileFormat::WriteToFile(
	const SdfLayer& layer,
	const std::string& filePath,
	const std::string& comment,
	const FileFormatArguments& args ) const
{
	TF_ERROR( UsdFbxError::USDFBX_WRITE_TO_FBX_ERROR, "Writing to Fbx is not implemented!" );
	return false;
}
