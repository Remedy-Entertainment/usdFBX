// Copyright (C) Remedy Entertainment Plc.
#pragma once

#include <pxr/base/tf/token.h>
#include <pxr/pxr.h>
#include <pxr/usd/sdf/abstractData.h>
#include <pxr/usd/sdf/fileFormat.h>
#include <pxr/usd/usd/timeCode.h>
#include <string>

PXR_NAMESPACE_USING_DIRECTIVE

namespace remedy
{
	using MetadataMap = std::map< TfToken, VtValue >;

	template< typename T >
	struct FbxDeleter
	{
		constexpr FbxDeleter() noexcept = default;

		template< class U, std::enable_if_t< std::is_convertible_v< U*, T* >, int > = 0 >
		FbxDeleter( const FbxDeleter< U >& ) noexcept
		{
		}

		template< class U, std::enable_if_t< std::is_convertible_v< U*, T* >, int > = 0 >
		void operator()( U* ptr ) const noexcept
		{
			if( ptr != nullptr )
			{
				ptr->Destroy();
			}
		}
	};

	template< typename T >
	using FbxPtr = std::unique_ptr< T, FbxDeleter< T > >;

	/// Shamelessly stolen from the alembic example in the Usd sources
	class UsdFbxDataReader
	{
	public:
		typedef int64_t Index;

		/// An optional ordering of name children or properties.
		using Ordering = std::optional< TfTokenVector >;

		/// Property cache.
		struct Property
		{
			bool hasConnection = false;
			SdfValueTypeName typeName = SdfValueTypeNames->Token;
			MetadataMap metadata = {};
			std::vector< std::tuple< UsdTimeCode, VtValue > > timeSamples = {};
			std::vector< SdfPath > targetPaths = {};
			SdfVariability variability = SdfVariabilityVarying;
			VtValue value;
		};

		using PropertyMap = std::map< SdfPath, Property >;

		/// Prim cache. This represents the prim specs that can be requested by Usd
		struct Prim
		{
			Prim()
				: specifier( SdfSpecifierDef )
			{
			}

			TfToken typeName;
			TfTokenVector children;
			SdfSpecifier specifier;
			Ordering primOrdering;
			Ordering propertyOrdering;
			MetadataMap metadata;
			PropertyMap propertiesCache;
			SdfPath prototype; // Path to prototype; only set on instances, currently unused
		};

		// Basic interface with UsdSdfAbstractData
		UsdFbxDataReader() = default;
		~UsdFbxDataReader() = default;

		UsdFbxDataReader( const UsdFbxDataReader& ) = delete;
		UsdFbxDataReader& operator=( const UsdFbxDataReader& ) = delete;
		UsdFbxDataReader( const UsdFbxDataReader&& other ) = delete;
		UsdFbxDataReader& operator=( const UsdFbxDataReader&& ) = delete;

		/// Open a file.  Returns \c true on success;  errors are reported by
		/// \c GetErrors().
		bool Open( const std::string& filePath, const SdfFileFormat::FileFormatArguments& );

		void Close()
		{
		}

		/// Return any errors.
		[[nodiscard]] std::string GetErrors() const;

		/// Test for the existence of a spec at \p path.
		[[nodiscard]] bool HasSpec( const SdfPath& path ) const;

		/// Returns the spec type for the spec at \p path.
		[[nodiscard]] SdfSpecType GetSpecType( const SdfPath& path ) const;
		/// Test for the existence of and optionally return the value at
		/// (\p path,\p fieldName).
		[[nodiscard]] bool Has(
			const SdfPath& path,
			const TfToken& fieldName,
			VtValue* value,
			UsdTimeCode time = UsdTimeCode::Default() ) const;

		/// Visit the specs.
		void VisitSpecs( const SdfAbstractData& owner, SdfAbstractDataSpecVisitor* visitor ) const;

		/// List the fields.
		[[nodiscard]] TfTokenVector List( const SdfPath& path ) const;

		[[nodiscard]] std::set< double > ListAllTimeSamples() const;
		[[nodiscard]] std::set< double > ListTimeSamplesForPath( const SdfPath& path ) const;

		// Prim/Property specific interface
		// ------

		Prim& AddPrim( const SdfPath& path );
		[[nodiscard]] std::optional< const Prim* > GetPrim( const SdfPath& path ) const;
		[[nodiscard]] std::optional< Prim* > GetPrim( const SdfPath& path );

		[[nodiscard]] std::optional< Property* > AddProperty( const SdfPath& path );
		[[nodiscard]] Property& AddProperty( Prim& prim, const SdfPath& path );

		[[nodiscard]] std::optional< const Property* > GetProperty( const Prim&, const SdfPath& path ) const;
		[[nodiscard]] std::optional< Property* > GetProperty( const Prim&, const SdfPath& path );
		[[nodiscard]] std::optional< const Property* > GetProperty( const SdfPath& path ) const;
		[[nodiscard]] std::optional< Property* > GetProperty( const SdfPath& path );

		[[nodiscard]] SdfPath GetRootPath() const;

	private:
		std::string m_errorLog;
		using PrimMap = std::map< SdfPath, Prim >;
		PrimMap m_prims;
		Prim* m_pseudoRoot = nullptr;
	};
} // namespace remedy
