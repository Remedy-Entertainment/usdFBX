// Copyright (C) Remedy Entertainment Plc.
#pragma once

#include "pxr/base/tf/staticTokens.h"
#include "pxr/pxr.h"
#include "pxr/usd/sdf/fileFormat.h"

#include <iosfwd>
#include <string>

#define USDFBX_VERSION_STRINGIFY( x ) #x
constexpr const char* USDFBX_VERSION = {
#include "VERSION"
};
#undef USDFBX_VERSION_STRINGIFY

#define USDFBX_FILE_FORMAT_TOKENS ( ( Id, "fbx" ) )( ( Version, USDFBX_VERSION ) )( ( Target, "usd" ) )
PXR_NAMESPACE_USING_DIRECTIVE

TF_DECLARE_PUBLIC_TOKENS( UsdFbxFileFormatTokens, USDFBX_FILE_FORMAT_TOKENS );

namespace remedy
{
	TF_DECLARE_WEAK_AND_REF_PTRS( UsdFbxFileFormat );

	// NOTE: Ensure the full class name (ex. "remedy::UsdFbxFileFormat") is present
	// in the plugInfo.json's "Types" dict
	class UsdFbxFileFormat : public SdfFileFormat
	{
	public:
		SdfAbstractDataRefPtr InitData( const FileFormatArguments& ) const override;
		bool CanRead( const std::string& file ) const override;
		bool Read( SdfLayer* layer, const std::string& resolvedPath, bool metadataOnly ) const override;
		bool ReadFromString( SdfLayer* layer, const std::string& str ) const override;

		bool WriteToString( const SdfLayer& layer, std::string* str, const std::string& comment = std::string() ) const override;

		bool WriteToStream( const SdfSpecHandle& spec, std::ostream& out, size_t indent ) const override;

		bool WriteToFile(
			const SdfLayer& layer,
			const std::string& filePath,
			const std::string& comment,
			const FileFormatArguments& args ) const override;

	protected:
		// NOTE: Using direct friend class declaration due to namespacing issues with SDF_FILE_FORMAT_FACTORY_ACCESS
		template< typename T >
		friend class PXR_INTERNAL_NS::Sdf_FileFormatFactory;

		UsdFbxFileFormat();

	private:
		SdfFileFormatConstPtr m_usda;
	};
} // namespace remedy
