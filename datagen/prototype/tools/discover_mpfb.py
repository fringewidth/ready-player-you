import bpy
import mpfb
import json

def list_operators():
    ops = []
    for category in dir(bpy.ops):
        cat_obj = getattr(bpy.ops, category)
        for op in dir(cat_obj):
            ops.append(f"{category}.{op}")
    return ops

def list_mpfb_api():
    methods = [m for m in dir(mpfb) if not m.startswith("__")]
    return methods

if __name__ == "__main__":
    print("---MPFB_START---")
    try:
        print(f"MPFB version: {mpfb.__version__ if hasattr(mpfb, '__version__') else 'unknown'}")
    except:
        pass
    
    # List operators that might be relevant
    relevant_ops = [op for op in list_operators() if "mpfb" in op.lower() or "human" in op.lower()]
    print(f"Relevant operators: {json.dumps(relevant_ops, indent=2)}")
    
    # Try to find create human operator
    # Common MPFB operator is mpfb.new_human or similar
    
    print("---MPFB_END---")
