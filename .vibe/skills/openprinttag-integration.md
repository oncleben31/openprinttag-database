---
name: OpenPrintTag Material Integration
description: Guide complet pour intégrer les matériaux d'un fabricant dans OpenPrintTag, basé sur l'expérience Francofil.
version: 1.0
author: Vibe Code (with oncleben31)
---

# 🎯 OpenPrintTag Material Integration Skill

---

## 📋 Overview
Guide **pratique et testé** pour intégrer un nouveau fabricant dans la base OpenPrintTag.
Basé sur l'expérience réelle avec **Francofil (99 matériaux)**.

---

## 🚀 Quick Start

### 1. Setup initial
```bash
git checkout main-pr && git pull origin main-pr
git checkout -b fabricant-{nom}
mkdir -p data/materials/{fabricant} data/material-packages/{fabricant}
```

### 2. Extraction initiale (si le fabricant existe déjà)
```bash
find data/materials -path "*/{fabricant}/*" -name "*.yaml" -exec cp {} data/materials/{fabricant}/ \;
find data/material-packages -path "*/{fabricant}/*" -name "*.yaml" -exec cp {} data/material-packages/{fabricant}/ \;
find data/material-containers -name "{fabricant}*.yaml" -exec cp {} data/material-containers/ \;
```

### 3. Premier commit
```bash
git add data/materials/{fabricant}/ data/material-packages/{fabricant}/ data/material-containers/
git commit -m "feat({fabricant}): initial extraction"
git push -u origin fabricant-{nom}
gh pr create --title "feat: Add {fabricant} materials" --draft
```

---

## 🔍 Tâche 1 : Suppression des doublons

### Comment identifier les doublons ?
```bash
# 1. Extraire toutes les URLs
grep -h "url:" data/materials/{fabricant}/*.yaml | sort -u > /tmp/urls.txt

# 2. Trouver les URLs dupliquées
sort /tmp/urls.txt | uniq -d > /tmp/duplicate_urls.txt

# 3. Lister les fichiers concernés
while read url; do
  echo "=== $url ==="
  grep -l "$url" data/materials/{fabricant}/*.yaml
done < /tmp/duplicate_urls.txt
```

### Règles de conservation
| Critère | À conserver | À supprimer |
|---------|-------------|-------------|
| **Langue** | Anglais (`asa-red`) | Français (`asa-rouge`) |
| **Nom** | Commence par le type (`PLA Black`) | Ne commence pas par le type (`Black PLA`) |
| **URL** | Version la plus complète | Version incomplète |

### Suppression et mise à jour
```bash
# Exemple : garder asa-red.yaml, supprimer asa-rouge.yaml
rm data/materials/{fabricant}/{fabricant}-asa-rouge.yaml

# Mettre à jour les références dans les packages
old="{fabricant}-asa-rouge"
new="{fabricant}-asa-red"
find data/material-packages/{fabricant}/ data/material-containers/ -name "*.yaml" -exec sed -i "s|$old|$new|g" {} \;
```

### Commit
```bash
git add -A
git commit -m "feat({fabricant}): remove duplicate materials"
```

---

## 🏷️ Tâche 2 : Normalisation des noms et slugs

### Pattern requis
```
{fabricant}-{type}-{name}.yaml
```
✅ `francofil-pla-translucent-blue.yaml`
❌ `francofil-translucent-blue-pla.yaml`

### Script de normalisation
```bash
#!/bin/bash
cd data/materials/{fabricant}

for file in *.yaml; do
    # Extraire le type depuis le YAML
    type=$(grep "^type:" "$file" | awk '{print $2}' | tr '[:upper:]' '[:lower:]')
    
    # Construire le nouveau nom
    base=$(basename "$file" .yaml)
    new_name="${base/#${fabricant}-/$fabricant-$type-}"
    
    if [ "$file" != "$new_name.yaml" ]; then
        mv "$file" "$new_name.yaml"
        sed -i "s|^slug: .*|slug: $new_name|" "$new_name.yaml"
        echo "Renamed: $file -> $new_name.yaml"
    fi
done
```

### Vérification des noms
```bash
# Trouver les matériaux dont le nom ne commence pas par le type
for file in *.yaml; do
    type=$(grep "^type:" "$file" | awk '{print $2}' | tr '[:upper:]' '[:lower:]')
    name=$(grep "^name:" "$file" | cut -d' ' -f2-)
    if [[ ! "$name" =~ ^$type ]]; then
        echo "⚠️  $file: '$name' should start with '$type'"
        # Correction automatique
        new_name="${type} ${name}"
        sed -i "s|^name: .*|name: $new_name|" "$file"
    fi
done
```

### Mise à jour des références
```bash
# Mettre à jour tous les packages et conteneurs
for file in *.yaml; do
    slug=$(grep "^slug:" "$file" | awk '{print $2}')
    find ../../material-packages/{fabricant}/ ../../material-containers/ -name "*.yaml" -exec sed -i "s|{fabricant}-[^/]*|$slug|g" {} \;
done
```

### Commit
```bash
git add -A
git commit -m "feat({fabricant}): normalize filenames and slugs"
```

---

## 📊 Tâche 3 : Extraction des propriétés techniques

### ⚠️ RÈGLE D'OR
**NE JAMAIS utiliser les fiches techniques PDF génériques.**
- Elles donnent des valeurs moyennes qui ne correspondent pas aux matériaux spécifiques.
- **Exemple** : PETG ESD nécessite 270-290°C, pas 235-260°C (valeur standard PETG).

---

### Méthode recommandée : Parsing HTML
Les pages produits ont des tableaux **bien structurés en HTML** avec `<th>` et `<td>`.

#### Script Python complet
```python
#!/usr/bin/env python3
import urllib.request
import re
import yaml
import os
from pathlib import Path

FABRICANT = "{fabricant}"  # À remplacer
MATERIALS_DIR = f"data/materials/{FABRICANT}"
HEADERS = {'User-Agent': 'Mozilla/5.0'}

DEFAULT_DENSITIES = {
    "PLA": 1.24, "PETG": 1.30, "ASA": 1.06,
    "ABS": 1.01, "TPU": 1.15, "TPE": 1.15
}

def extract_properties(html):
    props = {}
    match = re.search(r'Printing parameters.*?</table>', html, re.DOTALL | re.IGNORECASE)
    if not match:
        return props
    
    pairs = re.findall(r'<th[^>]*>([^<]+)</th>.*?<td[^>]*>([^<]+)</td>', match.group(0), re.DOTALL)
    for th, td in pairs:
        th = th.strip().lower()
        td = td.strip().replace('\xa0', ' ').replace('\u00b0', ' ')
        
        temps = re.findall(r'(\d+)\s*[-–]\s*(\d+)', td)
        if temps:
            min_t, max_t = int(temps[0][0]), int(temps[0][1])
            if 'nozzle temperature' in th:
                props['min_print_temperature'] = min_t
                props['max_print_temperature'] = max_t
            elif 'bed temperature' in th or 'heated bed' in th:
                props['min_bed_temperature'] = min_t
                props['max_bed_temperature'] = max_t
    return props

def main():
    updated = 0
    for yaml_file in Path(MATERIALS_DIR).glob("*.yaml"):
        with open(yaml_file, 'r') as f:
            material = yaml.safe_load(f)
            url = material.get('url', '')
            if not url:
                continue
            
            try:
                req = urllib.request.Request(url, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=30) as response:
                    html = response.read().decode('utf-8')
                    props = extract_properties(html)
                    
                    # Ajouter densité par défaut si manquante
                    mat_type = material.get('type', '')
                    if 'density' not in material.get('properties', {}) and mat_type in DEFAULT_DENSITIES:
                        props['density'] = DEFAULT_DENSITIES[mat_type]
                    
                    if props:
                        material.setdefault('properties', {}).update(props)
                        with open(yaml_file, 'w') as f_out:
                            yaml.dump(material, f_out, sort_keys=False, default_flow_style=False, allow_unicode=True)
                        updated += 1
                        print(f"✅ {material.get('slug')}: {props}")
            except Exception as e:
                print(f"⚠️  {material.get('slug')}: {e}")
    
    print(f"\n📊 {updated} matériaux mis à jour")

if __name__ == "__main__":
    main()
```

#### Exécution
```bash
chmod +x extract_properties.py
python3 extract_properties.py
```

---

### Champs valides du schéma
```yaml
properties:
  min_print_temperature: 240    # °C (entier)
  max_print_temperature: 260    # °C (entier)
  min_bed_temperature: 90      # °C (entier)
  max_bed_temperature: 110     # °C (entier)
  density: 1.06                # g/cm³ (float)
```

### Commit
```bash
git add data/materials/{fabricant}/*.yaml
git commit -m "feat({fabricant}): add printing properties from product pages"
```

---

## 🏷️ Tâche 4 : Tags et Certifications

---

### 📋 Tags valides (enum du schéma)
| Catégorie | Tags |
|-----------|------|
| **Filtration** | `filtration_recommended` |
| **Écologie** | `biocompatible`, `home_compostable`, `industrially_compostable`, `bio_based`, `recycled` |
| **Mécanique** | `abrasive`, `self_extinguishing`, `foaming`, `castable` |
| **Électrique** | `esd_safe`, `conductive`, `emi_shielding`, `antibacterial`, `air_filtering` |
| **Additifs** | `contains_metal`, `contains_ceramic`, `contains_glass_fiber`, `contains_ptfe`, `contains_carbon_fiber`, `contains_wood`, `contains_organic_material` |
| **Visuels** | `translucent`, `transparent`, `without_pigments`, `glitter`, `glow_in_the_dark` |
| **Certifications** | `ul_2818`, `ul_94_v0`, `ul_2904` |

⚠️ **RoHS, REACH, FDA, PMUC ne sont PAS dans le schéma** → Créer une issue pour les proposer.

---

### Script pour ajouter les tags
```python
#!/usr/bin/env python3
import urllib.request
import re
import yaml
from pathlib import Path

FABRICANT = "{fabricant}"
MATERIALS_DIR = f"data/materials/{FABRICANT}"
HEADERS = {'User-Agent': 'Mozilla/5.0'}

TAG_RULES = {
    'biocompatible': [r'food contact', r'food safety', r'alimentaire'],
    'abrasive': [r'\babrasive\b'],
    'esd_safe': [r'\bESD\b', r'anti-static'],
    'contains_metal': [r'metallic particles', r'M-XR'],
    'contains_ceramic': [r'ceramic particles'],
    'contains_glass_fiber': [r'fiberglass', r'glass fiber'],
    'contains_ptfe': [r'\bPTFE\b', r'Teflon'],
    'contains_carbon_fiber': [r'carbon fiber'],
    'contains_wood': [r'\bwood\b', r'\bbois\b'],
    'industrially_compostable': [r'compostable'],
    'low_outgassing': [r'low outgassing'],
    'filtration_recommended': [r'filtration'],
    'translucent': [r'\btranslucent\b'],
    'glow_in_the_dark': [r'phosphorescent'],
    'glitter': [r'\bglitter\b'],
}

def main():
    for yaml_file in Path(MATERIALS_DIR).glob("*.yaml"):
        with open(yaml_file, 'r') as f:
            material = yaml.safe_load(f)
            url = material.get('url', '')
            existing_tags = material.get('tags', [])
            
            if not url:
                continue
            
            try:
                req = urllib.request.Request(url, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=30) as response:
                    html = response.read().decode('utf-8')
                    content = re.search(r'(?s)Printing parameters.*?Additional information', html)
                    content = content.group(0) if content else html
                    
                    new_tags = []
                    for tag, patterns in TAG_RULES.items():
                        if tag in existing_tags:
                            continue
                        for pattern in patterns:
                            if re.search(pattern, content, re.IGNORECASE):
                                new_tags.append(tag)
                                break
                    
                    if new_tags:
                        material['tags'] = existing_tags + new_tags
                        with open(yaml_file, 'w') as f_out:
                            yaml.dump(material, f_out, sort_keys=False, default_flow_style=False, allow_unicode=True)
                        print(f"🏷️  {material.get('slug')}: +{new_tags}")
            except Exception as e:
                print(f"⚠️  {material.get('slug')}: {e}")

if __name__ == "__main__":
    main()
```

### Commit
```bash
git add data/materials/{fabricant}/*.yaml
git commit -m "feat({fabricant}): add missing tags"
```

---

## 📝 Tâche 5 : Validation finale et gestion du PR

---

### Checklist de validation
```bash
# 1. Vérifier le pattern des fichiers
ls data/materials/{fabricant}/ | grep -vE '^{fabricant}-[a-z]+-[a-z0-9-]+\.yaml$' && echo "❌ Fichiers non conformes" || echo "✅ Pattern OK"

# 2. Vérifier slugs vs noms de fichiers
for f in data/materials/{fabricant}/*.yaml; do
    slug=$(grep "^slug:" "$f" | awk '{print $2}')
    expected=$(basename "$f" .yaml)
    [ "$slug" != "$expected" ] && echo "❌ $f: slug '$slug' != '$expected'"
done

# 3. Vérifier noms vs types
for f in data/materials/{fabricant}/*.yaml; do
    type=$(grep "^type:" "$f" | awk '{print $2}' | tr '[:upper:]' '[:lower:]')
    name=$(grep "^name:" "$f" | cut -d' ' -f2-)
    [[ ! "$name" =~ ^$type ]] && echo "❌ $f: '$name' should start with '$type'"
done

# 4. Vérifier les doublons
grep -h "url:" data/materials/{fabricant}/*.yaml | sort | uniq -d | while read url; do
    echo "❌ Duplicata: $url"
    grep -l "$url" data/materials/{fabricant}/*.yaml
done

# 5. Vérifier les propriétés manquantes
no_props=$(grep -l "properties: {}" data/materials/{fabricant}/*.yaml | wc -l)
[ "$no_props" -gt 0 ] && echo "⚠️  $no_props matériaux sans propriétés" || echo "✅ Toutes les propriétés sont présentes"
```

---

### Mettre à jour le PR
```bash
git push origin fabricant-{fabricant}
gh pr edit $(gh pr list --head fabricant-{fabricant} --json number -q '.[0].number') \
  --title "feat: Add {fabricant} materials with complete properties" \
  --body-file pr-body.md
```

---

### Exemple de `pr-body.md`
```markdown
## Summary
- Added {X} materials from {fabricant}
- Normalized filenames: `{fabricant}-{type}-{name}.yaml`
- Extracted properties from product pages
- Added tags: esd_safe, contains_glass_fiber, biocompatible, etc.
- Removed {Y} duplicates

## Files
- `data/materials/{fabricant}/`: {X} files
- `data/material-packages/{fabricant}/`: {Z} files

## Properties
| Type | Count | Nozzle Temp | Bed Temp |
|------|-------|-------------|----------|
| PLA  | {N}   | 200-230°C   | 30-70°C  |
| PETG | {N}   | 220-260°C   | 70-90°C  |

## Special Cases
- {fabricant}-petg-esd-red: 270-290°C / 80-85°C (ESD additives)
- {fabricant}-petg-detectable-m-xr: biocompatible (food contact)

## Notes
- Properties from product pages only (no generic datasheets)
- See [Issue #27](link) for table formatting issues
- See [Issue #29](link) for schema enhancement (RoHS/REACH/FDA)
```

---

## 💡 Astuces et Bonnes Pratiques

---

### 1. Déboguer une page produit
```bash
python3 -c "
import urllib.request, re
url = 'https://fabricant.com/product/xyz'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as r:
    html = r.read().decode('utf-8')
    table = re.search(r'Printing parameters.*?</table>', html, re.DOTALL)
    print(table.group(0) if table else 'Tableau non trouvé')
"
```

---

### 2. Vérifier les URLs en double
```bash
grep -h "url:" data/materials/{fabricant}/*.yaml | sort | uniq -d
```

---

### 3. Compter par type
```bash
grep -h "type:" data/materials/{fabricant}/*.yaml | sort | uniq -c | sort -rn
```

---

### 4. Normalisation rapide des noms
```bash
for f in data/materials/{fabricant}/*.yaml; do
    new=$(echo "$f" | sed 's/ /-/g; s/--/-/g')
    [ "$f" != "$new" ] && mv "$f" "$new" && sed -i "s|slug: .*|slug: $(basename "$new" .yaml)|" "$new"
done
```

---

### 5. Mise à jour des références
```bash
old="ancien-slug"
new="nouveau-slug"
find data/material-packages/{fabricant}/ data/material-containers/ -name "*.yaml" -exec sed -i "s|$old|$new|g" {} \;
```

---

### 6. Validation YAML
```bash
python3 -c "
import yaml, sys
for f in sys.argv[1:]:
    try:
        with open(f) as file: yaml.safe_load(file)
        print(f'✅ {f}')
    except Exception as e:
        print(f'❌ {f}: {e}')
" data/materials/{fabricant}/*.yaml
```

---

## ⚠️ Pièges Courants et Solutions

| Problème | Cause | Solution |
|----------|-------|----------|
| **Tableaux illisibles** | `web_fetch` retourne du texte brut mal formaté | Utiliser `urllib.request` + parsing HTML |
| **Faux positifs (tags)** | Mots-clés dans footer/navigation | Limiter la recherche à la section produit |
| **Certifications non supportées** | Schéma limité à UL | Créer une issue (ex: [#29](https://github.com/oncleben31/openprinttag-database/issues/29)) |
| **Doublons non détectés** | URLs différentes mais même matériau | Vérifier manuellement noms/descriptions |
| **Propriétés incohérentes** | Utilisation de fiches techniques génériques | **Toujours** utiliser les pages produits |
| **Erreurs YAML** | Fichiers mal formatés | Réécrire avec `yaml.dump()` |
| **Températures aberrantes** | Erreur sur le site fabricant | Vérifier et corriger manuellement |

---

## 📚 Ressources

- **Schéma OpenPrintTag** : [OpenPrintTag/openprinttag-architecture](https://github.com/OpenPrintTag/openprinttag-architecture)
- **Fichiers clés** :
  - `openprinttag/schema/material.schema.json`
  - `openprinttag/schema/material_properties.schema.json`
- **Issues de référence** :
  - [#27](https://github.com/oncleben31/openprinttag-database/issues/27) : Problème de formatage des tableaux
  - [#29](https://github.com/oncleben31/openprinttag-database/issues/29) : Proposition de certifications

---

## ✅ Checklist Finale

- [ ] Branche `fabricant-{nom}` créée
- [ ] Fichiers initiaux extraits
- [ ] Doublons supprimés
- [ ] Noms de fichiers normalisés (`{fabricant}-{type}-{name}.yaml`)
- [ ] Slugs mis à jour
- [ ] Noms des matériaux commencent par leur type
- [ ] Propriétés extraites depuis les pages produits
- [ ] Tags valides ajoutés
- [ ] Références mises à jour
- [ ] Validation passée
- [ ] PR créé/mis à jour

---

**🎉 Conseils finaux :**
1. Commencez par 5-10 matériaux pour valider la méthodologie
2. Scriptz tout ce qui est répétitif
3. Vérifiez souvent avec `git status` et `git diff`
4. Documentez les cas spéciaux dans le PR
