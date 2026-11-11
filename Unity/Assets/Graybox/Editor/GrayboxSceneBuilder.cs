using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
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
        const string VolumePath = "Assets/Graybox/NightVolume.asset";
        const string FogTexturePath = "Assets/Graybox/FogPuff.asset";
        const string DustMaterialPath = "Assets/Graybox/MoonDust.mat";
        const string VolumetricMaterialPath = "Assets/Graybox/Rendering/VolumetricFog.mat";
        const string VolumetricShaderName = "Hidden/Storypinner/VolumetricFog";
        // ce a ramas de la ceata veche facuta din particule / mesh (se sterge la build)
        static readonly string[] StaleFogAssets =
            { "Assets/Graybox/CornerFog.mat", "Assets/Graybox/MoonShaft.mat", "Assets/Graybox/MoonShaft.asset" };
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

        // night mode: lumina rece a lunii prin fereastra, ambient albastru inchis, ceata
        // albastra, lampa calda pe birou si veioza, o lumina cyan slaba pe peretele cu lantul
        // de scene, plus bloom ca sa straluceasca firele, cardurile, luna si luminitele
        static readonly Color NightFog = new Color(0.015f, 0.022f, 0.06f);

        static void AddLightsAndCamera(GameObject room)
        {
            // cerul, luna si stelele sunt afara: nu au voie sa blocheze lumina lunii
            foreach (var r in room.GetComponentsInChildren<Renderer>())
                if (r.name.StartsWith("Sky_"))
                {
                    r.shadowCastingMode = ShadowCastingMode.Off;
                    foreach (var c in r.GetComponents<Collider>())
                        Object.DestroyImmediate(c);
                }

            var moon = new GameObject("Moonlight").AddComponent<Light>();
            moon.type = LightType.Directional;
            moon.color = new Color(0.55f, 0.66f, 1f);
            moon.intensity = 1.2f;
            moon.shadows = LightShadows.Soft;
            // din spatele ferestrei (nord, sus) spre covor, ca sa cada un dreptunghi de lumina pe podea
            var rug = Center(room, "Rug");
            var window = Center(room, "Window_Frame");
            moon.transform.rotation = Quaternion.LookRotation((rug - (window + Vector3.up * 1.1f)).normalized);

            AddPoint("Desk Lamp", Center(room, "DeskLamp_Bulb"), new Color(1f, 0.72f, 0.45f), 2.5f, 3.5f, true);
            AddPoint("Night Light", Center(room, "NightLight_Bulb"), new Color(1f, 0.7f, 0.45f), 1.5f, 2.5f, false);
            var chain = Center(room, "TextCard_Scene2");
            AddPoint("Card Wall Glow", chain + new Vector3(0.8f * Mathf.Sign(rug.x - chain.x), 0.2f, 0f),
                new Color(0.3f, 0.6f, 1f), 2.5f, 4f, false);
            // lumina slaba si rece de la benzile LED de sub tavan, in doua puncte
            var top = Center(room, "CeilingLamp") + Vector3.down * 0.3f;
            AddPoint("Neon Fill A", top + Vector3.right * 2f, new Color(0.2f, 0.35f, 1f), 2f, 7f, false);
            AddPoint("Neon Fill B", top + Vector3.left * 2f, new Color(0.2f, 0.35f, 1f), 2f, 7f, false);
            AddPoint("Candle", Center(room, "CoffeeTable_Flame") + Vector3.up * 0.05f, new Color(1f, 0.65f, 0.35f), 0.8f, 1.5f, false);

            RenderSettings.skybox = null;
            RenderSettings.ambientMode = AmbientMode.Trilight;
            RenderSettings.ambientSkyColor = new Color(0.08f, 0.10f, 0.24f);
            RenderSettings.ambientEquatorColor = new Color(0.05f, 0.06f, 0.15f);
            RenderSettings.ambientGroundColor = new Color(0.02f, 0.03f, 0.07f);
            // ceata clasica (doar dupa distanta) e oprita: o face shader-ul volumetric, in 3D
            RenderSettings.fog = false;
            RenderSettings.sun = moon;
            AddNightVolume();
            AddVolumetricFog(room);
            AddMoonDust(room, moon.transform.forward);

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
                    SetupCamera(c);
                var sim = AssetDatabase.LoadAssetAtPath<GameObject>(SimulatorPrefabPath);
                if (sim != null)
                    PrefabUtility.InstantiatePrefab(sim);
                return;
            }
            var cam = new GameObject("Main Camera").AddComponent<Camera>();
            cam.tag = "MainCamera";
            cam.gameObject.AddComponent<AudioListener>();
            SetupCamera(cam);
            cam.transform.SetPositionAndRotation(floor + Vector3.up * EyeHeight, facing);
        }

        static void AddPoint(string name, Vector3 pos, Color color, float intensity, float range, bool shadows)
        {
            var l = new GameObject(name).AddComponent<Light>();
            l.type = LightType.Point;
            l.color = color;
            l.intensity = intensity;
            l.range = range;
            l.shadows = shadows ? LightShadows.Soft : LightShadows.None;
            l.transform.position = pos;
        }

        static void SetupCamera(Camera c)
        {
            c.nearClipPlane = 0.02f;
            c.clearFlags = CameraClearFlags.SolidColor;
            c.backgroundColor = NightFog;
            c.GetUniversalAdditionalCameraData().renderPostProcessing = true;
        }

        // volum global: bloom (pentru tot ce are emisie), tonemapping si o vigneta albastra slaba
        static void AddNightVolume()
        {
            if (AssetDatabase.LoadAssetAtPath<VolumeProfile>(VolumePath) != null)
                AssetDatabase.DeleteAsset(VolumePath);
            var profile = ScriptableObject.CreateInstance<VolumeProfile>();
            AssetDatabase.CreateAsset(profile, VolumePath);
            var bloom = profile.Add<Bloom>(true);
            bloom.threshold.Override(0.9f);
            bloom.intensity.Override(1.5f);
            bloom.scatter.Override(0.65f);
            bloom.tint.Override(new Color(0.75f, 0.85f, 1f));
            profile.Add<Tonemapping>(true).mode.Override(TonemappingMode.ACES);
            var adj = profile.Add<ColorAdjustments>(true);
            adj.postExposure.Override(0.9f);
            adj.colorFilter.Override(new Color(0.88f, 0.93f, 1f));
            var vignette = profile.Add<Vignette>(true);
            vignette.intensity.Override(0.35f);
            vignette.color.Override(new Color(0.02f, 0.03f, 0.1f));
            foreach (var comp in profile.components)
            {
                comp.hideFlags = HideFlags.HideInInspector | HideFlags.HideInHierarchy;
                AssetDatabase.AddObjectToAsset(comp, profile);
            }
            EditorUtility.SetDirty(profile);
            AssetDatabase.SaveAssets();

            var volume = new GameObject("Night Volume").AddComponent<Volume>();
            volume.isGlobal = true;
            volume.sharedProfile = profile;
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

        // aceleasi culori ca in Blender/graybox.py (COLORS, EMISSION) - night mode
        static readonly Dictionary<string, Color> Colors = new Dictionary<string, Color>
        {
            { "Wall", new Color(0.05f, 0.07f, 0.15f) },
            { "Floor", new Color(0.03f, 0.04f, 0.09f) },
            { "Furniture", new Color(0.09f, 0.11f, 0.20f) },
            { "Wood", new Color(0.10f, 0.09f, 0.17f) },
            { "Fabric", new Color(0.08f, 0.09f, 0.26f) },
            { "Trim", new Color(0.14f, 0.18f, 0.32f) },
            { "Neon", new Color(0.20f, 0.42f, 1.00f) },
            { "Plant", new Color(0.08f, 0.24f, 0.26f) },
            { "Sky", new Color(0.03f, 0.06f, 0.18f) },
            { "Moon", new Color(0.85f, 0.90f, 1.00f) },
            { "Glow", new Color(1.00f, 0.74f, 0.45f) },
            { "Screen", new Color(0.22f, 0.42f, 0.85f) },
            { "Cover", new Color(0.20f, 0.32f, 0.56f) },
            { "Card", new Color(0.86f, 0.90f, 0.98f) },
            { "Accent", new Color(0.30f, 0.75f, 1.00f) },
            { "Ghost", new Color(0.55f, 0.70f, 1.00f, 0.4f) },
            { "UI", new Color(0.08f, 0.10f, 0.20f) },
            { "Marker", new Color(0.25f, 0.85f, 0.75f) },
        };

        // cat de tare lumineaza materialul singur (HDR; peste pragul de bloom = straluceste)
        static readonly Dictionary<string, float> Emission = new Dictionary<string, float>
        {
            { "Neon", 2.5f }, { "Sky", 0.6f }, { "Moon", 4f }, { "Glow", 4f }, { "Screen", 1.6f },
            { "Accent", 2.5f }, { "Ghost", 0.8f }, { "Card", 0.25f }, { "Marker", 0.6f },
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
            if (Emission.TryGetValue(name, out var e))
            {
                mat.EnableKeyword("_EMISSION");
                mat.globalIlluminationFlags = MaterialGlobalIlluminationFlags.RealtimeEmissive;
                mat.SetColor("_EmissionColor", new Color(color.r, color.g, color.b) * e);
            }
            else
            {
                mat.DisableKeyword("_EMISSION");
                mat.SetColor("_EmissionColor", Color.black);
            }
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

        // ceata volumetrica: un shader (Rendering/VolumetricFog.shader) care, pentru fiecare pixel,
        // merge prin camera pas cu pas si aduna ceata + lumina. Razele lunii vin din shadow map, deci
        // sunt taiate de rama ferestrei si se vad din orice unghi. Shader-ul e desenat de un renderer
        // feature (VolumetricFogFeature) pus pe toate renderer-ele URP din proiect.
        static void AddVolumetricFog(GameObject room)
        {
            foreach (var path in StaleFogAssets)
                if (AssetDatabase.LoadMainAssetAtPath(path) != null)
                    AssetDatabase.DeleteAsset(path);

            var floor = FindBounds(room, "Floor");
            if (floor.size == Vector3.zero)
            {
                Debug.LogWarning("Nu am gasit Floor pentru ceata volumetrica");
                return;
            }
            var shader = Shader.Find(VolumetricShaderName);
            if (shader == null)
            {
                Debug.LogWarning($"Nu gasesc shader-ul {VolumetricShaderName}");
                return;
            }
            var mat = AssetDatabase.LoadAssetAtPath<Material>(VolumetricMaterialPath);
            if (mat == null)
            {
                mat = new Material(shader);
                AssetDatabase.CreateAsset(mat, VolumetricMaterialPath);
            }
            mat.shader = shader;

            const float roomHeight = 3.4f; // ROOM_H din graybox.py
            var wallsMin = new Vector3(floor.min.x, floor.max.y, floor.min.z);
            var wallsMax = new Vector3(floor.max.x, floor.max.y + roomHeight, floor.max.z);
            mat.SetVector("_RoomMin", wallsMin);
            mat.SetVector("_RoomMax", wallsMax);
            // rgb = lumina albastra slaba pe care o are ceata peste tot, a = densitatea de baza (pe metru)
            mat.SetVector("_FogColor", new Vector4(0.03f, 0.05f, 0.15f, 0.045f));
            // colturile: cat de deasa e ceata acolo si pe ce raza; jos langa podea: densitate si inaltime
            mat.SetVector("_CornerParams", new Vector4(0.8f, 1.3f, 0.3f, 0.45f));
            // luna: putere, cat de mult imprastie inainte (raza straluceste cand te uiti spre fereastra),
            // extinctie, distanta maxima de mers
            mat.SetVector("_MoonParams", new Vector4(7f, 0.6f, 1f, 16f));
            // banda albastra de sub tavan (LED-urile)
            mat.SetVector("_NeonColor", new Vector4(0.06f, 0.14f, 0.5f, 0.55f));
            mat.SetVector("_NoiseParams", new Vector4(0.7f, 0.65f, 0.12f, 0f));

            // 4 lampi care coloreaza ceata in jurul lor (fara umbre, doar halou)
            var glows = new (string name, Color color, float range)[]
            {
                ("Desk Lamp", new Color(1f, 0.62f, 0.32f) * 0.9f, 1.6f),
                ("Night Light", new Color(1f, 0.6f, 0.3f) * 0.6f, 1.2f),
                ("Card Wall Glow", new Color(0.25f, 0.55f, 1f) * 0.5f, 2.2f),
                ("Candle", new Color(1f, 0.55f, 0.25f) * 0.5f, 0.8f),
            };
            for (int i = 0; i < 4; i++)
            {
                var light = GameObject.Find(glows[i].name);
                var p = light != null ? light.transform.position : Vector3.zero;
                mat.SetVector($"_P{i}", new Vector4(p.x, p.y, p.z, light != null ? glows[i].range : 0f));
                mat.SetVector($"_C{i}", glows[i].color);
            }
            EditorUtility.SetDirty(mat);
            AssetDatabase.SaveAssets();
            InstallFogFeature(mat);
        }

        // pune VolumetricFogFeature pe fiecare renderer URP (PC si Mobile), o singura data
        static void InstallFogFeature(Material mat)
        {
            foreach (var guid in AssetDatabase.FindAssets("t:UniversalRendererData"))
            {
                var path = AssetDatabase.GUIDToAssetPath(guid);
                if (path.Contains("/Samples/"))
                    continue;
                var data = AssetDatabase.LoadAssetAtPath<UniversalRendererData>(path);
                if (data == null)
                    continue;
                var feature = data.rendererFeatures.OfType<Storypinner.Rendering.VolumetricFogFeature>().FirstOrDefault();
                if (feature == null)
                {
                    feature = ScriptableObject.CreateInstance<Storypinner.Rendering.VolumetricFogFeature>();
                    feature.name = "Volumetric Fog";
                    AssetDatabase.AddObjectToAsset(feature, data);
                    AssetDatabase.TryGetGUIDAndLocalFileIdentifier(feature, out _, out long localId);
                    var so = new SerializedObject(data);
                    var list = so.FindProperty("m_RendererFeatures");
                    var map = so.FindProperty("m_RendererFeatureMap");
                    list.arraySize++;
                    list.GetArrayElementAtIndex(list.arraySize - 1).objectReferenceValue = feature;
                    map.arraySize++;
                    map.GetArrayElementAtIndex(map.arraySize - 1).longValue = localId;
                    so.ApplyModifiedPropertiesWithoutUndo();
                }
                feature.material = mat;
                feature.passEvent = RenderPassEvent.BeforeRenderingPostProcessing;
                feature.SetActive(true);
                feature.Create();
                EditorUtility.SetDirty(feature);
                data.SetDirty();
                EditorUtility.SetDirty(data);
            }
            AssetDatabase.SaveAssets();
        }

        static Bounds FindBounds(GameObject room, string name)
        {
            foreach (var t in room.GetComponentsInChildren<Transform>())
                if (t.name == name && t.GetComponentInChildren<Renderer>() is Renderer r)
                    return r.bounds;
            return default;
        }

        // praf fin care pluteste in raza lunii (particule mici aditive). Raza in sine e in ceata volumetrica.
        static void AddMoonDust(GameObject room, Vector3 dir)
        {
            var win = FindBounds(room, "Window_Frame");
            if (win.size == Vector3.zero || dir.y > -0.05f)
            {
                Debug.LogWarning("Nu am gasit Window_Frame (sau luna nu bate in jos) pentru praful din raza");
                return;
            }
            const float floorY = 0.02f;
            var topMid = new Vector3(win.center.x, win.center.y, win.center.z);
            var botMid = topMid + dir * ((topMid.y - floorY) / -dir.y);
            float length = Vector3.Distance(topMid, botMid);

            var dust = new GameObject("Moon Dust");
            dust.transform.SetPositionAndRotation((topMid + botMid) * 0.5f, Quaternion.LookRotation(dir, Vector3.up));
            var ps = dust.AddComponent<ParticleSystem>();
            ps.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            var main = ps.main;
            main.loop = true;
            main.prewarm = true;
            main.startLifetime = new ParticleSystem.MinMaxCurve(8f, 14f);
            main.startSpeed = new ParticleSystem.MinMaxCurve(0f, 0.02f);
            main.startSize = new ParticleSystem.MinMaxCurve(0.006f, 0.016f);
            main.startColor = new ParticleSystem.MinMaxGradient(new Color(0.6f, 0.72f, 1f, 0.4f), new Color(0.85f, 0.9f, 1f, 0.8f));
            main.maxParticles = 400;
            main.simulationSpace = ParticleSystemSimulationSpace.World;
            var emission = ps.emission;
            emission.rateOverTime = 30f;
            var shape = ps.shape;
            shape.shapeType = ParticleSystemShapeType.Box;
            shape.scale = new Vector3(win.size.x * 0.7f, win.size.y * 0.5f, length * 0.9f);
            var col = ps.colorOverLifetime;
            col.enabled = true;
            var fade = new Gradient();
            fade.SetKeys(
                new[] { new GradientColorKey(Color.white, 0f), new GradientColorKey(Color.white, 1f) },
                new[] { new GradientAlphaKey(0f, 0f), new GradientAlphaKey(1f, 0.2f), new GradientAlphaKey(1f, 0.8f), new GradientAlphaKey(0f, 1f) });
            col.color = fade;
            var noise = ps.noise;
            noise.enabled = true;
            noise.strength = 0.05f;
            noise.frequency = 0.3f;
            noise.scrollSpeed = 0.1f;
            var r = dust.GetComponent<ParticleSystemRenderer>();
            r.sharedMaterial = FogMaterial(DustMaterialPath, true);
            r.shadowCastingMode = ShadowCastingMode.Off;
            r.receiveShadows = false;
            ps.Play();
        }

        // textura moale (pata rotunda care se stinge spre margini) + material URP Particles/Unlit transparent
        static Material FogMaterial(string path, bool additive)
        {
            var tex = AssetDatabase.LoadAssetAtPath<Texture2D>(FogTexturePath);
            if (tex == null)
            {
                const int n = 128;
                tex = new Texture2D(n, n, TextureFormat.RGBA32, true) { wrapMode = TextureWrapMode.Clamp, name = "FogPuff" };
                var px = new Color[n * n];
                for (int y = 0; y < n; y++)
                    for (int x = 0; x < n; x++)
                    {
                        float dx = (x + 0.5f) / n * 2f - 1f, dy = (y + 0.5f) / n * 2f - 1f;
                        float d = Mathf.Clamp01(Mathf.Sqrt(dx * dx + dy * dy));
                        // putin zgomot ca sa nu para un cerc perfect
                        float wobble = 0.85f + 0.15f * Mathf.PerlinNoise(x * 0.06f, y * 0.06f);
                        float a = Mathf.Pow(1f - Mathf.SmoothStep(0f, 1f, d), 2f) * wobble;
                        px[y * n + x] = new Color(1f, 1f, 1f, a);
                    }
                tex.SetPixels(px);
                tex.Apply(true);
                AssetDatabase.CreateAsset(tex, FogTexturePath);
            }

            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (mat == null)
            {
                mat = new Material(Shader.Find("Universal Render Pipeline/Particles/Unlit"));
                AssetDatabase.CreateAsset(mat, path);
            }
            mat.SetTexture("_BaseMap", tex);
            mat.SetColor("_BaseColor", Color.white);
            mat.SetFloat("_Surface", 1f);
            // aditiv = lumina (raza lunii, praful); alpha = ceata care acopera
            mat.SetFloat("_Blend", additive ? 2f : 0f);
            mat.SetOverrideTag("RenderType", "Transparent");
            mat.SetInt("_SrcBlend", (int)UnityEngine.Rendering.BlendMode.SrcAlpha);
            mat.SetInt("_DstBlend", (int)(additive ? UnityEngine.Rendering.BlendMode.One : UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha));
            mat.SetFloat("_Cull", 0f); // raza se vede si din interior
            mat.SetInt("_ZWrite", 0);
            mat.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
            mat.renderQueue = (int)RenderQueue.Transparent;
            EditorUtility.SetDirty(mat);
            AssetDatabase.SaveAssets();
            return mat;
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
