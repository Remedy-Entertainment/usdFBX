// Copyright (C) Remedy Entertainment Plc.

#pragma once

#include "UsdFbxDataReader.h"

#include <fbxsdk.h>
#include <pxr/usd/sdf/schema.h>
#include <pxr/usd/usd/attribute.h>
#include <pxr/usd/usd/schemaBase.h>

namespace remedy
{
	class FbxNodeReaderContext
	{
	public:
		using Prim = UsdFbxDataReader::Prim;
		using Property = UsdFbxDataReader::Property;

		FbxNodeReaderContext(
			UsdFbxDataReader& dataReader,
			FbxNode* node,
			SdfPath path,
			FbxAnimLayer* animLayer,
			FbxTimeSpan animTimeSpan,
			double scaleFactor );

		[[nodiscard]] double GetScaleFactor() const
		{
			return m_scaleFactor;
		}

		/// Returns the prim object.
		[[nodiscard]] const FbxNode* GetNode() const
		{
			return m_fbxNode;
		}

		[[nodiscard]] FbxNode* GetNode()
		{
			return m_fbxNode;
		}

		[[nodiscard]] FbxAnimLayer* GetAnimLayer()
		{
			return m_fbxAnimLayer;
		}

		[[nodiscard]] const FbxAnimLayer* GetAnimLayer() const
		{
			return m_fbxAnimLayer;
		}

		[[nodiscard]] FbxTimeSpan& GetAnimTimeSpan()
		{
			return m_fbxTimeSpan;
		}

		[[nodiscard]] const FbxTimeSpan& GetAnimTimeSpan() const
		{
			return m_fbxTimeSpan;
		}

		/// Returns the Usd path to this prim.
		[[nodiscard]] const SdfPath& GetPath() const
		{
			return m_usdPath;
		}

		[[nodiscard]] Prim& GetOrAddPrim()
		{
			if( const auto maybePrim = GetPrimAtPath( m_usdPath ) )
			{
				return *maybePrim.value();
			}
			return AddPrim( m_usdPath );
		}

		[[nodiscard]] std::optional< Prim* > GetPrimAtPath( const SdfPath& path )
		{
			return m_dataReader.GetPrim( path );
		}

		[[nodiscard]] std::optional< const Prim* > GetPrimAtPath( const SdfPath& path ) const
		{
			return m_dataReader.GetPrim( path );
		}

		[[nodiscard]] Prim& AddPrim( const SdfPath& path ) const
		{
			return m_dataReader.AddPrim( path );
		}

		[[nodiscard]] SdfPath GetRootPath() const
		{
			return m_dataReader.GetRootPath();
		}

		[[nodiscard]] UsdFbxDataReader& GetDataReader()
		{
			return m_dataReader;
		}

		[[nodiscard]] const UsdFbxDataReader& GetDataReader() const
		{
			return m_dataReader;
		}

		Property& CreateProperty(
			const SdfPath& propertyPath,
			const SdfValueTypeName& typeName,
			VtValue&& defaultValue,
			std::function< VtValue( FbxNode*, FbxTime ) >&& valueAtTimeFn,
			MetadataMap&& metadata = {},
			SdfVariability variability = SdfVariabilityVarying );

		Property& CreateProperty(
			const TfToken& propertyName,
			const SdfValueTypeName& typeName,
			VtValue&& defaultValue,
			std::function< VtValue( FbxNode*, FbxTime ) >&& valueAtTimeFn,
			MetadataMap&& metadata = {},
			SdfVariability variability = SdfVariabilityVarying );

		Property& CreateProperty(
			const SdfPath& propertyPath,
			const SdfValueTypeName& typeName,
			VtValue&& defaultValue,
			FbxProperty* fbxProperty,
			MetadataMap&& metadata = {},
			SdfVariability variability = SdfVariabilityVarying );

		Property& CreateProperty(
			const TfToken& propertyName,
			const SdfValueTypeName& typeName,
			VtValue&& defaultValue,
			FbxProperty* fbxProperty,
			MetadataMap&& metadata = {},
			SdfVariability variability = SdfVariabilityVarying );

		Property& CreateProperty(
			const SdfPath& propertyPath,
			const SdfValueTypeName& typeName,
			VtValue&& defaultValue,
			MetadataMap&& metadata = {},
			SdfVariability variability = SdfVariabilityVarying );

		Property& CreateProperty(
			const TfToken& propertyName,
			const SdfValueTypeName& typeName,
			VtValue&& defaultValue,
			MetadataMap&& metadata = {},
			SdfVariability variability = SdfVariabilityVarying );

		Property& CreateUniformProperty(
			const TfToken& propertyName,
			const SdfValueTypeName& typeName,
			VtValue&& defaultValue,
			MetadataMap&& metadata = {} );

		Property& CreateUniformProperty(
			const SdfPath& propertyPath,
			const SdfValueTypeName& typeName,
			VtValue&& defaultValue,
			MetadataMap&& metadata = {} );

		Property& CreateRelationship( const SdfPath& from, const SdfPath& to, MetadataMap&& metadata = {} );
		Property& CreateRelationship( const TfToken& from, const SdfPath& to, MetadataMap&& metadata = {} );

		Property& CreateConnection(
			const SdfPath& sourcePath,
			const TfToken& sourceAttribute,
			const SdfPath& targetPath,
			const TfToken& targetAttribute,
			const SdfValueTypeName& typeName,
			MetadataMap&& metadata = {} );

	private:
		[[nodiscard]] Property& createPropertyAtPath( const SdfPath& path ) const;
		[[nodiscard]] Property& createPropertyAtPath( const TfToken& name ) const;

		UsdFbxDataReader& m_dataReader;
		FbxNode* m_fbxNode;
		SdfPath m_usdPath;
		FbxAnimLayer* m_fbxAnimLayer;
		FbxTimeSpan m_fbxTimeSpan;
		double m_scaleFactor;
	};

	using NodeReaderFn = std::function< void( FbxNodeReaderContext& ) >;

	class FbxNodeReaders
	{
	public:
		FbxNodeReaders();

		[[nodiscard]] const std::vector< NodeReaderFn >& Get( FbxNodeAttribute::EType attributeType ) const
		{
			const auto it = m_nodeTypeReaderMap.find( attributeType );
			if( it == m_nodeTypeReaderMap.end() )
			{
				TF_WARN( "Unable to find a reader for Fbx Node type %s", FBX_STRINGIFY( attributeType ) );
				return m_nodeTypeReaderMap.at( FbxNodeAttribute::eUnknown ).Get();
			}

			return it->second.Get();
		}

	private:
		// Wrapper struct around a std::vector so we can use the
		// .AddReader().AddReader()... pattern
		struct FbxNodeReaderFnContainer
		{
			FbxNodeReaderFnContainer& AddReader( const NodeReaderFn& readerFn )
			{
				functions.push_back( readerFn );
				return *this;
			}

			[[nodiscard]] const std::vector< NodeReaderFn >& Get() const
			{
				return functions;
			}

		private:
			std::vector< NodeReaderFn > functions;
		};

		std::map< FbxNodeAttribute::EType, FbxNodeReaderFnContainer > m_nodeTypeReaderMap;
	};
} // namespace remedy
