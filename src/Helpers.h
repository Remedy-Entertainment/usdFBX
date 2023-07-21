// Copyright (C) Remedy Entertainment Plc.

#pragma once

#include <pxr/pxr.h>
#include <pxr/usd/usd/tokens.h>

PXR_NAMESPACE_USING_DIRECTIVE

namespace remedy
{
	inline std::string cleanName( const std::string& inName, const char* trimLeading, const std::set< std::string >& usedNames )
	{
		if( SdfPath::IsValidIdentifier( inName ) )
		{
			return { inName };
		}

		if( inName.empty() )
		{
			return { '_' };
		}

		std::string name = TfStringTrimLeft( inName, trimLeading );
		name = TfMakeValidIdentifier( name );

		// If the input had already been sanitized, we output the same sanitized name suffixed by an integer
		if( usedNames.find( name ) != usedNames.end() )
		{
			int i = 0;
			std::string attempt = TfStringPrintf( "%s_%d", name.c_str(), ++i );
			while( usedNames.find( attempt ) != usedNames.end() )
			{
				attempt = TfStringPrintf( "%s_%d", name.c_str(), ++i );
			}
			name = attempt;
		}
		return name;
	}

	inline std::string cleanName( const std::string& inName )
	{
		return cleanName( inName, " _", {} );
	}

	inline std::string cleanName( const std::string& inName, const char* trimLeading )
	{
		return cleanName( inName, trimLeading, {} );
	}

	inline std::string cleanName( const std::string& inName, const std::set< std::string >& usedNames )
	{
		return cleanName( inName, " _", usedNames );
	}
} // namespace remedy
