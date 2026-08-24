#!/usr/bin/env python3
"""
Script pour corriger les doublons et standardiser les noms des matériaux Arianeplast.

Règles appliquées :
1. Tous les noms sont en anglais
2. Format : "PLA+ [Modificateur] [Couleur]"
3. Utilisation de "grey" au lieu de "gray"
4. Correction des fautes ("mtallis" -> "metallic")
5. Standardisation des slugs et noms de fichiers
"""

import os
import yaml
import re
import shutil
from pathlib import Path

# Répertoire des matériaux Arianeplast
MATERIALS_DIR = Path("data/materials/arianeplast")

# Mappings pour les corrections
# Format: {ancien_nom_fichier: (nouveau_nom_fichier, nouveau_name, nouveau_slug)}
CORRECTIONS = {
    # Fautes d'orthographe (mtallis -> metallic)
    "arianeplast-pla-noir-mtallis.yaml": ("arianeplast-pla-metallic-black.yaml", "PLA+ Metallic Black", "arianeplast-pla-metallic-black"),
    "arianeplast-pla-rouge-mtallis.yaml": ("arianeplast-pla-metallic-red.yaml", "PLA+ Metallic Red", "arianeplast-pla-metallic-red"),
    "arianeplast-pla-vert-mtallis.yaml": ("arianeplast-pla-metallic-green.yaml", "PLA+ Metallic Green", "arianeplast-pla-metallic-green"),
    "arianeplast-pla-rose-mtallis.yaml": ("arianeplast-pla-metallic-pink.yaml", "PLA+ Metallic Pink", "arianeplast-pla-metallic-pink"),
    
    # Traduction FR -> EN (noir -> black)
    "arianeplast-pla-noir.yaml": ("arianeplast-pla-black.yaml", "PLA+ Black", "arianeplast-pla-black"),
    
    # Traduction FR -> EN (rouge -> red)
    "arianeplast-pla-rouge.yaml": ("arianeplast-pla-red.yaml", "PLA+ Red", "arianeplast-pla-red"),
    
    # Standardisation grey au lieu de gray
    "arianeplast-pla-gray.yaml": ("arianeplast-pla-grey.yaml", "PLA+ Grey", "arianeplast-pla-grey"),
    "arianeplast-pla-silk-gray.yaml": ("arianeplast-pla-silk-grey.yaml", "PLA+ Silk Grey", "arianeplast-pla-silk-grey"),
    
    # Correction format inversé (Grey PLA+ -> PLA+ Grey)
    "arianeplast-grey-pla.yaml": ("arianeplast-pla-grey.yaml", "PLA+ Grey", "arianeplast-pla-grey"),
    "arianeplast-light-grey-pla.yaml": ("arianeplast-pla-light-grey.yaml", "PLA+ Light Grey", "arianeplast-pla-light-grey"),
    
    # Traduction FR -> EN (rose -> pink)
    "arianeplast-pla-rose-metallic.yaml": ("arianeplast-pla-metallic-pink.yaml", "PLA+ Metallic Pink", "arianeplast-pla-metallic-pink"),
    "arianeplast-pla-silk-rose.yaml": ("arianeplast-pla-silk-pink.yaml", "PLA+ Silk Pink", "arianeplast-pla-silk-pink"),
    "arianeplast-pla-rose-translucide.yaml": ("arianeplast-pla-translucent-pink.yaml", "PLA+ Translucent Pink", "arianeplast-pla-translucent-pink"),
    
    # Traduction FR -> EN (violet -> purple)
    "arianeplast-pla-metallic-violet.yaml": ("arianeplast-pla-metallic-purple.yaml", "PLA+ Metallic Purple", "arianeplast-pla-metallic-purple"),
    "arianeplast-pla-violet-translucide.yaml": ("arianeplast-pla-translucent-purple.yaml", "PLA+ Translucent Purple", "arianeplast-pla-translucent-purple"),
    
    # Suppression de vert 4043D (non une nuance)
    "arianeplast-pla-vert-4043d.yaml": None,  # Supprimer
    
    # Standardisation blue/grey -> blue-grey
    "arianeplast-pla-bluegrey.yaml": ("arianeplast-pla-blue-grey.yaml", "PLA+ Blue Grey", "arianeplast-pla-blue-grey"),
    
    # Correction casse (yellow -> Yellow)
    "arianeplast-pla-yellow.yaml": ("arianeplast-pla-yellow.yaml", "PLA+ Yellow", "arianeplast-pla-yellow"),
    
    # Standardisation des couleurs vert avec Pantone (conserver Pantone)
    "arianeplast-pla-vert-pantone-3268c.yaml": ("arianeplast-pla-pantone-3268c-green.yaml", "PLA+ Pantone 3268C Green", "arianeplast-pla-pantone-3268c-green"),
    
    # Standardisation translucent (minuscule -> majuscule)
    "arianeplast-pla-translucent-blue.yaml": ("arianeplast-pla-translucent-blue.yaml", "PLA+ Translucent Blue", "arianeplast-pla-translucent-blue"),
    "arianeplast-pla-translucent-green.yaml": ("arianeplast-pla-translucent-green.yaml", "PLA+ Translucent Green", "arianeplast-pla-translucent-green"),
    "arianeplast-pla-translucent-bottle-green.yaml": ("arianeplast-pla-translucent-bottle-green.yaml", "PLA+ Translucent Bottle Green", "arianeplast-pla-translucent-bottle-green"),
    
    # Standardisation Metallic (minuscule -> majuscule)
    "arianeplast-pla-metallic-blue.yaml": ("arianeplast-pla-metallic-blue.yaml", "PLA+ Metallic Blue", "arianeplast-pla-metallic-blue"),
    "arianeplast-pla-metallic-purple.yaml": ("arianeplast-pla-metallic-purple.yaml", "PLA+ Metallic Purple", "arianeplast-pla-metallic-purple"),
    "arianeplast-pla-metallic-ochre.yaml": ("arianeplast-pla-metallic-ochre.yaml", "PLA+ Metallic Ochre", "arianeplast-pla-metallic-ochre"),
    "arianeplast-pla-metallic-aluminum.yaml": ("arianeplast-pla-metallic-aluminum.yaml", "PLA+ Metallic Aluminum", "arianeplast-pla-metallic-aluminum"),
    "arianeplast-pla-metallic-anthracite-gray.yaml": ("arianeplast-pla-metallic-anthracite-grey.yaml", "PLA+ Metallic Anthracite Grey", "arianeplast-pla-metallic-anthracite-grey"),
    "arianeplast-pla-metallic-interferential-blue.yaml": ("arianeplast-pla-metallic-interferential-blue.yaml", "PLA+ Metallic Interferential Blue", "arianeplast-pla-metallic-interferential-blue"),
    "arianeplast-pla-metallic-red.yaml": ("arianeplast-pla-metallic-red.yaml", "PLA+ Metallic Red", "arianeplast-pla-metallic-red"),
    "arianeplast-pla-metallic-violet.yaml": ("arianeplast-pla-metallic-violet.yaml", "PLA+ Metallic Purple", "arianeplast-pla-metallic-purple"),
    
    # Standardisation Silk
    "arianeplast-pla-silk-black.yaml": ("arianeplast-pla-silk-black.yaml", "PLA+ Silk Black", "arianeplast-pla-silk-black"),
    "arianeplast-pla-silk-white.yaml": ("arianeplast-pla-silk-white.yaml", "PLA+ Silk White", "arianeplast-pla-silk-white"),
    "arianeplast-pla-silk-blue.yaml": ("arianeplast-pla-silk-blue.yaml", "PLA+ Silk Blue", "arianeplast-pla-silk-blue"),
    
    # Standardisation Pearl
    "arianeplast-pla-pearl-blue.yaml": ("arianeplast-pla-pearl-blue.yaml", "PLA+ Pearl Blue", "arianeplast-pla-pearl-blue"),
    "arianeplast-pla-pearl-white.yaml": ("arianeplast-pla-pearl-white.yaml", "PLA+ Pearl White", "arianeplast-pla-pearl-white"),
    
    # Standardisation Fluorescent/Safety
    "arianeplast-pla-fluorescent-yellow.yaml": ("arianeplast-pla-fluorescent-yellow.yaml", "PLA+ Fluorescent Yellow", "arianeplast-pla-fluorescent-yellow"),
    "arianeplast-pla-safety-yellow.yaml": ("arianeplast-pla-safety-yellow.yaml", "PLA+ Safety Yellow", "arianeplast-pla-safety-yellow"),
    
    # Standardisation DNA Anti-counterfeiting
    "arianeplast-pla-dna-anti-counterfeiting-black.yaml": ("arianeplast-pla-dna-anti-counterfeiting-black.yaml", "PLA+ DNA Anti-counterfeiting Black", "arianeplast-pla-dna-anti-counterfeiting-black"),
    "arianeplast-pla-dna-anti-counterfeiting-white.yaml": ("arianeplast-pla-dna-anti-counterfeiting-white.yaml", "PLA+ DNA Anti-counterfeiting White", "arianeplast-pla-dna-anti-counterfeiting-white"),
    
    # Standardisation autres couleurs
    "arianeplast-pla-navy-blue.yaml": ("arianeplast-pla-navy-blue.yaml", "PLA+ Navy Blue", "arianeplast-pla-navy-blue"),
    "arianeplast-pla-france-blue.yaml": ("arianeplast-pla-france-blue.yaml", "PLA+ France Blue", "arianeplast-pla-france-blue"),
    "arianeplast-pla-yellow-ocher.yaml": ("arianeplast-pla-yellow-ochre.yaml", "PLA+ Yellow Ochre", "arianeplast-pla-yellow-ochre"),
    "arianeplast-pla-yellow-gold.yaml": ("arianeplast-pla-yellow-gold.yaml", "PLA+ Yellow Gold", "arianeplast-pla-yellow-gold"),
    "arianeplast-pla-yellow-pantone-116u.yaml": ("arianeplast-pla-pantone-116u-yellow.yaml", "PLA+ Pantone 116U Yellow", "arianeplast-pla-pantone-116u-yellow"),
    "arianeplast-pla-ultra-violet-pantone-5f4b8b.yaml": ("arianeplast-pla-pantone-5f4b8b-purple.yaml", "PLA+ Pantone 5F4B8B Purple", "arianeplast-pla-pantone-5f4b8b-purple"),
    
    # Conservation des Skin (nuances spécifiques)
    "arianeplast-pla-skin-2r15sp.yaml": ("arianeplast-pla-skin-2r15sp.yaml", "PLA+ Skin 2R15SP", "arianeplast-pla-skin-2r15sp"),
    "arianeplast-pla-skin-3y09sp.yaml": ("arianeplast-pla-skin-3y09sp.yaml", "PLA+ Skin 3Y09SP", "arianeplast-pla-skin-3y09sp"),
    "arianeplast-pla-skin-5y06sp.yaml": ("arianeplast-pla-skin-5y06sp.yaml", "PLA+ Skin 5Y06SP", "arianeplast-pla-skin-5y06sp"),
    "arianeplast-pla-skin-5y09sp.yaml": ("arianeplast-pla-skin-5y09sp.yaml", "PLA+ Skin 5Y09SP", "arianeplast-pla-skin-5y09sp"),
    
    # Autres couleurs à vérifier
    "arianeplast-pla-green.yaml": ("arianeplast-pla-green.yaml", "PLA+ Green", "arianeplast-pla-green"),
    "arianeplast-pla-red.yaml": ("arianeplast-pla-red.yaml", "PLA+ Red", "arianeplast-pla-red"),
    "arianeplast-pla-white.yaml": ("arianeplast-pla-white.yaml", "PLA+ White", "arianeplast-pla-white"),
    "arianeplast-pla-purple.yaml": ("arianeplast-pla-purple.yaml", "PLA+ Purple", "arianeplast-pla-purple"),
    "arianeplast-pla-pink-bonbon.yaml": ("arianeplast-pla-pink-bonbon.yaml", "PLA+ Pink Bonbon", "arianeplast-pla-pink-bonbon"),
    "arianeplast-pla-pink-funky.yaml": ("arianeplast-pla-pink-funky.yaml", "PLA+ Pink Funky", "arianeplast-pla-pink-funky"),
    "arianeplast-pla-peach.yaml": ("arianeplast-pla-peach.yaml", "PLA+ Peach", "arianeplast-pla-peach"),
    "arianeplast-pla-oyster.yaml": ("arianeplast-pla-oyster.yaml", "PLA+ Oyster", "arianeplast-pla-oyster"),
    "arianeplast-pla-coral.yaml": ("arianeplast-pla-coral.yaml", "PLA+ Coral", "arianeplast-pla-coral"),
    "arianeplast-pla-pistachio.yaml": ("arianeplast-pla-pistachio.yaml", "PLA+ Pistachio", "arianeplast-pla-pistachio"),
    "arianeplast-pla-brown.yaml": ("arianeplast-pla-brown.yaml", "PLA+ Brown", "arianeplast-pla-brown"),
    "arianeplast-pla-sky.yaml": ("arianeplast-pla-sky.yaml", "PLA+ Sky", "arianeplast-pla-sky"),
    "arianeplast-pla-turquoise.yaml": ("arianeplast-pla-turquoise.yaml", "PLA+ Turquoise", "arianeplast-pla-turquoise"),
    "arianeplast-pla-natural.yaml": ("arianeplast-pla-natural.yaml", "PLA+ Natural", "arianeplast-pla-natural"),
    "arianeplast-pla-multicolor.yaml": ("arianeplast-pla-multicolor.yaml", "PLA+ Multicolor", "arianeplast-pla-multicolor"),
    "arianeplast-pla-moule.yaml": ("arianeplast-pla-moule.yaml", "PLA+ Moule", "arianeplast-pla-moule"),
    "arianeplast-pla-carbon.yaml": ("arianeplast-pla-carbon.yaml", "PLA+ Carbon", "arianeplast-pla-carbon"),
    "arianeplast-pla-copper.yaml": ("arianeplast-pla-copper.yaml", "PLA+ Copper", "arianeplast-pla-copper"),
    "arianeplast-pla-bordeaux.yaml": ("arianeplast-pla-bordeaux.yaml", "PLA+ Bordeaux", "arianeplast-pla-bordeaux"),
    "arianeplast-pla-gold.yaml": ("arianeplast-pla-gold.yaml", "PLA+ Gold", "arianeplast-pla-gold"),
    "arianeplast-pla-silver.yaml": ("arianeplast-pla-silver.yaml", "PLA+ Silver", "arianeplast-pla-silver"),
    "arianeplast-pla-ochre-orange.yaml": ("arianeplast-pla-ochre-orange.yaml", "PLA+ Ochre Orange", "arianeplast-pla-ochre-orange"),
    "arianeplast-pla-orange.yaml": ("arianeplast-pla-orange.yaml", "PLA+ Orange", "arianeplast-pla-orange"),
    "arianeplast-pla-khaki.yaml": ("arianeplast-pla-khaki.yaml", "PLA+ Khaki", "arianeplast-pla-khaki"),
    "arianeplast-pla-phosphorescent.yaml": ("arianeplast-pla-phosphorescent.yaml", "PLA+ Phosphorescent", "arianeplast-pla-phosphorescent"),
    "arianeplast-pla-electrically-conductive.yaml": ("arianeplast-pla-electrically-conductive.yaml", "PLA+ Electrically Conductive", "arianeplast-pla-electrically-conductive"),
    "arianeplast-pla-fluorescent-yellow.yaml": ("arianeplast-pla-fluorescent-yellow.yaml", "PLA+ Fluorescent Yellow", "arianeplast-pla-fluorescent-yellow"),
    "arianeplast-pla-safety-yellow.yaml": ("arianeplast-pla-safety-yellow.yaml", "PLA+ Safety Yellow", "arianeplast-pla-safety-yellow"),
    "arianeplast-light-grey-pla.yaml": ("arianeplast-pla-light-grey.yaml", "PLA+ Light Grey", "arianeplast-pla-light-grey"),
}


def load_yaml(filepath):
    """Charger un fichier YAML"""
    with open(filepath, 'r') as f:
        return yaml.safe_load(f) or {}


def save_yaml(filepath, data):
    """Sauvegarder un fichier YAML"""
    with open(filepath, 'w') as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


def process_files():
    """Traiter tous les fichiers selon les corrections définies"""
    files = list(MATERIALS_DIR.glob("*.yaml"))
    processed_files = set()
    
    print(f"Traitement de {len(files)} fichiers...")
    
    # D'abord, supprimer les fichiers à supprimer
    for old_filename, correction in CORRECTIONS.items():
        if correction is None:
            old_path = MATERIALS_DIR / old_filename
            if old_path.exists():
                print(f"  ✗ Suppression: {old_filename}")
                old_path.unlink()
    
    # Ensuite, renommer et mettre à jour les fichiers
    for old_filename, correction in CORRECTIONS.items():
        if correction is None:
            continue
        
        new_filename, new_name, new_slug = correction
        old_path = MATERIALS_DIR / old_filename
        new_path = MATERIALS_DIR / new_filename
        
        if not old_path.exists():
            print(f"  ⚠ Fichier introuvable: {old_filename}")
            continue
        
        # Charger les données
        data = load_yaml(old_path)
        
        # Mettre à jour les champs
        data['name'] = new_name
        data['slug'] = new_slug
        
        # S'assurer que la marque est correcte
        if 'brand' in data:
            if isinstance(data['brand'], dict):
                data['brand']['slug'] = 'arianeplast'
                data['brand']['name'] = 'Arianeplast'
            else:
                data['brand'] = {'slug': 'arianeplast', 'name': 'Arianeplast'}
        
        # Sauvegarder sous le nouveau nom
        if old_path != new_path:
            # Supprimer l'ancien fichier
            old_path.unlink()
            # Sauvegarder le nouveau
            save_yaml(new_path, data)
            print(f"  ✓ Renommé: {old_filename} -> {new_filename}")
            print(f"    Nom: {data.get('name', 'N/A')}")
            print(f"    Slug: {data.get('slug', 'N/A')}")
        else:
            # Juste mettre à jour le contenu
            save_yaml(old_path, data)
            print(f"  ✓ Mis à jour: {old_filename}")
            print(f"    Nom: {data.get('name', 'N/A')}")
            print(f"    Slug: {data.get('slug', 'N/A')}")
        
        processed_files.add(new_filename)
    
    # Vérifier s'il reste des fichiers non traités
    remaining_files = set(f.name for f in MATERIALS_DIR.glob("*.yaml")) - processed_files
    if remaining_files:
        print(f"\n⚠ Fichiers non traités ({len(remaining_files)}):")
        for f in sorted(remaining_files):
            print(f"  - {f}")
    
    print(f"\n✅ Traitement terminé!")


if __name__ == "__main__":
    # Vérifier qu'on est dans le bon répertoire
    if not MATERIALS_DIR.exists():
        print(f"Erreur: Le répertoire {MATERIALS_DIR} n'existe pas!")
        exit(1)
    
    # Créer une sauvegarde
    backup_dir = Path("/tmp/arianeplast_backup_final")
    backup_dir.mkdir(exist_ok=True)
    
    files = list(MATERIALS_DIR.glob("*.yaml"))
    for f in files:
        shutil.copy(f, backup_dir / f.name)
    
    print(f"Sauvegarde créée dans {backup_dir}")
    print()
    
    process_files()
