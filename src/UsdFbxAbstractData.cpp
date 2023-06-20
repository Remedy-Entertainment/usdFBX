// Copyright (C) Remedy Entertainment Plc.

#include "UsdFbxAbstractData.h"

#include "DebugCodes.h"
#include "PrecompiledHeader.h"
#include "UsdFbxDataReader.h"

#include <pxr/base/tf/fileUtils.h>
#include <pxr/base/trace/trace.h>
#include <pxr/pxr.h>
#include <pxr/usd/sdf/schema.h>
#include <pxr/usd/usd/timeCode.h>

PXR_NAMESPACE_USING_DIRECTIVE

#define RAISE_UNSUPPORTED( M ) TF_RUNTIME_ERROR( "Fbx " #M "() not supported" )

namespace
{
	template< class T >
	bool bracketTimeSamples( const T& samples, double usdTime, double* tLower, double* tUpper )
	{
		if( samples.empty() )
		{
			return false;
		}

		auto i = std::lower_bound( samples.cbegin(), samples.cend(), usdTime );
		if( i == samples.end() )
		{
			// Past last sample.
			*tLower = *tUpper = *--i;
		}
		else if( i == samples.begin() || *i == usdTime )
		{
			// Before first sample or at a sample.
			*tLower = *tUpper = *i;
		}
		else
		{
			// Bracket a sample.
			*tUpper = *i;
			*tLower = *--i;
		}
		return true;
	}
} // namespace

remedy::UsdFbxAbstractData::UsdFbxAbstractData( SdfFileFormat::FileFormatArguments args )
	: m_arguments( std::move( args ) )
{
}

remedy::UsdFbxAbstractData::~UsdFbxAbstractData()
{
	if( m_reader )
	{
		m_reader->Close();
	}
}

remedy::UsdFbxAbstractDataRefPtr remedy::UsdFbxAbstractData::New( SdfFileFormat::FileFormatArguments args )
{
	return TfCreateRefPtr( new UsdFbxAbstractData( std::move( args ) ) );
}

bool remedy::UsdFbxAbstractData::Open( const std::string& filePath )
{
	TfAutoMallocTag2 tag( "UsdFbxAbstractData", "UsdFbxAbstractData::Open" );
	TRACE_FUNCTION()

	m_reader.reset( new UsdFbxDataReader() );
	if( m_reader->Open( filePath, m_arguments ) )
	{
		return true;
	}

	TF_RUNTIME_ERROR( "Failed to open FBX file \"%s\": %s\n", filePath.c_str(), m_reader->GetErrors().c_str() );
	return false;
}

void remedy::UsdFbxAbstractData::Close()
{
	m_reader->Close();
}

bool remedy::UsdFbxAbstractData::StreamsData() const
{
	return true;
}

void remedy::UsdFbxAbstractData::CreateSpec( const SdfPath& path, SdfSpecType specType )
{
	RAISE_UNSUPPORTED( CreateSpec );
}

bool remedy::UsdFbxAbstractData::HasSpec( const SdfPath& path ) const
{
	return m_reader ? m_reader->HasSpec( path ) : ( path == SdfPath::AbsoluteRootPath() );
}

void remedy::UsdFbxAbstractData::EraseSpec( const SdfPath& path )
{
	RAISE_UNSUPPORTED( EraseSpec );
}

void remedy::UsdFbxAbstractData::MoveSpec( const SdfPath& oldPath, const SdfPath& newPath )
{
	RAISE_UNSUPPORTED( MoveSpec );
}

SdfSpecType remedy::UsdFbxAbstractData::GetSpecType( const SdfPath& path ) const
{
	if( path == SdfPath::AbsoluteRootPath() )
	{
		return SdfSpecTypePseudoRoot;
	}

	return m_reader ? m_reader->GetSpecType( path ) : SdfSpecTypeUnknown;
}

void remedy::UsdFbxAbstractData::_VisitSpecs( SdfAbstractDataSpecVisitor* visitor ) const
{
	if( m_reader )
	{
		m_reader->VisitSpecs( *this, visitor );
	}
}

bool remedy::UsdFbxAbstractData::Has( const SdfPath& path, const TfToken& fieldName, SdfAbstractDataValue* value ) const
{
	if( !m_reader )
	{
		return false;
	}

	if( value )
	{
		VtValue val;
		if( m_reader->Has( path, fieldName, &val ) )
		{
			return value->StoreValue( val );
		}
	}
	else
	{
		return m_reader->Has( path, fieldName, nullptr );
	}
	return false;
}

bool remedy::UsdFbxAbstractData::Has( const SdfPath& path, const TfToken& fieldName, VtValue* value ) const
{
	const bool res = m_reader ? m_reader->Has( path, fieldName, value ) : false;
	return res;
}

bool remedy::UsdFbxAbstractData::HasSpecAndField(
	const SdfPath& path,
	const TfToken& fieldName,
	SdfAbstractDataValue* value,
	SdfSpecType* spec ) const
{
	*spec = GetSpecType( path );
	return *spec != SdfSpecTypeUnknown && Has( path, fieldName, value );
}

bool remedy::UsdFbxAbstractData::HasSpecAndField(
	const SdfPath& path,
	const TfToken& fieldName,
	VtValue* value,
	SdfSpecType* spec ) const
{
	*spec = GetSpecType( path );
	return *spec != SdfSpecTypeUnknown && Has( path, fieldName, value );
}

VtValue remedy::UsdFbxAbstractData::Get( const SdfPath& path, const TfToken& fieldName ) const
{
	VtValue result;
	if( m_reader )
	{
		if( !m_reader->Has( path, fieldName, &result ) )
		{
			return VtValue();
		}
	}
	return result;
}

void remedy::UsdFbxAbstractData::Set( const SdfPath& path, const TfToken& fieldName, const VtValue& value )
{
	RAISE_UNSUPPORTED( Set );
}

void remedy::UsdFbxAbstractData::Set( const SdfPath& path, const TfToken& fieldName, const SdfAbstractDataConstValue& value )
{
	RAISE_UNSUPPORTED( Set );
}

void remedy::UsdFbxAbstractData::Erase( const SdfPath& path, const TfToken& fieldName )
{
	RAISE_UNSUPPORTED( Erase );
}

std::vector< TfToken > remedy::UsdFbxAbstractData::List( const SdfPath& path ) const
{
	return m_reader ? m_reader->List( path ) : std::vector< TfToken >();
}

std::set< double > remedy::UsdFbxAbstractData::ListAllTimeSamples() const
{
	return m_reader ? m_reader->ListAllTimeSamples() : std::set< double >{};
}

std::set< double > remedy::UsdFbxAbstractData::ListTimeSamplesForPath( const SdfPath& path ) const
{
	return m_reader ? m_reader->ListTimeSamplesForPath( path ) : std::set< double >{};
}

bool remedy::UsdFbxAbstractData::GetBracketingTimeSamples( double time, double* tLower, double* tUpper ) const
{
	return bracketTimeSamples( ListAllTimeSamples(), time, tLower, tUpper );
}

size_t remedy::UsdFbxAbstractData::GetNumTimeSamplesForPath( const SdfPath& path ) const
{
	return ListTimeSamplesForPath( path ).size();
}

bool remedy::UsdFbxAbstractData::GetBracketingTimeSamplesForPath(
	const SdfPath& path,
	double time,
	double* tLower,
	double* tUpper ) const
{
	return bracketTimeSamples( ListTimeSamplesForPath( path ), time, tLower, tUpper );
}

bool remedy::UsdFbxAbstractData::QueryTimeSample( const SdfPath& path, double time, SdfAbstractDataValue* value ) const
{
	if( !m_reader )
	{
		return false;
	}

	if( value )
	{
		VtValue val;
		if( m_reader->Has( path, path.GetNameToken(), &val, UsdTimeCode( time ) ) )
		{
			return value->StoreValue( val );
		}
	}
	return m_reader->Has( path, path.GetNameToken(), nullptr, UsdTimeCode( time ) );
}

bool remedy::UsdFbxAbstractData::QueryTimeSample( const SdfPath& path, double time, VtValue* value ) const
{
	return m_reader ? m_reader->Has( path, path.GetNameToken(), value, UsdTimeCode( time ) ) : false;
}

void remedy::UsdFbxAbstractData::SetTimeSample( const SdfPath& path, double time, const VtValue& value )
{
	RAISE_UNSUPPORTED( SetTimeSample );
}

void remedy::UsdFbxAbstractData::EraseTimeSample( const SdfPath& path, double time )
{
	RAISE_UNSUPPORTED( EraseTimeSample );
}
