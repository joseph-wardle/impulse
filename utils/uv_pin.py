from xmlrpc.client import Boolean
import maya.cmds as cmds

def make_uv_pin (
        object_to_pin: str, 
        surface: str, 
        u: float = 0, 
        v: float = 0,
        local_space: bool = False,
        normalize: bool = False,
        normal_axis: str = None,
        tangent_axis: str = None,
        reset_transforms: bool = True,
) -> str:
    """
    Create a UVPin node that pins an object to a given surface at specified UV coordinates.

    Args:
        object_to_pin: The name of the object to be pinned.
        surface: The name of the surface (mesh or NURBS) to pin to.
        u: The U coordinate.
        v: The V coordinate.
        local_space: When true, sets UVPin node to local relativeSpaceMode. When false, the pinned object has inheritsTransform disabled to prevent double transforms.
        normalize: Enable Isoparm normalization (NURBS UV will be remapped between 0-1).
        normal_axis: Normal axis of the generated uvPin, can be x y z -x -y -z.
        tangent_axis: Tangent axis of the generated uvPin, can be x y z -x -y -z.
        reset_transforms: When True, reset the pinned object's transforms.
    Returns:
        The name of the created UVPin node.
    """
    # Retrieve shape nodes from the surface.
    shapes = cmds.listRelatives(surface, children=True, shapes=True) or []
    if not shapes:
        cmds.error(f"No shape nodes found on surface: {surface}")
    
    # Choose the primary shape (non-intermediate if available) and check for an existing intermediate shape.
    primary_shape = next((s for s in shapes if not cmds.getAttr(f"{s}.intermediateObject")), shapes[0])
    shape_origin = next((s for s in shapes if cmds.getAttr(f"{s}.intermediateObject")), None) 

    # Determine attribute names based on surface type.
    surface_type = cmds.objectType(primary_shape)
    if surface_type == "mesh":
        attr_input = ".inMesh"
        attr_world = ".worldMesh[0]"
        attr_output = ".outMesh"
    elif surface_type == "nurbsSurface":
        attr_input = ".create"
        attr_world = ".worldSpace[0]"
        attr_output = ".local"
    else:
        cmds.error(f"Unsupported surface type: {surface_type}")

    # If no intermediate shape exists, create one.
    if shape_origin is None:
        duplicated = cmds.duplicate(primary_shape)[0]
        shape_origin_list = cmds.listRelatives(duplicated, children=True, shapes=True)
        if not shape_origin_list:
            cmds.error("Could not create intermediate shape.")
        shape_origin = shape_origin_list[0]
        cmds.parent(shape_origin, surface, shape=True, relative=True)
        cmds.delete(duplicated)
        new_name = f"{primary_shape}Orig"
        shape_origin = cmds.rename(shape_origin, new_name)
        # If there is an incoming connection, reconnect it.
        in_conn = cmds.listConnections(f"{primary_shape}{attr_input}", plugs=True, connections=True, destination=True)
        if in_conn:
            cmds.connectAttr(in_conn[1], f"{shape_origin}{attr_input}")
        cmds.connectAttr(f"{shape_origin}{attr_world}", f"{primary_shape}{attr_input}", force=True)
        cmds.setAttr(f"{shape_origin}.intermediateObject", 1)
    
    # Create the UVPin node and connect it.
    uv_pin = cmds.createNode("uvPin", name=f"{object_to_pin}_uvPin")
    cmds.connectAttr(f"{primary_shape}{attr_world}", f"{uv_pin}.deformedGeometry")
    cmds.connectAttr(f"{shape_origin}{attr_output}", f"{uv_pin}.originalGeometry")
    cmds.xform(object_to_pin, translation=[0, 0, 0], rotation=[0, 0, 0])
    
    if normal_axis:
        if normal_axis == "x":
            cmds.setAttr(f"{uv_pin}.normalAxis", 0)
        elif normal_axis == "y":
            cmds.setAttr(f"{uv_pin}.normalAxis", 1)
        elif normal_axis == "z":
            cmds.setAttr(f"{uv_pin}.normalAxis", 2)
        elif normal_axis == "-x":
            cmds.setAttr(f"{uv_pin}.normalAxis", 3)
        elif normal_axis == "-y":
            cmds.setAttr(f"{uv_pin}.normalAxis", 4)
        elif normal_axis == "-z":
            cmds.setAttr(f"{uv_pin}.normalAxis", 5)
        else:
            raise RuntimeError(f"{normal_axis} isn't a valid axis, it should be x y z -x -y -z")
    else:
        cmds.setAttr(f"{uv_pin}.normalAxis", 1)

    if tangent_axis:
        if tangent_axis == "x":
            cmds.setAttr(f"{uv_pin}.tangentAxis", 0)
        elif tangent_axis == "y":
            cmds.setAttr(f"{uv_pin}.tangentAxis", 1)
        elif tangent_axis == "z":
            cmds.setAttr(f"{uv_pin}.tangentAxis", 2)
        elif tangent_axis == "-x":
            cmds.setAttr(f"{uv_pin}.tangentAxis", 3)
        elif tangent_axis == "-y":
            cmds.setAttr(f"{uv_pin}.tangentAxis", 4)
        elif tangent_axis == "-z":
            cmds.setAttr(f"{uv_pin}.tangentAxis", 5)
        else:
            raise RuntimeError(f"{tangent_axis} isn't a valid axis, it should be x y z -x -y -z")
    else:
        cmds.setAttr(f"{uv_pin}.tangentAxis", 0)
    

    cmds.setAttr(f"{uv_pin}.normalizedIsoParms", 0)
    cmds.setAttr(f"{uv_pin}.coordinate[0]", u, v, type="float2")
    cmds.connectAttr(f"{uv_pin}.outputMatrix[0]", f"{object_to_pin}.offsetParentMatrix")

    if normalize:
        cmds.setAttr(f"{uv_pin}.normalizedIsoParms", 1)

    if local_space:
        cmds.setAttr(f"{uv_pin}.relativeSpaceMode", 1)
    else:
        cmds.setAttr(f"{object_to_pin}.inheritsTransform", 0)
    return uv_pin