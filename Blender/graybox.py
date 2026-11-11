"""Graybox-ul camerei Storypinner: doar cutii, cilindri, conuri si sfere, la scara reala (metri).

blender -b -P Blender/graybox.py
  -> Blender/graybox.blend      camera mobilata + kit-ul de modele pe un rand
  -> Blender/room.blend         doar camera mobilata (instante ale modelelor din kit)
  -> Unity/Assets/Graybox/      Graybox.fbx, Models/*.fbx, RoomShell.fbx, layout.json

Axe Blender: X = de la stanga la dreapta, Y = spre peretele cu fereastra (nord), Z = sus.
Dimensiunile camerei sunt estimate; se schimba din constantele de mai jos.

Varianta night mode: camera 8.0 x 6.5 x 3.4 m, aproape intunecata, in albastru
inchis: fereastra deschisa spre un cer de noapte cu luna si stele, perdele, covor,
canapea, birou cu monitor si lampa, veioza, plante, o ghirlanda de luminite si benzi
LED albastre pe sub tavan, sub pat si in spatele monitorului.
"""
import json
import math
import os
import random

import bpy

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLEND = os.path.join(ROOT, "Blender", "graybox.blend")
ROOM_BLEND = os.path.join(ROOT, "Blender", "room.blend")
FBX = os.path.join(ROOT, "Unity", "Assets", "Graybox", "Graybox.fbx")

ROOM_W, ROOM_D, ROOM_H = 8.0, 6.5, 3.4  # x, y, z
WALL = 0.1
WIN_X0, WIN_X1, WIN_Z0, WIN_Z1 = 2.5, 5.5, 0.9, 2.7  # golul ferestrei din peretele de nord
DESK_X = (WIN_X0 + WIN_X1) / 2  # biroul sta sub fereastra
RUG = (4.4, 3.25)  # centrul covorului si al zonei libere

# night mode: albastru inchis peste tot, cardurile si firele raman deschise / luminoase
# ca sa se citeasca in intuneric. Aceleasi culori (si emisia) sunt in GrayboxSceneBuilder.cs.
COLORS = {
    "Wall": (0.05, 0.07, 0.15),
    "Floor": (0.03, 0.04, 0.09),
    "Furniture": (0.09, 0.11, 0.20),
    "Wood": (0.10, 0.09, 0.17),
    "Fabric": (0.08, 0.09, 0.26),
    "Trim": (0.14, 0.18, 0.32),
    "Neon": (0.20, 0.42, 1.00),
    "Plant": (0.08, 0.24, 0.26),
    "Sky": (0.03, 0.06, 0.18),
    "Moon": (0.85, 0.90, 1.00),
    "Glow": (1.00, 0.74, 0.45),
    "Screen": (0.22, 0.42, 0.85),
    "Cover": (0.20, 0.32, 0.56),
    "Card": (0.86, 0.90, 0.98),
    "Accent": (0.30, 0.75, 1.00),
    "Ghost": (0.55, 0.70, 1.00),
    "UI": (0.08, 0.10, 0.20),
    "Marker": (0.25, 0.85, 0.75),
}
EMISSION = {"Neon": 6.0, "Sky": 0.3, "Moon": 4.0, "Glow": 5.0, "Screen": 1.5, "Accent": 2.0, "Ghost": 0.5, "Card": 0.15, "Marker": 0.5}


def mat(name):
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
        m.diffuse_color = (*COLORS[name], 1.0)
        m.use_nodes = True
        bsdf = m.node_tree.nodes["Principled BSDF"]
        bsdf.inputs["Base Color"].default_value = (*COLORS[name], 1.0)
        if name in EMISSION:
            bsdf.inputs["Emission Color"].default_value = (*COLORS[name], 1.0)
            bsdf.inputs["Emission Strength"].default_value = EMISSION[name]
    return m


def collection(name):
    c = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(c)
    return c


def finish(obj, name, material, coll):
    obj.name = name
    obj.data.name = name
    obj.data.materials.append(mat(material))
    for c in obj.users_collection:
        c.objects.unlink(obj)
    coll.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    obj.select_set(False)
    return obj


def box(name, size, center, material, coll, rot_z=0.0):
    """Cutie cu marimea (x, y, z) in metri si centrul dat."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=center, rotation=(0, 0, rot_z))
    bpy.context.object.scale = size
    return finish(bpy.context.object, name, material, coll)


def floor_box(name, x0, y0, w, d, h, material, coll, z0=0.0):
    """Cutie pusa pe podea (sau la z0), data prin coltul de jos-stanga si marime."""
    return box(name, (w, d, h), (x0 + w / 2, y0 + d / 2, z0 + h / 2), material, coll)


def sphere(name, r, center, material, coll, segments=12, rings=8):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=center, segments=segments, ring_count=rings)
    return finish(bpy.context.object, name, material, coll)


def cylinder(name, r, depth, center, material, coll, vertices=24):
    """Cilindru vertical (axa Z) cu centrul dat."""
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=depth, vertices=vertices, location=center)
    return finish(bpy.context.object, name, material, coll)


def cone(name, r1, r2, depth, center, material, coll, vertices=24):
    """Trunchi de con vertical: r1 jos, r2 sus (abajurul lampii)."""
    bpy.ops.mesh.primitive_cone_add(radius1=r1, radius2=r2, depth=depth, vertices=vertices, location=center)
    return finish(bpy.context.object, name, material, coll)


def join(name, parts):
    """Lipeste mai multe bucati intr-un singur obiect (originea ramane a primei bucati)."""
    bpy.ops.object.select_all(action="DESELECT")
    for p in parts:
        p.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    if len(parts) > 1:
        bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    obj.name = obj.data.name = name
    obj.select_set(False)
    return obj


def wire(name, a, b, coll, r=0.002, material="Accent"):
    """Firul dintre doua puncte: un cilindru subtire intre a si b."""
    dx, dy, dz = (b[i] - a[i] for i in range(3))
    length = math.sqrt(dx * dx + dy * dy + dz * dz)
    mid = tuple((a[i] + b[i]) / 2 for i in range(3))
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=length, vertices=8, location=mid)
    o = bpy.context.object
    o.rotation_euler = (0, math.acos(dz / length), math.atan2(dy, dx))
    return finish(o, name, material, coll)


def build_shell():
    """Carcasa camerei si decorul fix (tot ce nu e model separat in Unity) -> colectia Room.

    In Unity, obiectele Sky_* nu arunca umbre (ca lumina lunii sa intre pe fereastra),
    iar luminile se pun dupa DeskLamp_Bulb, NightLight_Bulb, Sky_Moon si Rug.
    """
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system = "METRIC"
    room = collection("Room")

    # podea, tavan, pereti (cu grosime, in afara volumului interior)
    floor_box("Floor", 0, 0, ROOM_W, ROOM_D, WALL, "Floor", room, z0=-WALL)
    floor_box("Ceiling", 0, 0, ROOM_W, ROOM_D, WALL, "Wall", room, z0=ROOM_H)
    floor_box("Wall_South", -WALL, -WALL, ROOM_W + 2 * WALL, WALL, ROOM_H, "Wall", room)
    floor_box("Wall_West", -WALL, 0, WALL, ROOM_D, ROOM_H, "Wall", room)
    floor_box("Wall_East", ROOM_W, 0, WALL, ROOM_D, ROOM_H, "Wall", room)
    # peretele de nord are un gol adevarat pentru fereastra: 4 bucati in jurul lui
    floor_box("Wall_North_Left", -WALL, ROOM_D, WIN_X0 + WALL, WALL, ROOM_H, "Wall", room)
    floor_box("Wall_North_Right", WIN_X1, ROOM_D, ROOM_W + WALL - WIN_X1, WALL, ROOM_H, "Wall", room)
    floor_box("Wall_North_Below", WIN_X0, ROOM_D, WIN_X1 - WIN_X0, WALL, WIN_Z0, "Wall", room)
    floor_box("Wall_North_Above", WIN_X0, ROOM_D, WIN_X1 - WIN_X0, WALL, ROOM_H - WIN_Z1, "Wall", room, z0=WIN_Z1)

    # plinte de jur imprejur (o linie mai deschisa care contureaza podeaua in intuneric)
    t, h = 0.02, 0.08
    floor_box("Baseboard_S", 0, 0, ROOM_W, t, h, "Trim", room)
    floor_box("Baseboard_W", 0, 0, t, ROOM_D, h, "Trim", room)
    floor_box("Baseboard_E", ROOM_W - t, 0, t, ROOM_D, h, "Trim", room)
    floor_box("Baseboard_N", 0, ROOM_D - t, ROOM_W, t, h, "Trim", room)

    # rama ferestrei, crucea din mijloc si pervazul
    f, d = 0.06, WALL + 0.06
    yc = ROOM_D + WALL / 2 - 0.03
    xm, zm = (WIN_X0 + WIN_X1) / 2, (WIN_Z0 + WIN_Z1) / 2
    join("Window_Frame", [
        box("wf", (WIN_X1 - WIN_X0 + 2 * f, d, f), (xm, yc, WIN_Z1 + f / 2), "Trim", room),
        box("wf", (WIN_X1 - WIN_X0 + 2 * f, d, f), (xm, yc, WIN_Z0 - f / 2), "Trim", room),
        box("wf", (f, d, WIN_Z1 - WIN_Z0), (WIN_X0 - f / 2, yc, zm), "Trim", room),
        box("wf", (f, d, WIN_Z1 - WIN_Z0), (WIN_X1 + f / 2, yc, zm), "Trim", room),
        box("wf", (0.04, 0.04, WIN_Z1 - WIN_Z0), (xm, ROOM_D + WALL / 2, zm), "Trim", room),
        box("wf", (WIN_X1 - WIN_X0, 0.04, 0.04), (xm, ROOM_D + WALL / 2, zm + 0.1), "Trim", room),
    ])
    floor_box("Window_Sill", WIN_X0 - 0.15, ROOM_D - 0.14, WIN_X1 - WIN_X0 + 0.3, 0.16, 0.04, "Trim", room,
              z0=WIN_Z0 - 0.06)

    # perdele de o parte si de alta a ferestrei, pe o bara
    cy = ROOM_D - 0.1
    floor_box("Curtain_L", WIN_X0 - 0.5, cy - 0.04, 0.42, 0.08, WIN_Z1 + 0.25 - 0.3, "Fabric", room, z0=0.3)
    floor_box("Curtain_R", WIN_X1 + 0.08, cy - 0.04, 0.42, 0.08, WIN_Z1 + 0.25 - 0.3, "Fabric", room, z0=0.3)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.015, depth=WIN_X1 - WIN_X0 + 1.2, vertices=12,
                                        location=(xm, cy, WIN_Z1 + 0.28), rotation=(0, math.pi / 2, 0))
    finish(bpy.context.object, "Curtain_Rod", "Trim", room)

    # afara: un panou de cer, luna si stele (doar pentru ce se vede pe fereastra)
    sky_y = ROOM_D + 4.0
    floor_box("Sky_Backdrop", -4.0, sky_y, ROOM_W + 8.0, 0.1, 9.0, "Sky", room, z0=-2.0)
    moon = (xm + 0.9, sky_y - 0.4, 2.6)
    sphere("Sky_Moon", 0.36, moon, "Moon", room, segments=24, rings=16)
    rng = random.Random(7)
    stars = []
    for _ in range(70):
        x, z = rng.uniform(-3.5, ROOM_W + 3.5), rng.uniform(0.2, 6.5)
        if (x - moon[0]) ** 2 + (z - moon[2]) ** 2 < 0.6:  # nu peste luna
            continue
        stars.append(sphere("st", rng.uniform(0.012, 0.035), (x, sky_y - 0.1, z), "Moon", room, segments=6, rings=4))
    join("Sky_Stars", stars)

    # ghirlanda de luminite deasupra ferestrei: becuri pe un snur care atarna
    n, x0, x1, top, sag = 30, 0.5, ROOM_W - 0.5, ROOM_H - 0.18, 0.3
    pts = []
    for i in range(n):
        u = i / (n - 1)
        pts.append((x0 + (x1 - x0) * u, ROOM_D - 0.04, top - sag * 4 * u * (1 - u)))
    join("StringLights_Bulbs", [sphere("bl", 0.022, (x, y, z - 0.03), "Moon", room, segments=8, rings=6)
                                for x, y, z in pts])
    join("StringLights_Cord", [wire("cd", pts[i], pts[i + 1], room, r=0.003, material="UI") for i in range(n - 1)])

    # usa pe peretele de sud, cu clanta
    floor_box("Door", 6.6, 0, 0.9, 0.03, 2.1, "Wood", room)
    floor_box("Door_Frame_Top", 6.54, 0, 1.02, 0.05, 0.06, "Trim", room, z0=2.1)
    floor_box("Door_Handle", 7.35, 0.03, 0.12, 0.04, 0.025, "Trim", room, z0=1.0)

    # benzi LED albastre: de jur imprejurul tavanului (cove), lumina vine doar din ele si din luna
    led, zl = 0.025, ROOM_H - 0.06
    join("Neon_Cove", [
        floor_box("nc", 0.04, 0.04, ROOM_W - 0.08, led, led, "Neon", room, z0=zl),
        floor_box("nc", 0.04, ROOM_D - 0.04 - led, ROOM_W - 0.08, led, led, "Neon", room, z0=zl),
        floor_box("nc", 0.04, 0.04, led, ROOM_D - 0.08, led, "Neon", room, z0=zl),
        floor_box("nc", ROOM_W - 0.04 - led, 0.04, led, ROOM_D - 0.08, led, "Neon", room, z0=zl),
    ])

    # covorul rotund din mijloc si pozitia de start pe el
    cylinder("Rug_Border", 1.66, 0.006, (*RUG, 0.003), "Trim", room, vertices=64)
    cylinder("Rug", 1.6, 0.01, (*RUG, 0.005), "Fabric", room, vertices=64)
    cylinder("PlayerStart", 0.3, 0.004, (RUG[0], RUG[1] - 0.25, 0.012), "Marker", room)

    # canapea joasa pe peretele de sud, cu fata spre covor, si o masuta
    sx0 = 3.2
    floor_box("Sofa_Base", sx0, 0.05, 2.2, 0.85, 0.4, "Fabric", room)
    floor_box("Sofa_Back", sx0, 0.05, 2.2, 0.22, 0.85, "Fabric", room)
    floor_box("Sofa_Arm_L", sx0 - 0.18, 0.05, 0.18, 0.85, 0.6, "Fabric", room)
    floor_box("Sofa_Arm_R", sx0 + 2.2, 0.05, 0.18, 0.85, 0.6, "Fabric", room)
    for i in range(3):
        floor_box(f"Sofa_Cushion_{i + 1}", sx0 + 0.05 + 0.72 * i, 0.3, 0.66, 0.55, 0.1, "Furniture", room, z0=0.4)
    floor_box("Sofa_LED", sx0 - 0.1, 0.9, 2.4, 0.02, 0.02, "Neon", room, z0=0.02)
    floor_box("CoffeeTable", sx0 + 0.6, 1.2, 1.0, 0.5, 0.04, "Wood", room, z0=0.36)
    floor_box("CoffeeTable_Base", sx0 + 0.75, 1.3, 0.7, 0.3, 0.36, "Furniture", room)
    cylinder("CoffeeTable_Candle", 0.03, 0.08, (sx0 + 1.3, 1.45, 0.44), "Card", room, vertices=12)
    sphere("CoffeeTable_Flame", 0.012, (sx0 + 1.3, 1.45, 0.495), "Glow", room, segments=8, rings=6)

    # lampa din tavan (stinsa noaptea)
    cylinder("CeilingLamp", 0.28, 0.06, (DESK_X, RUG[1], ROOM_H - 0.03), "Trim", room, vertices=32)
    cylinder("CeilingLamp_Diffuser", 0.24, 0.02, (DESK_X, RUG[1], ROOM_H - 0.07), "Card", room, vertices=32)

    # pe birou (biroul e model; sta la (DESK_X, ROOM_D - 0.36), blatul la 0.75 m)
    top_z, dx = 0.75, DESK_X - 3.0  # cotele de mai jos sunt pentru un birou cu centrul la x = 3.0
    floor_box("Monitor_Stand", dx + 2.95, ROOM_D - 0.22, 0.1, 0.08, 0.12, "UI", room, z0=top_z)
    floor_box("Monitor_Base", dx + 2.85, ROOM_D - 0.3, 0.3, 0.18, 0.015, "UI", room, z0=top_z)
    floor_box("Monitor", dx + 2.68, ROOM_D - 0.2, 0.64, 0.03, 0.38, "UI", room, z0=top_z + 0.1)
    floor_box("Monitor_Screen", dx + 2.7, ROOM_D - 0.205, 0.6, 0.005, 0.34, "Screen", room, z0=top_z + 0.12)
    floor_box("Monitor_LED", dx + 2.72, ROOM_D - 0.17, 0.56, 0.01, 0.01, "Neon", room, z0=top_z + 0.3)
    floor_box("Keyboard", dx + 2.78, ROOM_D - 0.56, 0.44, 0.14, 0.02, "Furniture", room, z0=top_z)
    lx, ly = dx + 3.55, ROOM_D - 0.28
    cylinder("DeskLamp_Base", 0.07, 0.02, (lx, ly, top_z + 0.01), "Trim", room)
    cylinder("DeskLamp_Stem", 0.01, 0.38, (lx, ly, top_z + 0.2), "Trim", room, vertices=8)
    cone("DeskLamp_Shade", 0.12, 0.05, 0.14, (lx, ly, top_z + 0.43), "Trim", room)
    sphere("DeskLamp_Bulb", 0.035, (lx, ly, top_z + 0.38), "Glow", room)

    # noptiera langa pat, cu o veioza mica
    floor_box("Nightstand", 0.1, 3.2, 0.45, 0.45, 0.5, "Wood", room)
    floor_box("Nightstand_Drawer", 0.15, 3.195, 0.35, 0.01, 0.12, "Trim", room, z0=0.3)
    cylinder("NightLight_Base", 0.05, 0.08, (0.32, 3.42, 0.54), "Trim", room)
    sphere("NightLight_Bulb", 0.07, (0.32, 3.42, 0.65), "Glow", room)
    # banda LED sub pat (patul e model, intre y 1.68 si 3.12, pana la x 2.2)
    join("Bed_LED", [floor_box("bl", 0.1, 1.62, 2.12, 0.02, 0.02, "Neon", room, z0=0.02),
                     floor_box("bl", 0.1, 3.16, 2.12, 0.02, 0.02, "Neon", room, z0=0.02),
                     floor_box("bl", 2.24, 1.62, 0.02, 1.56, 0.02, "Neon", room, z0=0.02)])

    # raft pe peretele de vest, deasupra patului, cu carti
    floor_box("WallShelf", 0.0, 1.8, 0.24, 1.2, 0.03, "Wood", room, z0=1.55)
    rng_b = random.Random(3)
    y_book, books = 1.85, []
    for i in range(9):
        w = rng_b.uniform(0.03, 0.06)
        books.append(floor_box("bk", 0.03, y_book, 0.18, w, rng_b.uniform(0.18, 0.26),
                               ("Fabric", "Trim", "Cover", "Card")[i % 4], room, z0=1.58))
        y_book += w + 0.005
    join("WallShelf_Books", books)

    # plante in colturi: ghiveci + 3 sfere de frunze
    for name, (px, py), s in (("Plant_SE", (ROOM_W - 0.4, 0.4), 1.0), ("Plant_NW", (0.45, ROOM_D - 0.45), 0.8),
                              ("Plant_NE", (ROOM_W - 0.4, ROOM_D - 1.3), 1.15)):
        cylinder(f"{name}_Pot", 0.17 * s, 0.32 * s, (px, py, 0.16 * s), "Trim", room)
        join(f"{name}_Leaves", [sphere("lf", r * s, (px + dx * s, py + dy * s, z * s), "Plant", room)
                                for r, dx, dy, z in ((0.26, 0, 0, 0.62), (0.2, 0.1, -0.06, 0.88), (0.17, -0.09, 0.05, 1.0))])

    # stalp de 1.75 m pentru scara
    cylinder("Ref_175cm", 0.02, 1.75, (0.3, 4.6, 0.875), "Marker", room, vertices=8)
    return room


def export(path, selection):
    bpy.ops.export_scene.fbx(
        filepath=path,
        use_selection=selection,
        apply_unit_scale=True,
        apply_scale_options="FBX_SCALE_UNITS",
        axis_forward="-Z",
        axis_up="Y",
        bake_space_transform=True,
        object_types={"MESH"},
        mesh_smooth_type="FACE",
        add_leaf_bones=False,
        bake_anim=False,
    )


def build_kit():
    """Fiecare obiect ca model separat, cu pivotul in origine, pentru prefab-uri in Unity.

    Cardurile si panourile au fata spre -Y si pivotul in centru; mobila, raftul si
    cartea au pivotul jos, la mijloc. Firul are 1 m pe Z, de la pivot in sus, ca sa
    se intinda doar din scala.
    """
    kit = collection("Kit")
    models = {}

    def model(name, parts):
        obj = join(name, parts)
        # dupa join, originea e a primei bucati; pivotul modelului trebuie sa fie in (0, 0, 0)
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.context.scene.cursor.location = (0, 0, 0)
        bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
        obj.select_set(False)
        models[name] = obj

    model("Card_Text", [box("a", (0.15, 0.005, 0.21), (0, 0, 0), "Card", kit)])
    model("Card_Ghost", [box("a", (0.15, 0.005, 0.21), (0, 0, 0), "Ghost", kit)])
    model("Card_Image", [box("a", (0.30, 0.01, 0.225), (0, 0, 0), "Trim", kit),
                         box("b", (0.27, 0.01, 0.195), (0, -0.002, 0), "Card", kit)])
    model("FileCard", [box("a", (0.06, 0.003, 0.04), (0, 0, 0), "Card", kit)])
    shelf = [box("a", (1.0, 0.35, 1.2), (0, 0, 0.6), "Wood", kit)]
    for i in range(3):
        shelf.append(box("d", (0.9, 0.02, 0.15), (0, -0.18, 1.02 - 0.17 * i), "Furniture", kit))
        shelf.append(box("h", (0.12, 0.02, 0.02), (0, -0.195, 1.02 - 0.17 * i), "Trim", kit))
    model("FileShelf", shelf)
    model("Book", [box("a", (0.17, 0.24, 0.04), (0, 0, 0.02), "Cover", kit),
                   box("b", (0.16, 0.23, 0.03), (0.006, 0, 0.02), "Card", kit)])
    dropdown = [box("a", (0.25, 0.01, 0.22), (0, 0.006, 0), "UI", kit)]
    for i in range(5):
        dropdown.append(box("r", (0.23, 0.004, 0.036), (0, -0.002, 0.088 - 0.042 * i),
                            "Accent" if i == 0 else "Card", kit))
    model("Dropdown", dropdown)
    model("TagBubble", [sphere("a", 0.025, (0, 0, 0), "Card", kit)])
    model("PlusButton", [sphere("a", 0.02, (0, 0, 0), "Accent", kit),
                         box("h", (0.022, 0.006, 0.005), (0, -0.018, 0), "Card", kit),
                         box("v", (0.005, 0.006, 0.022), (0, -0.018, 0), "Card", kit)])
    bpy.ops.mesh.primitive_cylinder_add(radius=0.002, depth=1.0, vertices=8, location=(0, 0, 0.5))
    model("Wire", [finish(bpy.context.object, "a", "Accent", kit)])
    legs = ((-1, -1), (1, -1), (-1, 1), (1, 1))
    model("Desk", [box("top", (1.6, 0.7, 0.04), (0, 0, 0.73), "Wood", kit),
                   box("drawer", (0.45, 0.6, 0.18), (0.55, 0, 0.62), "Furniture", kit)]
          + [box("l", (0.05, 0.05, 0.71), (0.76 * sx, 0.31 * sy, 0.355), "Furniture", kit) for sx, sy in legs])
    model("Chair", [box("seat", (0.46, 0.46, 0.06), (0, 0, 0.45), "Fabric", kit),
                    box("back", (0.46, 0.05, 0.5), (0, 0.205, 0.73), "Fabric", kit)]
          + [box("l", (0.04, 0.04, 0.42), (0.2 * sx, 0.2 * sy, 0.21), "Furniture", kit) for sx, sy in legs])
    # patul: lung pe Y, tablia la +Y
    model("Bed", [box("frame", (1.44, 2.04, 0.3), (0, 0, 0.15), "Wood", kit),
                  box("mattress", (1.4, 2.0, 0.18), (0, 0, 0.39), "Furniture", kit),
                  box("blanket", (1.46, 1.3, 0.05), (0, -0.35, 0.5), "Fabric", kit),
                  box("head", (1.44, 0.06, 0.95), (0, 1.03, 0.475), "Wood", kit),
                  box("p", (0.55, 0.35, 0.12), (-0.33, 0.75, 0.54), "Card", kit),
                  box("p", (0.55, 0.35, 0.12), (0.33, 0.75, 0.54), "Card", kit)])
    # dulapul: usile spre -Y
    model("Wardrobe", [box("body", (1.2, 0.6, 2.2), (0, 0, 1.1), "Furniture", kit),
                       box("gap", (0.01, 0.005, 2.0), (0, -0.3, 1.1), "Trim", kit),
                       box("h", (0.02, 0.03, 0.2), (-0.06, -0.31, 1.1), "Trim", kit),
                       box("h", (0.02, 0.03, 0.2), (0.06, -0.31, 1.1), "Trim", kit)])

    out = os.path.join(os.path.dirname(FBX), "Models")
    os.makedirs(out, exist_ok=True)
    x = ROOM_W + 7.0
    for name, obj in models.items():
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        export(os.path.join(out, f"{name}.fbx"), selection=True)
        # in .blend modelele stau intr-un rand langa camera, ca sa nu se suprapuna
        obj.location.x = x + obj.dimensions.x / 2
        x += obj.dimensions.x + 0.3
    bpy.ops.object.select_all(action="DESELECT")
    print("kit ok:", len(models), "models")
    return models


def assemble(models):
    """Camera mobilata cu instante ale modelelor din kit (linked duplicates).

    Pozitiile ajung in layout.json, din care Unity pune prefab-urile din Models/ in scena Room.
    Carcasa singura -> RoomShell.fbx; carcasa + instantele -> Graybox.fbx (totul intr-un model).
    """
    placed = collection("Placed")
    items = []
    east, half_turn = -math.pi / 2, math.pi  # cardurile din kit privesc spre -Y; pe est trebuie spre -X

    def put(model, name, loc, rot=(0.0, 0.0, 0.0), scale=(1.0, 1.0, 1.0)):
        obj = models[model].copy()
        obj.name = name
        obj.location = loc
        obj.rotation_euler = rot
        obj.scale = scale
        placed.objects.link(obj)
        items.append((name, model, obj))

    def put_wire(name, a, b):
        dx, dy, dz = (b[i] - a[i] for i in range(3))
        length = math.sqrt(dx * dx + dy * dy + dz * dz)
        put("Wire", name, a, (0.0, math.acos(dz / length), math.atan2(dy, dx)), (1.0, 1.0, length))

    # mobila: biroul sub fereastra, patul cu tablia la peretele de vest, dulapul pe sud,
    # raftul cu fisiere in coltul de nord-est (sertarele spre sud)
    put("Desk", "Desk", (DESK_X, ROOM_D - 0.36, 0))
    put("Chair", "Chair", (DESK_X, ROOM_D - 1.0, 0), (0, 0, half_turn))
    put("Bed", "Bed", (1.15, 2.4, 0), (0, 0, math.pi / 2))
    put("Wardrobe", "Wardrobe", (1.2, 0.3, 0), (0, 0, half_turn))
    put("FileShelf", "FileShelf", (ROOM_W - 0.75, ROOM_D - 0.175, 0))
    for i in range(4):  # fise culcate pe raft
        put("FileCard", f"FileCard_{i + 1}", (ROOM_W - 1.05 + 0.11 * i, ROOM_D - 0.2 - 0.04 * (i % 2), 1.2015),
            (math.pi / 2, 0, 0))

    # lantul de scene pe peretele de est (functionalitatea principala).
    # Cu fata spre est, nordul (+Y) e in stanga, deci lantul merge spre Y mai mic.
    card_x, z = ROOM_W - 0.0125, 1.5
    chain = tuple(ROOM_D / 2 + d for d in (0.3, 0.0, -0.3))
    for i, y in enumerate(chain):
        put("Card_Text", f"TextCard_Scene{i + 1}", (card_x, y, z), (0, 0, east))
    x_front = ROOM_W - 0.025
    for i in range(2):
        put_wire(f"Wire_{i + 1}", (x_front, chain[i] - 0.075, z), (x_front, chain[i + 1] + 0.075, z))
    # 3 drumuri: carduri fantoma in evantai, 15 cm in fata peretelui
    end = (x_front, chain[-1] - 0.075, z)
    for i, dz in enumerate((0.4, 0.0, -0.4)):
        put("Card_Ghost", f"Branch_{'ABC'[i]}", (ROOM_W - 0.1625, chain[-1] - 0.55, z + dz), (0, 0, east))
        put_wire(f"BranchWire_{'ABC'[i]}", end, (ROOM_W - 0.17, chain[-1] - 0.47, z + dz))
    put("Dropdown", "Dropdown", (ROOM_W - 0.17, chain[-1], 1.22), (0, 0, east))

    # carduri imagine pe peretele de nord (stanga ferestrei), cu tagurile si butonul +
    img_x, img_z, img_y = 1.25, 1.6, ROOM_D - 0.015
    put("Card_Image", "ImageCard", (img_x, img_y, img_z))
    put("Card_Image", "ImageCard_2", (0.6, img_y, 1.25))
    for i in range(5):
        a = math.radians(160 - 35 * i)
        put("TagBubble", f"TagBubble_{i + 1}",
            (img_x + 0.25 * math.cos(a), ROOM_D - 0.08, img_z + 0.05 + 0.2 * math.sin(a)))
    put("PlusButton", "PlusButton", (img_x + 0.2, ROOM_D - 0.08, img_z - 0.1))

    # cartea pe birou, un card in aer langa covor
    put("Book", "Book", (DESK_X - 0.55, ROOM_D - 0.38, 0.75))
    put("Card_Text", "TextCard_Floating", (RUG[0] + 0.3, RUG[1] + 0.6, 1.4))

    bpy.context.view_layer.update()
    shell = bpy.data.collections["Room"]
    bpy.ops.object.select_all(action="DESELECT")
    for obj in shell.objects:
        obj.select_set(True)
    export(os.path.join(os.path.dirname(FBX), "RoomShell.fbx"), selection=True)
    for obj in placed.objects:
        obj.select_set(True)
    export(FBX, selection=True)
    bpy.ops.object.select_all(action="DESELECT")

    # pentru Unity: pozitia si axele locale Y, Z ale fiecarei instante, in coordonate Blender
    layout = {"items": []}
    for name, model, obj in items:
        m = obj.matrix_world
        layout["items"].append({
            "name": name,
            "model": model,
            "position": list(m.translation),
            "axisY": list(m.col[1].xyz.normalized()),
            "axisZ": list(m.col[2].xyz.normalized()),
            "scale": list(obj.scale),
        })
    with open(os.path.join(os.path.dirname(FBX), "layout.json"), "w") as f:
        json.dump(layout, f, indent=1)
    print("room ok:", len(items), "instances,", len(shell.objects), "shell objects")


build_shell()
models = build_kit()
assemble(models)
bpy.ops.wm.save_as_mainfile(filepath=BLEND)  # camera + kit-ul pe un rand
bpy.context.scene.collection.children.unlink(bpy.data.collections["Kit"])
bpy.ops.wm.save_as_mainfile(filepath=ROOM_BLEND)  # doar camera mobilata
