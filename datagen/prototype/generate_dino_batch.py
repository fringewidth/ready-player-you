import bpy
import mathutils
import os
import sys
import json
import random
import math
import colorsys

# Add project root to path dynamically
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
if ROOT not in sys.path:
    sys.path.append(ROOT)
# Dynamic vision-digitized asset metadata
METADATA_PATH = os.path.join(ROOT, "datagen", "asset_metadata.json")
ASSET_METADATA = {}
if os.path.exists(METADATA_PATH):
    with open(METADATA_PATH, 'r') as f:
        ASSET_METADATA = json.load(f)

def get_semantic_vector(asset_name):
    """Returns the 3-float vector from digitized metadata or a zero fallback."""
    if not asset_name or asset_name.lower() == "none":
        return [0.0, 0.0, 0.0]
    return ASSET_METADATA.get(asset_name, [0.0, 0.0, 0.0])

MPFB_BASE = "bl_ext.blender_org.mpfb"
USER_DATA_PATH = os.path.expanduser("~/Library/Application Support/Blender/5.1/extensions/.user/blender_org/mpfb/data")

GLASSES_LIST = [
    "none",
    "culturalibre_doc_ock_glasses",
    "frankyaye_glasses_library_male",
    "kwnet_at_optical_glasses",
    "spamrakuen_sagerfrogs_glasses_01",
    "spamrakuen_sagerfrogs_glasses_02",
    "spamrakuen_sagerfrogs_glasses_03",
    "spamrakuen_sagerfrogs_glasses_04",
    "spamrakuen_tbm_glasses_frames_01",
    "toigo_round_glasses_leopard"
]

BEARDS_LIST = [
    "none",
    "culturalibre_faun_beard",
    "grinsegold_beard_sigmund_wip",
    "rehmanpolanski_beard_viking",
    "rehmanpolanski_moustache_viking",
    "wdg_scruffy_beard",
    "culturalibre_dal_moustache",
    "elvs_scruffy_beard1",
    "grinsegold_full_beard",
    "grinsegold_moustache"
]

def list_mh_assets(category):
    cat_path = os.path.join(USER_DATA_PATH, category)
    if not os.path.exists(cat_path):
        return []
    return [d for d in os.listdir(cat_path) if os.path.isdir(os.path.join(cat_path, d))]

def get_asset_path(category, name):
    if not name or name == "none":
        return None
    path = os.path.join(USER_DATA_PATH, category, name, f"{name}.mhclo")
    if os.path.exists(path):
        return path
    return None

def apply_stylized_skin(obj, color):
    """Creates a fresh material and assigns it to the primary slot of the human mesh."""
    if not obj: return
    
    # Create fresh material
    mat_name = f"Skin_{obj.name}"
    mat = bpy.data.materials.new(name=mat_name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (color[0], color[1], color[2], 1.0)
        bsdf.inputs["Roughness"].default_value = 0.4
        
    # Assign to slot 0 (The Body)
    if len(obj.data.materials) > 0:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)

def apply_asset_color(obj, color, slot_name_filter=None):
    """Applies a flat RGB color to a mesh's materials, with optional slot filtering."""
    if not obj: return
    
    for slot in obj.material_slots:
        mat = slot.material
        if not mat: continue
        
        # Filter by name (Skin, Body, Human) or fallback to slot 0 if it's the main mesh
        is_skin_slot = False
        skin_keywords = ["skin", "body", "human", "base"]
        if slot_name_filter:
            is_skin_slot = any(k in mat.name.lower() for k in skin_keywords)
        else:
            is_skin_slot = True # Asset meshes usually only have one relevant color slot
            
        if not is_skin_slot and slot.slot_index != 0:
            continue
            
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        
        # Support Principled BSDF, Hair BSDF, or simple Diffuse
        shader_node = next((n for n in nodes if n.type in ['BSDF_PRINCIPLED', 'BSDF_HAIR_PRINCIPLED', 'BSDF_DIFFUSE']), None)
        
        if shader_node:
            color_input = shader_node.inputs.get("Base Color") or shader_node.inputs.get("Color")
            if color_input:
                for link in list(mat.node_tree.links):
                    if link.to_socket == color_input:
                        mat.node_tree.links.remove(link)
                color_input.default_value = (color[0], color[1], color[2], 1.0)

def sample_eye_color():
    """Returns a stylized eye color (Linear RGB)."""
    palette = [
        (0.02, 0.05, 0.2),  # Deep Blue
        (0.05, 0.15, 0.05), # Emerald Green
        (0.3, 0.15, 0.05), # Amber/Light Brown
        (0.08, 0.04, 0.02), # Dark Brown
        (0.1, 0.1, 0.15)    # Steel Gray
    ]
    res_srgb = random.choice(palette)
    # They are already roughly linear in my definition, but let's ensure
    return res_srgb

def apply_eye_color(obj, color):
    """Manipulates eye material nodes to tint the iris while keeping sclera white."""
    if not obj: return
    for slot in obj.material_slots:
        mat = slot.material
        if not mat or not mat.use_nodes: continue
        
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        bsdf = nodes.get("Principled BSDF")
        if not bsdf: continue
        
        # Find the existing image texture input
        base_color_input = bsdf.inputs['Base Color']
        if not base_color_input.is_linked: continue
        
        source_link = base_color_input.links[0]
        source_node = source_link.from_node
        source_socket = source_link.from_socket
        
        # Inject ColorRamp
        ramp = nodes.new(type='ShaderNodeValToRGB')
        ramp.location = (bsdf.location.x - 300, bsdf.location.y)
        
        # Configure Ramp: 0.0 = EyeColor, 0.6 = White
        ramp.color_ramp.elements[0].position = 0.0
        ramp.color_ramp.elements[0].color = (color[0], color[1], color[2], 1.0)
        ramp.color_ramp.elements[1].position = 0.6
        ramp.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)
        
        # Re-link: [Texture] -> [Ramp] -> [BSDF]
        links.new(source_socket, ramp.inputs[0])
        links.new(ramp.outputs[0], base_color_input)

def sample_hair_color(age):
    """Samples a hair color based on the age of the character."""
    if random.random() < 0.9:
        # Comprehensive Natural human hair palette
        naturals = [
            (0.02, 0.02, 0.02), # Black
            (0.05, 0.03, 0.01), # Raven Black
            (0.12, 0.06, 0.02), # Dark Brown
            (0.3, 0.15, 0.05),  # Medium Brown
            (0.45, 0.25, 0.1),  # Light Brown
            (0.5, 0.15, 0.05),  # Auburn/Red
            (0.7, 0.6, 0.3),    # Honey Blonde
            (0.85, 0.75, 0.45), # Golden Blonde
            (0.95, 0.9, 0.8)    # Platinum
        ]
        
        # Only add elderly colors if age is high
        if age > 0.75:
            naturals += [(0.7, 0.7, 0.7), (0.95, 0.95, 0.95)]
            
        return random.choice(naturals)
    # 10% Exotic (Full RGB range)
    return (random.random(), random.random(), random.random())

SKIN_PALETTE = [
    (255, 245, 223), (255, 221, 196), (255, 217, 174), (255, 203, 147), (246, 226, 172),
    (255, 216, 185), (238, 194, 168), (220, 183, 139), (243, 183, 141), (231, 173, 134),
    (228, 171, 132), (205, 154, 119), (202, 149, 117), (214, 139, 98), (204, 138, 111),
    (196, 139, 105), (198, 127, 90), (180, 113, 81), (164, 103, 74), (147, 92, 65),
    (134, 85, 60), (165, 115, 88), (152, 105, 81), (142, 100, 77), (134, 85, 60),
    (137, 58, 46), (136, 65, 67), (145, 52, 0), (109, 68, 49), (88, 53, 39),
    (76, 46, 33), (65, 39, 28)
]

def sample_skin_color():
    """Interpolates across the 32-point palette and converts to Linear RGB."""
    t = random.random() * (len(SKIN_PALETTE) - 1)
    idx = int(t)
    frac = t - idx
    
    p1 = SKIN_PALETTE[idx]
    p2 = SKIN_PALETTE[min(idx + 1, len(SKIN_PALETTE) - 1)]
    
    # Interpolate in sRGB [0-255] then normalize and gamma correct
    res_srgb = [p1[i] + (p2[i] - p1[i]) * frac for i in range(3)]
    
    # Simple sRGB to Linear approximation (gamma 2.2)
    res_linear = [( (c / 255.0) ** 2.2 ) for c in res_srgb]
    return tuple(res_linear)

def create_human_and_assets():
    HumanService = __import__(f"{MPFB_BASE}.services.humanservice", fromlist=["HumanService"]).HumanService
    
    age = random.uniform(0.5, 1.0)
    gender = random.uniform(0.0, 1.0)
    height = 0.5 + (0.12 * gender)
    
    r1, r2, r3 = random.random(), random.random(), random.random()
    s = r1 + r2 + r3
    race_dir = {"african": r1/s, "asian": r2/s, "caucasian": r3/s}
    
    macro_details = {
        "gender": gender, "age": age, "muscle": random.random(), "weight": random.random(),
        "proportions": random.random(), "height": height, "race": race_dir,
        "cupsize": random.uniform(0.0, 0.1) if gender > 0.6 else random.uniform(0.3, 1.0),
        "firmness": random.random()
    }
    
    basemesh = HumanService.create_human(mask_helpers=True, detailed_helpers=True, scale=0.1, macro_detail_dict=macro_details)
    HumanService.add_builtin_rig(basemesh, "mixamo", import_weights=True)
    
    # 1. Colors
    s_color = sample_hair_color(age)
    ns_color = s_color if random.random() < 0.95 else sample_hair_color(age)
    skin_color = sample_skin_color()
    eye_color = sample_eye_color()
    
    # Force update to ensure materials are linked
    bpy.context.view_layer.update()
    
    # Apply Skin Color to basemesh (Direct Injection)
    apply_stylized_skin(basemesh, skin_color)
    
    # 2. Asset Picking
    hair_pool = list_mh_assets("hair") + ["none"] * 6
    brows_pool = list_mh_assets("eyebrows")
    lashes_pool = list_mh_assets("eyelashes")
    
    # Clothes (Focus on tops for SFY body views)
    all_clothes = list_mh_assets("clothes")
    tops_pool = [c for c in all_clothes if any(w in c.lower() for w in ["shirt", "top", "jacket", "suit", "jersey", "vest", "sweater"])]
    if not tops_pool: tops_pool = all_clothes
    
    hair = random.choice(hair_pool)
    brows = random.choice(brows_pool)
    lashes = random.choice(lashes_pool)
    clothes_top = random.choice(tops_pool) if random.random() < 0.9 else "none"
    
    # User Constraint: Beard (25% chance if masculine)
    if gender > 0.6 and random.random() < 0.25:
        beard = random.choice([b for b in BEARDS_LIST if b != "none"])
    else:
        beard = "none"
        
    # User Constraint: Glasses (10% chance)
    if random.random() < 0.1:
        glasses = random.choice([g for g in GLASSES_LIST if g != "none"])
    else:
        glasses = "none"
    
    # Apply
    scalp_obj = None
    face_objs = []
    
    # Always add Low Poly Eyes
    eye_path = get_asset_path("eyes", "low-poly")
    if eye_path:
        eye_obj = HumanService.add_mhclo_asset(eye_path, basemesh, asset_type="eyes")
        apply_eye_color(eye_obj, eye_color)
    
    for cat, name in [("hair", hair), ("eyebrows", brows), ("eyelashes", lashes), ("clothes", beard), ("clothes", glasses), ("clothes", clothes_top)]:
        path = get_asset_path(cat, name)
        if path:
            print(f"Adding {cat}: {name}")
            obj = HumanService.add_mhclo_asset(path, basemesh, asset_type=cat)
            if cat == "hair": scalp_obj = obj
            elif name in BEARDS_LIST or cat in ["eyebrows", "eyelashes"]: face_objs.append(obj)
                
    bpy.context.view_layer.update()
    if scalp_obj: apply_asset_color(scalp_obj, s_color)
    for o in face_objs: apply_asset_color(o, ns_color)
    
    # 4. Find Armature for Tracking
    armature = next((o for o in bpy.data.objects if o.type == 'ARMATURE'), None)

    # 5. Label Vector Generation (42 floats)
    label_vector = [
        gender, age, macro_details["muscle"], macro_details["weight"], 
        race_dir["african"], race_dir["asian"], race_dir["caucasian"], height, macro_details["proportions"]
    ]
    label_vector += get_semantic_vector(beard)
    label_vector += get_semantic_vector(hair)
    label_vector += get_semantic_vector(glasses)
    label_vector += get_semantic_vector(brows)
    label_vector += get_semantic_vector(lashes)
    label_vector += list(s_color)
    label_vector += list(ns_color)
    label_vector += list(skin_color)
    label_vector += list(eye_color)
    
    return armature, label_vector

def get_bone_location(armature, bone_name):
    if not armature: return (0,0,1.6)
    bone = armature.pose.bones.get(bone_name)
    if not bone:
        # Fallback for different naming conventions
        bone = next((b for b in armature.pose.bones if bone_name.lower() in b.name.lower()), None)
    if bone:
        # Get head location and offset by half length along the bone's Y axis (up)
        # In pose space, Y is along the bone
        local_center = mathutils.Vector((0, bone.length * 0.5, 0))
        return armature.matrix_world @ (bone.matrix @ local_center)
    return (0,0,1.6)

def setup_camera_and_render(output_path, armature, target_bone, base_dist, name):
    base_target = get_bone_location(armature, target_bone)
    
    # Mode-based framing logic
    if "selfie" in name:
        dist = random.uniform(0.75, 0.9)  # Balanced distance
        yaw = random.uniform(-0.5, 0.5)
        pitch = random.uniform(-0.1, 0.1)
        roll = random.uniform(-0.08, 0.08)
        # Use bone center directly without offset
        target_point = mathutils.Vector(base_target)
    else:  # body
        dist = 6.0
        yaw = random.uniform(-0.4, 0.4)
        pitch = random.uniform(-0.2, 0.1)
        roll = random.uniform(-0.1, 0.1)
        target_point = mathutils.Vector(base_target)

    # Spherical to Cartesian (Relative to target)
    x = dist * math.sin(yaw) * math.cos(pitch)
    y = -dist * math.cos(yaw) * math.cos(pitch)
    z = dist * math.sin(pitch)
    
    # Perturbations
    pos_noise = mathutils.Vector((random.uniform(-0.05, 0.05), random.uniform(-0.05, 0.05), random.uniform(-0.05, 0.05)))
    target_noise = mathutils.Vector((random.uniform(-0.02, 0.02), random.uniform(-0.02, 0.02), random.uniform(-0.02, 0.02)))
    
    cam_obj = bpy.data.objects.get("Camera")
    if not cam_obj:
        bpy.ops.object.camera_add()
        cam_obj = bpy.context.active_object
        
    cam_obj.location = target_point + mathutils.Vector((x, y, z)) + pos_noise
    
    # Final Track-To with Roll
    direction = (target_point + target_noise) - cam_obj.location
    rot_quat = direction.to_track_quat('-Z', 'Y')
    roll_quat = mathutils.Quaternion((0, 0, 1), roll)
    cam_obj.rotation_euler = (rot_quat @ roll_quat).to_euler()
    
    bpy.context.scene.camera = cam_obj
    cam_obj.data.lens = random.uniform(24, 85) # Wide range (24mm to 85mm)
    
    bpy.context.scene.render.filepath = os.path.join(output_path, f"{name}.png")
    bpy.ops.render.render(write_still=True)
    
    return [yaw, pitch, roll]

def setup_environment_lighting():
    # Dynamic HDRI pool from Poly Haven
    hdri_base = os.path.join(ROOT, "datagen/assets/hdris")
    
    if not os.path.exists(hdri_base) or not os.listdir(hdri_base):
        # FALLBACK: Use a standard 3-point light rig if no HDRIs are available
        print("No HDRIs found, using fallback 3-point lighting.")
        for name, pos, energy in [("Key", (3, -3, 3), 3000), ("Fill", (-3, -2, 2), 1000), ("Rim", (0, 4, 3), 1500)]:
            if name not in bpy.data.objects:
                bpy.ops.object.light_add(type='POINT', location=pos)
                bpy.data.objects["Light"].name = name
            bpy.data.objects[name].data.energy = energy
        return

    hdri_files = [f for f in os.listdir(hdri_base) if f.endswith(".exr")]
    selected_hdri = os.path.join(hdri_base, random.choice(hdri_files))
    
    # Setup World Nodes
    world = bpy.context.scene.world
    if not world:
        world = bpy.data.worlds.new("World")
        bpy.context.scene.world = world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    nodes.clear()
    
    node_env = nodes.new(type='ShaderNodeTexEnvironment')
    node_env.image = bpy.data.images.load(selected_hdri)
    
    node_map = nodes.new(type='ShaderNodeMapping')
    node_map.inputs['Rotation'].default_value[2] = random.uniform(0, 6.28) # Random Z rotation
    
    node_coord = nodes.new(type='ShaderNodeTexCoord')
    
    node_background = nodes.new(type='ShaderNodeBackground')
    node_background.inputs['Strength'].default_value = random.uniform(0.5, 2.0)
    
    node_output = nodes.new(type='ShaderNodeOutputWorld')
    
    links = world.node_tree.links
    links.new(node_coord.outputs['Generated'], node_map.inputs['Vector'])
    links.new(node_map.outputs['Vector'], node_env.inputs['Vector'])
    links.new(node_env.outputs['Color'], node_background.inputs['Color'])
    links.new(node_background.outputs['Background'], node_output.inputs['Surface'])
    
    # Add a subtle rim-light point to ensure silhouettes are clean
    if "RimLight" not in bpy.data.objects:
        bpy.ops.object.light_add(type='POINT', location=(4, 4, 2))
        bpy.data.objects["Light"].name = "RimLight"
    bpy.data.objects["RimLight"].data.energy = random.uniform(500, 2000)

def cleanup_scene():
    bpy.ops.object.select_all(action='DESELECT')
    for obj in bpy.data.objects:
        if obj.type in ['MESH', 'ARMATURE']: obj.select_set(True)
    bpy.ops.object.delete()
    for mesh in bpy.data.meshes: bpy.data.meshes.remove(mesh)
    for sk in bpy.data.shape_keys: bpy.data.shape_keys.remove(sk)
    for arm in bpy.data.armatures: bpy.data.armatures.remove(arm)

if __name__ == "__main__":
    out = "/tmp/renders/sweep_dino"
    os.makedirs(out, exist_ok=True)
    for i in range(10):
        cleanup_scene()
        setup_environment_lighting()
        armature, labels = create_human_and_assets()
        
        # Capture view angles (Yaw, Pitch, Roll) and add them to the labels
        s_angles = setup_camera_and_render(out, armature, "head", 0.7, f"sample_{i}_selfie")
        b_angles = setup_camera_and_render(out, armature, "hips", 6.0, f"sample_{i}_body")
        
        # Final label vector is the pure 36-float identity map
        # Camera poses are used for rendering but removed from semantic labels
        full_labels = labels 
        
        with open(os.path.join(out, f"sample_{i}_labels.json"), 'w') as f:
            json.dump({"vector": full_labels}, f)
    print(f"Batch generation complete. Renders and labels in {out}")
    
    # Auto-copy to final preview folder
    preview_path = "/tmp/final_prototype_renders"
    os.makedirs(preview_path, exist_ok=True)
    import shutil
    for f in os.listdir(out):
        shutil.copy(os.path.join(out, f), os.path.join(preview_path, f))
    print(f"Preview updated at {preview_path}")
