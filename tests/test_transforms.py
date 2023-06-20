import pytest

import FbxCommon as fbx
from pxr import Usd, UsdGeom, Vt, Gf

from data import Mesh, TransformableNode, Transform, scenebuilder, Node
from typing import List


def load_stage_and_test_transform(file_path, nodes: List[Node], root_prim_name):
    stage = Usd.Stage.Open(file_path)
    node = nodes[0]
    prim = stage.GetPrimAtPath(f"/{root_prim_name}/{node.name}")
    xformable = UsdGeom.Xformable(prim)
    assert xformable
    xformAPI = UsdGeom.XformCommonAPI(prim)
    assert xformable

    t, r, s, *_ = xformAPI.GetXformVectors(Usd.TimeCode.Default())
    assert t == Gf.Vec3d(*node.transform.t)
    # NOTE: We are using GfVec3f for rotation and scale here, as those are what `GetXformVectors' outputs.
    # there is an issue with expressing R/S as `double3` _and_ using `GetXformVectors` due to data narrowing
    assert r == Gf.Vec3f(*node.transform.r)
    assert s == Gf.Vec3f(*node.transform.s)


@pytest.fixture(
    params=[
        Transform(t=(10, 10, 10)),
        Transform(r=(45, 0, 45)),
        Transform(s=(2, 2, 2)),
        Transform(t=(10, 10, 10), r=(45, 0, 45), s=(2, 2, 2)),
    ],
    scope="session",
)
def transform(request):
    yield request.param


@pytest.fixture
def transformed_null_fbx(fbx_defaults, transform):
    output_dir, manager, scene, fbx_file_format = fbx_defaults
    with scenebuilder.SceneBuilder(manager, scene, output_dir) as builder:
        builder.settings.file_format = fbx_file_format
        builder.nodes.append(TransformableNode(name="null", transform=transform))
    yield str(builder.settings.file_path), builder.nodes


def test_null_transform(transformed_null_fbx, root_prim_name):
    file_path, nodes = transformed_null_fbx
    load_stage_and_test_transform(file_path, nodes, root_prim_name)


@pytest.fixture
def transformed_mesh_fbx(fbx_defaults, transform):
    output_dir, manager, scene, fbx_file_format = fbx_defaults
    with scenebuilder.SceneBuilder(manager, scene, output_dir) as builder:
        builder.settings.file_format = fbx_file_format
        builder.nodes.append(
            Mesh(
                name="basic_plane",
                points=[(-1, 0, -1), (1, 0, -1), (1, 0, 1), (-1, 0, 1)],
                polygons=[(0, 3, 2), (2, 1, 0)],
                transform=transform,
            )
        )
    yield str(builder.settings.file_path), builder.nodes


def test_geometry_transform(transformed_mesh_fbx, root_prim_name):
    file_path, nodes = transformed_mesh_fbx
    load_stage_and_test_transform(file_path, nodes, root_prim_name)


@pytest.fixture(
    params=[
        (
            Transform(ro=fbx.EFbxRotationOrder.eEulerXYZ),
            UsdGeom.XformCommonAPI.RotationOrderXYZ,
        ),
        (
            Transform(ro=fbx.EFbxRotationOrder.eEulerXZY),
            UsdGeom.XformCommonAPI.RotationOrderXZY,
        ),
        (
            Transform(ro=fbx.EFbxRotationOrder.eEulerYXZ),
            UsdGeom.XformCommonAPI.RotationOrderYXZ,
        ),
        (
            Transform(ro=fbx.EFbxRotationOrder.eEulerYZX),
            UsdGeom.XformCommonAPI.RotationOrderYZX,
        ),
        (
            Transform(ro=fbx.EFbxRotationOrder.eEulerZXY),
            UsdGeom.XformCommonAPI.RotationOrderZXY,
        ),
        (
            Transform(ro=fbx.EFbxRotationOrder.eEulerZYX),
            UsdGeom.XformCommonAPI.RotationOrderZYX,
        ),
        (
            Transform(ro=fbx.EFbxRotationOrder.eSphericXYZ),
            UsdGeom.XformCommonAPI.RotationOrderXYZ,
        ),
    ],
    scope="session",
)
def rotation_orders_fbx(fbx_defaults, request):
    output_dir, manager, scene, fbx_file_format = fbx_defaults
    with scenebuilder.SceneBuilder(manager, scene, output_dir) as builder:
        builder.settings.file_format = fbx_file_format
        builder.nodes.append(TransformableNode(name="null", transform=request.param[0]))
    yield str(builder.settings.file_path), builder.nodes, request.param[1]


def test_rotation_orders(rotation_orders_fbx, root_prim_name, capfd):
    file_path, nodes, expected = rotation_orders_fbx
    node = nodes[0]
    stage = Usd.Stage.Open(file_path)

    if node.transform.ro == fbx.EFbxRotationOrder.eSphericXYZ:
        _, err = capfd.readouterr()
        assert err.startswith("Warning:") and "SphericXYZ is not supported" in err

    prim = stage.GetPrimAtPath(f"/{root_prim_name}/{node.name}")
    xformAPI = UsdGeom.XformCommonAPI(prim)

    # Note: it may be necessary to also verify the resulting rotation via the xformcommonAPI
    # but that seems to fall in the realm of "testing standard USD" stuff which should be covered
    # by USD's own internal tests. If there's odd behavior with rotation orders in practice, do add a test here

    rotation_order = xformAPI.GetXformVectors(Usd.TimeCode.Default())[4]
    assert rotation_order == expected
