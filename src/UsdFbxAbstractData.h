// Copyright (C) Remedy Entertainment Plc.
#pragma once

#include <pxr/base/tf/declarePtrs.h>
#include <pxr/usd/sdf/data.h>
#include <pxr/usd/sdf/fileFormat.h>

PXR_NAMESPACE_USING_DIRECTIVE

namespace remedy
{
	TF_DECLARE_WEAK_AND_REF_PTRS( UsdFbxAbstractData );

	/// \class UsdFbxAbstractData
	///
	/// Provides an SdfAbstractData interface to Fbx data.
	///
	class UsdFbxAbstractData : public SdfAbstractData
	{
	public:
		static UsdFbxAbstractDataRefPtr New( SdfFileFormat::FileFormatArguments = {} );

		bool Open( const std::string& filePath );

		void Close();

		bool StreamsData() const override;
		void CreateSpec( const SdfPath&, SdfSpecType specType ) override;
		bool HasSpec( const SdfPath& ) const override;
		void EraseSpec( const SdfPath& ) override;
		void MoveSpec( const SdfPath& oldPath, const SdfPath& newPath ) override;
		SdfSpecType GetSpecType( const SdfPath& ) const override;
		bool Has( const SdfPath&, const TfToken& fieldName, SdfAbstractDataValue* value ) const override;
		bool Has( const SdfPath&, const TfToken& fieldName, VtValue* value = nullptr ) const override;

		bool HasSpecAndField( const SdfPath& path, const TfToken& fieldName, SdfAbstractDataValue* value, SdfSpecType* specType )
			const override;

		bool HasSpecAndField( const SdfPath& path, const TfToken& fieldName, VtValue* value, SdfSpecType* specType )
			const override;

		VtValue Get( const SdfPath&, const TfToken& fieldName ) const override;
		void Set( const SdfPath&, const TfToken& fieldName, const VtValue& value ) override;
		void Set( const SdfPath&, const TfToken& fieldName, const SdfAbstractDataConstValue& value ) override;
		void Erase( const SdfPath&, const TfToken& fieldName ) override;
		std::vector< TfToken > List( const SdfPath& ) const override;
		std::set< double > ListAllTimeSamples() const override;
		std::set< double > ListTimeSamplesForPath( const SdfPath& ) const override;
		bool GetBracketingTimeSamples( double time, double* tLower, double* tUpper ) const override;
		size_t GetNumTimeSamplesForPath( const SdfPath& path ) const override;
		bool GetBracketingTimeSamplesForPath( const SdfPath&, double time, double* tLower, double* tUpper ) const override;
		bool QueryTimeSample( const SdfPath&, double time, SdfAbstractDataValue* value ) const override;
		bool QueryTimeSample( const SdfPath&, double time, VtValue* value ) const override;
		void SetTimeSample( const SdfPath&, double, const VtValue& ) override;
		void EraseTimeSample( const SdfPath&, double ) override;

	protected:
		UsdFbxAbstractData( SdfFileFormat::FileFormatArguments );
		~UsdFbxAbstractData() override;

		void _VisitSpecs( SdfAbstractDataSpecVisitor* visitor ) const override;

	private:
		std::unique_ptr< class UsdFbxDataReader > m_reader;

		// Currently unused, but will be helpful in the future
		const SdfFileFormat::FileFormatArguments m_arguments;
	};
} // namespace remedy
