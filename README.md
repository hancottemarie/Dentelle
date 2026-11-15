# Bobbin Lace Generator
## Architecture dossier du projet
bobbin-lace-generator/
├── docker-compose.yml              # Orchestration locale en 1 commande
├── Makefile                        # Commandes rapides (install, dev, test)
├── README.md
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt            # fastapi, uvicorn, opencv-python-headless, scikit-image, shapely, reportlab, svgwrite, pydantic
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # Endpoints FastAPI (/upload, /generate, /export/pdf, /export/svg)
│   │   ├── models.py               # Schémas Pydantic (PatternConfig, ZoneData, StitchDefinition)
│   │   ├── data/
│   │   │   └── stitches.json       # Base de connaissances des points de dentelle
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── lace_engine.py      # Segmentation OpenCV/Skimage, grilles 45°/60°, pavage Shapely
│   │   │   ├── border_ornaments.py # Génération de picots, coquilles et festons le long des contours
│   │   │   ├── pdf_exporter.py     # Export PDF ReportLab 1:1 strict avec mire 10x10 mm
│   │   │   └── svg_exporter.py     # Export SVG vectoriel à l'échelle mm
│   └── tests/
│       ├── test_grid_accuracy.py   # Tests unitaires de précision millimétrique (< 0.001 mm)
│       └── test_segmentation.py
│
└── frontend/
    ├── package.json                # react, react-dom, react-konva, konva, lucide-react, tailwindcss
    ├── vite.config.js
    └── src/
        ├── App.jsx                 # État global du patron et synchronisation API (debounce 150ms)
        ├── api/
        │   └── laceApi.js          # Client HTTP vers FastAPI
        └── components/
            ├── LaceCanvas.jsx      # Canvas Konva.js (zoom/pan, sélection de zones, rendu 60fps)
            ├── ControlPanel.jsx    # Curseurs (taille mm, pas, difficulté, densité, ornements)
            └── StitchCatalog.jsx   # Cases à cocher des points maîtrisés par l'utilisateur

## Modèle de données des points (backend/app/data/stitches.json)
    Chaque point est défini dans un repère local normalisé où $(0, 0)$ est l'intersection courante de la grille, $u$ est le vecteur unitaire le long de l'axe horizontal de la maille et $v$ est le vecteur unitaire le long de l'axe incliné ($45^\circ$ ou $60^\circ$). Cela permet d'adapter dynamiquement n'importe quel point à n'importe quel pas en millimètres (pitch_mm).
## Moteur géométrique Python(backend/app/core/lace_engine.py)
    Ce module implémente la segmentation morphologique en 3 zones (Contours/Meneurs, Remplissage, Fond), la mise à l'échelle exacte en millimètres, le pavage sur grilles $45^\circ$ ou $60^\circ$, l'application des règles de filtrage (points connus + difficulté) et la génération des ornements de bordure.

## Générateur PDF à l'échelle stricte 1:1 (backend/app/core/pdf_exporter.py)
    Ce module utilise l'unité native mm de ReportLab ($1\text{ mm} = 2.83464567\text{ pt}$) pour garantir une précision géométrique absolue lors de l'impression sur papier cartonné ou bristol. Il adapte dynamiquement le format de page (A4, A3 ou format sur mesure avec marges de $15\text{ mm}$) et intègre systématiquement le carré de calibration de $10 \times 10\text{ mm}$.

## Schémas de validation Pydantic (backend/app/models.py)
    Ce fichier garantit la validation stricte des paramètres envoyés par les curseurs temps réel de l'interface React (pas en mm, angle $45^\circ/60^\circ$, niveau de difficulté, liste des points maîtrisés et surcharges manuelles par zone).

## Exportateur SVG à l'échelle millimétrique (backend/app/core/svg_exporter.py)
    Ce module complète pdf_exporter.py en générant un fichier vectoriel SVG dont les attributs width, height et viewBox sont exprimés directement en millimètres (mm) pour être ouvert dans Inkscape ou découpé/perforé sur machine.

## Point d'entrée API FastAPI (backend/app/main.py)
    Ce serveur expose tous les endpoints nécessaires à l'application : contrôle de santé, lecture du catalogue de points, import et segmentation d'image avec mise en cache en mémoire (pour que les déplacements de curseurs s'exécutent en moins de 150 ms sans re-segmenter l'image), et exports PDF/SVG.

Initialisation et dépendances (frontend/package.json & vite.config.js)

Créez le dossier frontend/ à la racine de votre dépôt Dentelle et ajoutez ces deux fichiers de configuration :
Client HTTP vers FastAPI (frontend/src/api/laceApi.js)

Ce service gère la communication avec les endpoints FastAPI (/api/stitches, /api/upload, /api/generate, /api/export/pdf et /api/export/svg).
Catalogue des points maîtrisés (frontend/src/components/StitchCatalog.jsx)Affiche la liste interactive des points avec leur badge de difficulté ($1$ à $5$), l'angle compatible ($45^\circ / 60^\circ$) et le filtrage visuel en temps réel.


Panneau de contrôle temps réel (frontend/src/components/ControlPanel.jsx)Regroupe tous les curseurs dynamiques (largeur globale en mm, pas de grille, angle $45^\circ/60^\circ$, niveau de difficulté, densité et ornements de bordure) ainsi que les boutons d'export PDF/SVG à l'échelle 1:1.

Canvas vectoriel interactif (frontend/src/components/LaceCanvas.jsx)Utilise react-konva pour afficher le carton à haute vitesse ($60\text{ FPS}$), gérer le zoom à la molette, le déplacement (pan), l'affichage optionnel de l'image source en calque semi-transparent et le menu contextuel permettant de forcer un point spécifique au clic sur n'importe quelle zone.

Assemblage principal avec debounce temps réel (frontend/src/App.jsx)Synchronise le panneau de contrôle, le sauvegarde automatique des points maîtrisés dans localStorage, le recalcul temps réel déporté sur FastAPI (avec debounce de $150\text{ ms}$) et le canvas Konva.


