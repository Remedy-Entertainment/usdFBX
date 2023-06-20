from contextlib import contextmanager
import pathlib
import uuid
import warnings

import FbxCommon as fbx
from . import (
    export_fbx,
    primitives,
    Settings,
    TransformableNode,
    Camera,
    Mesh,
    Joint,
)

class Builder:
    __slots__ = ["manager", "scene", "nodes", "settings", "output_dir"]

    def __init__(self, manager: fbx.FbxManager, scene: fbx.FbxScene, output_dir:pathlib.Path) -> None:
        self.manager = manager
        self.scene = scene
        self.output_dir = output_dir
        self.nodes = []
        self.settings = Settings()  # No need to have a builder for this
        self.settings.file_path = self.output_dir/ f"{str(uuid.uuid4())}.fbx"

    def build(self) -> None:
        type_primitive_map = {
            Joint: primitives.create_joint,
            Mesh: primitives.create_mesh,
            TransformableNode: primitives.create_null,
            Camera: primitives.create_camera,
        }

        settings = self.scene.GetGlobalSettings()
        settings.SetSystemUnit(self.settings.units)
        settings.SetAxisSystem(self.settings.axis)
        
        if self.settings.original_axis is not None:
            settings.SetOriginalUpAxis(self.settings.original_axis)

        if self.settings.anim_layers:
            anim_stack = fbx.FbxAnimStack.Create(self.scene, "RootStack")
            self.scene.SetCurrentAnimationStack(anim_stack)

        for anim_layer in self.settings.anim_layers:
            self.scene.GetCurrentAnimationStack().AddMember(
                fbx.FbxAnimLayer.Create(self.scene, anim_layer)
            )

        root_joint_nodes = [
            node for node in self.nodes if type(node) is Joint and node.is_root
        ]
        root = self.scene.GetRootNode()
        node_to_fbx_map = {}
        # First pass, construct all transformables
        for node in self.nodes:
            fn = type_primitive_map.get(type(node), None)
            if fn is None:
                warnings.warn(f'unable to find primitive mapping for "{type(node)}"')
            fbx_node = fn(self.manager, node)[0]
            primitives.apply_transform(fbx_node, node.transform)
            primitives.set_or_create_properties(fbx_node, node.properties, self.scene)

            node_to_fbx_map[node] = fbx_node

        # Second pass, reparent where needed
        for node, fbx_node in node_to_fbx_map.items():
            if node.parent is None:
                root.AddChild(fbx_node)
                continue
            parent_node = node_to_fbx_map.get(node.parent, None)
            assert parent_node, "parent cannot be none at this stage"
            parent_node.AddChild(fbx_node)

        # Third pass, apply any links like skin clusters
        anim_evaluator = self.scene.GetAnimationEvaluator()
        for node, fbx_node in node_to_fbx_map.items():
            if type(node) is not Mesh:
                continue
            if not node.skinbinding:
                continue

            skin = fbx.FbxSkin.Create(self.manager, "")
            bind_pose = fbx.FbxPose.Create(self.manager, f"bindpose_{node.name}")
            bind_pose.SetIsBindPose(True)
            rest_pose = fbx.FbxPose.Create(self.manager, f"restpose_{node.name}")

            root_joint = node_to_fbx_map.get(root_joint_nodes[0], None)  # This is kind of silly, but it'll do for now
            assert root_joint is not None, "No root joint found or defined!"
            root_global_xform = anim_evaluator.GetNodeGlobalTransform(root_joint)
            rest_pose.Add(root_joint, fbx.FbxMatrix(root_global_xform), False)

            xform_matrix = anim_evaluator.GetNodeGlobalTransform(fbx_node)

            for binding in node.skinbinding:
                target_fbx_joint = node_to_fbx_map.get(binding.target_joint, None)
                assert (
                    target_fbx_joint is not None
                ), f"Target joint is None for skinbing on {node.name}"
                # Add joint to both rest and bind poses
                if target_fbx_joint != root_joint:
                    local_xform = anim_evaluator.GetNodeLocalTransform(target_fbx_joint)
                    rest_pose.Add(target_fbx_joint, fbx.FbxMatrix(local_xform), True)
                global_xform = anim_evaluator.GetNodeGlobalTransform(target_fbx_joint)
                bind_pose.Add(target_fbx_joint, fbx.FbxMatrix(global_xform))

                cluster = fbx.FbxCluster.Create(self.manager, "")
                cluster.SetLink(target_fbx_joint)
                cluster.SetLinkMode(binding.link_mode)
                for index, weight in binding.vertex_weights:
                    cluster.AddControlPointIndex(index, weight)

                link_matrix = self.scene.GetAnimationEvaluator().GetNodeGlobalTransform(
                    target_fbx_joint
                )
                cluster.SetTransformLinkMatrix(link_matrix)
                cluster.SetTransformMatrix(xform_matrix)

                skin.AddCluster(cluster)

            fbx_node.GetNodeAttribute().AddDeformer(skin)
            self.scene.AddPose(bind_pose)
            self.scene.AddPose(rest_pose)
        return self.scene


@contextmanager
def SceneBuilder(fbx_manager: fbx.FbxManager, fbx_scene: fbx.FbxScene, output_dir: pathlib.Path):
    builder = Builder(fbx_manager, fbx_scene, output_dir)
    yield builder
    builder.build()
    #if scene.settings.output_path.exists:
    #    scene.settings.output_path = scene.settings.output_path.parent / f"{str(uuid.uuid4())}.fbx"
    export_fbx(
        builder.settings.file_path,
        fbx_scene,
        fbx_manager,
        builder.settings.file_format,
        builder.settings.compatibility,
    )
    builder.scene.Clear()
