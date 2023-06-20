from pxr import Usd, Tf, UsdGeom
import pytest
from data import TransformableNode, scenebuilder


@pytest.fixture(scope="session")
def single_null_fbx(fbx_defaults):
    output_dir, manager, scene, fbx_file_format = fbx_defaults
    with scenebuilder.SceneBuilder(manager, scene, output_dir) as builder:
        builder.settings.file_format = fbx_file_format
        builder.nodes.append(TransformableNode("some_null"))

    yield str(builder.settings.file_path), builder.settings, builder.nodes


def test_load_fbx(single_null_fbx):
    stage = Usd.Stage.Open(single_null_fbx[0])
    assert stage.GetPseudoRoot()


def test_default_prim(single_null_fbx, root_prim_name):
    stage = Usd.Stage.Open(single_null_fbx[0])
    default_prim = stage.GetDefaultPrim()
    assert default_prim
    assert default_prim == stage.GetPrimAtPath(f"/{root_prim_name}")


def test_reference_fbx(simple_hierarchy_fbx):
    stage = Usd.Stage.CreateInMemory()
    ref = stage.OverridePrim("/ref")
    file_path, _, nodes_used = simple_hierarchy_fbx
    ref.GetReferences().AddReference(file_path)
    assert (
        len([x for x in stage.Traverse()]) == len(nodes_used) + 1
    )  # {root_prim_name}/ref/{nodes_used[1].name} should be the only prims present, +1 as ROOT as implied


@pytest.fixture(scope="session")
def specific_fbx_version_fbx(fbx_defaults, fbx_file_compat_versions):
    output_dir, manager, scene, fbx_file_format = fbx_defaults

    with scenebuilder.SceneBuilder(manager, scene, output_dir) as builder:
        builder.settings.file_format = fbx_file_format
        builder.settings.compatibility = fbx_file_compat_versions[0]
    yield str(builder.settings.file_path), fbx_file_compat_versions[1]


def test_load_fbx_versions(specific_fbx_version_fbx):
    # second unpacked variable is the fbx_version string if it's needed in the future
    file_path, should_load = specific_fbx_version_fbx
    if not should_load:
        with pytest.raises(Tf.ErrorException):
            _ = Usd.Stage.Open(file_path)
    else:
        assert Usd.Stage.Open(file_path)


def test_multiple_fbx_scenes(single_null_fbx, basic_plane_fbx, root_prim_name):
    null_file_path, _, null_nodes = single_null_fbx
    mesh_file_path, _, mesh_nodes = basic_plane_fbx
    assert null_file_path != mesh_file_path

    stage = Usd.Stage.CreateInMemory("tmp.usda")
    # create root
    _ = UsdGeom.Xform.Define(stage, f"/{root_prim_name}")

    # create ref to null fbx
    null_prim = stage.OverridePrim(f"/{root_prim_name}/null_scene")
    null_prim.GetReferences().AddReference(assetPath=null_file_path)

    # create ref to mesh fbx
    mesh_prim = stage.OverridePrim(f"/{root_prim_name}/mesh_scene")
    mesh_prim.GetReferences().AddReference(assetPath=mesh_file_path)

    # validate that the referenced prims are sensible, we only test whether the proper schemas are applied
    # Concrete tests of the data itself are done elsewhere
    # If the apis cannot be applied, the underlying bool operator will return False, failing the assert.
    assert UsdGeom.Xformable.Get(
        stage, f"/{root_prim_name}/null_scene/{null_nodes[0].name}"
    )
    assert UsdGeom.Mesh.Get(stage, f"/{root_prim_name}/mesh_scene/{mesh_nodes[0].name}")


@pytest.fixture(scope="session")
def multiple_roots_fbx(fbx_defaults):
    output_dir, manager, scene, fbx_file_format = fbx_defaults
    with scenebuilder.SceneBuilder(manager, scene, output_dir) as builder:
        builder.settings.file_format = fbx_file_format
        for name in tuple("abcde"):
            builder.nodes.append(TransformableNode(name))
    yield str(builder.settings.file_path), builder.nodes


def test_multiple_roots(multiple_roots_fbx, root_prim_name):
    file_path, nodes = multiple_roots_fbx
    stage = Usd.Stage.Open(file_path)
    default_prim = stage.GetDefaultPrim()
    assert default_prim.GetName().lower() == root_prim_name.lower()

    assert sorted(default_prim.GetChildrenNames()) == sorted([o.name for o in nodes])
