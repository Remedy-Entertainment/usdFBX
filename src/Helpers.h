// Copyright (C) Remedy Entertainment Plc.

#pragma once

#include <pxr/pxr.h>
#include <pxr/usd/usd/tokens.h>

PXR_NAMESPACE_USING_DIRECTIVE

namespace remedy
{
	struct FbxNameFixer
	{
		std::string operator()( const std::string& x ) const
		{
			return TfMakeValidIdentifier( x );
		}
	};

	template< class T >
	std::string cleanName(
		const std::string& inName,
		const char* trimLeading,
		const std::set< std::string >& usedNames,
		T fixer,
		bool ( *test )( const std::string& ) = &SdfPath::IsValidIdentifier )
	{
		if( test( inName ) )
		{
			return { inName };
		}

		// Mangle name into desired form.
		// Handle empty name.
		std::string name = inName;
		if( name.empty() )
		{
			name = '_';
		}
		else
		{
			// Trim leading.
			name = TfStringTrimLeft( name, trimLeading );

			// If name is not a valid identifier then substitute characters.
			if( !test( name ) )
			{
				name = fixer( name );
			}
		}

		// Now check against usedNames.
		if( usedNames.find( name ) != usedNames.end() )
		{
			// Just number the tries.
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

	template< class T >
	std::string cleanName( const std::string& inName, const char* trimLeading, T fixer )
	{
		return cleanName( inName, trimLeading, {}, fixer );
	}
} // namespace remedy
