import bpy
import mathutils
import os
import sys
import json
import random

# Add project modules to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from blender.asset_profile import get_asset_vector

MPFB_BASE = "bl_ext.blender_org.mpfb"
USER_DATA_PATH = "/Users/hrishik/Library/Application Support/Blender/5.1/extensions/.user/blender_org/mpfb/data"

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

def apply_asset_color(obj, color):
    if not obj or not hasattr(obj.data, "materials") or len(obj.data.materials) == 0:
        return
    mat = obj.data.materials[0]
    if not mat or not mat.use_nodes:
        return
    nodes = mat.node_tree.nodes
    principled = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if principled:
        base_color_input = principled.inputs.get("Base Color")
        if base_color_input:
            for link in base_color_input.links:
                mat.node_tree.links.remove(link)
            base_color_input.default_value = (color[0], color[1], color[2], 1.0)

def sample_hair_color():
    if random.random() < 0.9:
        # Natural colors
        naturals = [(0.02,0.02,0.02), (0.12,0.06,0.02), (0.3,0.15,0.05), (0.7,0.6,0.3), (0.5,0.15,0.05)]
        return random.choice(naturals)
    return (random.random(), random.random(), random.random())

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
        "cupsize": random.uniform(0.5, 1.0) if gender > 0.5 else random.random(),
        "firmness": random.random()
    }
    
    basemesh = HumanService.create_human(mask_helpers=True, detailed_helpers=True, scale=0.1, macro_detail_dict=macro_details)
    HumanService.add_builtin_rig(basemesh, "mixamo", import_weights=True)
    
    # 1. Colors
    s_color = sample_hair_color()
    ns_color = s_color if random.random() < 0.95 else sample_hair_color()
    
    # 2. Asset Picking
    hair_pool = list_mh_assets("hair") + ["none"] * 6 # ~10% baldness
    brows_pool = list_mh_assets("eyebrows")
    lashes_pool = list_mh_assets("eyelashes")
    
    hair = random.choice(hair_pool)
    brows = random.choice(brows_pool)
    lashes = random.choice(lashes_pool)
    beard = random.choice(BEARDS_LIST)
    glasses = random.choice(GLASSES_LIST)
    
    # Apply
    scalp_obj = None
    face_objs = []
    
    for cat, name in [("hair", hair), ("eyebrows", brows), ("eyelashes", lashes), ("clothes", beard), ("clothes", glasses)]:
        path = get_asset_path(cat, name)
        if path:
            print(f"Adding {cat}: {name}")
            obj = HumanService.add_mhclo_asset(path, basemesh, asset_type=cat)
            if cat == "hair": scalp_obj = obj
            elif name in BEARDS_LIST or cat in ["eyebrows", "eyelashes"]: face_objs.append(obj)
                
    if scalp_obj: apply_asset_color(scalp_obj, s_color)
    for o in face_objs: apply_asset_color(o, ns_color)
    
    # 4. Find Armature for Tracking
    armature = next((o for o in bpy.data.objects if o.type == 'ARMATURE'), None)

    # 5. Label Vector Generation (Fixed Length)
    # [Sliders(9), Beard(3), Hair(3), Glasses(3), Colors(6)] = 24 floats
    label_vector = [
        gender, age, macro_details["muscle"], macro_details["weight"], 
        race_dir["african"], race_dir["asian"], race_dir["caucasian"], height, macro_details["proportions"]
    ]
    label_vector += get_asset_vector("beard", beard)
    label_vector += get_asset_vector("hair", hair)
    label_vector += get_asset_vector("glasses", glasses)
    label_vector += list(s_color)
    label_vector += list(ns_color)
    
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

def setup_camera_and_render(output_path, armature, target_bone, camera_offset, name):
    base_target = get_bone_location(armature, target_bone)
    
    # User Request: Track only the Z of the head/bone, X and Y should be 0 (center)
    target_point = mathutils.Vector((0.0, 0.0, base_target[2]))
    
    # Random perturbations for "imperfect" selfies
    # Scale perturbation: ~2-5cm shift in camera location
    pos_noise = mathutils.Vector((random.uniform(-0.05, 0.05), 
                                  random.uniform(-0.05, 0.05), 
                                  random.uniform(-0.05, 0.05)))
                                  
    # Target noise: ~1-2cm shift in what we are looking at
    target_noise = mathutils.Vector((random.uniform(-0.02, 0.02),
                                     random.uniform(-0.02, 0.02),
                                     random.uniform(-0.02, 0.02)))
    
    cam_obj = bpy.data.objects.get("Camera")
    if not cam_obj:
        bpy.ops.object.camera_add()
        cam_obj = bpy.context.active_object
    
    # Final location = base head Z + standard offset + noise
    cam_obj.location = target_point + mathutils.Vector(camera_offset) + pos_noise
    
    # Final Look-At = head target + target noise
    direction = (target_point + target_noise) - cam_obj.location
    cam_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    
    bpy.context.scene.camera = cam_obj
    # Randomize focal length slightly (e.g. 45mm to 55mm) to simulate different phones
    cam_obj.data.lens = random.uniform(45, 55)
    
    bpy.context.scene.render.filepath = os.path.join(output_path, f"{name}.png")
    bpy.ops.render.render(write_still=True)

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
        if "Light" not in bpy.data.objects:
            bpy.ops.object.light_add(type='POINT', location=(2,-2,4))
            bpy.data.objects["Light"].data.energy = 3000
        armature, labels = create_human_and_assets()
        
        # Selfie tracks Head, Body tracks Hips/Spine
        setup_camera_and_render(out, armature, "head", (0,-0.7,0), f"sample_{i}_selfie")
        setup_camera_and_render(out, armature, "hips", (0,-3.5,0), f"sample_{i}_body")
        
        with open(os.path.join(out, f"sample_{i}_labels.json"), 'w') as f:
            json.dump({"vector": labels}, f)
    print(f"Batch generation complete. Renders and labels in {out}")
