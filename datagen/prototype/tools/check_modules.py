import sys
import bpy

print("---SYS_MODULES_START---")
for name in sorted(sys.modules.keys()):
    if "mpfb" in name.lower():
        print(name)
print("---SYS_MODULES_END---")
