import bpy
import mathutils
import os
import sys
import json
import random

# Use the full extension namespace for imports
MPFB_BASE = "bl_ext.blender_org.mpfb"

def create_random_human(i):
    HumanService = __import__(f"{MPFB_BASE}.services.humanservice", fromlist=["HumanService"]).HumanService
    
    # 1. Macro randomization
    age = random.uniform(0.5, 1.0)
    gender = random.uniform(0.0, 1.0)
    
    r1 = random.uniform(0, 1)
    r2 = random.uniform(0, 1)
    r3 = random.uniform(0, 1)
    s = r1 + r2 + r3
    race_dir = {"african": r1/s, "asian": r2/s, "caucasian": r3/s}
    
    muscle = random.uniform(0, 1)
    weight = random.uniform(0, 1)
    proportions = random.uniform(0, 1)
    height = 0.5 
    
    if gender < 0.5:
        cupsize = random.uniform(0.0, 1.0)
    else:
        cupsize = random.uniform(0.5, 1.0)
    
    firmness = random.uniform(0.0, 1.0)
    
    macro_details = {
        "gender": gender,
        "age": age,
        "muscle": muscle,
        "weight": weight,
        "proportions": proportions,
        "height": height,
        "race": race_dir,
        "cupsize": cupsize,
        "firmness": firmness
    }
    
    print(f"[{i}] Creating human with gender={gender:.2f}, age={age:.2f}")
    
    basemesh = HumanService.create_human(
        mask_helpers=True,
        detailed_helpers=True,
        extra_vertex_groups=True,
        feet_on_ground=True,
        scale=0.1,
        macro_detail_dict=macro_details
    )
    
    return basemesh

def randomize_shape_keys(basemesh):
    import random
    blocks = basemesh.data.shape_keys.key_blocks
    
    # Subtle randomization of other targets
    for key in blocks:
        if key.name == "Basis" or key.name.startswith("$md"):
            continue
            
        skip_words = ["breast", "buttocks", "foot", "feet", "genital", "pelvis", "hand"]
        if any(w in key.name.lower() for w in skip_words):
            continue
            
        if random.random() < 0.05: # 5% chance
            key.value = random.uniform(0, 0.3)

    # Symmetry
    relevant_symmetry = ["cheek", "ear", "eye", "arm"]
    for key in blocks:
        if "left" in key.name.lower():
            if any(w in key.name.lower() for w in relevant_symmetry):
                right_name = key.name.lower().replace("left", "right")
                for k in blocks:
                    if k.name.lower() == right_name:
                        k.value = key.value
                        break
                    
def setup_camera_and_render(output_path, target_point, camera_offset, name):
    cam_obj = bpy.data.objects.get("Camera")
    if not cam_obj:
        bpy.ops.object.camera_add()
        cam_obj = bpy.context.active_object
        
    cam_obj.location = (target_point[0] + camera_offset[0], 
                        target_point[1] + camera_offset[1], 
                        target_point[2] + camera_offset[2])
    
    direction = mathutils.Vector(target_point) - cam_obj.location
    rot_quat = direction.to_track_quat('-Z', 'Y')
    cam_obj.rotation_euler = rot_quat.to_euler()
    
    bpy.context.scene.camera = cam_obj
    bpy.context.scene.render.filepath = os.path.join(output_path, f"{name}.png")
    bpy.ops.render.render(write_still=True)

def cleanup_scene():
    # Remove all meshes
    bpy.ops.object.select_all(action='DESELECT')
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            obj.select_set(True)
    bpy.ops.object.delete()
    
    # Also cleanup data
    for mesh in bpy.data.meshes:
        bpy.data.meshes.remove(mesh)
    for sk in bpy.data.shape_keys:
        bpy.data.shape_keys.remove(sk)

if __name__ == "__main__":
    try:
        HumanService = __import__(f"{MPFB_BASE}.services.humanservice", fromlist=["HumanService"]).HumanService
    except ImportError:
        import sys
        sys.path.append(os.path.expanduser("~/Library/Application Support/Blender/5.1/extensions/.user/blender_org/mpfb"))
        from mpfb.services.humanservice import HumanService

    output_dir = "/tmp/renders/sweep_10"
    os.makedirs(output_dir, exist_ok=True)
    
    # Lighting setup
    if "Light" in bpy.data.objects:
        bpy.data.objects["Light"].data.energy = 5000 # Brighter for background rendering
        bpy.data.objects["Light"].location = (2, -2, 4)

    for i in range(10):
        cleanup_scene()
        basemesh = create_random_human(i)
        randomize_shape_keys(basemesh)
        
        # Body Pose
        setup_camera_and_render(output_dir, (0, 0, 0.9), (0, -3.5, 0), f"sample_{i}_body")
        
        # Face Selfie
        setup_camera_and_render(output_dir, (0, 0, 1.65), (0, -0.6, 0), f"sample_{i}_face")
        
    print(f"Batch generation complete. Files in {output_dir}")
