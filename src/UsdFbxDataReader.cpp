// Copyright (C) Remedy Entertainment Plc.

#include "UsdFbxDataReader.h"

#include "DebugCodes.h"
#include "Error.h"
#include "FbxNodeReader.h"
#include "Helpers.h"
#include "PrecompiledHeader.h"
#include "Tokens.h"

#include <fbxsdk.h>
#include <fbxsdk/core/fbxsystemunit.h>
#include <filesystem>
#include <pxr/base/trace/trace.h>
#include <pxr/usd/kind/registry.h>
#include <pxr/usd/sdf/schema.h>
#include <pxr/usd/usd/tokens.h>
#include <pxr/usd/usdGeom/metrics.h>
#include <pxr/usd/usdGeom/tokens.h>
#include <shared_mutex>

PXR_NAMESPACE_USING_DIRECTIVE

std::mutex mutex;
using namespace std::chrono_literals;

namespace
{
	class FbxGlobals
	{
	public:
		static FbxGlobals& getInstance()
		{
			static FbxGlobals instance;
			return instance;
		}

		FbxManager* getManager() const
		{
			return m_fbxManager.get();
		}

	private:
		FbxGlobals()
		{
			m_fbxManager.reset( FbxManager::Create() );
		}

		remedy::FbxPtr< FbxManager > m_fbxManager;

	public:
		FbxGlobals( const FbxGlobals& ) = delete;
		void operator=( const FbxGlobals& ) = delete;
	};

	std::tuple< FbxManager*, remedy::FbxPtr< FbxScene > > importFbxScene( const std::string& filePath )
	{
		auto fbxSdkManager = FbxGlobals::getInstance().getManager();
		const auto pIOSettings = remedy::FbxPtr< FbxIOSettings >( FbxIOSettings::Create( fbxSdkManager, IOSROOT ) );
		auto scene = remedy::FbxPtr< FbxScene >( FbxScene::Create( fbxSdkManager, filePath.c_str() ) );
		auto importer = remedy::FbxPtr< FbxImporter >( FbxImporter::Create( fbxSdkManager, "" ) );

		pIOSettings->SetBoolProp( IMP_FBX_MATERIAL, true );
		pIOSettings->SetBoolProp( IMP_FBX_TEXTURE, true );
		pIOSettings->SetBoolProp( IMP_FBX_LINK, true );
		pIOSettings->SetBoolProp( IMP_FBX_SHAPE, true );
		pIOSettings->SetBoolProp( IMP_FBX_GOBO, true );
		pIOSettings->SetBoolProp( IMP_FBX_ANIMATION, true );
		pIOSettings->SetBoolProp( IMP_FBX_GLOBAL_SETTINGS, true );
		fbxSdkManager->SetIOSettings( pIOSettings.get() );

		TF_DEBUG( USDFBX ).Msg( "UsdFbx - Opening \"%s\"\n", filePath.c_str() );

		int sdkMajor, sdkMinor, sdkRevision;
		FbxManager::GetFileFormatVersion( sdkMajor, sdkMinor, sdkRevision );
		TF_DEBUG( USDFBX ).Msg( "UsdFbx - Fbx version (%d.%d.%d)\n", sdkMajor, sdkMinor, sdkRevision );

		const bool bImportStatus = importer->Initialize( filePath.c_str() );
		if( !bImportStatus )
		{
			TF_ERROR( UsdFbxError::FBX_UNABLE_TO_OPEN, "[x] FBX import failed! Unable to initialize FbxImporter\n" );
			return { nullptr, nullptr };
		}

		int fileMajor, fileMinor, fileRevision;
		importer->GetFileVersion( fileMajor, fileMinor, fileRevision );
		TF_DEBUG( USDFBX ).Msg( "UsdFbx - File FBX version (%i.%i.%i)\n", fileMajor, fileMinor, fileRevision );

		if( fileMajor > sdkMajor || ( fileMajor >= sdkMajor && fileMinor > sdkMinor ) )
		{
			TF_ERROR(
				UsdFbxError::FBX_INCOMPATIBLE_VERSIONS,
				"[x] FBX import failed! file version (%d.%d.%d) is newer than SDK "
				"version (%d.%d.%d)\n",
				fileMajor,
				fileMinor,
				fileRevision,
				sdkMajor,
				sdkMinor,
				sdkRevision );
			return { nullptr, nullptr };
		}

		const bool success = importer->Import( scene.get() );
		if( !success )
		{
			TF_ERROR( UsdFbxError::FBX_UNABLE_TO_OPEN, "[x] FBX import failed!\n" );

			return { nullptr, nullptr };
		}
		return { fbxSdkManager, std::move( scene ) };
	}

	bool getPropertyValue( const remedy::UsdFbxDataReader::Property* property, VtValue* value )
	{
		TRACE_FUNCTION()

		// See if only checking for existence.
		if( value == nullptr )
		{
			return true;
		}

		if( property->value.IsEmpty() )
		{
			return false;
		}

		*value = property->value;
		return true;
	}

	bool getPropertyFieldValue(
		const remedy::UsdFbxDataReader::Property* prop,
		const TfToken& fieldName,
		VtValue* value,
		UsdTimeCode timeCode )
	{
		VtValue val;

		// If we're not dealing with the default time code, we need to fetch the value
		// of this property at that time
		if( !timeCode.IsDefault() )
		{
			const auto it = std::find_if(
				prop->timeSamples.cbegin(),
				prop->timeSamples.cend(),
				[ & ]( const auto& tup ) { return std::get< 0 >( tup ) == timeCode; } );
			if( it == prop->timeSamples.cend() )
			{
				return false;
			}
			val = std::get< 1 >( *it );
		}

		if( fieldName == SdfFieldKeys->Default )
		{
			return getPropertyValue( prop, value );
		}

		if( fieldName == SdfFieldKeys->TypeName && prop->typeName )
		{
			val = VtValue( prop->typeName.GetAsToken() );
		}

		if( fieldName == SdfFieldKeys->Variability )
		{
			val = VtValue( prop->variability );
		}

		if( fieldName == SdfFieldKeys->TargetPaths )
		{
			SdfPathListOp res = SdfPathListOp::CreateExplicit( prop->targetPaths );
			val = VtValue( res );
		}

		if( fieldName == SdfFieldKeys->TimeSamples && !prop->timeSamples.empty() )
		{
			// Fill a map of values over all time samples.
			SdfTimeSampleMap samples;
			for( const auto& [ time, sample ] : prop->timeSamples )
			{
				samples[ time.GetValue() ] = sample;
			}
			val = VtValue( samples );
		}

		const auto j = prop->metadata.find( fieldName );
		if( j != prop->metadata.end() )
		{
			val = j->second;
		}

		if( value != nullptr && !val.IsEmpty() )
		{
			*value = val;
			return true;
		}

		if( value == nullptr && !val.IsEmpty() )
		{
			return true;
		}

		return false;
	}

	bool getPrimFieldValue(
		const remedy::UsdFbxDataReader::Prim* prim,
		bool isPseudoRoot,
		const TfToken& fieldName,
		VtValue* value )
	{
		VtValue val;
		if( fieldName == SdfChildrenKeys->PrimChildren )
		{
			if( !prim->children.empty() )
			{
				val = VtValue( prim->children );
			}
		}

		if( !isPseudoRoot )
		{
			if( fieldName == SdfFieldKeys->TypeName )
			{
				val = VtValue( prim->typeName );
			}

			if( fieldName == SdfFieldKeys->PrimOrder )
			{
				if( prim->primOrdering )
				{
					val = VtValue( *prim->primOrdering );
				}
			}
			if( fieldName == SdfFieldKeys->PropertyOrder )
			{
				if( prim->propertyOrdering )
				{
					val = VtValue( *prim->propertyOrdering );
				}
			}
			if( fieldName == SdfFieldKeys->Specifier )
			{
				val = VtValue( prim->specifier );
			}
			if( fieldName == SdfFieldKeys->TargetPaths )
			{
				if( !prim->propertiesCache.empty() )
				{
					TfTokenVector res;
					for( const auto& [ propPath, prop ] : prim->propertiesCache )
					{
						for( const auto& path : prop.targetPaths )
						{
							res.push_back( path.GetAsToken() );
						}
					}

					val = VtValue( res );
				}
			}
			else if( fieldName == SdfChildrenKeys->PropertyChildren )
			{
				TfTokenVector res;
				if( !prim->propertiesCache.empty() )
				{
					res.reserve( prim->propertiesCache.size() );
					std::transform(
						prim->propertiesCache.begin(),
						prim->propertiesCache.end(),
						std::back_inserter( res ),
						[]( const auto& kvp )
						{
							TfToken result = kvp.first.GetNameToken();
							if( kvp.first.IsTargetPath() )
							{
								result = SdfPath( kvp.first.GetParentPath().GetPrimPath() )
											 .AppendProperty( kvp.first.GetParentPath().GetNameToken() )
											 .AppendTarget( kvp.first.GetTargetPath() )
											 .GetAsToken();
							}
							return result;
						} );
				}
				val = VtValue( res );
			}
			else if( fieldName == SdfFieldKeys->References )
			{
				if( !prim->prototype.IsEmpty() )
				{
					SdfReferenceListOp refs;
					SdfReferenceVector items;
					items.push_back( SdfReference( std::string(), prim->prototype ) );
					refs.SetExplicitItems( items );
					val = VtValue( refs );
				}
			}
		}

		const auto it = prim->metadata.find( fieldName );
		if( it != prim->metadata.end() )
		{
			val = VtValue( it->second );
		}

		// If value is not null, we can fill it in if we found a value. This path
		// implies that Usd requests the actual value
		if( value != nullptr && !val.IsEmpty() )
		{
			*value = val;
			return true;
		}
		// On the other hand, if value is null but val is not empty, it implies that
		// USD is merely interested in knowing whether this exists
		if( value == nullptr && !val.IsEmpty() )
		{
			return true;
		}

		TF_DEBUG( USDFBX ).Msg( "UsdFbx - Unable to find fieldName=%s \n", fieldName.GetString().c_str() );
		return false;
	}

	std::vector< std::function< void( remedy::FbxNodeReaderContext& ) > > getFbxNodeReaders(
		FbxNodeAttribute::EType attributeType )
	{
		static remedy::FbxNodeReaders _fbxNodeReaders;
		return _fbxNodeReaders.Get( attributeType );
	}

	void collectFbxNodes(
		remedy::UsdFbxDataReader& context,
		FbxNode* node,
		const SdfPath& parentPath,
		remedy::UsdFbxDataReader::Prim& parentPrim,
		FbxAnimLayer* animLayer,
		FbxTimeSpan animTimeSpan,
		const double scaleFactor )
	{
		// We bail out when we encounter an FBXNode that has not attribute pointer
		// (very rare) but is also not covered by a reader. Usd _demands_ that any
		// prim has at least one spec, the readers give it the specs needed
		const auto* attr = node->GetNodeAttribute();
		if( attr == nullptr )
		{
			return;
		}

		const auto readers = getFbxNodeReaders( attr->GetAttributeType() );
		if( readers.empty() )
		{
			return;
		}

		// Collect children names.  By prepopulating usedNames we ensure that
		// the child with the valid name gets its name even if a child with a
		// lower index has a name that mangles to the valid name.
		std::set< std::string > usedNames;
		for( size_t i = 0, n = node->GetChildCount(); i != n; ++i )
		{
			usedNames.insert( node->GetChild( static_cast< int >( i ) )->GetName() );
		}

		const std::string name
			= remedy::cleanName( node->GetName(), " _", usedNames, remedy::FbxNameFixer(), &SdfPath::IsValidIdentifier );

		if( name.empty() )
		{
			TF_WARN( "Encountered empty FBX Node name, unable to continue" );
			return;
		}

		const SdfPath nodePath = parentPath.AppendChild( TfToken( name ) );
		remedy::FbxNodeReaderContext primContext( context, node, nodePath, animLayer, animTimeSpan, scaleFactor );
		for( const auto& reader : readers )
		{
			reader( primContext );
		}

		// Special case for dealing with skeletal data due to how Usd skeletons are
		// supposed to look. We halt here and assume the reader has created the
		// correct prims for us
		if( node->GetNodeAttribute()->GetAttributeType() == FbxNodeAttribute::eSkeleton )
		{
			return;
		}

		parentPrim.children.push_back( TfToken( name ) );
		remedy::UsdFbxDataReader::Prim& newPrim = context.AddPrim( nodePath );
		for( size_t i = 0, n = node->GetChildCount(); i != n; ++i )
		{
			FbxNode* child = node->GetChild( static_cast< int >( i ) );
			collectFbxNodes( context, child, nodePath, newPrim, animLayer, animTimeSpan, scaleFactor );
		}
	}

	void bakeAnimationLayers( FbxScene* scene, FbxAnimStack* animStack )
	{
		FbxAnimEvaluator* pEvaluator = scene->GetAnimationEvaluator();
		const double framerate = FbxTime::GetFrameRate( scene->GetGlobalSettings().GetTimeMode() );
		const FbxTimeSpan timeSpan = animStack->GetLocalTimeSpan();
		const FbxTime lclStart = timeSpan.GetStart();
		const FbxTime lclStop = timeSpan.GetStop();
		FbxTime fbxBakePeriod;
		fbxBakePeriod.SetSecondDouble( 1.0 / framerate );
		animStack->BakeLayers( pEvaluator, lclStart, lclStop, fbxBakePeriod );
	}

	void processAnimations( FbxNode* node, FbxAnimLayer* animLayer )
	{
		std::vector< FbxProperty > propertiesWithCurves;
		for( FbxProperty property = node->GetFirstProperty(); property.IsValid(); property = node->GetNextProperty( property ) )
		{
			if( property.GetCurveNode( animLayer ) == nullptr )
			{
				continue;
			}

			const EFbxType ePropertyType = property.GetPropertyDataType().GetType();

			if( ( ePropertyType == eFbxHalfFloat ) || ( ePropertyType == eFbxFloat ) || ( ePropertyType == eFbxDouble ) )
			{
				propertiesWithCurves.push_back( property );
			}
		}

		for( size_t i = 0, n = node->GetChildCount(); i != n; ++i )
		{
			FbxNode* child = node->GetChild( static_cast< int >( i ) );
			processAnimations( child, animLayer );
		}
	}

	std::string axisSystemToString( const FbxAxisSystem& axisSystem )
	{
		static const std::map< const FbxAxisSystem::EUpVector, const char > axisStringMap{
			{ FbxAxisSystem::EUpVector::eXAxis, 'X' },
			{ FbxAxisSystem::EUpVector::eYAxis, 'Y' },
			{ FbxAxisSystem::EUpVector::eZAxis, 'Z' }
		};
		static const std::map< FbxAxisSystem::ECoordSystem, const char* > coordSystemStringMap{
			{ FbxAxisSystem::ECoordSystem::eLeftHanded, "Left Handed" },
			{ FbxAxisSystem::ECoordSystem::eRightHanded, "Right Handed" }
		};
		std::vector< FbxAxisSystem::EUpVector > allAxis{ FbxAxisSystem::EUpVector::eXAxis,
														 FbxAxisSystem::EUpVector::eYAxis,
														 FbxAxisSystem::EUpVector::eZAxis };
		int upAxisSign = 0;
		const auto upAxis = axisSystem.GetUpVector( upAxisSign );
		const auto it = std::remove( allAxis.begin(), allAxis.end(), upAxis );
		allAxis.erase( it );

		int frontVectorSign = 0;
		const auto frontVector = axisSystem.GetFrontVector( frontVectorSign );
		FbxAxisSystem::EUpVector frontVectorAxisID = FbxAxisSystem::EUpVector::eZAxis;
		switch( frontVector )
		{
		case FbxAxisSystem::eParityEven:
			frontVectorAxisID = allAxis[ 0 ];
			break;
		case FbxAxisSystem::eParityOdd:
			frontVectorAxisID = allAxis[ 1 ];
			break;
		}
		return TfStringPrintf(
			"%c%c-up, %s, %c%c-front",
			upAxisSign < 0 ? '-' : '+',
			axisStringMap.at( upAxis ),
			coordSystemStringMap.at( axisSystem.GetCoorSystem() ),
			frontVectorSign < 0 ? '-' : '+',
			axisStringMap.at( frontVectorAxisID ) );
	}
} // namespace

bool remedy::UsdFbxDataReader::Open( const std::string& filePath, const SdfFileFormat::FileFormatArguments& args )
{
	TRACE_FUNCTION()
	// Warning: importFbxScene _has_ to lock to prevent multithreaded access to
	// the underlying FbxManager.
	std::lock_guard lock( mutex );

	FbxManager* fbxManager = nullptr;
	FbxPtr< FbxScene > scene = nullptr;
	std::tie( fbxManager, scene ) = importFbxScene( filePath );

	if( !scene )
	{
		TF_DEBUG( USDFBX ).Msg( "UsdFbx - Failed to import FBX scene\n" );
		return false;
	}

	const std::string fileName = std::filesystem::path( filePath ).filename().generic_string();

	// Checking and logging mismatching Axis and Units first. The scene will be
	// converted to support USD natively (Y-up/RH/0.01m per unit)
	int upAxisSign = 1;
	const auto exportedSceneUp = scene->GetGlobalSettings().GetAxisSystem().GetUpVector( upAxisSign );
	if( upAxisSign < 0 )
	{
		TF_WARN(
			"%s: Unsupported coordinate system. UpAxis sign is negative, this "
			"may yield inconsistent results!",
			fileName.c_str() );
	}
	const int originalAxis = scene->GetGlobalSettings().GetOriginalUpAxis();
	const auto authoredSceneUp = originalAxis < 0 ? exportedSceneUp : static_cast< FbxAxisSystem::EUpVector >( originalAxis + 1 );

	if( exportedSceneUp == FbxAxisSystem::EUpVector::eXAxis )
	{
		// This is technically not allowed! According to spec, upAxis can only be Y
		// or Z See UsdGeomStageSetUpAxis implementation.
		TF_WARN(
			"%s: Unsupported coordinate system. X-up is not supported by Usd "
			"specification!",
			fileName.c_str() );
	}

	if( authoredSceneUp != exportedSceneUp )
	{
		const std::map< FbxAxisSystem::EUpVector, const char* > axisStringMap{ { FbxAxisSystem::EUpVector::eXAxis, "X" },
																			   { FbxAxisSystem::EUpVector::eYAxis, "Y" },
																			   { FbxAxisSystem::EUpVector::eZAxis, "Z" } };
		TF_WARN(
			"%s: This scene was exported with %s-up but originally authored in "
			"%s-up.",
			fileName.c_str(),
			axisStringMap.find( exportedSceneUp )->second,
			axisStringMap.find( authoredSceneUp )->second );
	}

	TF_DEBUG( USDFBX ).Msg(
		"UsdFbx - Converting from %s to %s Coordinate system\n",
		axisSystemToString( scene->GetGlobalSettings().GetAxisSystem() ).c_str(),
		axisSystemToString( FbxAxisSystem::MayaYUp ).c_str() );
	FbxAxisSystem::MayaYUp.DeepConvertScene( scene.get() );

	TF_DEBUG( USDFBX ).Msg(
		"UsdFbx - Converting from %f to %f metersPerUnit\n",
		scene->GetGlobalSettings().GetSystemUnit().GetConversionFactorTo( FbxSystemUnit::m ),
		FbxSystemUnit::cm.GetConversionFactorTo( FbxSystemUnit::m ) );
	// TODO: Deprecated, this conversion factor is not needed any longer.
	const auto conversionFactorToCm = FbxSystemUnit::cm.GetConversionFactorFrom( scene->GetGlobalSettings().GetSystemUnit() );
	TF_DEBUG( USDFBX ).Msg(
		"UsdFbx - Current System Units -> %s\n",
		scene->GetGlobalSettings().GetSystemUnit().GetScaleFactorAsString( false ).Buffer() );
	TF_DEBUG( USDFBX ).Msg(
		"UsdFbx - CurrentSystemUnit GetConversionFactorTo cm -> %f\n",
		scene->GetGlobalSettings().GetSystemUnit().GetConversionFactorTo( FbxSystemUnit::cm ) );
	FbxSystemUnit::cm.ConvertScene( scene.get() );
	const auto conversionFactorToMeter = scene->GetGlobalSettings().GetSystemUnit().GetConversionFactorTo( FbxSystemUnit::m );
	TF_DEBUG( USDFBX ).Msg( "UsdFbx - new metersPerUnit: %f\n", conversionFactorToMeter );
	TF_DEBUG( USDFBX ).Msg( "UsdFbx - new Up Axis: %s\n", UsdGeomTokens->y.GetText() );

	// Fill pseudo-root in the cache.
	const SdfPath rootPath = SdfPath::AbsoluteRootPath();
	m_pseudoRoot = &AddPrim( rootPath );
	m_pseudoRoot->metadata[ SdfFieldKeys->Documentation ] = "Generated by UsdFbx";
	m_pseudoRoot->metadata[ UsdGeomTokens->upAxis ] = VtValue( UsdGeomTokens->y );
	m_pseudoRoot->metadata[ UsdGeomTokens->metersPerUnit ] = VtValue( conversionFactorToMeter );

	FbxNode* root = scene->GetRootNode();
	Prim& rootPrim = *m_pseudoRoot;
	TfToken defaultPrim;

	bool sceneHasSkeletons = false;
	for( int nodeIndex = 0; nodeIndex < scene->GetNodeCount(); ++nodeIndex )
	{
		const auto* node = scene->GetNode( nodeIndex );
		if( !node )
		{
			continue;
		}
		if( node->GetNodeAttribute() && node->GetNodeAttribute()->GetAttributeType() == FbxNodeAttribute::eSkeleton )
		{
			sceneHasSkeletons = true;
			break;
		}
	}

	const bool sceneHasAnimation = scene->GetSrcObjectCount< FbxAnimStack >() > 0;
	FbxAnimLayer* animLayer = nullptr;
	FbxTimeSpan animTimeSpan;
	if( sceneHasAnimation )
	{
		TF_DEBUG( USDFBX ).Msg( "UsdFbx - Scene has animation data, authoring layer metrics\n" );
		FbxArray< FbxString* > animStackNames;
		scene->FillAnimStackNameArray( animStackNames );
		const auto animStack = scene->FindMember< FbxAnimStack >( animStackNames[ 0 ]->Buffer() );

		// Bake and resample multiple animlayers to the base layer
		// This does not bake keys! It only merges multiple anim layers to a
		// singular one
		bakeAnimationLayers( scene.get(), animStack );
		animLayer = animStack->GetMember< FbxAnimLayer >( 0 );

		// Write out start/stop timecode for the layer
		animTimeSpan = animStack->GetLocalTimeSpan();
		const FbxTime lclStart = animTimeSpan.GetStart();
		const FbxTime lclStop = animTimeSpan.GetStop();
		m_pseudoRoot->metadata[ SdfFieldKeys->StartTimeCode ] = VtValue( lclStart.GetFrameCountPrecise( FbxTime::eDefaultMode ) );
		m_pseudoRoot->metadata[ SdfFieldKeys->EndTimeCode ] = VtValue( lclStop.GetFrameCountPrecise( FbxTime::eDefaultMode ) );
		m_pseudoRoot->metadata[ SdfFieldKeys->TimeCodesPerSecond ]
			= VtValue( FbxTime::GetFrameRate( scene->GetGlobalSettings().GetTimeMode() ) );
		// Not 100% certain this is needed. As Usd generally deals with TimeCodes,
		// not frames
		m_pseudoRoot->metadata[ SdfFieldKeys->FramesPerSecond ]
			= VtValue( FbxTime::GetFrameRate( scene->GetGlobalSettings().GetTimeMode() ) );

		TF_DEBUG( USDFBX ).Msg(
			"UsdFbx - startTimeCode: %f\n",
			m_pseudoRoot->metadata[ SdfFieldKeys->StartTimeCode ].Get< double >() );
		TF_DEBUG( USDFBX ).Msg(
			"UsdFbx - endTimeCode: %f\n",
			m_pseudoRoot->metadata[ SdfFieldKeys->EndTimeCode ].Get< double >() );
		TF_DEBUG( USDFBX ).Msg(
			"UsdFbx - timeCodesPerSecond: %f\n",
			m_pseudoRoot->metadata[ SdfFieldKeys->TimeCodesPerSecond ].Get< double >() );
		TF_DEBUG( USDFBX ).Msg(
			"UsdFbx - framesPerSecond: %f\n",
			m_pseudoRoot->metadata[ SdfFieldKeys->FramesPerSecond ].Get< double >() );
	}

	// Always create a "buffer" root sort to speak. If we're dealing with
	// FbxSkeletons in the scene we make this root also a SkeletonRoot The root is
	// always tagged as a component
	const TfToken name( "ROOT" );
	rootPrim.children.push_back( name );
	const SdfPath nodePath = rootPath.AppendChild( name );
	Prim& newPrim = AddPrim( nodePath );
	newPrim.typeName = sceneHasSkeletons ? UsdFbxPrimTypeNames->SkelRoot : UsdFbxPrimTypeNames->Scope;
	newPrim.metadata[ SdfFieldKeys->Kind ] = VtValue( KindTokens->component );
	// The owning prim _must_ have the skeletonBindingAPI applied, not doing so
	// will result in a bunch of deprecation warnings in 21.11
	if( sceneHasSkeletons )
	{
		TF_DEBUG( USDFBX ).Msg( "UsdFbx - Scene has skeletons, adding SkelBindingAPI to </%s>\n", name.GetText() );
		newPrim.metadata.emplace( UsdTokens->apiSchemas, VtValue( SdfTokenListOp::Create( { TfToken( "SkelBindingAPI" ) } ) ) );
	}

	for( int childId = 0; childId < root->GetChildCount(); ++childId )
	{
		collectFbxNodes( *this, root->GetChild( childId ), nodePath, newPrim, animLayer, animTimeSpan, conversionFactorToCm );
	}

	if( !m_pseudoRoot->children.empty() )
	{
		TF_DEBUG( USDFBX ).Msg( "UsdFbx - Default Prim: /%s\n", m_pseudoRoot->children[ 0 ].GetText() );
		m_pseudoRoot->metadata[ SdfFieldKeys->DefaultPrim ] = VtValue( m_pseudoRoot->children[ 0 ] );
	}

	return true;
}

std::string remedy::UsdFbxDataReader::GetErrors() const
{
	return m_errorLog;
}

bool remedy::UsdFbxDataReader::HasSpec( const SdfPath& path ) const
{
	if( auto prim = GetPrim( path ) )
	{
		return path.IsAbsoluteRootOrPrimPath() || GetProperty( *prim.value(), path );
	}
	return false;
}

SdfSpecType remedy::UsdFbxDataReader::GetSpecType( const SdfPath& path ) const
{
	const auto prim = GetPrim( path );
	if( !prim )
	{
		return SdfSpecTypeUnknown;
	}
	if( !path.IsAbsoluteRootOrPrimPath() )
	{
		if( const auto& prop = GetProperty( *prim.value(), path ) )
		{
			if( !prop.value()->targetPaths.empty() )
			{
				return SdfSpecTypeRelationship;
			}
			return SdfSpecTypeAttribute;
		}
	}
	return *prim == m_pseudoRoot ? SdfSpecTypePseudoRoot : SdfSpecTypePrim;
}

void remedy::UsdFbxDataReader::VisitSpecs( const SdfAbstractData& owner, SdfAbstractDataSpecVisitor* visitor ) const
{
	// Visit the pseudoroot.
	if( !visitor->VisitSpec( owner, SdfPath::AbsoluteRootPath() ) )
	{
		return;
	}

	// Visit prims in path sorted order.
	for( const auto& [ primPath, prim ] : m_prims )
	{
		if( !visitor->VisitSpec( owner, primPath ) )
		{
			return;
		}

		if( &prim != m_pseudoRoot )
		{
			for( const auto& [ propertyPath, property ] : prim.propertiesCache )
			{
				if( !visitor->VisitSpec( owner, propertyPath ) )
				{
					return;
				}
			}
		}
	}
}

bool remedy::UsdFbxDataReader::Has( const SdfPath& path, const TfToken& fieldName, VtValue* value, UsdTimeCode timeCode ) const
{
	if( auto prim = GetPrim( path ) )
	{
		if( !path.IsAbsoluteRootOrPrimPath() )
		{
			if( auto prop = GetProperty( *prim.value(), path ) )
			{
				// Only place where we should get a field at a certain time code, prim
				// fields like "propertyOrder, primChildren, etc.." do not get animated
				return getPropertyFieldValue( prop.value(), fieldName, value, timeCode );
			}
		}
		else
		{
			return getPrimFieldValue( prim.value(), prim.value() == m_pseudoRoot, fieldName, value );
		}
	}
	return false;
}

TfTokenVector remedy::UsdFbxDataReader::List( const SdfPath& path ) const
{
	TfTokenVector result;
	const auto primRes = GetPrim( path );
	if( !primRes )
	{
		return result;
	}

	const auto prim = *primRes;

	if( !path.IsAbsoluteRootOrPrimPath() )
	{
		if( const auto prop = GetProperty( *prim, path ) )
		{
			result.push_back( SdfFieldKeys->Custom );
			result.push_back( SdfFieldKeys->Variability );
			if( !( *prop )->timeSamples.empty() )
			{
				result.push_back( SdfFieldKeys->TimeSamples );
			}
			if( !( *prop )->targetPaths.empty() )
			{
				result.push_back( SdfFieldKeys->TargetPaths );
			}
			else // we don't push typename for relationships. This may change
			{
				result.push_back( SdfFieldKeys->TypeName );
			}
			// Add metadata.
			for( const auto& v : ( *prop )->metadata )
			{
				result.push_back( v.first );
			}
		}
	}
	else
	{
		if( prim != m_pseudoRoot )
		{
			if( !prim->typeName.IsEmpty() )
			{
				result.push_back( SdfFieldKeys->TypeName );
			}
			result.push_back( SdfFieldKeys->Specifier );
			if( !prim->propertiesCache.empty() )
			{
				result.push_back( SdfChildrenKeys->PropertyChildren );
			}
			if( prim->primOrdering )
			{
				result.push_back( SdfFieldKeys->PrimOrder );
			}
			if( prim->propertyOrdering )
			{
				result.push_back( SdfFieldKeys->PropertyOrder );
			}
			if( !prim->prototype.IsEmpty() )
			{
				result.push_back( SdfFieldKeys->References );
			}
		}
		if( !prim->children.empty() )
		{
			result.push_back( SdfChildrenKeys->PrimChildren );
		}
		for( const auto& v : prim->metadata )
		{
			result.push_back( v.first );
		}
	}
	return result;
}

std::set< double > remedy::UsdFbxDataReader::ListAllTimeSamples() const
{
	std::set< double > result;
	for( const auto& [ path, prim ] : m_prims )
	{
		for( const auto& [ propPath, prop ] : prim.propertiesCache )
		{
			std::transform(
				prop.timeSamples.cbegin(),
				prop.timeSamples.cend(),
				std::inserter( result, result.end() ),
				[]( const auto& data ) -> double { return std::get< 0 >( data ).GetValue(); } );
		}
	}
	return result;
}

std::set< double > remedy::UsdFbxDataReader::ListTimeSamplesForPath( const SdfPath& path ) const
{
	std::set< double > result;
	if( !path.IsPropertyPath() )
	{
		return result;
	}

	if( const auto prim = GetPrim( path ) )
	{
		if( const auto property = GetProperty( *prim.value(), path ) )
		{
			std::transform(
				( *property )->timeSamples.cbegin(),
				( *property )->timeSamples.cend(),
				std::inserter( result, result.end() ),
				[]( const auto& data ) -> double { return std::get< 0 >( data ).GetValue(); } );
		}
	}
	return result;
}

// -----
// PRIM/PROPERTY/DATA HANDLING
// -----

remedy::UsdFbxDataReader::Prim& remedy::UsdFbxDataReader::AddPrim( const SdfPath& path )
{
	const auto ptr = m_prims.emplace( path, Prim() );
	return ptr.first->second;
}

std::optional< const remedy::UsdFbxDataReader::Prim* > remedy::UsdFbxDataReader::GetPrim( const SdfPath& path ) const
{
	const auto it = m_prims.find( path.IsAbsoluteRootPath() ? path : path.GetPrimPath() );
	if( it == m_prims.end() )
	{
		return std::nullopt;
	}
	return &it->second;
}

std::optional< remedy::UsdFbxDataReader::Prim* > remedy::UsdFbxDataReader::GetPrim( const SdfPath& path )
{
	const auto it = m_prims.find( path.GetPrimPath() );
	if( it == m_prims.end() )
	{
		return std::nullopt;
	}
	return &it->second;
}

std::optional< remedy::UsdFbxDataReader::Property* > remedy::UsdFbxDataReader::AddProperty( const SdfPath& path )
{
	const auto prim = GetPrim( path );
	if( !prim )
	{
		return std::nullopt;
	}
	return &AddProperty( *prim.value(), path );
}

remedy::UsdFbxDataReader::Property& remedy::UsdFbxDataReader::AddProperty( Prim& prim, const SdfPath& path )
{
	return prim.propertiesCache.emplace( path, Property() ).first->second;
}

std::optional< const remedy::UsdFbxDataReader::Property* > remedy::UsdFbxDataReader::GetProperty( const SdfPath& path ) const
{
	const auto it = m_prims.find( path.GetPrimPath() );
	if( it != m_prims.end() )
	{
		const auto propIt = it->second.propertiesCache.find( path );
		if( propIt != it->second.propertiesCache.end() )
		{
			return &propIt->second;
		}
	}
	return std::nullopt;
}

std::optional< remedy::UsdFbxDataReader::Property* > remedy::UsdFbxDataReader::GetProperty( const SdfPath& path )
{
	const auto it = m_prims.find( path.GetPrimPath() );
	if( it == m_prims.end() )
	{
		return std::nullopt;
	}
	return GetProperty( it->second, path );
}

std::optional< const remedy::UsdFbxDataReader::Property* > remedy::UsdFbxDataReader::GetProperty(
	const Prim& prim,
	const SdfPath& path ) const
{
	const auto it = prim.propertiesCache.find( path );
	if( it != prim.propertiesCache.end() )
	{
		return &it->second;
	}
	return std::nullopt;
}

// TODO: Not sure how I feel about the const_cast here...
std::optional< remedy::UsdFbxDataReader::Property* > remedy::UsdFbxDataReader::GetProperty(
	const Prim& prim,
	const SdfPath& path )
{
	auto prop = const_cast< const UsdFbxDataReader* >( this )->GetProperty( prim, path );
	if( !prop )
	{
		return std::nullopt;
	}
	return const_cast< Property* >( prop.value() );
}

SdfPath remedy::UsdFbxDataReader::GetRootPath() const
{
	return m_pseudoRoot ? SdfPath::AbsoluteRootPath().AppendChild( m_pseudoRoot->children[ 0 ] ) : SdfPath::AbsoluteRootPath();
}
