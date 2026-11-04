"""Graybox-ul camerei Storypinner: doar cutii, cilindri si sfere, la scara reala (metri).

blender -b -P Blender/graybox.py
  -> Blender/graybox.blend      camera cu toate obiectele + kit-ul de modele pe un rand
  -> Blender/room.blend         camera mobilata cu instante ale modelelor din kit
  -> Unity/Assets/Graybox/      Graybox.fbx, Models/*.fbx, RoomShell.fbx, layout.json

Axe Blender: X = de la stanga la dreapta, Y = spre peretele cu fereastra (nord), Z = sus.
Dimensiunile camerei sunt estimate; se schimba din constantele de mai jos.
"""
import json
import math
import os

import bpy

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLEND = os.path.join(ROOT, "Blender", "graybox.blend")
ROOM_BLEND = os.path.join(ROOT, "Blender", "room.blend")
FBX = os.path.join(ROOT, "Unity", "Assets", "Graybox", "Graybox.fbx")

ROOM_W, ROOM_D, ROOM_H = 4.0, 3.2, 2.6  # x, y, z
WALL = 0.1

COLORS = {
    "Wall": (0.62, 0.60, 0.56),
    "Floor": (0.45, 0.42, 0.38),
    "Furniture": (0.60, 0.58, 0.55),
    "Wood": (0.55, 0.45, 0.33),
    "Window": (0.65, 0.78, 0.88),
    "Card": (0.96, 0.95, 0.92),
    "Accent": (0.77, 0.52, 0.16),
    "Ghost": (0.85, 0.83, 0.80),
    "UI": (0.30, 0.30, 0.32),
    "Marker": (0.30, 0.60, 0.40),
}


def mat(name):
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
        m.diffuse_color = (*COLORS[name], 1.0)
        m.use_nodes = True
        m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (*COLORS[name], 1.0)
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


def sphere(name, r, center, material, coll):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=center, segments=12, ring_count=8)
    return finish(bpy.context.object, name, material, coll)


def wire(name, a, b, coll, r=0.002):
    """Firul dintre doua carduri: un cilindru de 4 mm intre punctele a si b."""
    dx, dy, dz = (b[i] - a[i] for i in range(3))
    length = math.sqrt(dx * dx + dy * dy + dz * dz)
    mid = tuple((a[i] + b[i]) / 2 for i in range(3))
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=length, vertices=8, location=mid)
    o = bpy.context.object
    o.rotation_euler = (0, math.acos(dz / length), math.atan2(dy, dx))
    return finish(o, name, "Accent", coll)


def wall_card(name, kind, u, z, wall, coll, material="Card", offset=0.0):
    """Card pe un perete. kind: 'text' (A5) sau 'image'. u = pozitia de-a lungul peretelui."""
    w, h, t = (0.15, 0.21, 0.005) if kind == "text" else (0.30, 0.225, 0.01)
    offset += 0.01  # 1 cm de perete: lipit de tot, cardul se pierde in perete de la distanta
    if wall == "east":  # x = ROOM_W, cardul priveste spre vest
        return box(name, (t, w, h), (ROOM_W - t / 2 - offset, u, z), material, coll)
    if wall == "north":  # y = ROOM_D, cardul priveste spre sud
        return box(name, (w, t, h), (u, ROOM_D - t / 2 - offset, z), material, coll)
    raise ValueError(wall)


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system = "METRIC"

    room = collection("Room")
    furn = collection("Furniture")
    props = collection("Interactables")

    # camera: podea, tavan, 4 pereti (cu grosime, in afara volumului interior)
    floor_box("Floor", 0, 0, ROOM_W, ROOM_D, WALL, "Floor", room, z0=-WALL)
    floor_box("Ceiling", 0, 0, ROOM_W, ROOM_D, WALL, "Wall", room, z0=ROOM_H)
    floor_box("Wall_North", -WALL, ROOM_D, ROOM_W + 2 * WALL, WALL, ROOM_H, "Wall", room)
    floor_box("Wall_South", -WALL, -WALL, ROOM_W + 2 * WALL, WALL, ROOM_H, "Wall", room)
    floor_box("Wall_West", -WALL, 0, WALL, ROOM_D, ROOM_H, "Wall", room)
    floor_box("Wall_East", ROOM_W, 0, WALL, ROOM_D, ROOM_H, "Wall", room)
    # fereastra si usa sunt doar placi subtiri pe perete, ca repere de scara
    floor_box("Window", 1.4, ROOM_D - 0.01, 1.2, 0.01, 1.4, "Window", room, z0=0.9)
    floor_box("Door", 3.1, 0, 0.85, 0.02, 2.05, "Wood", room)

    # mobila (planul camerei, cadrul 11 din storyboard)
    floor_box("Desk", 1.4, ROOM_D - 0.65, 1.2, 0.6, 0.75, "Wood", furn)
    floor_box("Chair_Seat", 1.78, 2.03, 0.44, 0.44, 0.45, "Furniture", furn)
    floor_box("Chair_Back", 1.78, 1.99, 0.44, 0.04, 0.45, "Furniture", furn, z0=0.45)
    floor_box("Bed", 0.05, 0.0, 0.9, 2.0, 0.45, "Furniture", furn)
    floor_box("Wardrobe", ROOM_W - 0.65, 1.8, 0.6, 1.0, 2.0, "Furniture", furn)

    # raftul cu fisiere: corp + 3 sertare intre 0.6 si 1.1 m, pe fata dinspre vest
    floor_box("FileShelf", 2.75, 2.15, 0.35, 1.0, 1.2, "Wood", props)
    for i, label in enumerate(("Images", "Texts", "Books")):
        z = 1.1 - 0.17 * i - 0.08
        box(f"FileShelf_Drawer_{label}", (0.02, 0.9, 0.15), (2.74, 2.65, z), "Furniture", props)
    for i in range(4):  # fise mici puse pe raft (6 x 4 cm)
        box(f"FileCard_{i + 1}", (0.06, 0.04, 0.003), (2.85 + 0.07 * (i % 2), 2.4 + 0.08 * i, 1.2015), "Card", props)

    # lantul de scene pe peretele de est (functionalitatea principala).
    # Cu fata spre est, nordul (+Y) e in stanga, deci lantul merge spre Y mai mic.
    z = 1.5
    chain = []
    for i, y in enumerate((1.55, 1.25, 0.95)):
        wall_card(f"TextCard_Scene{i + 1}", "text", y, z, "east", props)
        chain.append(y)
    x_front = ROOM_W - 0.025
    for i in range(2):
        wire(f"Wire_{i + 1}", (x_front, chain[i] - 0.075, z), (x_front, chain[i + 1] + 0.075, z), props)
    # 3 drumuri: carduri fantoma in evantai, la ~40 cm una de alta, 15 cm in fata peretelui
    end = (x_front, chain[-1] - 0.075, z)
    for i, dz in enumerate((0.4, 0.0, -0.4)):
        tip = (ROOM_W - 0.17, 0.48, z + dz)
        wall_card(f"Branch_{'ABC'[i]}", "text", 0.4, z + dz, "east", props, "Ghost", offset=0.15)
        wire(f"BranchWire_{'ABC'[i]}", end, tip, props, r=0.0015)
    # dropdown-ul: panou 25 cm cu 5 randuri de 4 cm, 15 cm in fata ultimului card, sub el
    dd_x, dd_y, dd_top = ROOM_W - 0.17, 0.95, 1.33
    box("Dropdown_Panel", (0.01, 0.25, 0.22), (dd_x + 0.006, dd_y, dd_top - 0.11), "UI", props)
    for i in range(5):
        box(f"Dropdown_Row{i + 1}", (0.004, 0.23, 0.036), (dd_x - 0.002, dd_y, dd_top - 0.022 - 0.042 * i),
            "Accent" if i == 0 else "Card", props)

    # card imagine pe peretele de nord, cu tagurile in arc si butonul +
    img_x, img_z = 0.75, 1.55
    wall_card("ImageCard", "image", img_x, img_z, "north", props)
    for i in range(5):
        a = math.radians(160 - 35 * i)
        sphere(f"TagBubble_{i + 1}", 0.025, (img_x + 0.25 * math.cos(a), ROOM_D - 0.08, img_z + 0.05 + 0.2 * math.sin(a)),
               "Card", props)
    sphere("PlusButton", 0.02, (img_x + 0.2, ROOM_D - 0.08, img_z - 0.1), "Accent", props)
    wall_card("ImageCard_2", "image", 0.3, 1.2, "north", props)

    # cartea pe birou si un card text care pluteste in aer
    floor_box("Book", 1.6, ROOM_D - 0.45, 0.17, 0.24, 0.04, "Accent", props, z0=0.75)
    box("TextCard_Floating", (0.15, 0.005, 0.21), (2.2, 1.6, 1.4), "Card", props)

    # repere: pozitia de start (centrul zonei libere) si un stalp de 1.75 m pentru scara
    bpy.ops.mesh.primitive_cylinder_add(radius=0.3, depth=0.005, vertices=24, location=(2.2, 1.1, 0.003))
    finish(bpy.context.object, "PlayerStart", "Marker", room)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.02, depth=1.75, vertices=8, location=(0.3, 2.6, 0.875))
    finish(bpy.context.object, "Ref_175cm", "Marker", room)

    os.makedirs(os.path.dirname(FBX), exist_ok=True)
    export(FBX, selection=False)
    print("graybox ok:", len(bpy.data.objects), "objects")


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
        bpy.ops.object.select_all(action="DESELECT")
        for p in parts:
            p.select_set(True)
        bpy.context.view_layer.objects.active = parts[0]
        if len(parts) > 1:
            bpy.ops.object.join()
        obj = bpy.context.view_layer.objects.active
        # dupa join, originea e a primei bucati; pivotul modelului trebuie sa fie in (0, 0, 0)
        bpy.context.scene.cursor.location = (0, 0, 0)
        bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
        obj.name = obj.data.name = name
        models[name] = obj

    model("Card_Text", [box("a", (0.15, 0.005, 0.21), (0, 0, 0), "Card", kit)])
    model("Card_Ghost", [box("a", (0.15, 0.005, 0.21), (0, 0, 0), "Ghost", kit)])
    model("Card_Image", [box("a", (0.30, 0.01, 0.225), (0, 0, 0), "Wood", kit),
                         box("b", (0.27, 0.01, 0.195), (0, -0.002, 0), "Card", kit)])
    model("FileCard", [box("a", (0.06, 0.003, 0.04), (0, 0, 0), "Card", kit)])
    shelf = [box("a", (1.0, 0.35, 1.2), (0, 0, 0.6), "Wood", kit)]
    for i in range(3):
        shelf.append(box(f"d{i}", (0.9, 0.02, 0.15), (0, -0.18, 1.02 - 0.17 * i), "Furniture", kit))
    model("FileShelf", shelf)
    model("Book", [box("a", (0.17, 0.24, 0.04), (0, 0, 0.02), "Accent", kit),
                   box("b", (0.16, 0.23, 0.03), (0.006, 0, 0.02), "Card", kit)])
    dropdown = [box("a", (0.25, 0.01, 0.22), (0, 0.006, 0), "UI", kit)]
    for i in range(5):
        dropdown.append(box(f"r{i}", (0.23, 0.004, 0.036), (0, -0.002, 0.088 - 0.042 * i),
                            "Accent" if i == 0 else "Card", kit))
    model("Dropdown", dropdown)
    model("TagBubble", [sphere("a", 0.025, (0, 0, 0), "Card", kit)])
    model("PlusButton", [sphere("a", 0.02, (0, 0, 0), "Accent", kit),
                         box("h", (0.022, 0.006, 0.005), (0, -0.018, 0), "Card", kit),
                         box("v", (0.005, 0.006, 0.022), (0, -0.018, 0), "Card", kit)])
    bpy.ops.mesh.primitive_cylinder_add(radius=0.002, depth=1.0, vertices=8, location=(0, 0, 0.5))
    model("Wire", [finish(bpy.context.object, "a", "Accent", kit)])
    model("Desk", [box("a", (1.2, 0.6, 0.75), (0, 0, 0.375), "Wood", kit)])
    model("Chair", [box("a", (0.44, 0.44, 0.45), (0, 0, 0.225), "Furniture", kit),
                    box("b", (0.44, 0.04, 0.45), (0, 0.2, 0.675), "Furniture", kit)])
    model("Bed", [box("a", (0.9, 2.0, 0.45), (0, 0, 0.225), "Furniture", kit)])
    model("Wardrobe", [box("a", (1.0, 0.6, 2.0), (0, 0, 1.0), "Furniture", kit)])

    out = os.path.join(os.path.dirname(FBX), "Models")
    os.makedirs(out, exist_ok=True)
    x = ROOM_W + 1.0
    for name, obj in models.items():
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        export(os.path.join(out, f"{name}.fbx"), selection=True)
        # in .blend modelele stau intr-un rand langa camera, ca sa nu se suprapuna
        obj.location.x = x + obj.dimensions.x / 2
        x += obj.dimensions.x + 0.3
    print("kit ok:", len(models), "models")
    return models


def assemble(models):
    """A doua varianta a camerei: aceeasi carcasa, mobilata cu instante ale modelelor din kit.

    Fiecare instanta foloseste mesh-ul modelului (linked duplicate). Pozitiile ajung si in
    layout.json, din care Unity pune prefab-urile din Models/ in scena Room.
    """
    keep = set(models.values())  # dupa obiect: in Interactables exista si un "Book" care nu e modelul
    for name in ("Furniture", "Interactables", "Kit"):
        coll = bpy.data.collections[name]
        for obj in list(coll.objects):
            if obj not in keep:
                bpy.data.objects.remove(obj)
        bpy.context.scene.collection.children.unlink(coll)
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

    # mobila si raftul, ca in planul camerei
    put("Desk", "Desk", (2.0, ROOM_D - 0.35, 0))
    put("Chair", "Chair", (2.0, 2.25, 0), (0, 0, half_turn))
    put("Bed", "Bed", (0.5, 1.0, 0))
    put("Wardrobe", "Wardrobe", (ROOM_W - 0.35, 2.3, 0), (0, 0, math.pi / 2))
    put("FileShelf", "FileShelf", (2.925, 2.65, 0), (0, 0, east))
    for i in range(4):  # fise culcate pe raft
        put("FileCard", f"FileCard_{i + 1}", (2.85 + 0.07 * (i % 2), 2.4 + 0.08 * i, 1.2015), (math.pi / 2, 0, 0))

    # lantul de scene pe peretele de est, cu 3 drumuri si dropdown-ul
    card_x, z = ROOM_W - 0.0125, 1.5
    chain = (1.55, 1.25, 0.95)
    for i, y in enumerate(chain):
        put("Card_Text", f"TextCard_Scene{i + 1}", (card_x, y, z), (0, 0, east))
    x_front = ROOM_W - 0.025
    for i in range(2):
        put_wire(f"Wire_{i + 1}", (x_front, chain[i] - 0.075, z), (x_front, chain[i + 1] + 0.075, z))
    end = (x_front, chain[-1] - 0.075, z)
    for i, dz in enumerate((0.4, 0.0, -0.4)):
        put("Card_Ghost", f"Branch_{'ABC'[i]}", (ROOM_W - 0.1625, 0.4, z + dz), (0, 0, east))
        put_wire(f"BranchWire_{'ABC'[i]}", end, (ROOM_W - 0.17, 0.48, z + dz))
    put("Dropdown", "Dropdown", (ROOM_W - 0.17, 0.95, 1.22), (0, 0, east))

    # card imagine pe peretele de nord, cu tagurile si butonul +
    img_x, img_z, img_y = 0.75, 1.55, ROOM_D - 0.015
    put("Card_Image", "ImageCard", (img_x, img_y, img_z))
    put("Card_Image", "ImageCard_2", (0.3, img_y, 1.2))
    for i in range(5):
        a = math.radians(160 - 35 * i)
        put("TagBubble", f"TagBubble_{i + 1}",
            (img_x + 0.25 * math.cos(a), ROOM_D - 0.08, img_z + 0.05 + 0.2 * math.sin(a)))
    put("PlusButton", "PlusButton", (img_x + 0.2, ROOM_D - 0.08, img_z - 0.1))

    # cartea pe birou, un card in aer
    put("Book", "Book", (1.685, ROOM_D - 0.33, 0.75))
    put("Card_Text", "TextCard_Floating", (2.2, 1.6, 1.4))

    bpy.context.view_layer.update()
    shell = bpy.data.collections["Room"]
    bpy.ops.object.select_all(action="DESELECT")
    for obj in shell.objects:
        obj.select_set(True)
    export(os.path.join(os.path.dirname(FBX), "RoomShell.fbx"), selection=True)

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
    bpy.ops.wm.save_as_mainfile(filepath=ROOM_BLEND)
    print("room ok:", len(items), "instances")


build()
models = build_kit()
bpy.ops.wm.save_as_mainfile(filepath=BLEND)
assemble(models)
