import FbxCommon as fbx
from dataclasses import dataclass, field, fields
from typing import Any, List, Tuple, Dict, Union
from enum import Enum
import pathlib
from pxr import UsdGeom

Vec3_t = Tuple[float, float, float]
Vec4_t = Tuple[float, float, float, float]


def export_fbx(filename, scene, manager, file_format_name, compat_version="FBX201600"):
    if not filename:
        raise ValueError("No filename was specified, unable to export Fbx")
    exporter = fbx.FbxExporter.Create(manager, "")
    file_format = manager.GetIOPluginRegistry().FindWriterIDByDescription(
        file_format_name
    )

    if not manager.GetIOSettings():
        ios = fbx.FbxIOSettings.Create(manager, fbx.IOSROOT)
        manager.SetIOSettings(ios)

    manager.GetIOSettings().SetBoolProp(fbx.EXP_FBX_MATERIAL, True)
    manager.GetIOSettings().SetBoolProp(fbx.EXP_FBX_TEXTURE, True)
    manager.GetIOSettings().SetBoolProp(fbx.EXP_FBX_EMBEDDED, False)
    manager.GetIOSettings().SetBoolProp(fbx.EXP_FBX_SHAPE, True)
    manager.GetIOSettings().SetBoolProp(fbx.EXP_FBX_GOBO, True)
    manager.GetIOSettings().SetBoolProp(fbx.EXP_FBX_ANIMATION, True)
    manager.GetIOSettings().SetBoolProp(fbx.EXP_FBX_GLOBAL_SETTINGS, True)

    result = exporter.Initialize(
        str(filename.resolve()), file_format, manager.GetIOSettings()
    )
    if not result:
        exporter.Destroy()
        return result

    assert exporter.SetFileExportVersion(
        compat_version, fbx.FbxSceneRenamer.ERenamingMode.eNone
    )  # value fetched from `#define FBX_2016_00_COMPATIBLE` in fbxio.h

    success = exporter.Export(scene)
    exporter.Destroy()

    return success


class DataclassFactory:
    cache = {}

    @classmethod
    def from_dict(cls, class_to_create: type, class_data: Dict):
        if class_to_create not in cls.cache:
            cls.cache[class_to_create] = {
                f.name for f in fields(class_to_create) if f.init
            }

        field_set = cls.cache[class_to_create]
        filtered_args = {k: v for k, v in class_data.items() if k in field_set}
        return class_to_create(**filtered_args)


class Axis(Enum):
    X = 0
    Y = 1
    Z = 2


@dataclass
class Settings:
    file_path: pathlib.Path = ""
    file_format: str = "FBX binary (*.fbx)"
    compatibility: str = "FBX202000"
    axis: fbx.FbxAxisSystem = fbx.FbxAxisSystem.MayaYUp
    original_axis: fbx.FbxAxisSystem = None
    units: fbx.FbxSystemUnit = fbx.FbxSystemUnit.cm
    anim_layers: Tuple[str, ...] = ()


@dataclass
class Transform:
    t: Vec3_t = (0.0, 0.0, 0.0)
    r: Vec3_t = (0.0, 0.0, 0.0)
    s: Vec3_t = (1.0, 1.0, 1.0)
    ro: fbx.EFbxRotationOrder = fbx.EFbxRotationOrder.eEulerXYZ

    def __hash__(self):
        return hash(self.t + self.r + self.s) + hash(self.ro)


@dataclass
class AnimationCurve:
    name: str = ""
    anim_layer: str = ""
    times: List[fbx.FbxTime] = field(default_factory=list)
    values: List[Union[float, Vec3_t, Vec4_t]] = field(default_factory=list)


# Dataclass representing generic property setting/animating
@dataclass
class Property:
    name: str
    value: Any = None
    user_defined: bool = False
    data_name_and_type: Tuple[
        str, fbx.EFbxType
    ] = None  # only used in conjunction with user_defined
    animation_curves: List[AnimationCurve] = field(default_factory=list)


@dataclass
class Node:
    name: str = ""
    parent: "Node" = None  # In the future typing.Self could be used
    properties: List[Property] = field(default_factory=list)


@dataclass
class TransformableNode(Node):
    transform: Transform = Transform()

    def __hash__(self):
        return hash(self.name) + hash(self.transform)


@dataclass
class Joint(TransformableNode):
    size: float = 1.0
    is_root: bool = False

    def __hash__(self):
        return hash(self.name) + hash(self.transform) + hash(self.size)


@dataclass
class SkinBinding:
    target_joint: Joint
    # List of (vertexId, weightValue) for the target joint
    vertex_weights: Tuple[Tuple[int, float], ...]
    link_mode: fbx.FbxCluster.ELinkMode = fbx.FbxCluster.ELinkMode.eTotalOne

    def __hash__(self) -> int:
        return (
            hash(self.target_joint) + hash(self.vertex_weights) + hash(self.link_mode)
        )


@dataclass
class MappedCoordinates(Node):
    # List of unique nD coordinates
    coordinates: List[Tuple[float, ...]] = field(default_factory=list)
    # list of indices into coordinates for each point in geometry
    # It's the data provider's responsibility to ensure that this data corresponds to the correct reference and mapping modes
    point_mapping: List[int] = field(default_factory=list)

    def __hash__(self):
        return hash(self.name) + hash(
            tuple(self.coordinates) + tuple(self.point_mapping)
        )

@dataclass
class TextureChannel():
    path: pathlib.Path = ""
    channel: str = ""
    name: str = "My Texture"
    uv_set: str = "default"

@dataclass
class LambertMaterial:
    name: str = ""
    textures: List[TextureChannel] = field(default_factory=list)
    emissive: Vec3_t = (0.0, 0.0, 0.0)
    emissive_factor: float = 0.0
    ambient: Vec3_t = (0.0, 0.0, 0.0)
    ambient_factor: float = 0.0
    diffuse: Vec3_t = (0.0, 0.0, 0.0)
    diffuse_factor: float = 1.0
    normal_map: Vec3_t = (0.0, 0.0, 0.0)
    bump: Vec3_t = (0.0, 0.0, 0.0)
    bump_factor: float = 1.0
    transparency: Vec3_t = (0.0, 0.0, 0.0)
    transparency_factor: float = 0.0
    displacement: Vec3_t = (0.0, 0.0, 0.0)
    displacement_factor: float = 0.0
    vector_displacement: Vec3_t = (0.0, 0.0, 0.0)
    vector_displacement_factor: float = 0.0
    
@dataclass
class PhongMaterial(LambertMaterial):
    specular: Vec3_t = (0.0, 0.0, 0.0)
    specular_factor: float = 0.0
    shininess: float = 0.0
    reflection: Vec3_t = (0.0, 0.0, 0.0)
    reflection_factor: float = 0.0


@dataclass
class Mesh(TransformableNode):
    # List of vec3 vertex positions
    points: List[Vec3_t] = field(default_factory=list)
    # List of varying sized tuples of vertex Ids. Each tuple indicates num vertices per polgon
    polygons: List[Tuple[int, ...]] = field(default_factory=list)
    # List of unique normal directions
    normals: MappedCoordinates = None
    uvs: List[MappedCoordinates] = field(default_factory=dict)
    vertex_colors: List[MappedCoordinates] = field(default_factory=dict)
    mapping_mode: fbx.FbxLayerElement.EMappingMode = (
        fbx.FbxLayerElement.EMappingMode.eByPolygonVertex
    )
    reference_mode: fbx.FbxLayerElement.EReferenceMode = (
        fbx.FbxLayerElement.EReferenceMode.eIndexToDirect
    )
    skinbinding: Tuple[SkinBinding, ...] = ()
    materials: List[Tuple[Union[LambertMaterial, PhongMaterial], int]] = field(default_factory=list)

    # Necessary so we can use Mesh instances as keys in dicts
    def __hash__(self):
        return (
            hash(self.name)
            + hash(self.transform)
            + hash(self.mapping_mode)
            + hash(self.reference_mode)
            + hash(tuple(self.points))
            + hash(tuple(self.polygons))
            + hash(self.normals)
            + hash(tuple(self.uvs))
            + hash(tuple(self.vertex_colors))
            + hash(self.skinbinding)
        )


@dataclass
class Camera(TransformableNode):
    camera_format: fbx.FbxCamera.EFormat = fbx.FbxCamera.EFormat.ePAL
    fov: float = 45.0
    aperture_mode: fbx.FbxCamera.EApertureMode = fbx.FbxCamera.EApertureMode.eVertical
    aperture_format: fbx.FbxCamera.EApertureFormat = (
        fbx.FbxCamera.EApertureFormat.e35mmFullAperture
    )
    focal_length: float = 50  # in mm
    focus_distance: float = 10.0
    clipping_range: Tuple[float, float] = (10, 1000)
    projection: fbx.FbxCamera.EProjectionType = (
        fbx.FbxCamera.EProjectionType.ePerspective
    )
    role: str = "mono"  # "mono" or "stereo"
    # unused unless format is eCustomAperture
    aperture_width: float = 1.0
    aperture_height: float = 1.0
    squeeze_ratio: float = 1.0

    def __hash__(self):
        class_fields = fields(self)
        hashed = sum([hash(f) for f in class_fields])
        return super().__hash__() + hashed


@dataclass
class NodeValidationData:
    name: str
    vertex_positions: List[Vec3_t] = field(default_factory=list)
    normals: List[Vec3_t] = field(default_factory=list)
    face_vertex_counts: List[float] = field(default_factory=list)
    face_vertex_indices: List[float] = field(default_factory=list)
    uvs: Dict[str, Tuple[str, List[float]]] = field(default_factory=dict)
    vertex_colors: List[Tuple[float]] = field(default_factory=list)
    parent: int = -1  # Index to parent in the scene object list
    # Translation, Rotation Scale
    trs: Tuple[Tuple[float]] = field(
        default_factory=lambda: ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (1.0, 1.0, 1.0))
    )


@dataclass
class SceneValidationData:
    objects: List[NodeValidationData]
    up_axis = UsdGeom.Tokens.y
    meters_per_unit: int = 1
