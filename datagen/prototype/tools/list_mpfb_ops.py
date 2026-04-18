import bpy
import json

def list_mpfb_operators():
    ops = []
    if hasattr(bpy.ops, "mpfb"):
        cat_obj = bpy.ops.mpfb
        for op in dir(cat_obj):
            if not op.startswith("_"):
                ops.append(f"mpfb.{op}")
    return ops

if __name__ == "__main__":
    print("---MPFB_OPS_START---")
    ops = list_mpfb_operators()
    print(json.dumps(ops, indent=2))
    print("---MPFB_OPS_END---")
