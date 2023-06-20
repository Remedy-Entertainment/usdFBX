import pathlib
import uuid
from dotenv import load_dotenv
import pytest

load_dotenv(
    dotenv_path=(pathlib.Path(__file__).parent / "../.env").resolve(),
    verbose=True,
    override=True,
)

import FbxCommon as fbx
from pxr import Usd, Plug, Gf, UsdGeom

from data import TransformableNode, scenebuilder, MappedCoordinates, Mesh

from helpers import create_FbxTime


@pytest.fixture
def root_prim_name():
    yield "ROOT"


@pytest.fixture(
    params=[
        ("FBX201600", True),
        ("FBX201800", True),
        ("FBX201900", True),
        ("FBX202000", True),  # Current version of the SDK used in the plugin
    ],
    scope="session",
    ids=lambda x: f"{x[3:7]} compat",
)
def fbx_file_compat_versions(request):
    yield request.param


@pytest.fixture(
    params=["FBX binary (*.fbx)", "FBX ascii (*.fbx)"],
    scope="session",
    ids=["Binary FBX", "ASCII FBX"],
)
def fbx_file_format(request):
    yield request.param


@pytest.fixture(
    params=[
        fbx.FbxAxisSystem.EUpVector.eXAxis,
        fbx.FbxAxisSystem.EUpVector.eYAxis,
        fbx.FbxAxisSystem.EUpVector.eZAxis,
    ],
    scope="session",
    ids=[f"Up: {axis}" for axis in ("X", "Y", "Z")],
)
def fbx_up_axis(request):
    yield request.param


@pytest.fixture(
    params=[
        fbx.FbxAxisSystem.EFrontVector.eParityEven,
        fbx.FbxAxisSystem.EFrontVector.eParityOdd,
    ],
    scope="session",
    ids=["Even Parity", "Odd Parity"],
)
def fbx_front_vector(request):
    yield request.param


@pytest.fixture(
    params=[
        fbx.FbxAxisSystem.ECoordSystem.eRightHanded,
        fbx.FbxAxisSystem.ECoordSystem.eLeftHanded,
    ],
    scope="session",
    ids=["Right Handed", "Left Handed"],
)
def fbx_coordinate_system(request):
    yield request.param


@pytest.fixture(scope="session")
def fbx_axis(fbx_up_axis, fbx_front_vector, fbx_coordinate_system):
    yield fbx.FbxAxisSystem(fbx_up_axis, fbx_front_vector, fbx_coordinate_system)


@pytest.fixture(
    params=[
        # Type, start_value, end_value, property_name
        (
            (create_FbxTime(0), create_FbxTime(100)),
            (Usd.TimeCode(0), Usd.TimeCode(100)),
        ),
        (
            (create_FbxTime(0), create_FbxTime(-100)),
            (Usd.TimeCode(0), Usd.TimeCode(-100)),
        ),
        (
            (create_FbxTime(-100), create_FbxTime(0)),
            (Usd.TimeCode(-100), Usd.TimeCode(0)),
        ),
        (
            (create_FbxTime(50), create_FbxTime(100)),
            (Usd.TimeCode(50), Usd.TimeCode(100)),
        ),
    ],
    scope="session",
)
def fbx_animation_time_codes(request):
    yield request.param


@pytest.fixture
def registry():
    reg = Plug.Registry()
    yield reg


@pytest.fixture(scope="session")
def fbx_sdk_objects():
    return fbx.InitializeSdkObjects()


@pytest.fixture(scope="session")
def fbx_defaults(tmp_path_factory, fbx_sdk_objects, fbx_file_format):
    manager, scene = fbx_sdk_objects
    output_dir = tmp_path_factory.mktemp(
        str(uuid.uuid4())
    )  # / f"{str(uuid.uuid4())}.fbx"
    yield output_dir, manager, scene, fbx_file_format


@pytest.fixture(scope="session")
def basic_plane_fbx(fbx_defaults):
    output_dir, manager, scene, fbx_file_format = fbx_defaults
    with scenebuilder.SceneBuilder(manager, scene, output_dir) as builder:
        builder.settings.file_format = fbx_file_format
        texcoords_a = MappedCoordinates(
            name="set_a",
            coordinates=[(0, 0), (1, 0), (1, 1), (0, 1)],
            point_mapping=[0, 3, 2, 2, 1, 0],
        )
        texcoords_b = MappedCoordinates(
            name="set_b",
            coordinates=[(0, 0), (1, 0), (1, 1), (0, 1)],
            point_mapping=list(
                reversed([0, 3, 2, 2, 1, 0])
            ),  # have to cast to list, otherwise it stores a generator
        )
        vertex_colors = MappedCoordinates(
            name="default_colors",
            coordinates=[(1, 0, 0)],  # all verts are red
            point_mapping=[0] * 4,  # One color per vertex
        )
        # TODO - Post 1.0: Parameterize normals mapping/reference modes
        mesh = Mesh(
            name="basic_plane",
            points=[(-1, 0, -1), (1, 0, -1), (1, 0, 1), (-1, 0, 1)],
            normals=MappedCoordinates(coordinates=[(0, 1, 0)], point_mapping=[0] * 6),
            polygons=[(0, 3, 2), (2, 1, 0)],
            uvs=[texcoords_a, texcoords_b],
            vertex_colors=[vertex_colors],
        )
        builder.nodes.append(mesh)

    yield str(builder.settings.file_path), builder.settings, builder.nodes


@pytest.fixture(scope="session")
def simple_hierarchy_fbx(fbx_defaults):
    output_dir, manager, scene, fbx_file_format = fbx_defaults
    with scenebuilder.SceneBuilder(manager, scene, output_dir) as builder:
        builder.settings.file_format = fbx_file_format
        parent = TransformableNode("parent")
        child = TransformableNode("child", parent=parent)
        builder.nodes.append(parent)
        builder.nodes.append(child)

    yield str(builder.settings.file_path), builder.settings, builder.nodes
