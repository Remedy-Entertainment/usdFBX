import pytest
from pxr import Usd, UsdGeom, Vt


def basic_plane_helper(basic_plane_fbx, root_prim_name):
    mesh_file_path, _, nodes = basic_plane_fbx
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
    normals = geometry.GetNormalsAttr()
    primvarApi = UsdGeom.PrimvarsAPI(geometry)
    normals_primvar = primvarApi.GetPrimvar("normals")
    assert normals or normals_primvar
    if normals_primvar:
        assert normals_primvar.GetInterpolation() == UsdGeom.Tokens.faceVarying
    if normals:
        assert geometry.GetNormalsInterpolation() == UsdGeom.Tokens.faceVarying

    per_polygon_normals = [
        mesh.normals.coordinates[i] for i in mesh.normals.point_mapping
    ]
    assert normals.Get() == per_polygon_normals


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


def test_vertex_colors(basic_plane_fbx, root_prim_name):
    stage, mesh, geometry = basic_plane_helper(basic_plane_fbx, root_prim_name)

    display_color = geometry.GetDisplayColorPrimvar()

    assert display_color
    assert display_color.HasAuthoredValue()
    assert UsdGeom.Primvar.IsValidInterpolation(display_color.GetInterpolation())
    assert display_color.GetInterpolation() == UsdGeom.Tokens.vertex

    colors = display_color.Get(Usd.TimeCode.Default())
    # At the moment, the plugin tends to just take the last color layer in the list.
    # TODO - Post 1.0: Add additional primvars for color maps like `primvars:color:<NAME>` but warn the user that only the last or first one will be used as the active displaycolor
    color_set = mesh.vertex_colors[-1]
    assert colors == [color_set.coordinates[i] for i in color_set.point_mapping]
