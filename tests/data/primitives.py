from typing import List

import FbxCommon as fbx
from . import (
    AnimationCurve,
    Joint,
    Camera,
    Mesh,
    TransformableNode,
    Transform,
    Property,
    LambertMaterial,
    PhongMaterial,
)


def apply_transform(node, transform: Transform):
    node.LclTranslation.Set(fbx.FbxDouble3(*transform.t))
    node.LclRotation.Set(fbx.FbxDouble3(*transform.r))
    node.LclScaling.Set(fbx.FbxDouble3(*transform.s))
    node.SetRotationOrder(fbx.FbxNode.EPivotSet.eSourcePivot, transform.ro)


def create_animation_curve(scene, fbx_prop, anim_curve: AnimationCurve):
    anim_stack = scene.GetCurrentAnimationStack()
    anim_layer = anim_stack.FindMember(fbx.FbxAnimLayer.ClassId, anim_curve.anim_layer)
    assert anim_layer is not None
    curve_node = fbx_prop.CreateCurveNode(anim_layer)
    assert curve_node is not None
    property_type = fbx_prop.GetPropertyDataType().GetType()
    for time, value in zip(anim_curve.times, anim_curve.values):
        if property_type in [fbx.EFbxType.eFbxDouble3, fbx.EFbxType.eFbxDouble4]:
            axis = ["X", "Y", "Z", "W"]
            for i in range(0, len([*value])):
                curve = fbx_prop.GetCurve(anim_layer, axis[i], True)
                curve.KeyModifyBegin()
                curve.KeySetValue(curve.KeyAdd(time)[0], value[i])
                curve.KeyModifyEnd()
        else:
            curve = fbx_prop.GetCurve(anim_layer, True)
            curve.KeyModifyBegin()
            curve.KeySetValue(curve.KeyAdd(time)[0], value)
            curve.KeyModifyEnd()


def set_or_create_properties(node, properties: List[Property], scene: fbx.FbxScene):
    for property in properties:
        fbx_prop = None
        try:
            fbx_prop = getattr(node, property.name)
        except AttributeError as e:
            if not property.user_defined:
                raise

        if fbx_prop is None:
            assert (
                property.data_name_and_type is not None
            ), "When defining a user property, you _must_ define it's internal name and type!"
            data_type = fbx.FbxDataType.Create(*property.data_name_and_type)
            fbx_prop = fbx.FbxProperty.Create(
                node, data_type, property.name, property.name
            )
        fbx_prop.Set(property.value)
        if property.user_defined:
            fbx_prop.ModifyFlag(fbx.FbxPropertyFlags.EFlags.eUserDefined, True)
        if property.animation_curves:
            fbx_prop.ModifyFlag(fbx.FbxPropertyFlags.EFlags.eAnimatable, True)
        for anim_curve in property.animation_curves:
            create_animation_curve(scene, fbx_prop, anim_curve)


def validate_coordinate_mapping(
    attr_name, mapping_mode, reference_mode, point_map, points
):
    # Do some pre-validation before setting the index array
    if mapping_mode == fbx.FbxLayerElement.EMappingMode.eByControlPoint:
        assert len(point_map) == len(
            points
        ), f"When using eByControlPoint, the `{attr_name}` array corresponds to each vertex, so it must be the same length as `points`"
        if (
            reference_mode != fbx.FbxLayerElement.EReferenceMode.eDirect
        ):  # eIndex and eIndexToDirect
            assert point_map, "`point_mapping` must be set!"


def write_layer_element(layer_element, layer_data, reference_mode, point_mapping):
    if layer_data:
        direct_array = layer_element.GetDirectArray()
        [direct_array.Add(n) for n in layer_data]
    if reference_mode != fbx.FbxLayerElement.EReferenceMode.eDirect:
        index_array = layer_element.GetIndexArray()
        [index_array.Add(idx) for idx in point_mapping]


def create_mesh(manager: fbx.FbxManager, mesh: Mesh):
    if mesh.mapping_mode not in [
        fbx.FbxLayerElement.EMappingMode.eByControlPoint,
        fbx.FbxLayerElement.EMappingMode.eByPolygonVertex,
    ]:
        raise ValueError(
            f"Unsupported mapping mode: `{mesh.mapping_mode}` for mesh `{mesh.name}`"
        )

    fbx_node = fbx.FbxNode.Create(manager, mesh.name)
    fbx_mesh = fbx.FbxMesh.Create(manager, "")
    fbx_node.SetNodeAttribute(fbx_mesh)

    # Points
    control_points = [fbx.FbxVector4(*cp) for cp in mesh.points]
    fbx_mesh.InitControlPoints(len(control_points))
    [fbx_mesh.SetControlPointAt(cp, i) for i, cp in enumerate(control_points)]

    # Polygons
    for polygon in mesh.polygons:
        fbx_mesh.BeginPolygon(-1, -1, -1, False)  # (material, texture, group, legacy)
        for vertex in polygon:
            fbx_mesh.AddPolygon(vertex)
        fbx_mesh.EndPolygon()

    # Normals
    if mesh.normals is not None:
        validate_coordinate_mapping(
            "normal.vertex_colors",
            mesh.mapping_mode,
            mesh.reference_mode,
            mesh.normals.point_mapping,
            mesh.points,
        )
        geometry_normal_element = fbx_mesh.CreateElementNormal()
        geometry_normal_element.SetMappingMode(mesh.mapping_mode)
        geometry_normal_element.SetReferenceMode(mesh.reference_mode)

        normals = [fbx.FbxVector4(*n) for n in mesh.normals.coordinates]
        write_layer_element(
            geometry_normal_element,
            normals,
            mesh.reference_mode,
            mesh.normals.point_mapping,
        )
    # UVs
    for uv_set in mesh.uvs:
        validate_coordinate_mapping(
            f"uvs[{uv_set.name}].point_mapping",
            mesh.mapping_mode,
            mesh.reference_mode,
            uv_set.point_mapping,
            mesh.points,
        )
        uv_element = fbx_mesh.CreateElementUV(uv_set.name)
        # unlike normals, we _have_ to use eByPolygonVertex and eIndexToDirect with UVs.
        # Seemingly, UV layer elements do not recorded into the FBX otherwise, which is bizarre.
        # Alternatively, we keep the mapping and reference mode the same and author and check
        # for warnings from the USD plugin.
        uv_element.SetMappingMode(fbx.FbxLayerElement.EMappingMode.eByPolygonVertex)
        uv_element.SetReferenceMode(fbx.FbxLayerElement.EReferenceMode.eIndexToDirect)

        uvs = [fbx.FbxVector2(*uv) for uv in uv_set.coordinates]
        write_layer_element(
            uv_element,
            uvs,
            mesh.reference_mode,
            uv_set.point_mapping,
        )

    # Materials
    material_element = fbx_mesh.CreateElementMaterial()
    material_element.SetMappingMode(fbx.FbxLayerElement.EMappingMode.eByPolygon)
    material_element.SetReferenceMode(fbx.FbxLayerElement.EReferenceMode.eIndexToDirect)
    material_type_map = {
        LambertMaterial: fbx.FbxSurfaceLambert,
        PhongMaterial: fbx.FbxSurfacePhong,
    }
    material_mapping = [face for _, faces in mesh.materials for face in faces]
    for material, _ in mesh.materials:
        fbx_material = material_type_map[type(material)].Create(manager, material.name)

        fbx_material.Diffuse.Set(fbx.FbxDouble3(*material.diffuse))
        fbx_material.Emissive.Set(fbx.FbxDouble3(*material.emissive))
        fbx_material.Ambient.Set(fbx.FbxDouble3(*material.ambient))
        fbx_material.TransparentColor.Set(fbx.FbxDouble3(*material.transparency))
        fbx_material.TransparencyFactor.Set(material.transparency_factor)

        if type(material) is PhongMaterial:
            fbx_material.Shininess.Set(material.shininess)
            fbx_material.Reflection.Set(fbx.FbxDouble3(*material.reflection))
            fbx_material.ReflectionFactor.Set(material.reflection_factor)
            fbx_material.Specular.Set(fbx.FbxDouble3(*material.specular))
            fbx_material.SpecularFactor.Set(material.specular_factor)

        for texture in material.textures:
            fbx_texture = fbx.FbxFileTexture.Create(manager, "")
            fbx_texture.SetFileName(str(texture.path))
            fbx_texture.SetName(texture.name)
            fbx_texture.SetTextureUse(fbx.FbxTexture.ETextureUse.eStandard)
            fbx_texture.SetMappingType(fbx.FbxTexture.EMappingType.eUV)
            fbx_texture.SetMaterialUse(fbx.FbxFileTexture.EMaterialUse.eModelMaterial)
            fbx_texture.SetSwapUV(False)
            fbx_texture.SetAlphaSource(fbx.FbxTexture.EAlphaSource.eNone)
            fbx_texture.SetTranslation(0.0, 0.0)
            fbx_texture.SetScale(1.0, 1.0)
            fbx_texture.SetRotation(0.0, 0.0)
            fbx_texture.UVSet.Set(texture.uv_set)
            getattr(fbx_material, texture.channel).ConnectSrcObject(fbx_texture)

        fbx_node.AddMaterial(fbx_material)

    write_layer_element(
        material_element,
        [],  # Direct Array for material elements aren't used anymore
        fbx.FbxLayerElement.EReferenceMode.eIndexToDirect,
        material_mapping,
    )

    # Vertex Colors, always writing one color per vertex.
    for color_set in mesh.vertex_colors:
        validate_coordinate_mapping(
            f"vertex_colors[{color_set.name}].point_mapping",
            mesh.mapping_mode,
            mesh.reference_mode,
            color_set.point_mapping,
            mesh.points,
        )
        color_element = fbx_mesh.CreateElementVertexColor()
        color_element.SetName(color_set.name)
        color_element.SetMappingMode(fbx.FbxLayerElement.EMappingMode.eByPolygonVertex)
        color_element.SetReferenceMode(
            fbx.FbxLayerElement.EReferenceMode.eIndexToDirect
        )
        colors = [fbx.FbxColor(*c) for c in color_set.coordinates]
        write_layer_element(
            color_element,
            colors,
            mesh.reference_mode,
            color_set.point_mapping,
        )
    return fbx_node, fbx_mesh


def create_null(manager: fbx.FbxManager, null: TransformableNode):
    fbx_node = fbx.FbxNode.Create(manager, null.name)
    fbx_null = fbx.FbxNull.Create(manager, "")
    fbx_node.SetNodeAttribute(fbx_null)
    return fbx_node, fbx_null


def create_joint(manager: fbx.FbxManager, joint: Joint):
    fbx_node = fbx.FbxNode.Create(manager, joint.name)
    fbx_joint = fbx.FbxSkeleton.Create(manager, joint.name)
    fbx_joint.SetSkeletonType(fbx.FbxSkeleton.EType.eLimbNode)
    fbx_joint.Size.Set(joint.size)
    fbx_node.SetNodeAttribute(fbx_joint)
    return fbx_node, fbx_joint


def create_camera(manager: fbx.FbxManager, camera: Camera):
    fbx_node = fbx.FbxNode.Create(manager, camera.name)
    fbx_cam = fbx.FbxCamera.Create(manager, "")
    fbx_node.SetNodeAttribute(fbx_cam)

    fbx_cam.SetFormat(camera.camera_format)
    fbx_cam.SetApertureFormat(camera.aperture_format)
    fbx_cam.SetApertureMode(camera.aperture_mode)
    fbx_cam.FieldOfView.Set(camera.fov)
    fbx_cam.FocalLength.Set(camera.focal_length)
    fbx_cam.NearPlane.Set(camera.clipping_range[0])
    fbx_cam.FarPlane.Set(camera.clipping_range[1])
    fbx_cam.FocusDistance.Set(camera.focus_distance)
    # This got broken in 2020.3.4... SIGH
    # fbx_cam.SetProjectionType.Set(camera.projection)

    if camera.aperture_format == fbx.FbxCamera.EApertureFormat.eCustomAperture:
        fbx_cam.SetApertureWidth(camera.aperture_width)
        fbx_cam.SetApertureHeight(camera.aperture_height)
        fbx_cam.FilmSqueezeRatio.Set(camera.squeeze_ratio)
    return fbx_node, fbx_cam
