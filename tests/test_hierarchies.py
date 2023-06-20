from pxr import Usd


def test_simple_hierarchy(simple_hierarchy_fbx, root_prim_name):
    file_path, _, nodes = simple_hierarchy_fbx
    stage = Usd.Stage.Open(file_path)
    parent = nodes[0].name
    child = nodes[1].name
    assert stage.GetPrimAtPath(f"/{root_prim_name}/{parent}")
    assert stage.GetPrimAtPath(f"/{root_prim_name}/{parent}/{child}")
