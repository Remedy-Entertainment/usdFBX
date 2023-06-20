import pytest
from pxr import Usd, UsdGeom, Gf
import FbxCommon as fbx
from data import Mesh, Transform, scenebuilder, TransformableNode, Settings
import re


@pytest.fixture
def up_axis_fbx(fbx_defaults, fbx_axis):
    output_dir, manager, scene, fbx_file_format = fbx_defaults
    with scenebuilder.SceneBuilder(manager, scene, output_dir) as builder:
        builder.settings.file_format = fbx_file_format
        builder.settings.axis = fbx_axis
    yield str(builder.settings.file_path), builder.settings


def test_up_axis(up_axis_fbx, capfd):
    file_path, settings = up_axis_fbx
    stage = Usd.Stage.Open(file_path)
    up_vector = settings.axis.GetUpVector()
    if up_vector == fbx.FbxAxisSystem.EUpVector.eXAxis:
        _, err = capfd.readouterr()
        assert (
            err.startswith("Warning:")
            and "Unsupported coordinate system. X-up is not supported" in err
        )

    assert stage.HasAuthoredMetadata(UsdGeom.Tokens.upAxis)
    up_axis = UsdGeom.GetStageUpAxis(stage)
    assert up_axis == UsdGeom.Tokens.y

    # TODO: Test that non-y-up sources have their up vector data correctly applied


@pytest.fixture(
    params=[
        fbx.FbxSystemUnit.mm,
        fbx.FbxSystemUnit.cm,
        fbx.FbxSystemUnit.dm,
        fbx.FbxSystemUnit.m,
        fbx.FbxSystemUnit.km,
        fbx.FbxSystemUnit.Inch,
        fbx.FbxSystemUnit.Foot,
        fbx.FbxSystemUnit.Mile,
        fbx.FbxSystemUnit.Yard,
    ],
    scope="session",
)
def meters_per_unit_fbx(fbx_defaults, request):
    output_dir, manager, scene, fbx_file_format = fbx_defaults

    # FBX COORDINATES ARE ALWAYS IN CENTIMETER!
    # Only TRS is adjusted, so either have the usdFbx collapse scaling into the geometry, or take it as-is.

    value = 5  # in what ever units we author
    with scenebuilder.SceneBuilder(manager, scene, output_dir) as builder:
        builder.settings.file_format = fbx_file_format
        builder.settings.units = request.param
        builder.nodes.append(
            Mesh(
                name="triangle",
                points=[(-value, 0, 0), (value, 0, 0), (0, 0, value)],
                polygons=[(0, 1, 2)],
                transform=Transform(t=(value, value, value), s=(value, value, value)),
            )
        )
    # Geometry coordinates are always implicitly in centimeters in FBX.
    # We expect to see the same data in USD as the UsdFbx plugin converts to 0.01mpu, always
    expected_points = [
        (-value, 0, 0),
        (value, 0, 0),
        (0, 0, value),
    ]
    # Part of the conversion process involves rescaling SRT values in the space of centimeters
    expected_value = value * fbx.FbxSystemUnit.cm.GetConversionFactorFrom(request.param)

    yield str(
        builder.settings.file_path
    ), builder.nodes, expected_value, expected_points


def test_meters_per_unit(meters_per_unit_fbx, root_prim_name):
    file_path, nodes, expected_value, expected_points = meters_per_unit_fbx
    stage = Usd.Stage.Open(file_path)
    assert UsdGeom.StageHasAuthoredMetersPerUnit(stage)
    units = UsdGeom.GetStageMetersPerUnit(stage)
    assert units == 0.01  # Loaded Fbx's are always converted to 0.01

    target_prim = stage.GetPrimAtPath(f"/{root_prim_name}/{nodes[0].name}")
    xform_api = UsdGeom.XformCommonAPI(target_prim)
    t, _, s = xform_api.GetXformVectors(Usd.TimeCode.Default())[0:3]
    assert t == (expected_value,) * 3
    assert s == (expected_value,) * 3
    geometry = UsdGeom.Mesh(target_prim)
    assert geometry.GetPointsAttr().Get() == expected_points


@pytest.fixture(
    params=[
        (fbx.FbxAxisSystem.Max, fbx.FbxAxisSystem.MayaYUp),
        (fbx.FbxAxisSystem.MayaYUp, fbx.FbxAxisSystem.Max),
    ],
    scope="session",
)
def authored_vs_mixed_axis_fbx(fbx_defaults, request):
    output_dir, manager, scene, fbx_file_format = fbx_defaults
    t = Transform(t=(10, 20, 30))
    with scenebuilder.SceneBuilder(manager, scene, output_dir) as builder:
        builder.settings.file_format = fbx_file_format
        builder.settings.axis = request.param[0]
        builder.settings.original_axis = request.param[1]
        builder.nodes.append(TransformableNode(name="null", transform=t))
    expected_t = (10, 30, -20) if request.param[0] == fbx.FbxAxisSystem.Max else t.t
    yield str(builder.settings.file_path), builder.nodes, expected_t


def test_NL25260_fix_up_authored_vs_up_exported(
    authored_vs_mixed_axis_fbx, root_prim_name, capfd
):
    """
    When exporting under a different up-axis than the authored one, FBX will be apply offset rotations
    in the PreRotation attribute.
    The plugin's transform reader however will use FbxAxisSystem::DeepConvertScene which will modify geometry and trs data accordingly (like flipping axis/negations)
    """
    file_path, nodes, expected_t = authored_vs_mixed_axis_fbx
    stage = Usd.Stage.Open(file_path)

    err = capfd.readouterr()[1]
    pattern = re.compile(
        "^Warning:.*(This scene was exported with [X|Y|Z]-up but originally authored in [X|Y|Z]-up).*\n$"
    )
    assert (
        pattern.match(err) is not None
    ), "Expected a warning about mismatched Axis System"

    target_prim = stage.GetPrimAtPath(f"/{root_prim_name}/{nodes[0].name}")
    xform_api = UsdGeom.XformCommonAPI(target_prim)
    translation = xform_api.GetXformVectors(Usd.TimeCode.Default())[0]
    assert translation == expected_t
