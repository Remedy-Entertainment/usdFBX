import pytest
from pxr import Usd, UsdGeom

from helpers import (
    validate_property_animation,
    validate_stage_time_metrics,
)
from data import AnimationCurve, scenebuilder, TransformableNode, Property


@pytest.fixture(
    params=[
        (
            Property(name="Visibility", value=0.0),
            ("invisible", ("generated:visibility", 0.0)),
        ),
        (
            Property(name="Visibility", value=1.0),
            ("inherited", ("generated:visibility", 1.0)),
        ),
        (
            Property(name="Visibility", value=-1.0),
            ("invisible", ("generated:visibility", -1.0)),
        ),
        (
            Property(name="Visibility", value=10.0),
            ("inherited", ("generated:visibility", 10.0)),
        ),
        (
            Property(name="Visibility", value=1e-10),
            ("invisible", ("generated:visibility", 1e-10)),
        ),
        (
            Property(name="Visibility", value=5e-4),
            ("inherited", ("generated:visibility", 5e-4)),
        ),
        (
            Property(name="Visibility", value=-1e-10),
            ("invisible", ("generated:visibility", -1e-10)),
        ),
        (
            Property(name="Visibility", value=-5e-4),
            ("invisible", ("generated:visibility", -5e-4)),
        ),
    ],
    scope="session",
)
def imageable_properties_fbx(fbx_defaults, request):
    output_dir, manager, scene, fbx_file_format = fbx_defaults
    fbx_property, usd_expected = request.param
    with scenebuilder.SceneBuilder(manager, scene, output_dir) as builder:
        builder.settings.file_format = fbx_file_format
        null = TransformableNode("null1", properties=[fbx_property])
        builder.nodes.append(null)
    yield str(builder.settings.file_path), builder.nodes, usd_expected


def test_imageable_basic(imageable_properties_fbx, root_prim_name):
    file_path, nodes, expected = imageable_properties_fbx
    stage = Usd.Stage.Open(file_path)
    prim_path = f"/{root_prim_name}/{nodes[0].name}"
    target_prim = stage.GetPrimAtPath(prim_path)

    imageable = UsdGeom.Imageable(target_prim)
    assert imageable
    visibility = imageable.GetVisibilityAttr()
    assert visibility.Get() == expected[0]
    assert imageable.GetPurposeAttr().Get() == "default"
    float_visibility = target_prim.GetAttribute(expected[1][0])
    assert float_visibility
    assert float_visibility.Get() == pytest.approx(expected[1][1])


@pytest.fixture(
    params=[
        # (FBX property, expected in USD)
        (("Visibility", 0.0, 1.0), ("invisible", "inherited", 0.0, 1.0)),
        (("Visibility", 0.0, 100.0), ("invisible", "inherited", 0.0, 100.0)),
        (("Visibility", -1.0, 0.0), ("invisible", "invisible", -1.0, 0.0)),
    ],
    scope="session",
)
def animated_visibility_fbx(
    fbx_defaults,
    fbx_animation_time_codes,
    request,
):
    fbx_times, usd_expected_times = fbx_animation_time_codes
    output_dir, manager, scene, fbx_file_format = fbx_defaults
    property_def, usd_expected_values = request.param
    curve = AnimationCurve(
        anim_layer="Base", times=fbx_times, values=list(property_def[1:])
    )
    fbx_property = Property(
        name=property_def[0], animation_curves=[curve], value=property_def[1]
    )
    with scenebuilder.SceneBuilder(manager, scene, output_dir) as builder:
        builder.settings.file_format = fbx_file_format
        builder.settings.anim_layers = ("Base",)
        null = TransformableNode("null1", properties=[fbx_property])
        builder.nodes.append(null)
    expected = usd_expected_values + ("generated:visibility",) + usd_expected_times
    yield str(builder.settings.file_path), builder.nodes, expected


def test_imageable_animated(animated_visibility_fbx, root_prim_name):
    file_path, nodes, expected = animated_visibility_fbx
    usd_start_value, usd_end_value = expected[0:2]
    gen_start_value, gen_usd_end_value, gen_prop_name = expected[2:5]
    usd_start_time, usd_end_time = expected[5:]

    stage = Usd.Stage.Open(file_path)
    prim_path = f"/{root_prim_name}/{nodes[0].name}"
    target_prim = stage.GetPrimAtPath(prim_path)

    imageable = UsdGeom.Imageable(target_prim)
    visibility = imageable.GetVisibilityAttr()

    start_end_flipped = validate_stage_time_metrics(
        stage, (usd_start_time, usd_end_time)
    )
    for prop, expected_values in zip(
        [visibility, target_prim.GetAttribute(gen_prop_name)],
        [(usd_start_value, usd_end_value), (gen_start_value, gen_usd_end_value)],
    ):
        if start_end_flipped:
            expected_values = reversed(expected_values)
        validate_property_animation(stage, prop, expected_values)
