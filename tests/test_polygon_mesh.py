import pytest
from pxr import Usd, UsdGeom, Vt

from dataclasses import dataclass
from typing import Tuple
import string

from data import scenebuilder, MappedCoordinates, Mesh


def basic_plane_helper(basic_plane_fbx, root_prim_name):
    mesh_file_path, _, nodes = basic_plane_fbx[:3]
    stage = Usd.Stage.Open(mesh_file_path)
    mesh = nodes[0]
    mesh_path = f"/{root_prim_name}/{mesh.name}"
    assert stage.GetPrimAtPath(mesh_path)
    geometry = UsdGeom.Mesh.Get(stage, mesh_path)
    return stage, mesh, geometry


def test_points(basic_plane_fbx, root_prim_name):
    stage, mesh, geometry = basic_plane_helper(basic_plane_fbx, root_prim_name)

    points_attr = geometry.GetPointsAttr().Get()
    assert points_attr == mesh.points
    face_vertex_counts = geometry.GetFaceVertexCountsAttr().Get()
    assert face_vertex_counts == [len(polygon) for polygon in mesh.polygons]

    face_vertex_indices = geometry.GetFaceVertexIndicesAttr().Get()
    assert face_vertex_indices == [idx for polygon in mesh.polygons for idx in polygon]

    valid, why = UsdGeom.Mesh.ValidateTopology(
        Vt.IntArray(face_vertex_indices),
        Vt.IntArray(face_vertex_counts),
        len(points_attr),
    )
    assert valid
    assert not why


def test_subdivision_scheme(basic_plane_fbx, root_prim_name):
    stage, mesh, geometry = basic_plane_helper(basic_plane_fbx, root_prim_name)
    # For polygonal geometry, subdiv scheme has to be `none`
    assert geometry.GetSubdivisionSchemeAttr().Get() == "none"


def test_normals(basic_plane_fbx, root_prim_name):
    stage, mesh, geometry = basic_plane_helper(basic_plane_fbx, root_prim_name)
    # Normals should only be defined on polygonal meshes
    # Ie. subdivisionSchema should be "none"
    # We do not need to test for that value here as in the scope
    # of this test suite, it is already tested separately for the `simple_polygon_mesh` fixture

    primvarApi = UsdGeom.PrimvarsAPI(geometry)
    normals_primvar = primvarApi.GetPrimvar(UsdGeom.Tokens.normals)
    assert normals_primvar.GetInterpolation() == UsdGeom.Tokens.faceVarying

    per_polygon_normals = [
        mesh.normals.coordinates[i] for i in mesh.normals.point_mapping
    ]
    assert normals_primvar.Get() == per_polygon_normals


def test_texcoords(basic_plane_fbx, root_prim_name):
    stage, mesh, geometry = basic_plane_helper(basic_plane_fbx, root_prim_name)
    primvarApi = UsdGeom.PrimvarsAPI(geometry)
    texcoord_primvars = [
        primvar
        for primvar in primvarApi.GetPrimvars()
        if primvar.GetBaseName().startswith("st")
    ]
    assert texcoord_primvars
    assert len(texcoord_primvars) == len(mesh.uvs)
    uv_names = [uv.name for uv in mesh.uvs]
    assert sorted(
        [x.GetBaseName().partition("_")[2] for x in texcoord_primvars]
    ) == sorted(uv_names)

    for primvar in texcoord_primvars:
        assert primvar.HasAuthoredValue()
        assert UsdGeom.Primvar.IsValidPrimvarName(primvar.GetName())
        assert UsdGeom.Primvar.IsValidInterpolation(primvar.GetInterpolation())
        # Generally speaking we should be able to cover all types of FBX vertex mapping in our plugin
        assert primvar.GetInterpolation() == UsdGeom.Tokens.faceVarying

        set_name = primvar.GetBaseName().partition("_")[2]
        value = primvar.Get(Usd.TimeCode.Default())
        uv_set = [uv for uv in mesh.uvs if uv.name == set_name][0]
        per_polygon_uvs = [uv_set.coordinates[i] for i in uv_set.point_mapping]
        assert value == per_polygon_uvs


@dataclass
class VertexColorData:
    input_name: str = ""
    expected_name: str = "displayColor"
    color: Tuple[int] = (1, 0, 0)


@pytest.fixture(
    params=[
        [VertexColorData(input_name="a", color=(1, 0, 0))],
        [
            VertexColorData(input_name="a", color=(1, 0, 0)),
            VertexColorData(
                input_name="b", color=(0, 0, 1), expected_name="displayColor_b"
            ),
        ],
        [
            VertexColorData(
                input_name="b",
                color=(0, 0, 1),
            ),
            VertexColorData(
                input_name="a", color=(1, 0, 0), expected_name="displayColor_a"
            ),
        ],
    ]
    + [
        [
            VertexColorData(),
            VertexColorData(input_name=f"a{c}b", expected_name="displayColor_a_b"),
        ]
        for c in string.punctuation + string.whitespace
    ],
)
def vertex_colors_plane_fbx(fbx_defaults, request):
    color_sets = request.param
    output_dir, manager, scene, fbx_file_format = fbx_defaults
    vertex_colors = [
        MappedCoordinates(
            name=color_data.input_name,
            coordinates=[color_data.color],
            point_mapping=[0] * 4,
        )
        for color_data in color_sets
    ]
    with scenebuilder.SceneBuilder(manager, scene, output_dir) as builder:
        builder.settings.file_format = fbx_file_format
        mesh = Mesh(
            name="basic_plane",
            points=[(-1, 0, -1), (1, 0, -1), (1, 0, 1), (-1, 0, 1)],
            normals=MappedCoordinates(coordinates=[(0, 1, 0)], point_mapping=[0] * 6),
            polygons=[(0, 3, 2), (2, 1, 0)],
            vertex_colors=vertex_colors,
        )
        builder.nodes.append(mesh)

    yield str(builder.settings.file_path), builder.settings, builder.nodes, color_sets


def test_vertex_colors(vertex_colors_plane_fbx, root_prim_name):
    stage, mesh, geometry = basic_plane_helper(vertex_colors_plane_fbx, root_prim_name)
    input_sets = vertex_colors_plane_fbx[-1]
    primvarApi = UsdGeom.PrimvarsAPI(geometry)
    for layer_index, input_set in enumerate(input_sets):
        display_color = primvarApi.GetPrimvar(input_set.expected_name)
        assert display_color
        assert UsdGeom.Primvar.IsValidInterpolation(display_color.GetInterpolation())
        assert display_color.HasAuthoredValue()
        assert display_color.GetInterpolation() == UsdGeom.Tokens.vertex

        # At the moment, the plugin tends to just take the last color layer in the list.
        # TODO - Post 1.0: Add additional primvars for color maps like `primvars:color:<NAME>` but warn the user that only the last or first one will be used as the active displaycolor
        print(mesh.vertex_colors[layer_index], layer_index)
        color_set = mesh.vertex_colors[layer_index]
        # assert colors == [color_set.coordinates for i in color_set.point_mapping]
