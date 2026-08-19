# 📜 Instructions pour Mistral Code – Cohérence de la Base de Données OpenPrintTag

> **Objectif** : Assurer la cohérence entre la base de données OpenPrintTag et les catalogues des fabricants (ex: Arianeplast, Francofil).
> **Cible** : Agents IA (Mistral Code), contributeurs humains, et scripts automatisés.

---

## 🔹 1. Structure de la Base de Données

### 1.1. Répertoires et Fichiers
- **Matériaux** : `data/materials/<brand>/<brand>-<type>-<color>-<variant>.yaml`
  - Exemple : `arianeplast-pla-plus-aluminum-metallic.yaml`
  - Contenu : `slug`, `name`, `type`, `brand_specific_id`, `url`, `tags`, etc.

- **Packages Matériaux** : `data/material-packages/<brand>/<brand>-<type>-<color>-<weight>-<container>.yaml`
  - Exemple : `arianeplast-abs-black-1000-spool.yaml`
  - Contenu : `slug`, `material.slug`, `container`, `url`, `nominal_netto_full_weight`, etc.

### 1.2. Conventions de Nommage
| Type | Règle | Exemple |
|------|-------|---------|
| **Matériau** | `brand-type-color-variant` | `arianeplast-abs-anthracite-grey` |
| **Package Spool** | `brand-type-color-weight-spool` | `arianeplast-abs-black-1000-spool` |
| **Package Refill** | `brand-type-color-weight-refill` | `arianeplast-abs-black-1000-refill` |
| **PLA+** | Utiliser `pla-plus` dans le slug | `arianeplast-pla-plus-aluminum-metallic` |
| **Couleurs** | Utiliser des noms en anglais (sauf exceptions, voir §3.3) | `black`, `anthracite-grey` |
| **Variantes** | Ajouter des suffixes si nécessaire | `-metallic`, `-recycled`, `-eco` |

---

## 🔹 2. Identification des Types de Packages

### 2.1. **Spool (Bobine)**
- **Fichier** : Suffixe `-spool` dans le nom du fichier.
- **Champ `container`** : **Obligatoire** (ex: `spool-750`, `spool-1000`, `spool-2000`).
- **Exemple** :
  ```yaml
  slug: arianeplast-abs-black-1000-spool
  material:
    slug: arianeplast-abs-black
  container: spool-1000
  ```

### 2.2. **Refill (Recharge)**
- **Fichier** : Suffixe `-refill` dans le nom du fichier.
- **Champ `container`** : **Absent** (pas de conteneur physique).
- **Exemple** :
  ```yaml
  slug: arianeplast-abs-black-1000-refill
  material:
    slug: arianeplast-abs-black
  # Pas de champ 'container'
  ```

### 2.3. **Règle Supplémentaire**
- **Ignorer les packs multi-bobines** : Ne pas inclure les entrées catalogue du fabricant qui représentent des packs de plusieurs bobines (ex: "Pack 2x PLA Noir 1kg").

---

## 🔹 3. Règles de Nommage et Traduction

### 3.1. **Préfixe par Type de Matériau**
- **Tous les matériaux** doivent commencer par leur type dans le `name` et le `slug`.
  - Exemples :
    - `ABS Black` → `arianeplast-abs-black`
    - `PLA+ Aluminum Metallic` → `arianeplast-pla-plus-aluminum-metallic`
    - `PETG Translucent` → `arianeplast-petg-translucent`

### 3.2. **Types de Matériaux Standardisés**
| Type | Slug | Exemple de Nom |
|------|------|----------------|
| ABS | `abs` | `ABS Black` |
| ASA | `asa` | `ASA Black` |
| HIPS | `hips` | `HIPS White` |
| PCTG | `pctg` | `PCTG Clear` |
| PETG | `petg` | `PETG Black` |
| PLA | `pla` | `PLA White` |
| PLA+ | `pla-plus` | `PLA+ Aluminum Metallic` |
| PVA | `pva` | `PVA Soluble` |
| PS | `ps` | `PS Clear` |
| TPU | `tpu` | `TPU Black` |

### 3.3. **Traduction des Couleurs et Variantes**
- **Règle générale** : Utiliser des noms **en anglais** pour les couleurs et variantes.
  - Exemples :
    - `Noir` → `Black`
    - `Blanc` → `White`
    - `Rouge` → `Red`
    - `Vert` → `Green`
    - `Bleu` → `Blue`
    - `Gris Anthracite` → `Anthracite Grey`
    - `Or` → `Gold`
    - `Argent` → `Silver`
    - `Translucide` → `Translucent`
    - `Métallique` → `Metallic`

- **Exceptions (mots français conservés)** :
  Certains termes **n'ont pas d'équivalent standard en anglais** ou sont des marques déposées. Dans ce cas, **conserver le terme français** et **créer un issue de suivi** (ex: #24, #25).
  - Exemples autorisés :
    - `Bleu/gris` (pas d'équivalent exact en anglais)
    - `Liège/Cork` (mélange de termes)
    - `Noël` (dans `PLA Rouge Noël` → `PLA Red Christmas`)
  - **À éviter** :
    - `Flatter` (mauvaise traduction de "Flat" ou "Matte") → **Supprimer et remplacer par `Black`**
    - `Vert 4043D` → `Green 4043D` (si 4043D est un code couleur standard)

### 3.4. **Gestion des Duplicatas**
- **Détection** : Utiliser des scripts pour identifier les matériaux/packages avec des noms ou slugs similaires.
- **Fusion** : 
  - **Conserver le slug le plus explicite** (ex: `abs-anthracite-grey` plutôt que `abs-grey-anthracite`).
  - **Mettre à jour toutes les références** dans les packages.
  - **Supprimer l'ancien matériau** s'il n'a plus de références.
- **Exemple** :
  - `abs-anthracite-gray` + `abs-grey-anthracite` → **Fusionner en `abs-anthracite-grey`** (standardisation sur `grey` plutôt que `gray`).

---

## 🔹 4. Gestion des Matériaux Orphelins

### 4.1. **Définition d'un Matériau Orphelin**
- Un matériau est **orphelin** s'il **n'a aucune référence** dans un `MaterialPackage`.
- Vérifier avec :
  ```bash
  grep -r "material:" data/material-packages/<brand>/ | grep -c "<material-slug>"
  ```

### 4.2. **Actions à Entreprendre**
| Cas | Action |
|-----|--------|
| Matériau orphelin **sans URL valide** | **Supprimer** (ex: `arianeplast-pla-eco` si pas de page produit). |
| Matériau orphelin **avec URL valide** | **Vérifier manuellement** :
| | - Si l'URL pointe vers une **catégorie** (ex: "PLA Eco") → **Supprimer**. |
| | - Si l'URL pointe vers un **produit valide** → **Créer un package manquant**. |
| Matériau orphelin **créé par erreur** (ex: doublon) | **Supprimer**. |

### 4.3. **Outils pour Détecter les Orphelins**
```bash
# Lister tous les matériaux
MATERIALS=$(ls data/materials/<brand>/ | sed 's/.yaml//g')

# Lister tous les matériaux référencés dans les packages
REFERENCED=$(grep -h "slug:" data/material-packages/<brand>/* | sed 's/slug: //g' | sort -u)

# Trouver les orphelins
for mat in $MATERIALS; do
  if ! echo "$REFERENCED" | grep -q "$mat"; then
    echo "Orphelin: $mat"
  fi
done
```

---

## 🔹 5. Vérification de Cohérence avec le Site du Fabricant

### 5.1. **Méthodologie de Scraping**
- **Outils autorisés** :
  - `curl` + `grep`/`awk`/`jq` (pour extraire des données structurées).
  - `Python` avec `requests` + `BeautifulSoup` (si autorisé dans le sandbox).
  - **Alternative** : Utiliser des **dumps locaux** du site (fournis par l'utilisateur).

- **Cibles prioritaires** :
  - **Sitemap XML** : `https://<fabricant>.com/sitemap.xml` (liste toutes les URLs).
  - **Pages produits** : Filtrer les URLs contenant `/produit/` ou `/product/`.
  - **Catégories** : Ignorer les pages de type `/category/` ou `/categorie/`.

### 5.2. **Exemple de Script de Scraping (Bash)**
```bash
#!/bin/bash
BRAND="arianeplast"
SITEMAP_URL="https://www.arianeplast.com/sitemap.xml"

# Télécharger le sitemap
curl -s $SITEMAP_URL | grep -oP 'https?://[^<]+\.html' > /tmp/$BRAND_urls.txt

# Filtrer les pages produits (exemple)
grep -E "/produit/|/product/" /tmp/$BRAND_urls.txt > /tmp/$BRAND_products.txt

# Compter les produits par type (ABS, PLA, PETG, etc.)
for type in abs pla petg tpu asa; do
  count=$(grep -i "$type" /tmp/$BRAND_products.txt | wc -l)
  echo "$type: $count produits"
done
```

### 5.3. **Comparaison avec la Base de Données**
- **Pour chaque type de matériau** (ABS, PLA, PETG, etc.) :
  1. Compter le nombre de **produits spool** sur le site.
  2. Compter le nombre de **produits refill** sur le site.
  3. Comparer avec :
     ```bash
     # Compter les packages spool dans la DB
     ls data/material-packages/$BRAND/*-$type*-spool.yaml | wc -l
     
     # Compter les packages refill dans la DB
     ls data/material-packages/$BRAND/*-$type*-refill.yaml | wc -l
     ```
  4. **Si incohérence** :
     - Vérifier les **URLs manquantes** dans la DB.
     - Vérifier les **fichiers orphelins** (matériaux sans packages).
     - Corriger en **ajoutant/supprimant** les entrées nécessaires.

### 5.4. **Règle Spéciale : Ignorer les Packs Multi-Bobines**
- **Exemple** : Un pack "2x PLA Noir 1kg" sur le site du fabricant **ne doit pas** être ajouté comme un package unique.
- **Comment les détecter** :
  - Rechercher des mots-clés comme `pack`, `lot`, `bundle`, `2x`, `3x`, etc. dans les noms de produits.
  - Exclure ces URLs de la comparaison.

---

## 🔹 6. Procédures de Correction

### 6.1. **Renommage de Fichiers**
- **Utiliser `git mv`** pour renommer les fichiers (conserve l'historique).
  ```bash
  git mv data/materials/arianeplast/arianeplast-abs-old.yaml data/materials/arianeplast/arianeplast-abs-new.yaml
  ```
- **Mettre à jour les références** dans les packages :
  ```bash
  sed -i 's/arianeplast-abs-old/arianeplast-abs-new/g' data/material-packages/arianeplast/*.yaml
  ```

### 6.2. **Suppression de Fichiers**
- **Supprimer les orphelins** :
  ```bash
  git rm data/materials/arianeplast/arianeplast-pla-eco.yaml
  ```
- **Vérifier les dépendances** avant suppression :
  ```bash
  grep -r "arianeplast-pla-eco" data/material-packages/arianeplast/
  ```

### 6.3. **Création de Nouveaux Fichiers**
- **Structure d'un matériau** :
  ```yaml
  slug: arianeplast-abs-new-color
  name: ABS New Color
  type: ABS
  brand_specific_id: "NEW123"
  url: https://www.arianeplast.com/produit/abs-new-color
  tags:
    - abs
    - new-color
  ```
- **Structure d'un package** :
  ```yaml
  slug: arianeplast-abs-new-color-1000-spool
  material:
    slug: arianeplast-abs-new-color
  container: spool-1000
  url: https://www.arianeplast.com/produit/abs-new-color-1kg
  nominal_netto_full_weight: 1000
  ```

### 6.4. **Génération de UUIDs**
- **Pour les nouveaux matériaux** : Générer un UUID v4 unique.
  ```bash
  uuidgen
  ```
- **Ne pas réutiliser** les UUIDs des matériaux supprimés.

---

## 🔹 7. Validation et Tests

### 7.1. **Vérifications Automatiques**
- **Script de validation** (à exécuter avant chaque commit) :
  ```bash
  #!/bin/bash
  BRAND="arianeplast"
  
  # 1. Vérifier que tous les packages ont un matériau valide
  for pkg in data/material-packages/$BRAND/*.yaml; do
    mat_slug=$(grep "material:" $pkg | awk '{print $2}')
    if [ ! -f "data/materials/$BRAND/$mat_slug.yaml" ]; then
      echo "❌ Package $pkg référence un matériau inexistant: $mat_slug"
      exit 1
    fi
  done
  
  # 2. Vérifier que les spools ont un container
  for spool in data/material-packages/$BRAND/*-spool.yaml; do
    if ! grep -q "container:" $spool; then
      echo "❌ Spool sans container: $spool"
      exit 1
    fi
  done
  
  # 3. Vérifier que les refills n'ont PAS de container
  for refill in data/material-packages/$BRAND/*-refill.yaml; do
    if grep -q "container:" $refill; then
      echo "❌ Refill avec container: $refill"
      exit 1
    fi
  done
  
  # 4. Vérifier que les slugs de matériaux commencent par leur type
  for mat in data/materials/$BRAND/*.yaml; do
    slug=$(grep "^slug:" $mat | awk '{print $2}')
    type=$(grep "^type:" $mat | awk '{print $2}')
    if [[ ! $slug == $BRAND-$type* ]]; then
      echo "❌ Matériau $slug ne commence pas par $BRAND-$type"
      exit 1
    fi
  done
  
  echo "✅ Toutes les vérifications passées !"
  ```

### 7.2. **Tests Manuels**
- **Vérifier visuellement** 10-20 entrées aléatoires dans :
  - `data/materials/$BRAND/`
  - `data/material-packages/$BRAND/`
- **Comparer avec le site du fabricant** :
  - Ouvrir 5-10 URLs aléatoires pour confirmer qu'elles pointent vers des produits valides.

---

## 🔹 8. Gestion des Issues GitHub

### 8.1. **Créer un Issue pour les Incohérences**
- **Titre** : `[<Brand>] <Description de l'incohérence>`
  - Exemple : `[Arianeplast] Incohérence PLA: 71 spools en DB vs 288 sur le site`
- **Labels** : `coherence`, `<brand>`, `to-investigate`
- **Contenu** :
  ```markdown
  ## Description
  - **Type** : PLA
  - **Attendu** : 288 spools + 51 refills (site fabricant)
  - **Actuel** : 71 spools + 23 refills (DB)
  - **Écart** : -217 spools, -28 refills
  
  ## Actions Proposées
  - [ ] Vérifier les URLs manquantes
  - [ ] Ajouter les packages manquants
  - [ ] Supprimer les orphelins
  
  ## Liens
  - [Site Arianeplast - PLA](https://www.arianeplast.com/categorie/pla)
  ```

### 8.2. **Issues Existants**
- **#24** : [Arianeplast: French translation inconsistencies in material names](https://github.com/oncleben31/openprinttag-database/issues/24)
- **#25** : [Arianeplast: Naming decisions and translation liberties](https://github.com/oncleben31/openprinttag-database/issues/25)

---

## 🔹 9. Workflow Recommandé

### 9.1. **Pour un Nouveau Fabricant**
1. **Scraper le site** pour obtenir la liste des produits.
2. **Créer les matériaux** en suivant les règles de nommage (§3).
3. **Créer les packages** (spool/refill) avec les bons suffixes (§2).
4. **Valider** avec le script de vérification (§7.1).
5. **Ouvrir un PR** avec une description claire des changements.

### 9.2. **Pour Mettre à Jour un Fabricant Existant**
1. **Comparer** le catalogue actuel avec le site (§5).
2. **Identifier les incohérences** (manquants, doublons, orphelins).
3. **Corriger** en suivant les procédures (§6).
4. **Valider** et **tester** (§7).
5. **Créer un issue** si des incohérences persistent (§8).

### 9.3. **Pour Résoudre une Incohérence Spécifique**
1. **Isoler le problème** (ex: ABS a 28 spools sur le site vs 30 en DB).
2. **Lister les différences** :
   ```bash
   # Spools ABS dans la DB
   ls data/material-packages/arianeplast/*-abs*-spool.yaml
   
   # Spools ABS sur le site (à extraire via scraping)
   grep -i "abs" /tmp/arianeplast_products.txt
   ```
3. **Corriger** :
   - Supprimer les entrées en trop.
   - Ajouter les entrées manquantes.
   - Renommer les entrées mal nommées.

---

## 🔹 10. Exemples Concrets (Arianeplast)

### 10.1. **Correction d'un Matériau Mal Nommé**
- **Problème** : `arianeplast-asa-black-flatter` (mauvaise traduction de "flatter").
- **Solution** :
  ```bash
  # Renommer le matériau
  git mv data/materials/arianeplast/arianeplast-asa-black-flatter.yaml data/materials/arianeplast/arianeplast-asa-black.yaml
  
  # Mettre à jour le nom dans le fichier
  sed -i 's/name: ASA Black Flatter/name: ASA Black/g' data/materials/arianeplast/arianeplast-asa-black.yaml
  
  # Mettre à jour les références dans les packages
  sed -i 's/arianeplast-asa-black-flatter/arianeplast-asa-black/g' data/material-packages/arianeplast/*-asa-black*.yaml
  
  # Renommer les packages si nécessaire
  git mv data/material-packages/arianeplast/arianeplast-asa-black-flatter-1000-spool.yaml data/material-packages/arianeplast/arianeplast-asa-black-1000-spool.yaml
  ```

### 10.2. **Fusion de Doublons (ABS)**
- **Problème** : `arianeplast-abs-grey-anthracite` et `arianeplast-abs-anthracite-gray` sont des doublons.
- **Solution** :
  ```bash
  # Renommer le premier matériau
  git mv data/materials/arianeplast/arianeplast-abs-grey-anthracite.yaml data/materials/arianeplast/arianeplast-abs-anthracite-grey.yaml
  
  # Mettre à jour le nom
  sed -i 's/name: ABS Grey Anthracite/name: ABS Anthracite Grey/g' data/materials/arianeplast/arianeplast-abs-anthracite-grey.yaml
  
  # Mettre à jour les références dans les packages
  sed -i 's/arianeplast-abs-grey-anthracite/arianeplast-abs-anthracite-grey/g' data/material-packages/arianeplast/*.yaml
  
  # Supprimer l'ancien matériau (s'il n'a plus de références)
  git rm data/materials/arianeplast/arianeplast-abs-anthracite-gray.yaml
  ```

### 10.3. **Suppression d'un Orphelin**
- **Problème** : `arianeplast-pla-eco` n'a aucun package associé.
- **Solution** :
  ```bash
  # Vérifier qu'il n'a pas de références
  grep -r "arianeplast-pla-eco" data/material-packages/arianeplast/
  
  # Si aucune référence, supprimer
  git rm data/materials/arianeplast/arianeplast-pla-eco.yaml
  ```

---

## 🔹 11. Outils Recommandés

| Outil | Usage |
|-------|-------|
| `git` | Gestion des versions et des branches. |
| `grep`/`awk`/`sed` | Recherche et remplacement dans les fichiers. |
| `curl` | Scraping basique de sites web. |
| `jq` | Parsing de JSON (si le site a une API). |
| `uuidgen` | Génération de UUIDs pour les nouveaux matériaux. |
| `Python` (si autorisé) | Scraping avancé avec `requests` + `BeautifulSoup`. |

---

## 🔹 12. Checklist avant Commit

- [ ] Tous les **matériaux** commencent par leur type dans le `slug` et le `name`.
- [ ] Tous les **packages spool** ont un suffixe `-spool` et un champ `container`.
- [ ] Tous les **packages refill** ont un suffixe `-refill` et **pas de champ `container`**.
- [ ] Aucune **référence à un matériau inexistant** dans les packages.
- [ ] Aucun **matériau orphelin** (sans package) n'est présent (sauf si validé manuellement).
- [ ] Les **noms de couleurs** sont en anglais (sauf exceptions documentées).
- [ ] Les **PLA+** utilisent `pla-plus` dans le slug.
- [ ] Les **URLs** pointent vers des pages produits valides (pas des catégories).
- [ ] Les **doublons** ont été fusionnés ou supprimés.
- [ ] Un **issue GitHub** a été créé pour les incohérences non résolues.

---

## 🔹 13. Contacts et Ressources

- **Repository** : [oncleben31/openprinttag-database](https://github.com/oncleben31/openprinttag-database)
- **Issues** : [GitHub Issues](https://github.com/oncleben31/openprinttag-database/issues)
- **Documentation** : [README.md](README.md)
- **Branches de référence** :
  - `arianeplast-only` : Modifications Arianeplast uniquement.
  - `francofil-updates` : Modifications Francofil uniquement.

---

> **⚠️ Note Importante** : Ces instructions sont **évolutives**. Mettre à jour ce document en cas de nouvelles règles ou exceptions.
> **Dernière mise à jour** : `$(date +%Y-%m-%d)`
