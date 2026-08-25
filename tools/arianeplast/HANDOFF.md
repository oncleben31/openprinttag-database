# Arianeplast — état des travaux (handoff)

Document de reprise pour une nouvelle session. Dernière mise à jour : 2026-08-25.

## Mission

Compléter la base OpenPrintTag pour le fabricant **Arianeplast, et lui seul**.
Ne toucher à aucun autre fabricant.

### Règles imposées par l'utilisateur

1. **Ne rien inventer.** Toute information ajoutée doit provenir du site du
   fabricant, <https://arianeplast.com>.
2. **Respecter le schéma** publié sur
   <https://arch.openprinttag.org/#/materials?id=materialproperties>.
   Le schéma est aussi disponible hors ligne dans le repo après
   `bash scripts/fetch_schemas.sh` → `openprinttag/schema/*.json`
   (version épinglée dans `schema_version.conf`).
3. **Anglais prioritaire.** Le site est bilingue mais la traduction anglaise est
   incomplète et incohérente d'un produit à l'autre.
4. **Ménager le serveur du fabricant** : passer par un cache, ne scraper que le
   périmètre de l'activité en cours.
5. **Branche de travail : `arianeplast-claude`** (créée, poussée).

## État du dépôt

- Branche `arianeplast-claude`, poussée sur `origin`, à jour.
- Dernier commit : `4dfdbd0` *Add Arianeplast audit tooling and cached scraper*.
- **`data/` n'a pas été modifié.** Aucune donnée n'a encore été corrigée.
- Ajouts : `tools/arianeplast/*` et une ligne `.cache/` dans `.gitignore`.

## BLOQUANT — accès réseau

`arianeplast.com` est **injoignable** depuis la session Claude Code : la
politique d'egress de l'environnement n'autorise qu'une liste blanche
(GitHub, PyPI, npm…) et refuse tout le reste.

```
"detail": "gateway answered 403 to CONNECT (policy denial or upstream failure)",
"host":   "www.arianeplast.com:443"
```

Vérification rapide dans une nouvelle session :

```bash
curl -sS "$HTTPS_PROXY/__agentproxy/status" | head -20
```

Le blocage n'a pas été contourné. Il faut autoriser `arianeplast.com` dans la
configuration réseau de l'environnement
(<https://code.claude.com/docs/en/claude-code-on-the-web>).

Tant qu'il tient, seules les corrections **ne nécessitant pas le site** sont
réalisables (voir « Prochaines étapes », lot A).

## Activité 1 — analyse de la base : FAITE

Rejouable à tout moment, hors ligne :

```bash
python3 tools/arianeplast/analyze_db.py     # nécessite Python 3.12+ ; ici python3.13
```

### Inventaire

**78 matériaux, 0 packaging.** Tous `class: FFF` / `type: PLA`.

Répartition par listing d'origine (format de bobine lu dans l'URL produit) :
`pla-format-8kg` 51 · `pla-format-1-kg` 20 · `pla-format-23kg` 6 ·
`filaments-carbone` 1.

**Cause racine des doublons** : l'import a créé une fiche par *annonce*, or
Arianeplast liste le même filament une fois par format de bobine. Dans le
modèle OpenPrintTag le format appartient à `MaterialPackage`, pas à `Material`.

Complétude : `properties: {}` sur **78/78**, aucun `MaterialPackage`,
1 fiche sans couleur (`arianeplast-pla-multicolor`).

### 6 paires de doublons confirmées

| # | Conserver | Supprimer | Couleurs |
|---|---|---|---|
| 1 | `pla-gray` *PLA+ Gray* (1 kg) | `grey-pla` *Grey PLA+* (8 kg) | identiques `#545f67` |
| 2 | `pla-green` *PLA+ Green* (8 kg) | `pla-vert-4043d` (1 kg) | ⚠️ `#3d9441` vs `#06b100` |
| 3 | `pla-rose-metallic` (8 kg) | `pla-rose-mtallis` (1 kg) | identiques `#b13566` |
| 4 | `pla-metallic-purple` (1 kg) | `pla-metallic-violet` (8 kg) | ⚠️ `#8873c7` vs `#ae96d4` |
| 5 | `pla-metallic-red` (8 kg) | `pla-rouge-mtallis` (1 kg) | ⚠️ `#bb5152` vs `#e0493e` |
| 6 | `pla-red` *PLA+ Red* (8 kg) | `pla-rouge` *PLA+ rouge* (1 kg) | ⚠️ `#e03f26` vs `#e72f1d` |

Confirmé par les slugs d'URL (`pla-gris` 8 kg ↔ `pla-gris-4043d` 1 kg, etc.).
Après fusion : **72 matériaux uniques**.

Paire 6 : les deux annonces indiquent **RAL 3020**, donc au moins une des deux
valeurs RGB est fausse. Les 4 conflits ⚠️ ne sont pas arbitrables hors ligne.

### Point critique — UUID

`Material::uuid` = UUIDv5(`NAMESPACE_MATERIAL` + `brand_uuid` + **`name`**),
cf. `scripts/uuid_utils.py`. **Les 78 UUID actuels dérivent tous correctement**
(vérifié). Donc *tout* changement de nom — **y compris une simple majuscule** —
impose de régénérer l'UUID.

`brand_uuid` Arianeplast = `c4eab185-1ed0-577b-a38d-c7630cf6dd18`.

Les UUID des noms proposés sont pré-calculés dans `merge_plan.yaml`.
4 survivants sur 6 gardent leur UUID (`gray`, `green`, `metallic-red`, `red`) ;
2 en changent (`metallic-purple` à cause de la majuscule, `rose-metallic` s'il
devient *Metallic Pink*).

### Autres anomalies relevées

- **13 noms non traduits** : `pla-noir`, `pla-noir-mtallis`, `pla-rouge`,
  `pla-rouge-mtallis`, `pla-vert-4043d`, `pla-vert-fluo`, `pla-vert-mtallis`,
  `pla-vert-pantone-3268c`, `pla-rose-translucide`, `pla-violet-translucide`,
  `pla-moule`, `pla-pink-bonbon`, `pla-rose-mtallis`.
- **5 slugs corrompus** : le slugifier de l'import a *supprimé* les accents au
  lieu de les translittérer → `métallisé` devient **`mtallis`** (4 fiches) ;
  `blue/grey` devient `bluegrey` sans séparateur.
- **2 fiches hors convention** : `arianeplast-grey-pla` et
  `arianeplast-light-grey-pla` mettent la couleur avant « PLA », les 76 autres
  suivent `arianeplast-pla-<couleur>`.
- **Orthographes concurrentes** : `Gray` ×3 vs `Grey` ×3 ; `Ochre` ×2 vs
  `Ocher` ×1 ; `violet` et `purple` pour la même couleur sur 4 fiches.
- **Traductions douteuses à vérifier sur le site** : `pla-blue` est nommé
  *PLA+ Blue* mais son URL est `pla-bleuet` (**bleuet = cornflower blue**) ;
  `pla-moule` — « moule » est ambigu (coquillage ou moulage ?), son voisin
  `pla-oyster` (huître) suggère une gamme couleurs-coquillage.
- **3 URL à corriger** (`pla-purple`, `pla-turquoise`, `pla-vert-fluo`) :
  elles pointent sur `/fr/`, avec un fragment `#/1-diametre-175mm` et un
  identifiant de listing dupliqué (`5048-1043-`).
- **10 codes couleur partagés par des produits distincts**, vraisemblablement
  pipettés sur des photos : `#0099e6` Silk Blue = Sky · `#0378d0` navy blue =
  Pearl Blue · `#40b6e4` Metallic blue = Turquoise · `#62e480` Phosphorescent =
  Translucent Green · `#e4ff33` Fluorescent Yellow = Translucent Yellow ·
  `#e2c077` **Skin 3Y09SP = 5Y06SP = 5Y09SP** (3 teintes, 1 valeur). Ce ne sont
  pas des doublons, mais des couleurs à re-saisir depuis les fiches produit.
- **15 fiches métallisées/nacrées sans tag visuel**, alors que le vocabulaire
  du schéma propose `pearlescent`, `iridescent`, `imitates_metal`
  (`openprinttag/data/material_tags.yaml`). `silk` et `translucent` sont, eux,
  correctement posés.
- `PLA+ Ultra Violet Pantone 5F4B8B` porte `#6459eb` : le nom annonce un hex
  qui n'est pas celui enregistré.

## Solution préconisée pour les doublons

1. **Fusionner en même temps que la création des packages, pas avant.**
   Supprimer la fiche 1 kg fait perdre la seule trace du format 1 kg. Il faut,
   dans le même lot : une fiche `Material` par couleur/finition, et un
   `MaterialPackage` par (couleur × format × diamètre) portant le GTIN, le
   poids et le container.
2. Conserver systématiquement la fiche au nom anglais.
3. Les 4 conflits de couleur exigent la page anglaise du fabricant — ils sont
   marqués `verify:` dans `merge_plan.yaml`, aucun n'a été tranché.
4. Ce nettoyage ne traite que les doublons *visibles*. Si un coloris existe en
   8 kg sans avoir été importé, la base restera incomplète — seul le crawl du
   catalogue le dira.

## Outillage livré

```
tools/arianeplast/
├── analyze_db.py      audit hors-ligne — régénère toute l'analyse ci-dessus
├── cache.py           cache disque : 1 requête max par URL, TTL 30 j,
│                      délai 2 s entre requêtes, allowlist d'hôte
├── crawl.py           crawl limité aux catégories passées en argument
│                      (gamme PLA par défaut) + pagination
├── search_cache.py    recherche regex dans le cache, sans réseau
├── merge_plan.yaml    plan de résolution, UUID pré-calculés, chaque point
│                      nécessitant le site marqué `verify:`
└── README.md          mode d'emploi
```

`.cache/` est git-ignoré : le HTML brut du fabricant n'a pas sa place dans la
base.

**État de test** : `analyze_db.py` et `search_cache.py` sont testés et
fonctionnels. `crawl.py --dry-run` fonctionne, mais **son extraction de liens
n'a jamais vu le HTML réel du site** — à ajuster à la première exécution
réseau.

Note d'environnement : le `python3` par défaut du conteneur est en 3.11, or le
projet exige 3.12+ (`uuid.uuid5` sur des `bytes`). Utiliser `python3.13`, ou
`make setup` puis `venv/bin/python`.

## Prochaines étapes

**Lot A — sans réseau, réalisable tout de suite**
- Corriger les 5 slugs corrompus (`mtallis`, `bluegrey`).
- Aligner les 2 fiches hors convention (`grey-pla`, `light-grey-pla`).
- Nettoyer les 3 URL `/fr/` + fragments.
- Uniformiser `Gray` / `Ochre`.
- Régénérer les UUID de toutes les fiches renommées, puis `make validate`.

**Lot B — dès que `arianeplast.com` est autorisé**
1. `python3 tools/arianeplast/crawl.py` sur la gamme PLA (≈ 80–100 pages,
   une seule fois, mises en cache).
2. Ajuster l'extraction de liens de `crawl.py` sur le HTML réel.
3. Trancher les 4 conflits de couleur et les noms marqués `verify:`.
4. Re-saisir les 10 couleurs suspectes depuis les fiches produit.
5. Remplir `properties` (températures buse/plateau, séchage…) — 0/78
   actuellement.
6. Créer les `MaterialPackage` (GTIN, poids, container) et fusionner les
   6 doublons dans le même lot.
7. Ajouter les tags visuels manquants (`pearlescent`, etc.) selon ce que dit
   la fiche produit.
