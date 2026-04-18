import bpy
import json

def get_properties():
    data = {
        "objects": [],
        "meshes": [],
        "armatures": [],
        "materials": [],
    }
    
    for obj in bpy.data.objects:
        obj_data = {
            "name": obj.name,
            "type": obj.type,
            "location": list(obj.location),
            "custom_properties": list(obj.keys()),
        }
        data["objects"].append(obj_data)
        
        if obj.type == 'ARMATURE':
            armature_data = {
                "name": obj.name,
                "bones": [bone.name for bone in obj.data.bones]
            }
            data["armatures"].append(armature_data)
            
    return data

if __name__ == "__main__":
    # Check if a blend file is loaded
    print(f"Loaded blend file: {bpy.data.filepath}")
    
    props = get_properties()
    print("---METADATA_START---")
    print(json.dumps(props, indent=2))
    print("---METADATA_END---")
