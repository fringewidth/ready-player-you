import bpy
import os
import sys
import json
import random
import math
import uuid

# 1. Setup Environment
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
if ROOT not in sys.path:
    sys.path.append(ROOT)

# External digitized metadata
METADATA_PATH = os.path.join(ROOT, "datagen", "asset_metadata.json")
with open(METADATA_PATH, 'r') as f:
    ASSET_METADATA = json.load(f)

MPFB_BASE = "bl_ext.blender_org.mpfb"

# --- Biological Palettes (1:1 with Gold Prototype) ---

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
    t = random.random() * (len(SKIN_PALETTE) - 1)
    idx = int(t)
    frac = t - idx
    p1, p2 = SKIN_PALETTE[idx], SKIN_PALETTE[min(idx + 1, len(SKIN_PALETTE) - 1)]
    res_srgb = [p1[i] + (p2[i] - p1[i]) * frac for i in range(3)]
    return [( (c / 255.0) ** 2.2 ) for c in res_srgb]

def sample_hair_color(age):
    naturals = [
        (0.02, 0.02, 0.02), (0.05, 0.03, 0.01), (0.12, 0.06, 0.02), (0.3, 0.15, 0.05),
        (0.45, 0.25, 0.1), (0.5, 0.15, 0.05), (0.7, 0.6, 0.3), (0.85, 0.75, 0.45), (0.95, 0.9, 0.8)
    ]
    if age > 0.8: 
        naturals += [(0.7, 0.7, 0.7), (0.95, 0.95, 0.95)]
    if random.random() < 0.1: 
        return (random.random(), random.random(), random.random())
    return random.choice(naturals)

def sample_eye_color():
    palette = [(0.02, 0.05, 0.2), (0.05, 0.15, 0.05), (0.3, 0.15, 0.05), (0.08, 0.04, 0.02), (0.1, 0.1, 0.15)]
    return random.choice(palette)

# --- Material & Style Logic ---

def get_semantic_vector(name):
    if not name or name.lower() == "none": return [0.0, 0.0, 0.0]
    return ASSET_METADATA.get(name, [0.0, 0.0, 0.0])

def apply_stylized_skin(obj, color):
    if not obj: return
    mat = bpy.data.materials.new(name="StylizedSkin")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = (color[0], color[1], color[2], 1.0)
        bsdf.inputs['Roughness'].default_value = 0.5
    
    # Force slot creation if empty
    if not obj.data.materials:
        obj.data.materials.append(mat)
    else:
        obj.data.materials[0] = mat

def apply_eye_color(obj, color):
    if not obj: return
    for slot in obj.material_slots:
        mat = slot.material
        if not mat or not mat.use_nodes: continue
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        bsdf = nodes.get("Principled BSDF")
        if not bsdf or 'Base Color' not in bsdf.inputs or not bsdf.inputs['Base Color'].is_linked: continue
        
        source = bsdf.inputs['Base Color'].links[0].from_socket
        ramp = nodes.new(type='ShaderNodeValToRGB')
        ramp.color_ramp.elements[0].color = (color[0], color[1], color[2], 1.0)
        ramp.color_ramp.elements[1].position = 0.6
        ramp.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)
        links.new(source, ramp.inputs[0])
        links.new(ramp.outputs[0], bsdf.inputs['Base Color'])

# --- Human Generation Logic ---

def setup_environment_lighting():
    hdri_base = os.path.join(ROOT, "datagen/assets/hdris")
    if not os.path.exists(hdri_base): return
    
    hdri_files = [f for f in os.listdir(hdri_base) if f.endswith(".exr")]
    if not hdri_files: return
    
    selected_hdri = os.path.join(hdri_base, random.choice(hdri_files))
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
    node_map.inputs['Rotation'].default_value[2] = random.uniform(0, 6.28)
    
    node_coord = nodes.new(type='ShaderNodeTexCoord')
    node_background = nodes.new(type='ShaderNodeBackground')
    node_background.inputs['Strength'].default_value = random.uniform(0.5, 1.8)
    
    node_output = nodes.new(type='ShaderNodeOutputWorld')
    links = world.node_tree.links
    links.new(node_coord.outputs['Generated'], node_map.inputs['Vector'])
    links.new(node_map.outputs['Vector'], node_env.inputs['Vector'])
    links.new(node_env.outputs['Color'], node_background.inputs['Color'])
    links.new(node_background.outputs['Background'], node_output.inputs['Surface'])
    
    # Rim light
    if "Rim" not in bpy.data.objects:
        bpy.ops.object.light_add(type='POINT', location=(4, 4, 3))
        bpy.context.active_object.name = "Rim"
    bpy.data.objects["Rim"].data.energy = random.uniform(500, 2000)

def generate_one_avatar(output_dir, worker_id):
    from bl_ext.blender_org.mpfb.services.humanservice import HumanService
    from bl_ext.blender_org.mpfb.services.assetservice import AssetService
    
    def set_mat_color(mat, color):
        if not mat or not mat.use_nodes: return
        nodes = mat.node_tree.nodes
        shader = next((n for n in nodes if n.type in ['BSDF_PRINCIPLED', 'BSDF_HAIR_PRINCIPLED', 'BSDF_DIFFUSE']), None)
        if shader:
            inp = shader.inputs.get("Base Color") or shader.inputs.get("Color")
            if inp: inp.default_value = (color[0], color[1], color[2], 1.0)

    # Simple Local Helper for path resolution
    def get_mpfb_path(subdir, name):
        if not name or name == "none": return None
        if "." not in name: name_ext = name + ".mhclo"
        else: name_ext = name
        return AssetService.find_asset_absolute_path(name_ext, asset_subdir=subdir)

    # 1. Cleanup Scene
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    
    # 2. Setup Lighting
    setup_environment_lighting()
    bpy.context.scene.render.film_transparent = False
    
    # 3. Phenotype Macros
    age = random.uniform(0.5, 1.0)
    gender = random.uniform(0.0, 1.0)
    r = [random.random() for _ in range(3)]
    s = sum(r)
    race = {"african": r[0]/s, "asian": r[1]/s, "caucasian": r[2]/s}
    details = {
        "gender": gender, "age": age, "muscle": random.random(), "weight": random.random(),
        "proportions": random.random(), "height": 0.5 + (0.1*gender), "race": race,
        "cupsize": random.uniform(0.0, 0.2) if gender > 0.6 else random.uniform(0.4, 1.0),
        "firmness": random.random()
    }
    
    human = HumanService.create_human(scale=0.1, macro_detail_dict=details)
    armature = HumanService.add_builtin_rig(human, "mixamo", import_weights=True)
    
    # 4. Micro-variation (ShapeKeys)
    if human.data.shape_keys:
        blocks = human.data.shape_keys.key_blocks
        for key in blocks:
            if key.name == "Basis" or key.name.startswith("$md") or "genital" in key.name.lower(): continue
            if random.random() < 0.05: key.value = random.uniform(0, 0.3)

    # 5. Colors
    hair_color = sample_hair_color(age)
    beard_color = hair_color if random.random() < 0.95 else sample_hair_color(age)
    skin_color = sample_skin_color()
    eye_color = sample_eye_color()
    
    # 6. Apply Materials
    apply_stylized_skin(human, skin_color)
    
    eye_path = get_mpfb_path("eyes", "low-poly")
    if eye_path:
        eyes = HumanService.add_mhclo_asset(eye_path, human, asset_type="eyes")
        apply_eye_color(eyes, eye_color)

    # 7. Asset Logic (Parity with Prototype)
    all_keys = list(ASSET_METADATA.keys())
    
    hair_name = random.choice([k for k in all_keys if "hair" in k.lower()] + ["none"])
    brow_name = random.choice([k for k in all_keys if "eyebrow" in k.lower()] or ["none"])
    lash_name = random.choice([k for k in all_keys if "eyelashes" in k.lower()] or ["none"])
    
    beard_name = random.choice([k for k in all_keys if "beard" in k.lower()] or ["none"]) if gender > 0.6 and random.random() < 0.25 else "none"
    glasses_name = random.choice([k for k in all_keys if "glass" in k.lower()] or ["none"]) if random.random() < 0.15 else "none"
        
    # Clothes (Advanced Wardrobe Logic)
    clothes_dir = os.path.expanduser("~/Library/Application Support/Blender/5.1/extensions/.user/blender_org/mpfb/data/clothes")
    all_clothes = os.listdir(clothes_dir) if os.path.exists(clothes_dir) else []
    
    full_body_pool = [c for c in all_clothes if "suit" in c.lower() or "dress" in c.lower()]
    tops_pool = [c for c in all_clothes if any(w in c.lower() for w in ["shirt", "top", "jacket", "hoodie", "sweater", "polo", "bodice", "camisole", "tank"])]
    bottoms_pool = [c for c in all_clothes if any(w in c.lower() for w in ["pant", "skirt", "trouser", "bottom", "short", "legging", "harem"])]
    shoes_pool = [c for c in all_clothes if "shoes" in c.lower()]
    
    cl_to_add = []
    
    # 1. Base Layer (Clothes)
    if random.random() < 0.3 and full_body_pool:
        cl_to_add.append(("clothes", random.choice(full_body_pool)))
    else:
        if tops_pool: cl_to_add.append(("clothes", random.choice(tops_pool)))
        if bottoms_pool: cl_to_add.append(("clothes", random.choice(bottoms_pool)))
    
    # 2. Footwear
    if shoes_pool: cl_to_add.append(("clothes", random.choice(shoes_pool)))
    
    # 3. Identity Assets
    cl_to_add += [("hair", hair_name), ("eyebrows", brow_name), ("eyelashes", lash_name), ("clothes", beard_name), ("clothes", glasses_name)]

    # Add All Assets
    hair_obj = None
    face_assets = []
    
    for cat, name in cl_to_add:
        path = get_mpfb_path(cat, name)
        if path:
            obj = HumanService.add_mhclo_asset(path, human, asset_type=cat)
            if cat == "hair": hair_obj = obj
            elif cat in ["eyebrows", "eyelashes"] or (name and "beard" in name.lower()): face_assets.append(obj)

    # 8. Apply Asset Colors (Independence restored)
    if hair_obj:
        for slot in hair_obj.material_slots: set_mat_color(slot.material, hair_color)
    for asset in face_assets:
        if asset:
            # Brows and Lashes use hair_color, Beards use beard_color
            color_to_apply = beard_color if (asset.name and "beard" in asset.name.lower()) else hair_color
            for slot in asset.material_slots: set_mat_color(slot.material, color_to_apply)

    # 9. Label Generation (36 floats)
    label_vector = [gender, age, details["muscle"], details["weight"]] + list(race.values()) + [details["height"], details["proportions"]]
    label_vector += get_semantic_vector(beard_name)
    label_vector += get_semantic_vector(hair_name)
    label_vector += get_semantic_vector(glasses_name)
    label_vector += get_semantic_vector(brow_name)
    label_vector += get_semantic_vector(lash_name)
    label_vector += list(hair_color) + list(beard_color) + list(skin_color) + list(eye_color)

    while len(label_vector) < 36: label_vector.append(0.0)

    # 10. Render Sequence
    sample_id = f"w{worker_id}_{uuid.uuid4().hex[:8]}"
    
    def setup_cam(target_bone, dist):
        cam = bpy.data.objects.get("Camera")
        if not cam:
            bpy.ops.object.camera_add()
            cam = bpy.context.active_object
        
        target_pos = armature.matrix_world @ armature.pose.bones[target_bone].head
        yaw = random.uniform(-0.4, 0.4)
        pitch = random.uniform(-0.1, 0.1)
        
        cam.location = (target_pos.x + dist * math.sin(yaw), target_pos.y - dist * math.cos(yaw), target_pos.z + dist * math.sin(pitch))
        direction = target_pos - cam.location
        rot_quat = direction.to_track_quat('-Z', 'Y')
        cam.rotation_euler = rot_quat.to_euler()
        
        cam.data.lens = random.uniform(24, 85) # Focal Length Jitter
        bpy.context.scene.camera = cam

    # Selfie
    setup_cam("mixamorig:Head", 0.8)
    temp_selfie = os.path.join(output_dir, f"{sample_id}_selfie.png.tmp")
    bpy.context.scene.render.use_file_extension = False
    bpy.context.scene.render.filepath = temp_selfie
    bpy.ops.render.render(write_still=True)
    os.rename(temp_selfie, temp_selfie.replace(".tmp", ""))

    # Body
    setup_cam("mixamorig:Hips", 5.0)
    temp_body = os.path.join(output_dir, f"{sample_id}_body.png.tmp")
    bpy.context.scene.render.filepath = temp_body
    bpy.ops.render.render(write_still=True)
    os.rename(temp_body, temp_body.replace(".tmp", ""))
    
    # Final label write
    with open(os.path.join(output_dir, f"{sample_id}.json"), 'w') as f:
        json.dump({"vector": label_vector}, f)

if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:]
    out_dir = args[0]
    quota = int(args[1])
    worker_idx = args[2]
    
    for _ in range(quota):
        generate_one_avatar(out_dir, worker_idx)
    
    bpy.ops.wm.quit_blender()
