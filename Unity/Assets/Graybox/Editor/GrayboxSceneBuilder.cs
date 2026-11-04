using System.Collections.Generic;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.XR.Interaction.Toolkit.Interactables;

namespace Storypinner.EditorTools
{
    // Construieste scenele de graybox din ce scrie Blender/graybox.py:
    //   Graybox.unity - Graybox.fbx, camera cu toate obiectele intr-un singur model
    //   Room.unity    - RoomShell.fbx + cate o instanta din Models/ pentru fiecare obiect din layout.json
    // Din meniul Storypinner, sau din linia de comanda cu -executeMethod.
    public static class GrayboxSceneBuilder
    {
        const string FbxPath = "Assets/Graybox/Graybox.fbx";
        const string ShellPath = "Assets/Graybox/RoomShell.fbx";
        const string LayoutPath = "Assets/Graybox/layout.json";
        const string ScenePath = "Assets/Scenes/Graybox.unity";
        const string RoomScenePath = "Assets/Scenes/Room.unity";
        const string MaterialDir = "Assets/Graybox/Materials";
        const string ModelDir = "Assets/Graybox/Models";
        const string RigPrefabPath = "Assets/Samples/XR Interaction Toolkit/3.6.1/Starter Assets/Prefabs/XR Origin (XR Rig).prefab";
        const string SimulatorPrefabPath = "Assets/Samples/XR Interaction Toolkit/3.6.1/XR Device Simulator/XR Device Simulator.prefab";
        const float EyeHeight = 1.6f;
        static readonly string[] Grabbable = { "Card_Text", "Card_Ghost", "Card_Image", "FileCard", "Book", "TagBubble", "PlusButton" };

        [MenuItem("Storypinner/Build Graybox Scene")]
        public static void Build()
        {
            RemapAll();
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(FbxPath);
            if (model == null)
            {
                Debug.LogError($"Lipseste {FbxPath}; ruleaza intai Blender/graybox.py");
                return;
            }

            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var room = (GameObject)PrefabUtility.InstantiatePrefab(model, scene);
            room.name = "Graybox";
            AddColliders(room);
            AddLightsAndCamera(room);

            EditorSceneManager.SaveScene(scene, ScenePath);
            AddToBuildSettings(ScenePath);
            Debug.Log($"Graybox scene saved to {ScenePath}");
        }

        [MenuItem("Storypinner/Build Room Scene")]
        public static void BuildRoom()
        {
            RemapAll();
            var shell = AssetDatabase.LoadAssetAtPath<GameObject>(ShellPath);
            var json = AssetDatabase.LoadAssetAtPath<TextAsset>(LayoutPath);
            if (shell == null || json == null)
            {
                Debug.LogError($"Lipseste {ShellPath} sau {LayoutPath}; ruleaza intai Blender/graybox.py");
                return;
            }

            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var root = new GameObject("Room");
            var walls = (GameObject)PrefabUtility.InstantiatePrefab(shell, scene);
            walls.name = "Shell";
            walls.transform.SetParent(root.transform, false);
            AddColliders(walls);

            var objects = new GameObject("Objects").transform;
            objects.SetParent(root.transform, false);
            foreach (var item in JsonUtility.FromJson<Layout>(json.text).items)
            {
                var prefab = AssetDatabase.LoadAssetAtPath<GameObject>($"{ModelDir}/{item.model}.fbx");
                if (prefab == null)
                {
                    Debug.LogWarning($"Lipseste modelul {item.model} pentru {item.name}");
                    continue;
                }
                var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab, scene);
                go.name = item.name;
                go.transform.SetParent(objects, false);
                // Blender e Z-sus si dreptaci; FBX-ul ajunge in Unity ca (x, y, z) -> (-x, z, -y).
                // Axa locala Z din Blender devine "sus" in Unity, iar -Y devine "inainte".
                go.transform.SetPositionAndRotation(
                    ToUnity(item.position),
                    Quaternion.LookRotation(-ToUnity(item.axisY), ToUnity(item.axisZ)));
                go.transform.localScale = new Vector3(item.scale[0], item.scale[2], item.scale[1]);
                AddColliders(go);
                if (System.Array.IndexOf(Grabbable, item.model) >= 0)
                    MakeGrabbable(go);
            }
            AddLightsAndCamera(root);

            EditorSceneManager.SaveScene(scene, RoomScenePath);
            AddToBuildSettings(RoomScenePath);
            Debug.Log($"Room scene saved to {RoomScenePath}");
        }

        // pentru pornirea editorului direct in scena: Unity.exe -projectPath ... -executeMethod ...OpenRoom
        public static void OpenRoom() => EditorSceneManager.OpenScene(RoomScenePath);

        [System.Serializable]
        class Layout
        {
            public LayoutItem[] items;
        }

        [System.Serializable]
        class LayoutItem
        {
            public string name;
            public string model;
            public float[] position;
            public float[] axisY;
            public float[] axisZ;
            public float[] scale;
        }

        static Vector3 ToUnity(float[] v) => new Vector3(-v[0], v[2], -v[1]);

        // FBX-ul nu aduce culorile in URP: materialele din Blender sunt legate pe importer
        // de cate un URP Lit cu aceeasi culoare, pentru camera si pentru fiecare model din Models/
        static void RemapAll()
        {
            RemapMaterials(FbxPath);
            RemapMaterials(ShellPath);
            foreach (var guid in AssetDatabase.FindAssets("t:Model", new[] { ModelDir }))
                RemapMaterials(AssetDatabase.GUIDToAssetPath(guid));
        }

        // coliziuni pe tot, ca mainile si cardurile sa aiba de ce sa se loveasca la test
        static void AddColliders(GameObject root)
        {
            foreach (var mf in root.GetComponentsInChildren<MeshFilter>())
                mf.gameObject.AddComponent<MeshCollider>().sharedMesh = mf.sharedMesh;
        }

        static void AddLightsAndCamera(GameObject room)
        {
            var sun = new GameObject("Directional Light").AddComponent<Light>();
            sun.type = LightType.Directional;
            sun.intensity = 1.1f;
            sun.shadows = LightShadows.Soft;
            sun.transform.rotation = Quaternion.Euler(50f, -30f, 0f);
            var lamp = new GameObject("Room Light").AddComponent<Light>();
            lamp.type = LightType.Point;
            lamp.range = 6f;
            lamp.intensity = 1.5f;
            lamp.color = new Color(1f, 0.92f, 0.8f);
            lamp.transform.position = Center(room, "Floor") + Vector3.up * 2.3f;
            RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Flat;
            RenderSettings.ambientLight = new Color(0.45f, 0.43f, 0.4f);

            // rig-ul VR ca la laborator (XRI Starter Assets + Device Simulator), pe PlayerStart,
            // cu fata spre lantul de scene. Fara sample-uri importate ramane o camera simpla la 1.6 m.
            var start = Center(room, "PlayerStart");
            var target = Center(room, "TextCard_Scene2");
            var floor = new Vector3(start.x, 0f, start.z);
            var facing = Quaternion.LookRotation(new Vector3(target.x - start.x, 0f, target.z - start.z));
            var rigPrefab = AssetDatabase.LoadAssetAtPath<GameObject>(RigPrefabPath);
            if (rigPrefab != null)
            {
                var rig = (GameObject)PrefabUtility.InstantiatePrefab(rigPrefab);
                rig.transform.SetPositionAndRotation(floor, facing);
                foreach (var c in rig.GetComponentsInChildren<Camera>())
                    c.nearClipPlane = 0.02f;
                var sim = AssetDatabase.LoadAssetAtPath<GameObject>(SimulatorPrefabPath);
                if (sim != null)
                    PrefabUtility.InstantiatePrefab(sim);
                return;
            }
            var cam = new GameObject("Main Camera").AddComponent<Camera>();
            cam.tag = "MainCamera";
            cam.nearClipPlane = 0.02f;
            cam.gameObject.AddComponent<AudioListener>();
            cam.transform.SetPositionAndRotation(floor + Vector3.up * EyeHeight, facing);
        }

        // obiectele mici se pot prinde cu controller-ul si raman unde le lasi (fara gravitatie),
        // ca la testul de scara sa le poti tine in mana si lipi de perete
        static void MakeGrabbable(GameObject go)
        {
            foreach (var mc in go.GetComponentsInChildren<MeshCollider>())
            {
                mc.gameObject.AddComponent<BoxCollider>();
                Object.DestroyImmediate(mc);
            }
            var body = go.AddComponent<Rigidbody>();
            body.useGravity = false;
            body.isKinematic = true;
            var grab = go.AddComponent<XRGrabInteractable>();
            grab.movementType = XRBaseInteractable.MovementType.Instantaneous;
            grab.throwOnDetach = false;
        }

        // aceleasi culori ca in Blender/graybox.py (COLORS)
        static readonly Dictionary<string, Color> Colors = new Dictionary<string, Color>
        {
            { "Wall", new Color(0.62f, 0.60f, 0.56f) },
            { "Floor", new Color(0.45f, 0.42f, 0.38f) },
            { "Furniture", new Color(0.60f, 0.58f, 0.55f) },
            { "Wood", new Color(0.55f, 0.45f, 0.33f) },
            { "Window", new Color(0.65f, 0.78f, 0.88f) },
            { "Card", new Color(0.96f, 0.95f, 0.92f) },
            { "Accent", new Color(0.77f, 0.52f, 0.16f) },
            { "Ghost", new Color(0.85f, 0.83f, 0.80f, 0.5f) },
            { "UI", new Color(0.30f, 0.30f, 0.32f) },
            { "Marker", new Color(0.30f, 0.60f, 0.40f) },
        };

        static Material GetMaterial(string name)
        {
            name = name.Split(' ', '.')[0];
            var path = $"{MaterialDir}/{name}.mat";
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (mat == null)
            {
                if (!AssetDatabase.IsValidFolder(MaterialDir))
                    AssetDatabase.CreateFolder("Assets/Graybox", "Materials");
                mat = new Material(Shader.Find("Universal Render Pipeline/Lit"));
                AssetDatabase.CreateAsset(mat, path);
            }
            var color = Colors.TryGetValue(name, out var c) ? c : Color.magenta;
            mat.SetColor("_BaseColor", color);
            mat.SetFloat("_Smoothness", 0.1f);
            if (color.a < 1f)
            {
                // cardurile fantoma (drumurile propuse) sunt semitransparente
                mat.SetFloat("_Surface", 1f);
                mat.SetFloat("_Blend", 0f);
                mat.SetOverrideTag("RenderType", "Transparent");
                mat.SetInt("_SrcBlend", (int)UnityEngine.Rendering.BlendMode.SrcAlpha);
                mat.SetInt("_DstBlend", (int)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
                mat.SetInt("_ZWrite", 0);
                mat.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
                mat.renderQueue = (int)UnityEngine.Rendering.RenderQueue.Transparent;
            }
            EditorUtility.SetDirty(mat);
            return mat;
        }

        static void RemapMaterials(string path)
        {
            if (AssetDatabase.LoadAssetAtPath<GameObject>(path) == null)
                return;
            AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceUpdate);
            if (AssetImporter.GetAtPath(path) is not ModelImporter importer)
                return;
            var used = new HashSet<string>();
            foreach (var asset in AssetDatabase.LoadAllAssetsAtPath(path))
                if (asset is Renderer r)
                    foreach (var m in r.sharedMaterials)
                        if (m != null)
                            used.Add(m.name);
            foreach (var name in used)
                importer.AddRemap(new AssetImporter.SourceAssetIdentifier(typeof(Material), name), GetMaterial(name));
            importer.SaveAndReimport();
        }

        static Vector3 Center(GameObject root, string child)
        {
            // dupa numele obiectului, nu al mesh-ului: in Room.unity mesh-ul e copilul instantei
            foreach (var t in root.GetComponentsInChildren<Transform>())
                if (t.name == child && t.GetComponentInChildren<Renderer>() is Renderer r)
                    return r.bounds.center;
            Debug.LogWarning($"Nu am gasit {child} in graybox");
            return Vector3.zero;
        }

        static void AddToBuildSettings(string path)
        {
            var scenes = EditorBuildSettings.scenes;
            foreach (var s in scenes)
                if (s.path == path)
                    return;
            var list = new System.Collections.Generic.List<EditorBuildSettingsScene>(scenes);
            list.Insert(0, new EditorBuildSettingsScene(path, true));
            EditorBuildSettings.scenes = list.ToArray();
        }
    }
}
