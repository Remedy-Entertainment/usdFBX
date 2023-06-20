from cmath import exp
import pytest

from pxr import Usd, Gf
import FbxCommon as fbx

from helpers import validate_property_animation, validate_stage_time_metrics
from data import scenebuilder, AnimationCurve, Property, TransformableNode


@pytest.fixture(
    params=[
        (
            (
                "LclTranslation",
                fbx.FbxDouble3(1.0, 2.0, 3.0),
                fbx.FbxDouble3(10.0, 20.0, 30.0),
            ),
            ("xformOp:translate", Gf.Vec3d(1.0, 2.0, 3.0), Gf.Vec3d(10.0, 20.0, 30.0)),
        ),
        (
            (
                "LclRotation",
                fbx.FbxDouble3(0.0, 0.0, 0.0),
                fbx.FbxDouble3(90.0, 45.0, 120.0),
            ),
            ("xformOp:rotateXYZ", Gf.Vec3d(0.0, 0.0, 0.0), Gf.Vec3d(90.0, 45.0, 120.0)),
        ),
        (
            (
                "LclScaling",
                fbx.FbxDouble3(1.0, 1.0, 1.0),
                fbx.FbxDouble3(10.0, 20.0, 30.0),
            ),
            ("xformOp:scale", Gf.Vec3d(1.0, 1.0, 1.0), Gf.Vec3d(10.0, 20.0, 30.0)),
        ),
    ],
    scope="session",
)
def animated_property_fbx(fbx_defaults, fbx_animation_time_codes, request):
    output_dir, manager, scene, fbx_file_format = fbx_defaults
    property_def, usd_expected = request.param
    fbx_times, usd_expected_times = fbx_animation_time_codes
    with scenebuilder.SceneBuilder(manager, scene, output_dir) as builder:
        builder.settings.file_format = fbx_file_format
        builder.settings.anim_layers = ("Base",)

        curve = AnimationCurve(
            anim_layer="Base", times=fbx_times, values=list(property_def[1:])
        )
        fbx_property = Property(
            name=property_def[0], animation_curves=[curve], value=property_def[1]
        )
        builder.nodes.append(TransformableNode("null1", properties=[fbx_property]))
    yield (
        str(builder.settings.file_path),
        builder.nodes,
        usd_expected[0],
        usd_expected[1:],
        usd_expected_times,
    )


def test_property_animation(animated_property_fbx, root_prim_name):
    (
        file_path,
        nodes,
        expected_property,
        expected_values,
        expected_times,
    ) = animated_property_fbx
    stage = Usd.Stage.Open(file_path)
    prim_path = f"/{root_prim_name}/{nodes[0].name}"
    target_prim = stage.GetPrimAtPath(prim_path)
    prop = target_prim.GetAttribute(expected_property)
    assert prop, f"Could not find `{expected_property}` on prim <{prim_path}>"

    start_end_flipped = validate_stage_time_metrics(stage, expected_times)
    if start_end_flipped:
        expected_values = reversed(expected_values)
    validate_property_animation(stage, prop, expected_values)


@pytest.fixture(
    params=[
        (
            "someAnimatedFloat",
            (fbx.EFbxType.eFbxFloat, "Number", -10.0, 10.0),
            (-10.0, 10.0),
        ),
        ("someAnimatedInt", (fbx.EFbxType.eFbxInt, "Number", -10, 10), (-10.0, 10.0)),
        (
            "someAnimatedDouble3",
            (
                fbx.EFbxType.eFbxDouble3,
                "Vector",
                fbx.FbxDouble3(1.0, 2.0, 3.0),
                fbx.FbxDouble3(10.0, 20.0, 30.0),
            ),
            (Gf.Vec3d(1.0, 2.0, 3.0), Gf.Vec3d(10.0, 20.0, 30.0)),
        ),
    ],
    scope="session",
)
def animated_user_property_fbx(fbx_defaults, fbx_animation_time_codes, request):
    output_dir, manager, scene, fbx_file_format = fbx_defaults
    name, property_def, usd_expected = request.param
    fbx_times, usd_expected_times = fbx_animation_time_codes
    with scenebuilder.SceneBuilder(manager, scene, output_dir) as builder:
        builder.settings.file_format = fbx_file_format
        builder.settings.anim_layers = ("Base",)

        curve = AnimationCurve(
            anim_layer="Base", times=fbx_times, values=list(property_def[2:])
        )
        fbx_property = Property(
            name=name,
            animation_curves=[curve],
            value=property_def[1],
            user_defined=True,
            data_name_and_type=(property_def[1], property_def[0]),
        )
        builder.nodes.append(TransformableNode("null1", properties=[fbx_property]))
    yield (
        str(builder.settings.file_path),
        builder.nodes,
        name,
        usd_expected,
        usd_expected_times,
    )


def test_user_property_animation(animated_user_property_fbx, root_prim_name):
    (
        file_path,
        nodes,
        expected_property,
        expected_values,
        expected_times,
    ) = animated_user_property_fbx
    stage = Usd.Stage.Open(file_path)
    prim_path = f"/{root_prim_name}/{nodes[0].name}"
    target_prim = stage.GetPrimAtPath(prim_path)
    prop = target_prim.GetAttribute(f"userProperties:{expected_property}")

    start_end_flipped = validate_stage_time_metrics(stage, expected_times)
    if start_end_flipped:
        expected_values = reversed(expected_values)
    validate_property_animation(stage, prop, expected_values)
