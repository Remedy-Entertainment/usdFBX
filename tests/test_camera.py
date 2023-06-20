import pytest

from pxr import Usd, UsdGeom
import FbxCommon as fbx

from helpers import (
    validate_property_animation,
    validate_stage_time_metrics,
)
from data import scenebuilder, Camera

BASIC_CAMERA_NAME = "basic_camera"


def build_camera_scene(fbx_defaults, camera: Camera):
    output_dir, manager, scene, fbx_file_format = fbx_defaults
    with scenebuilder.SceneBuilder(manager, scene, output_dir) as builder:
        builder.settings.file_format = fbx_file_format
        builder.nodes.append(camera)
    return str(builder.settings.file_path)


@pytest.fixture(scope="session")
def simple_camera_fbx(fbx_defaults):
    cam = Camera(name=BASIC_CAMERA_NAME)
    yield build_camera_scene(fbx_defaults, cam), cam


def test_camera_creation(simple_camera_fbx, root_prim_name):
    file_path, camera_settings_used = simple_camera_fbx
    stage = Usd.Stage.Open(file_path)
    camera_prim_path = f"/{root_prim_name}/{camera_settings_used.name}"
    camera_prim = stage.GetPrimAtPath(camera_prim_path)
    assert camera_prim, f"could not find `{camera_prim_path}`"
    assert UsdGeom.Camera(camera_prim), f"`{camera_prim_path}` is not a UsdGeomCamera!"


def test_camera_basics(simple_camera_fbx, root_prim_name):
    file_path, camera_settings_used = simple_camera_fbx
    stage = Usd.Stage.Open(file_path)
    camera_prim_path = f"/{root_prim_name}/{camera_settings_used.name}"
    camera = UsdGeom.Camera(stage.GetPrimAtPath(camera_prim_path))
    # check default parameters

    clipping_range = camera.GetClippingRangeAttr().Get()
    assert clipping_range == camera_settings_used.clipping_range

    focus_distance = camera.GetFocusDistanceAttr().Get()
    assert focus_distance == camera_settings_used.focus_distance

    projection = camera.GetProjectionAttr().Get()
    assert (
        projection
        == {
            fbx.FbxCamera.EProjectionType.ePerspective: "perspective",
            fbx.FbxCamera.EProjectionType.eOrthogonal: "orthographic",
        }[camera_settings_used.projection]
    )

    role = camera.GetStereoRoleAttr().Get()
    assert role == camera_settings_used.role

    # fStop, exposure and shutter:open/close are not something that FBX supports. So we do not check those


@pytest.fixture(
    params=[
        # (Camera dict, expected result)
        (Camera(name=BASIC_CAMERA_NAME, fov=0.0), 0.0),
        (Camera(name=BASIC_CAMERA_NAME, fov=90.0), 90.0),
        (Camera(name=BASIC_CAMERA_NAME, fov=180.0), 180.0),
        (Camera(name=BASIC_CAMERA_NAME, fov=250.0), 250.0),
        (Camera(name=BASIC_CAMERA_NAME, fov=-90.0), -90.0),
        (Camera(name=BASIC_CAMERA_NAME, fov="unsupported_type"), 0.0),
    ],
    scope="session",
)
def camera_fov_fbx(fbx_defaults, request):
    cam = request.param[0]
    yield build_camera_scene(fbx_defaults, cam), cam, request.param[1], "generated:fov"


def test_camera_fov(camera_fov_fbx, root_prim_name):
    """
    The UsdGeomCamera spec does not define a spec for writing out FieldOfView, it is calculated from apertureWidth/Height instead
    At the moment, FOV is explicitly written out by the plugin as a custom user attribute.
    NOTE: This is subject to change
    """
    (
        file_path,
        camera_settings_used,
        expected_fov,
        expected_attribute,
    ) = camera_fov_fbx
    stage = Usd.Stage.Open(file_path)
    camera_prim = stage.GetPrimAtPath(f"/{root_prim_name}/{camera_settings_used.name}")
    fov_attr = camera_prim.GetAttribute(expected_attribute)
    assert fov_attr, "expected to have a user attribute for FOV written"
    assert fov_attr.IsCustom(), "expected FOV to be a custom attribute"
    assert fov_attr.Get() == expected_fov


@pytest.fixture(
    params=[
        # (Camera dict, expected result: (aperture width in 1/10th, aperture height))
        # Values fetched from https://help.autodesk.com/view/FBX/2020/ENU/?guid=FBX_Developer_Help_cpp_ref_class_fbx_camera_html
        (
            Camera(
                name=BASIC_CAMERA_NAME,
                focal_length=50,
                aperture_format=fbx.FbxCamera.EApertureFormat.e35mm185Projection,
            ),
            (0.825, 0.446, 1.0),
        ),  # 35mm spherical is the USD standard
        (
            Camera(
                name=BASIC_CAMERA_NAME,
                focal_length=50,
                aperture_format=fbx.FbxCamera.EApertureFormat.e35mmAnamorphic,
            ),
            (0.864, 0.732, 2.0),
        ),
        (
            Camera(
                name=BASIC_CAMERA_NAME,
                focal_length=50,
                aperture_format=fbx.FbxCamera.EApertureFormat.eCustomAperture,
                aperture_width=0.5,
                aperture_height=0.5,
                squeeze_ratio=1.5,
            ),
            (0.5, 0.5, 1.5),
        ),
    ],
    scope="session",
)
def camera_filmback_and_lens_properties_fbx(fbx_defaults, request):
    def aperture_inch_to_mm(value, squeeze_ratio=1.0, inch_to_mm_scale_factor=1.0):
        return value * squeeze_ratio * 25.4 * inch_to_mm_scale_factor

    ap = request.param[1]
    expected_aperture = (
        aperture_inch_to_mm(ap[0], ap[2]),
        aperture_inch_to_mm(ap[1], ap[2]),
    )

    cam = request.param[0]
    expected_focal_length = cam.focal_length
    yield build_camera_scene(
        fbx_defaults, cam
    ), cam, expected_aperture, expected_focal_length


def test_camera_filmback_and_lens_properties(
    camera_filmback_and_lens_properties_fbx, root_prim_name
):
    """
    It's important to note that UsdGeomCamera encodes lens and filmback properties in _ONE TENTH OF SCENE UNITS_
    Ie. when something like focal length is authored at 45 and the scene unit is 0.01 metersPerUnit
    The effective focal length is 0.01 * 0.1 * 45 meters per unit = 0.045m aka 45mm
    if mpu was 1, the value of 45 implies that the focal length is 45dm, expressing it as mm with relation to mpu would be 4.5
    Fbx on the other hand encodes focal length _always_ in mm

    The same is done with film size (film aperture). Which FBX always encodes in inches, because freedom

    Regardless, when filmback and lens properties are authored, they are all expected to be in the same "space", ie. 1/10th of scene units
    ex. If a FocalLength of 45 for 0.01mpu equates to 45mm, then the values for apertureHeight and -Width are assumed to also be in mm

    Note: Since UsdFbx 1.0.0, stage metrics are _always_ expressed in 0.01metersPerUnit and Y-up accordingly
    """
    (
        file_path,
        camera_settings_used,
        expected_aperture,
        expected_focal_length,
    ) = camera_filmback_and_lens_properties_fbx

    stage = Usd.Stage.Open(file_path)
    camera_prim = stage.GetPrimAtPath(f"/{root_prim_name}/{camera_settings_used.name}")
    camera = UsdGeom.Camera(camera_prim)

    horizontal_aperture = camera.GetHorizontalApertureAttr()
    assert expected_aperture[0] == pytest.approx(horizontal_aperture.Get())
    vertical_aperture = camera.GetVerticalApertureAttr()
    assert expected_aperture[1] == pytest.approx(vertical_aperture.Get())
    focal_length = camera.GetFocalLengthAttr()
    assert expected_focal_length == pytest.approx(focal_length.Get())
