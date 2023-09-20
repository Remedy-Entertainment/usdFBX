from pxr import Usd, UsdShade, Sdf, UsdGeom, Gf

import pytest
import pathlib
import copy

from data import (
    scenebuilder,
    MappedCoordinates,
    Mesh,
    LambertMaterial,
    PhongMaterial,
    TextureChannel,
)


def build_plane_with_materials(fbx_defaults, materials, points=None, polygons=None):
    output_dir, manager, scene, fbx_file_format = fbx_defaults
    texcoords = MappedCoordinates(
        name="uvset1",
        coordinates=[(0, 0), (1, 0), (1, 1), (0, 1)],
        point_mapping=[0, 3, 2, 2, 1, 0],
    )
    with scenebuilder.SceneBuilder(manager, scene, output_dir) as builder:
        builder.settings.file_format = fbx_file_format
        builder.nodes.append(
            Mesh(
                name="basic_plane",
                points=points or [(-1, 0, -1), (1, 0, -1), (1, 0, 1), (-1, 0, 1)],
                polygons=polygons or [(0, 3, 2), (2, 1, 0)],
                uvs=[texcoords],
                materials=materials,
            )
        )
    return str(builder.settings.file_path), builder.settings, builder.nodes


@pytest.fixture(scope="module")
def basic_lambert_material_plane_fbx(fbx_defaults):
    yield build_plane_with_materials(
        fbx_defaults,
        materials=[
            (
                LambertMaterial(name="test_lambert_material", diffuse=(1, 0.5, 0)),
                [0, 1],  # Face mapping
            )
        ],
    )


def test_basic_material(
    basic_lambert_material_plane_fbx, root_prim_name, mat_scope_name
):
    mesh_file_path, _, nodes = basic_lambert_material_plane_fbx
    stage = Usd.Stage.Open(mesh_file_path)

    material_path = Sdf.Path(
        f"/{root_prim_name}/{mat_scope_name}/{nodes[0].materials[0][0].name}"
    )
    material_prim = stage.GetPrimAtPath(material_path)
    assert material_prim

    mesh_prim = stage.GetPrimAtPath(f"/{root_prim_name}/{nodes[0].name}")
    assert UsdShade.MaterialBindingAPI(mesh_prim)

    material = UsdShade.Material(material_prim)
    assert material

    surface_output = material.GetSurfaceOutput()
    assert surface_output and surface_output.HasConnectedSource()
    surface_info = surface_output.GetConnectedSources()[0][0]
    surface_path = UsdShade.Utils.GetConnectedSourcePath(surface_info)
    assert surface_path == material_path.AppendChild("LambertSurface").AppendProperty(
        "outputs:surface"
    )


@pytest.fixture(scope="module")
def subset_material_fbx(fbx_defaults):
    yield build_plane_with_materials(
        fbx_defaults,
        materials=[
            (
                LambertMaterial(name="material_a", diffuse=(1, 0.5, 0)),
                [0],  # Face mapping
            ),
            (
                LambertMaterial(name="material_b", diffuse=(0, 0.5, 1)),
                [1],  # Face mapping
            ),
        ],
    )


def test_materialbind_subsets(subset_material_fbx, root_prim_name):
    mesh_file_path, _, nodes = subset_material_fbx
    stage = Usd.Stage.Open(mesh_file_path)
    mesh_prim = stage.GetPrimAtPath(f"/{root_prim_name}/{nodes[0].name}")
    mesh = UsdGeom.Mesh(mesh_prim)

    material_subsets = UsdGeom.Subset.GetGeomSubsets(
        mesh, UsdGeom.Tokens.face, "materialBind"
    )
    assert material_subsets and len(material_subsets) == len(nodes[0].materials)

    material_binding_apis = [
        UsdShade.MaterialBindingAPI.Apply(subset.GetPrim())
        for subset in material_subsets
    ]

    assert None not in [binding.GetDirectBinding() for binding in material_binding_apis]

    materials = [
        binding.GetDirectBinding().GetMaterial() for binding in material_binding_apis
    ]
    assert None not in materials

    # check assignments of materials is correct
    assert sorted([material.GetPrim().GetName() for material in materials]) == sorted(
        [material[0].name for material in nodes[0].materials]
    )

    # Check if face indices match
    indices = [list(subset.GetIndicesAttr().Get()) for subset in material_subsets]
    source_indices = [material[1] for material in nodes[0].materials]
    assert sorted(source_indices) == sorted(indices)


@pytest.fixture(scope="module")
def phong_material_fbx(fbx_defaults):
    yield build_plane_with_materials(
        fbx_defaults,
        materials=[
            (
                PhongMaterial(
                    name="Phong_material",
                    specular=(0, 0.5, 1),
                    shininess=0.4,
                    reflection_factor=0.4,
                ),
                [0, 1],
            ),
        ],
    )


def test_phong(phong_material_fbx, root_prim_name, mat_scope_name):
    mesh_file_path, _, nodes = phong_material_fbx
    stage = Usd.Stage.Open(mesh_file_path)
    shader_path = Sdf.Path(
        f"/{root_prim_name}/{mat_scope_name}/{nodes[0].materials[0][0].name}/PhongSurface"
    )
    shader = UsdShade.Shader(stage.GetPrimAtPath(shader_path))
    assert shader
    # Check phong specifics
    assert shader.GetInput("specularColor").Get() == nodes[0].materials[0][0].specular
    assert Gf.IsClose(
        shader.GetInput("roughness").Get(),
        1.0 - nodes[0].materials[0][0].shininess,
        1e-6,
    )
    assert Gf.IsClose(
        shader.GetInput("metallic").Get(),
        nodes[0].materials[0][0].reflection_factor,
        1e-6,
    )


@pytest.fixture(scope="module")
def lambert_material_fbx(fbx_defaults):
    yield build_plane_with_materials(
        fbx_defaults,
        materials=[
            (
                LambertMaterial(
                    name="lambert_material", diffuse=(1, 0.5, 0), emissive=(1, 1, 0)
                ),
                [0, 1],
            ),
        ],
    )


def test_lambert(lambert_material_fbx, root_prim_name, mat_scope_name):
    mesh_file_path, _, nodes = lambert_material_fbx
    stage = Usd.Stage.Open(mesh_file_path)
    shader_path = Sdf.Path(
        f"/{root_prim_name}/{mat_scope_name}/{nodes[0].materials[0][0].name}/LambertSurface"
    )
    shader = UsdShade.Shader(stage.GetPrimAtPath(shader_path))
    assert shader
    # Check colors
    for src, tgt in [("diffuse", "diffuseColor"), ("emissive", "emissiveColor")]:
        assert shader.GetInput(tgt).Get() == getattr(nodes[0].materials[0][0], src)


@pytest.fixture(
    scope="module",
    params=[("transparency", (0.2, 0.2, 0.2), 0.8), ("transparency_factor", 0.3, 0.7)],
)
def lambert_transparent_material_fbx(fbx_defaults, request):
    attribute, value, expected = request.param
    material = LambertMaterial(name="lambert_material")
    setattr(material, attribute, value)
    yield build_plane_with_materials(
        fbx_defaults,
        materials=[(material, [0, 1])],
    ) + (expected,)


# Note: Skipped until we can figure this out correctly
@pytest.mark.skip(reason="We seemingly cannot reliably author the Opacity FbxProperty via the FBX Python SDK")
def test_opacity(lambert_transparent_material_fbx, root_prim_name, mat_scope_name):
    mesh_file_path, _, nodes, expected = lambert_transparent_material_fbx
    stage = Usd.Stage.Open(mesh_file_path)
    shader_path = Sdf.Path(
        f"/{root_prim_name}/{mat_scope_name}/{nodes[0].materials[0][0].name}/LambertSurface"
    )
    shader = UsdShade.Shader(stage.GetPrimAtPath(shader_path))
    assert Gf.IsClose(shader.GetInput("opacity").Get(), expected, 1e-6)


@pytest.fixture(
    scope="module",
    params=[
        ("Diffuse", "diffuseColor"),
        ("Emissive", "emissiveColor"),
        ("NormalMap", "normal"),
        ("TransparentColor", "opacity"),
        ("DisplacementColor", "displacement"),
        ("Specular", "specularColor"),
        ("Shininess", "roughness"),
        ("Reflection", "metallic"),
    ],
)
def simple_textured_material_fbx(fbx_defaults, request):
    channel, target = request.param
    material = PhongMaterial(name="phong_material")
    material.textures.append(
        TextureChannel(
            name=f"{channel}Texture",
            channel=channel,
            path=pathlib.Path(__file__).parent
            / "data"
            / "images"
            / "checker_pattern.png",
            uv_set="uvset1",  # Name of the single UV set created by build_plane_with_materials
        )
    )
    yield build_plane_with_materials(
        fbx_defaults,
        materials=[(material, [0, 1])],
    ) + (target,)


def test_texture_assignment(
    simple_textured_material_fbx, root_prim_name, mat_scope_name
):
    file_path, _, nodes, target_property = simple_textured_material_fbx
    stage = Usd.Stage.Open(file_path)

    material_path = Sdf.Path(
        f"/{root_prim_name}/{mat_scope_name}/{nodes[0].materials[0][0].name}"
    )
    texture_used = nodes[0].materials[0][0].textures[0]

    # 1. Assert that all the right shaders are there (preview, texture and st)
    preview_shader = UsdShade.Shader(
        stage.GetPrimAtPath(material_path.AppendChild("PhongSurface"))
    )
    assert preview_shader
    texture_shader = UsdShade.Shader(
        stage.GetPrimAtPath(
            material_path.AppendChild(
                f"{target_property}_{texture_used.channel}Texture_tex"
            )
        )
    )
    assert texture_shader
    primvar_shader = UsdShade.Shader(
        stage.GetPrimAtPath(material_path.AppendChild("primvar_st_uvset1"))
    )
    assert primvar_shader

    # 2. Assert shader properties (texture filepath and st variable name)
    texture_path = pathlib.Path(texture_shader.GetInput("file").Get().resolvedPath)
    assert texture_path == texture_used.path

    assert primvar_shader.GetInput("varname").Get() == f"st_{texture_used.uv_set}"

    # 3. Assert that the connections are right
    target_property_input = preview_shader.GetInput(target_property)
    st_input = texture_shader.GetInput("st")

    assert target_property_input.HasConnectedSource()
    assert st_input.HasConnectedSource()

    diffuse_connection_info = target_property_input.GetConnectedSources()[0][0]
    assert (
        diffuse_connection_info.source.GetPath() == texture_shader.GetPrim().GetPath()
    )

    st_connection_info = st_input.GetConnectedSources()[0][0]
    assert st_connection_info.source.GetPath() == primvar_shader.GetPrim().GetPath()


@pytest.fixture(scope="module")
def two_meshes_one_material_two_uv_sets_fbx(fbx_defaults):
    output_dir, manager, scene, fbx_file_format = fbx_defaults
    uv_set_a = MappedCoordinates(
        name="uvset1",
        coordinates=[(0, 0), (1, 0), (1, 1), (0, 1)],
        point_mapping=[0, 3, 2, 2, 1, 0],
    )
    uv_set_b = copy.deepcopy(uv_set_a)
    uv_set_b.name = "a_completely_different_name"

    material = LambertMaterial(name="material")
    material.textures.append(
        TextureChannel(
            name=f"DiffuseTexture",
            channel="Diffuse",
            path=pathlib.Path(__file__).parent
            / "data"
            / "images"
            / "checker_pattern.png",
            uv_set=uv_set_a.name,
        )
    )
    materials = [(material, [0, 1])]
    points = [(-1, 0, -1), (1, 0, -1), (1, 0, 1), (-1, 0, 1)]
    polygons = [(0, 3, 2), (2, 1, 0)]
    with scenebuilder.SceneBuilder(manager, scene, output_dir) as builder:
        builder.settings.file_format = fbx_file_format
        builder.nodes.extend(
            [
                Mesh(
                    name="basic_plane_a",
                    points=points,
                    polygons=polygons,
                    uvs=[uv_set_a],
                    materials=materials,
                ),
                Mesh(
                    name="basic_plane_b",
                    points=points,
                    polygons=polygons,
                    uvs=[uv_set_b],
                    materials=materials,
                ),
            ]
        )
    return str(builder.settings.file_path), builder.nodes


def test_unknown_uvs(
    two_meshes_one_material_two_uv_sets_fbx, capfd, root_prim_name, mat_scope_name
):
    """
    This tests the situation where one material is shared betwixt multiple geometries, but each geometry has a
    differently named UV set. FBXFileTexture instances are bound to named UVs; thus when parsing, the UVs used by
    the texture must be present on the targeted geometry. With how materials are currently generated for the USD layer,
    a second material is created with a different primvar shader. 
    
    This may get resolved in the future by using usdshade variants instead
    """
    file_path, nodes = two_meshes_one_material_two_uv_sets_fbx
    stage = Usd.Stage.Open(file_path)
    used_material = nodes[0].materials[0][0]
    err = capfd.readouterr()[1]
    assert (
        err.startswith("Warning:")
        and f'FBX Texture "{used_material.textures[0].name}" used in material "{used_material.name}" uses an unknown UV Set!'
        in err
    )
    mat_scope = stage.GetPrimAtPath(f"/{root_prim_name}/{mat_scope_name}")
    assert len(mat_scope.GetChildren()) != len(nodes[0].materials)
    material_names = [x.GetName() for x in mat_scope.GetChildren()]
    expected_material_names = [used_material.name, f"{used_material.name}__CLONE_1"]
    assert sorted(material_names) == sorted(expected_material_names)
