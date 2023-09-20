import string

import pytest

import FbxCommon as fbx

from pxr import Usd, Gf

from data import scenebuilder, TransformableNode, Property
from helpers import create_FbxTime


@pytest.fixture(
    params=[
        ((fbx.EFbxType.eFbxUndefined, "", "undefined"), "UNKNOWN TYPE"),
        # NOTE: Signed chars are note supported by USD, so we will have to expect (and test against) wrap around values instead
        ((fbx.EFbxType.eFbxChar, 255, "someChar"), 255),
        ((fbx.EFbxType.eFbxChar, -1, "someChar"), 255),
        ((fbx.EFbxType.eFbxChar, -128, "someChar"), 128),
        ((fbx.EFbxType.eFbxUChar, 1, "someUChar"), 1),
        ((fbx.EFbxType.eFbxShort, -2, "someShort"), -2),
        ((fbx.EFbxType.eFbxUShort, 2, "someUShort"), 2),
        ((fbx.EFbxType.eFbxUInt, 123, "someUInt"), 123),
        ((fbx.EFbxType.eFbxInt, -123, "someInt"), -123),
        ((fbx.EFbxType.eFbxLongLong, -1234567890, "someLong"), -1234567890),
        ((fbx.EFbxType.eFbxULongLong, 1234567890, "someULong"), 1234567890),
        # Due to how fast precision deteriorates with half-precision,
        # we're checking against the same value with a much lower tolerance than normal floats
        ((fbx.EFbxType.eFbxHalfFloat, 0.05, "someHalf"), pytest.approx(0.05, abs=1e-3)),
        # The python fbx sdk creates this as an Action type instead of bool...
        # Commenting out but leaving it in there until a workaround is found
        # (fbx.eFbxBool, True, "someBool"),
        ((fbx.EFbxType.eFbxFloat, 1.2345, "someFloat"), pytest.approx(1.2345)),
        ((fbx.EFbxType.eFbxDouble, 1.2345, "someDouble"), pytest.approx(1.2345)),
        # Unable to set via python SDK
        # setting the type as double2 and writing a double3 results in a (0., 0.) value unfortunately
        # see https://forums.autodesk.com/t5/fbx-forum/python-fbx-sdk-2019-2-fbxproperty-set-does-not-accept-fbxdouble2/td-p/8620916
        # (fbx.eFbxDouble2, fbx.FbxDouble2(1.0, 2.0), "someDouble2"),
        (
            (fbx.EFbxType.eFbxDouble3, fbx.FbxDouble3(1.0, 2.0, 3.0), "someDouble3"),
            Gf.Vec3d(1.0, 2.0, 3.0),
        ),
        (
            (
                fbx.EFbxType.eFbxDouble4,
                fbx.FbxDouble4(1.0, 2.0, 3.0, 4.0),
                "someDouble4",
            ),
            Gf.Vec4d(1.0, 2.0, 3.0, 4.0),
        ),
        (
            (
                fbx.EFbxType.eFbxDouble4x4,
                fbx.FbxDouble4x4(
                    fbx.FbxDouble4(1.0, 2.0, 3.0, 4.0),
                    fbx.FbxDouble4(5.0, 6.0, 7.0, 8.0),
                    fbx.FbxDouble4(9.0, 10.0, 11.0, 12.0),
                    fbx.FbxDouble4(13.0, 14.0, 15.0, 16.0),
                ),
                "someDouble4x4",
            ),
            Gf.Matrix4d(*[float(x + 1) for x in range(16)]),
        ),
        # Unable to set via python SDK
        # (fbx.eFbxEnum, None, "someEnum"),
        (
            (fbx.EFbxType.eFbxString, fbx.FbxString("hello world"), "someString"),
            "hello world",
        ),
        (
            (fbx.EFbxType.eFbxString, fbx.FbxString("hElLo wOrLd"), "someString"),
            "hElLo wOrLd",
        ),
        ((fbx.EFbxType.eFbxTime, create_FbxTime(10), "someTime"), Usd.TimeCode(10.0)),
        # Unable to set via python SDK
        # (fbx.eFbxReference, None, "someReference"),
        # NOTE: While handy, it's probably fine to ignore FbxBlob attributes.
        # (fbx.eFbxBlob, str("d\x00S\x00"), "someBlob"),
        # Unable to set via python SDK
        # (fbx.eFbxDistance, fbx.FbxDistance(100.0, fbx.FbxSystemUnit.cm), "someDistance"),
        # Unable to set via python SDK
        # (fbx.eFbxDateTime, fbx.FbxDateTime(), "someDateTime"),
    ],
    scope="session",
)
def user_property_fbx(fbx_defaults, request):
    output_dir, manager, scene, fbx_file_format = fbx_defaults
    (prop_type, default_value, name), usd_expected = request.param
    with scenebuilder.SceneBuilder(manager, scene, output_dir) as builder:
        builder.settings.file_format = fbx_file_format
        prop = Property(
            name=name,
            value=default_value,
            data_name_and_type=("", prop_type),
            user_defined=True,
        )
        builder.nodes.append(TransformableNode("null1", properties=[prop]))
    yield str(builder.settings.file_path), builder.nodes, name, usd_expected


def test_user_properties(user_property_fbx, root_prim_name):
    file_path, nodes, prop_name, expected_value = user_property_fbx
    stage = Usd.Stage.Open(file_path)

    target_prim = stage.GetPrimAtPath(f"/{root_prim_name}/{nodes[0].name}")
    prop = target_prim.GetAttribute(f"userProperties:{prop_name}")
    assert prop, f"unable to find user property 'userProperties:{prop_name}'"

    assert (
        prop.HasAuthoredDisplayGroup()
    ), "No display group was authored for the user property!"
    display_group = prop.GetMetadata("displayGroup")
    assert (
        display_group == "User"
    ), f"expected 'User' for displayGroup metadata, got '{display_group}' instead"

    assert expected_value == prop.Get()


def test_bugfix_GetDisplayGroup(user_property_fbx, root_prim_name):
    """
    The internal fix for this (for Usd 21.xx) is giving a VtValue<std::string> or VtValue<const char*> instead
    of VtValue<TfToken> for the SdfFieldKeys->DisplayGroup metadatum

    If one passes a TfToken instead of a string it'll fail via GetDisplayGroup as that tries to read
    the metadatum into a std::string. While TfToken can easily convert to a std::string, something in
    VtValue seems to not fly well with that idea in this context.
    """
    file_path, nodes, prop_name, _ = user_property_fbx
    stage = Usd.Stage.Open(file_path)

    target_prim = stage.GetPrimAtPath(f"/{root_prim_name}/{nodes[0].name}")
    display_group = target_prim.GetAttribute(
        f"userProperties:{prop_name}"
    ).GetDisplayGroup()
    assert (
        display_group == "User"
    ), f"expected 'User' for displayGroup metadata, got '{display_group}' instead"


@pytest.fixture(
    params=[(f"foo{c}bar", "foo_bar") for c in string.punctuation + string.whitespace]
)
def node_name_fbx(fbx_defaults, request):
    output_dir, manager, scene, fbx_file_format = fbx_defaults
    input_name, expected_name = request.param
    with scenebuilder.SceneBuilder(manager, scene, output_dir) as builder:
        builder.settings.file_format = fbx_file_format
        builder.nodes.append(TransformableNode(input_name))
    yield str(builder.settings.file_path), builder.nodes, expected_name


def test_validPrimNames(node_name_fbx, root_prim_name):
    file_path, nodes, expected_name = node_name_fbx
    stage = Usd.Stage.Open(file_path)

    target_prim = stage.GetPrimAtPath(f"/{root_prim_name}/{expected_name}")

    assert target_prim, f"unable to find prim at path /{root_prim_name}/{expected_name}"
