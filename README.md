# Storypinner

Un spatiu VR al tau, in care iti aranjezi cu mainile pozele si textele de pe calculator, iar aplicatia te ajuta sa legi ideile intre ele si sa continui o poveste pe care ai scris-o.

**Meta Quest 2, Hand Tracking** (tema Innovative User Experience)

Team members: Aluculesei Robert (proiect individual)

## Document

State of the art, features, user journey, componente, moodboard si tehnologii:
https://docs.google.com/document/d/1ISRN_SnLLyiOWoaZlD__LqiLcTXfk2tYprkik-1qxUc/edit?usp=sharing

## Pe scurt

O camera virtuala (modelata dupa camera mea de acasa) in care fisierele de pe PC apar ca niste carduri. Le prinzi cu mana, le lipesti pe pereti sau le lasi sa pluteasca.

- Fire si drumuri: legi texte intre ele cu fire, alegi dintr-un dropdown ce sa faca AI-ul (Continua textul, Scoate idei sau un prompt facut de mine) si primesti 3 drumuri pe care poate merge povestea.
- Imagini si taguri: apesi pe o imagine si vezi descrierea si tagurile ei; apesi pe un tag si vezi alte imagini, taguri sau fisiere legate de el. Un + langa card da sugestii.
- Cartea ca lant: un text lung e impartit in scene, puse in ordine si deja legate.

Prezentare partiala: camera, cardurile din fisierele de pe PC, prinderea si lipirea cu mainile, firele, dropdown-ul cu Continua textul, notita noua si salvarea camerei.

Prezentare finala: drumurile multiple, prompturile mele, descrierea si tagurile, butonul +, imaginile asemanatoare, cartea ca lant si studiul.

## Structura

- `Unity/` - aplicatia VR: proiectul de baza (Unity 6000.6.4f1, URP); Meta XR SDK urmeaza
- serverul de pe PC (Node) se bazeaza pe hub-ul meu Soft Shape: fisiere, indexare CLIP, taguri JoyTag/WD14, apeluri catre model

## Progres saptamanal

### Saptamana 1

- Ideea si documentul de state of the art
- Repo-ul
