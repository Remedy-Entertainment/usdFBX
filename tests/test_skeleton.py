from re import A
import pytest
import FbxCommon as fbx
from pxr import Usd, UsdGeom, Gf, UsdSkel, Sdf
from data import (
    Joint,
    MappedCoordinates,
    Mesh,
    SkinBinding,
    TransformableNode,
    scenebuilder,
    Transform,
    Property,
    AnimationCurve,
)
from typing import List


def validate_skeleton(cache, prim, nodes: List[Joint]):
    def node_to_path(node):
        if node.parent is None or type(node.parent) is not Joint or node.is_root:
            return node.name
        return f"{node_to_path(node.parent)}/{node.name}"

    node_paths = [node_to_path(node) for node in nodes]
    query = cache.GetSkelQuery(prim)

    topology = query.GetTopology()
    joint_order = query.GetJointOrder()
    for i in range(len(topology)):
        name = Sdf.Path(joint_order[i]).name
        parent = topology.GetParent(i)

        try:
            validation_object = nodes[node_paths.index(joint_order[i])]
        except ValueError as e:
            raise ValueError(
                f"Could not find a match in the validation data for {name}"
            )

        parent_name = Sdf.Path(joint_order[parent]).name if parent >= 0 else None
        validation_parent_name = (
            validation_object.parent.name
            if validation_object.parent is not None
            else None
        )

        # TODO: Check transforms
        assert parent_name == validation_parent_name


@pytest.fixture
def simple_skeleton_fbx(fbx_defaults):
    output_dir, manager, scene, fbx_file_format = fbx_defaults
    t = (0.0, 40.0, 0.0)
    with scenebuilder.SceneBuilder(manager, scene, output_dir) as builder:
        builder.settings.file_format = fbx_file_format
        root_node = Joint(name="root", is_root=True)
        child_1 = Joint(name="child_1", parent=root_node, transform=Transform(t=t))
        child_2 = Joint(name="child_2", parent=child_1, transform=Transform(t=t))
        builder.nodes.extend([root_node, child_1, child_2])
    yield str(builder.settings.file_path), builder.nodes


def test_simple_skeleton(simple_skeleton_fbx):
    file_path, nodes = simple_skeleton_fbx
    stage = Usd.Stage.Open(file_path)
    root = None
    skeleton_prim = None
    unknowns = []
    for prim in stage.Traverse():
        if prim.IsA(UsdSkel.Root):
            root = UsdSkel.Root(prim)
        elif prim.IsA(UsdSkel.Skeleton):
            skeleton_prim = UsdSkel.Skeleton(prim)
        else:
            unknowns.append(prim)

    assert None not in [root, skeleton_prim]
    assert not unknowns

    # The plugin creates a Skeleton prim with the same name as the root joint of the hierarchy it represents
    assert skeleton_prim.GetPrim().GetName() == nodes[0].name

    cache = UsdSkel.Cache()

    validate_skeleton(cache, skeleton_prim, nodes)


@pytest.fixture
def multiple_skeletons_fbx(fbx_defaults):
    output_dir, manager, scene, fbx_file_format = fbx_defaults
    with scenebuilder.SceneBuilder(manager, scene, output_dir) as builder:
        builder.settings.file_format = fbx_file_format
        root_node_a = Joint(name="root_a", is_root=True)
        child_1 = Joint(name="child_1", parent=root_node_a)
        child_2 = Joint(name="child_2", parent=child_1)
        builder.nodes.extend([root_node_a, child_1, child_2])
        root_node_b = Joint(name="root_b", is_root=True)
        child_3 = Joint(name="child_1", parent=root_node_b)
        child_4 = Joint(name="child_2", parent=child_3)
        builder.nodes.extend([root_node_b, child_3, child_4])
    yield str(builder.settings.file_path), builder.nodes


def test_multiple_skeletons(multiple_skeletons_fbx):
    file_path, nodes = multiple_skeletons_fbx
    stage = Usd.Stage.Open(file_path)

    skeleton_prims = [
        UsdSkel.Skeleton(prim)
        for prim in stage.Traverse()
        if prim.IsA(UsdSkel.Skeleton)
    ]
    assert len(skeleton_prims) == len([obj for obj in nodes if obj.parent is None])

    cache = UsdSkel.Cache()

    for skeleton_prim in skeleton_prims:
        validate_skeleton(cache, skeleton_prim, nodes)


@pytest.fixture
def nested_skeletons_fbx(fbx_defaults):
    output_dir, manager, scene, fbx_file_format = fbx_defaults
    with scenebuilder.SceneBuilder(manager, scene, output_dir) as builder:
        builder.settings.file_format = fbx_file_format
        null = TransformableNode(name="null")
        root_node_a = Joint(name="root", parent=null, is_root=True)
        child_1 = Joint(name="child_1", parent=root_node_a)
        child_2 = Joint(name="child_2", parent=child_1)
        builder.nodes.extend([null, root_node_a, child_1, child_2])
    yield str(builder.settings.file_path), builder.nodes


def test_nested_skeleton(nested_skeletons_fbx, root_prim_name):
    """
    Tests for generating skeletons that are parented to other objects
    but within a SkeletonRoot.
    """
    file_path, nodes = nested_skeletons_fbx
    stage = Usd.Stage.Open(file_path)

    path_to_skel = "/".join([obj.name for obj in nodes[:2]])
    skeleton = UsdSkel.Skeleton.Get(stage, f"/{root_prim_name}/{path_to_skel}")
    assert skeleton
    parent = skeleton.GetPrim().GetParent()
    assert parent and not parent.IsA(UsdSkel.Skeleton)


@pytest.fixture
def mixed_type_hierarchy_fbx(fbx_defaults):
    output_dir, manager, scene, fbx_file_format = fbx_defaults
    with scenebuilder.SceneBuilder(manager, scene, output_dir) as builder:
        builder.settings.file_format = fbx_file_format
        a = Joint(name="A", is_root=True)
        b = Joint(name="B", parent=a)
        c = TransformableNode(name="C", parent=b)
        d = Joint(name="D", parent=c)
        builder.nodes.extend([a, b, c, d])
    yield str(builder.settings.file_path), builder.nodes


def test_hierarchy_with_mixed_types(mixed_type_hierarchy_fbx, capfd, root_prim_name):
    """
    Tests for skeletons that have mixed types in their hierarchy.

    Example:
        A (joint) -> B (joint) -> C (null) -> D (joint)
        The outcome of this should be a skeleton with joints A and B, but D is ignored
        as it has a non-skeleton parent.

    Note:
        This limitation is artificial and if it is deemed necessary to take _any_ transformable
        within a skeleton hierarchy as a joint, this can be changed in the plugin.

    """
    file_path, nodes = mixed_type_hierarchy_fbx
    stage = Usd.Stage.Open(file_path)

    out, err = capfd.readouterr()
    assert not out
    assert (
        "warn" in err.lower() and f'"{nodes[2].name}" is not an FbxSkeleton node' in err
    ), "No warnings have been raised, but were expected"

    skeleton = UsdSkel.Skeleton.Get(stage, f"/{root_prim_name}/{nodes[0].name}")
    cache = UsdSkel.Cache()
    query = cache.GetSkelQuery(skeleton)
    joint_order = query.GetJointOrder()
    assert len(joint_order) != len(
        nodes
    ), "Generated skeleton equates that of source, this is unexpected in this scenario"


@pytest.fixture
def skeleton_binding_fbx(fbx_defaults):
    output_dir, manager, scene, fbx_file_format = fbx_defaults
    offset = 10.0
    t = Transform(t=(offset, 0.0, 0.0))
    with scenebuilder.SceneBuilder(manager, scene, output_dir) as builder:
        builder.settings.file_format = fbx_file_format
        a = Joint(name="A", is_root=True)
        b = Joint(name="B", parent=a, transform=t)
        c = Joint(name="C", parent=b, transform=t)

        geo = Mesh(
            name="bound_skin",
            points=[
                p for x in range(3) for p in ((x * offset, 0, -1), (x * offset, 0, 1))
            ],
            skinbinding=(
                SkinBinding(
                    target_joint=a,
                    vertex_weights=((0, 1.0), (1, 1.0), (2, 0.25), (3, 0.25)),
                ),
                SkinBinding(target_joint=b, vertex_weights=((2, 0.5), (3, 0.5))),
                SkinBinding(
                    target_joint=c,
                    vertex_weights=((4, 1.0), (5, 1.0), (2, 0.25), (3, 0.25)),
                ),
            ),
            polygons=[(0, 1, 3), (3, 2, 0), (2, 3, 5), (5, 4, 2)],
        )
        builder.nodes.extend([a, b, c, geo])
    yield str(builder.settings.file_path), builder.nodes


def test_simple_binding(skeleton_binding_fbx, root_prim_name):
    file_path, nodes = skeleton_binding_fbx
    stage = Usd.Stage.Open(file_path)
    cache = UsdSkel.Cache()

    # NOTE: While fetching the skinned prim as is would be sufficient, it's important to use the UsdSkelAPI here
    it = iter(stage.Traverse())
    for prim in it:
        if prim.IsA(UsdSkel.Root):
            it.PruneChildren()

        root = UsdSkel.Root(prim)
        cache.Populate(root, Usd.TraverseInstanceProxies())

        bindings = cache.ComputeSkelBindings(root, Usd.TraverseInstanceProxies())
        assert bindings
        for binding in bindings:
            assert binding.GetSkeleton()
            query = cache.GetSkelQuery(binding.GetSkeleton())
            assert query
            skinning_xforms = query.ComputeSkinningTransforms(Usd.TimeCode.Default())
            assert len(skinning_xforms) == 3
            # Iterate over the prims that are skinned by this Skeleton.
            for skinning_query in binding.GetSkinningTargets():
                skinned_prim = skinning_query.GetPrim()
                assert skinned_prim
                assert skinned_prim.GetName() == nodes[-1].name

                binding_api = UsdSkel.BindingAPI(skinned_prim)
                assert binding_api

                joints_attr = binding_api.GetJointsAttr()
                assert joints_attr, "The plugin must define skel:joints"

                joint_indices_attr = binding_api.GetJointIndicesAttr()
                assert (
                    joint_indices_attr
                ), "The plugin must define primvars:skel:jointIndices"

                joint_weights_attr = binding_api.GetJointWeightsAttr()
                assert (
                    joint_weights_attr
                ), "The plugin must define primvars:skel:jointWeights"

                indices_primvar = UsdGeom.Primvar(joint_indices_attr)
                weights_primvar = UsdGeom.Primvar(joint_weights_attr)
                assert (
                    weights_primvar.GetElementSize() == indices_primvar.GetElementSize()
                ), "Weights and indices must match in elementSize!"


@pytest.fixture(
    params=[
        (
            "Visibility",
            False,
            "",
            None,
            0.0,
            1.0,
        ),
        (
            "some_float_property",
            True,
            "Number",
            fbx.EFbxType.eFbxFloat,
            -10.0,
            10.0,
        ),
    ],
    scope="session",
)
def animated_bone_properties_fbx(fbx_defaults, fbx_animation_time_codes, request):
    output_dir, manager, scene, fbx_file_format = fbx_defaults
    fbx_property_data = request.param
    fbx_times = fbx_animation_time_codes[0]

    with scenebuilder.SceneBuilder(manager, scene, output_dir) as builder:
        builder.settings.file_format = fbx_file_format
        builder.settings.anim_layers = ("Base",)

        curve = AnimationCurve(
            anim_layer="Base", times=fbx_times, values=list(fbx_property_data[4:])
        )
        fbx_property = Property(
            name=fbx_property_data[0],
            animation_curves=[curve],
            value=fbx_property_data[4],
            user_defined=fbx_property_data[1],
            data_name_and_type=(fbx_property_data[2:4])
            if fbx_property_data[3] is not None
            else None,
        )

        a = Joint(name="A", is_root=True)
        b = Joint(name="B", parent=a, properties=[fbx_property])
        c = Joint(name="C", parent=b)
        d = Joint(name="D", parent=c, properties=[fbx_property])
        builder.nodes.extend([a, b, c, d])

    expected = (
        f"userProperties:{fbx_property_data[0]}",  # property name
        2,  # num values per timesample
        ("A/B", "A/B/C/D"),  # owners
    )
    yield str(builder.settings.file_path), builder.nodes, expected


def test_animated_bone_properties(animated_bone_properties_fbx, root_prim_name):
    file_path, nodes, expected = animated_bone_properties_fbx
    stage = Usd.Stage.Open(file_path)

    anim_prim = stage.GetPrimAtPath(f"/{root_prim_name}/Animation{nodes[0].name}")
    assert anim_prim
    anim_node = UsdSkel.Animation(anim_prim)
    assert anim_node

    prop_name, values_per_sample, owners = expected
    attr = anim_prim.GetAttribute(prop_name)

    assert attr
    assert attr.GetNumTimeSamples()
    assert attr.GetTimeSamples()
    assert set([len(attr.Get(Usd.TimeCode(x))) for x in attr.GetTimeSamples()]) == {
        values_per_sample
    }

    owner_attr = anim_prim.GetAttribute(f"{prop_name}:owner")
    assert owner_attr
    assert owner_attr.Get() == owners
