# Storypinner

Un spatiu VR al tau, in care iti aranjezi cu mainile pozele si textele de pe calculator, iar aplicatia te ajuta sa legi ideile intre ele si sa continui o poveste pe care ai scris-o.

**Meta Quest 2, Hand Tracking** (tema Innovative User Experience)

Team members: Aluculesei Robert (proiect individual)

## Document

State of the art, features, user journey, componente, moodboard si tehnologii:
https://docs.google.com/document/d/1ISRN_SnLLyiOWoaZlD__LqiLcTXfk2tYprkik-1qxUc/edit?usp=sharing

Tema 5 - Main Modules (user story map, journey maps, storyboard, planul de asset-uri):
https://docs.google.com/document/d/1Y4efqNdeUUfywyRKNcmhAzpjsgUnVZtKMHkzw0swKtA/edit?usp=sharing

Storyboard-ul (schitele din document) e in `docs/storyboard`, desenat cu `docs/tools/storyboard.py`.

## Pe scurt

O camera virtuala (modelata dupa camera mea de acasa) in care fisierele de pe PC apar ca niste carduri. Le prinzi cu mana, le lipesti pe pereti sau le lasi sa pluteasca.

- Fire si drumuri: legi texte intre ele cu fire, alegi dintr-un dropdown ce sa faca AI-ul (Continua textul, Scoate idei sau un prompt facut de mine) si primesti 3 drumuri pe care poate merge povestea.
- Imagini si taguri: apesi pe o imagine si vezi descrierea si tagurile ei; apesi pe un tag si vezi alte imagini, taguri sau fisiere legate de el. Un + langa card da sugestii.
- Cartea ca lant: un text lung e impartit in scene, puse in ordine si deja legate.

Prezentare partiala: camera, cardurile din fisierele de pe PC, prinderea si lipirea cu mainile, firele, dropdown-ul cu Continua textul, notita noua si salvarea camerei.

Prezentare finala: drumurile multiple, prompturile mele, descrierea si tagurile, butonul +, imaginile asemanatoare, cartea ca lant si studiul.

## Structura

- `Unity/` - aplicatia VR (Unity 6000.6.4f1, URP), cu acelasi setup VR ca la laboratoare: XR Interaction Toolkit 3.6.1 (Starter Assets + XR Device Simulator), OpenXR 1.18.0 pe Standalone cu profilul Oculus Touch (Quest prin Link / Air Link)
  - `Assets/Scenes/Room.unity` - scena simpla: camera goala + fiecare obiect ca instanta separata a unui model din `Models/`, pus dupa `layout.json`; XR Origin pe pozitia de start, iar cardurile, fisele, cartea, tagurile si butonul + se pot prinde cu controller-ul (meniul Storypinner > Build Room Scene)
  - `Assets/Scenes/Graybox.unity` - aceeasi camera, dintr-un singur FBX (Storypinner > Build Graybox Scene)
  - `Assets/Graybox/` - camera exportata din Blender (`Graybox.fbx`), modelele separate cu pivotul in origine (`Models/`: carduri, raft, carte, dropdown, bule de taguri, butonul +, fir, mobila), materialele URP si scriptul care face scena (meniul Storypinner > Build Graybox Scene)
- `Blender/graybox.py` - graybox-ul camerei, doar cutii si sfere la scara reala; `blender -b -P Blender/graybox.py` reface `graybox.blend` (tot + modelele pe un rand), `room.blend` (camera mobilata cu instante ale modelelor), `Graybox.fbx`, `Models/`, `RoomShell.fbx` si `layout.json`
- `docs/` - storyboard-ul si sursa documentului de la Tema 5
- serverul de pe PC (Node) se bazeaza pe hub-ul meu Soft Shape: fisiere, indexare CLIP, taguri JoyTag/WD14, apeluri catre model

## Progres saptamanal

### Saptamana 1

- Ideea si documentul de state of the art
- Repo-ul

### Saptamana 2

- Tema 5: user story map (creator, participant la studiu, cercetator), 3 journey maps, storyboard de 11 cadre, planul de asset-uri
- Planul camerei la scara si graybox-ul ei in Blender (camera 4.0 x 3.2 x 2.6 m, mobila, raftul cu sertare, carduri A5 si imagine, firele, 3 drumuri, dropdown-ul, tagurile si butonul +, cartea), importat intr-o scena Unity
