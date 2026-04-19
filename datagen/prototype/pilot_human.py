import bpy
import mathutils
import os
import sys
import json
import random

# Add MPFB to path if necessary. We found it in the extensions directory.
# But it's already initialized by Blender anyway.

# Use the full extension namespace for imports
MPFB_BASE = "bl_ext.blender_org.mpfb"

def create_random_human():
    HumanService = __import__(f"{MPFB_BASE}.services.humanservice", fromlist=["HumanService"]).HumanService
    TargetService = __import__(f"{MPFB_BASE}.services.targetservice", fromlist=["TargetService"]).TargetService
    
    # 1. Macro randomization
    age = random.uniform(0.5, 1.0)
    gender = random.uniform(0.0, 1.0)
    
    # Race sums to 1.0
    r1 = random.uniform(0, 1)
    r2 = random.uniform(0, 1)
    r3 = random.uniform(0, 1)
    s = r1 + r2 + r3
    race_dir = {"african": r1/s, "asian": r2/s, "caucasian": r3/s}
    
    muscle = random.uniform(0, 1)
    weight = random.uniform(0, 1)
    proportions = random.uniform(0, 1)
    height = 0.5 # Frozen to 0.5
    
    # Breast constraints
    # user: "breast shape < 0.5 only when gender < 0.5"
    # gender 0.0 is female, 1.0 is male in MPFB? 
    # Let me check macro.json again: "low": "female", "high": "male" -> 0.0 is female.
    # So if gender >= 0.5 (male-ish), breast shape should be >= 0.5?
    # Wait, usually males have smaller breasts. Maybe the user meant the opposite?
    # "breast shape < 0.5 only when gender < 0.5" means if gender >= 0.5 then breast shape >= 0.5?
    # Let's follow the instruction literally:
    if gender < 0.5:
        cupsize = random.uniform(0.0, 1.0) # Can be any value? No, "only when" implies if gender >= 0.5 then cupsize >= 0.5.
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
    
    print(f"Creating human with macro: {json.dumps(macro_details, indent=2)}")
    
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
    TargetService = __import__(f"{MPFB_BASE}.services.targetservice", fromlist=["TargetService"]).TargetService
    
    # List all shape keys
    if not basemesh.data.shape_keys:
        return
    
    # Skip macro targets as they are already set
    # Macro targets in MPFB start with $md
    
    blocks = basemesh.data.shape_keys.key_blocks
    for key in blocks:
        if key.name == "Basis":
            continue
        if key.name.startswith("$md"):
            continue
            
        # USER: breast and buttocks sections are not touched.
        # feet, genitals, pelvis, hands are not touched.
        skip_words = ["breast", "buttocks", "foot", "feet", "genital", "pelvis", "hand"]
        if any(w in key.name.lower() for w in skip_words):
            continue
            
        # Randomize some other targets
        # Only randomize a small subset to avoid grotesque results for now
        # especially face related ones
        if random.random() < 0.1: # 10% chance to randomize a target
            key.value = random.uniform(0, 0.5) # subtle changes

    # USER: ensure symmetry
    # cheek bones, ears, eyes, arms
    # MPFB targets usually have -left/-right or .L/.R in their name
    for key in blocks:
        if "left" in key.name.lower():
            right_name = key.name.lower().replace("left", "right")
            # Find matching right key
            right_key = None
            for k in blocks:
                if k.name.lower() == right_name:
                    right_key = k
                    break
            
            if right_key:
                # User: "cheek bones symmetric", "ears symmetric", "eyes symmetric", "arms equal"
                relevant_symmetry = ["cheek", "ear", "eye", "arm"]
                if any(w in key.name.lower() for w in relevant_symmetry):
                    right_key.value = key.value
                    
def setup_camera_and_render(output_path, target_point, camera_offset, name):
    # Set up camera
    cam_obj = bpy.data.objects.get("Camera")
    if not cam_obj:
        bpy.ops.object.camera_add()
        cam_obj = bpy.context.active_object
        
    cam_obj.location = (target_point[0] + camera_offset[0], 
                        target_point[1] + camera_offset[1], 
                        target_point[2] + camera_offset[2])
    
    # Point camera to target
    direction = mathutils.Vector(target_point) - cam_obj.location
    rot_quat = direction.to_track_quat('-Z', 'Y')
    cam_obj.rotation_euler = rot_quat.to_euler()
    
    bpy.context.scene.camera = cam_obj
    bpy.context.scene.render.filepath = os.path.join(output_path, f"{name}.png")
    bpy.ops.render.render(write_still=True)

if __name__ == "__main__":
    try:
        HumanService = __import__(f"{MPFB_BASE}.services.humanservice", fromlist=["HumanService"]).HumanService
    except ImportError:
        # Fallback for older versions or different paths if needed
        import sys
        sys.path.append(os.path.expanduser("~/Library/Application Support/Blender/5.1/extensions/.user/blender_org/mpfb"))
        from mpfb.services.humanservice import HumanService

    basemesh = create_random_human()
    randomize_shape_keys(basemesh)
    
    # Quick fix for lighting if it's too dark
    if "Light" in bpy.data.objects:
        bpy.data.objects["Light"].data.energy = 1000
    
    # Find head location for selfie
    # Head joint is usually around (0, 0, 1.6) for scale 0.1? No, let's verify.
    # We can use the bounding box or specific vertices.
    # For a default human, z=1.5 to 1.8 is the head.
    
    output_dir = "/tmp/renders"
    os.makedirs(output_dir, exist_ok=True)
    
    # Full body pose (A-pose is default)
    setup_camera_and_render(output_dir, (0, 0, 0.9), (0, -4, 0), "body_pose")
    
    # Face selfie
    setup_camera_and_render(output_dir, (0, 0, 1.65), (0, -0.8, 0), "face_selfie")
    
    print(f"Renders saved to {output_dir}")
