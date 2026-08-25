# Arianeplast — état des travaux

Document de reprise. Dernière mise à jour : session 3 (2026-08-25) — le lot A et
le lot B ont été traités ensemble, `data/` est écrit et validé.

## Mission

Compléter la base OpenPrintTag pour le fabricant **Arianeplast, et lui seul**.

Règles imposées par l'utilisateur :

1. **Ne rien inventer.** Toute information doit provenir du site du fabricant,
   <https://arianeplast.com>. Ce qui n'y figure pas est listé comme tel dans
   `findings.md`, jamais comblé d'ailleurs.
2. **Respecter le schéma** — `bash scripts/fetch_schemas.sh`, puis
   `make validate`.
3. **Anglais prioritaire**, en sachant que la traduction du site est incomplète
   *et parfois fausse* (voir plus bas).
4. **Ménager le serveur** : cache obligatoire, crawl limité au périmètre.
5. **Branche de travail** : `claude/arianeplast-openprinttag-resume-nwxj31`.

## Accès réseau

Résolu. L'allowlist est exacte par hôte ; `www.arianeplast.com` a été ouvert en
début de session 3 et répond 200. `cache.py` autorise les deux hôtes. Le sitemap
anglais est servi par l'apex, les pages produit par `www`.

## Arbitrages rendus par l'utilisateur (session 3)

1. **Lot A et lot B ensemble**, une seule vague d'écriture, pour ne pas changer
   deux fois les UUID.
2. **Périmètre : la totalité du catalogue PLA**, pas seulement les 4 catégories
   du périmètre initial.
3. `industrially_compostable` **retiré** des 77 fiches qui le portaient sans
   source, remplacé par `bio_based`.
4. Les 13 produits sans nom anglais sur le site sont **traduits via un tableau
   versionné** (`SHOP_MISTRANSLATIONS` et `FR_EN`), pas laissés en français.
5. Les couleurs en conflit : **on garde la valeur de la fiche conservée** et on
   documente qu'aucune n'est sourçable — le site ne publie aucun code couleur.
6. Les échantillons 10 m ne donnent **pas** de `MaterialPackage` : le schéma
   exige un poids net, que le fabricant ne publie pas pour ce format.

## Ce qui a été fait

`data/` contient désormais, pour Arianeplast :

| | avant | après |
|---|---|---|
| Materials | 78 | **116** |
| MaterialPackages | 0 | **271** (222 avec GTIN) |
| fiches avec `properties` | 0 | **115** |
| fiches avec `primary_color` | 77 | 71 (les 6 doublons fusionnés) |

`make validate` passe.

Les 6 paires de doublons sont fusionnées, chacune dans le même commit que les
packages qui préservent les formats qu'elles portaient. Une fiche sans annonce
en ligne est conservée : `arianeplast-pla-skin-2r15sp` est intacte.

## Ce qu'il faut savoir avant de toucher à ce fabricant

* **La traduction anglaise du site est automatique et parfois fausse.**
  « huître » y devient *Eighth* (huit), « pêche » devient *Fishing*, « moule »
  devient *Mould*. Ces erreurs ne font pas que mal nommer : elles scindent un
  même produit en deux groupes. Le tableau de correction est dans
  `reconcile.py`, avec la source de chaque cas.
* **Le `<h1>` n'est pas la source du nom anglais** : il est tantôt anglais
  tantôt français selon le produit. Le `<title>` est anglais mais **tronqué à
  ~70 caractères**. Les lignes `Color Family` et `Effect` de la fiche technique
  sont les seules chaînes anglaises fiables.
* **Le blob `data-product="…"` de PrestaShop** porte tout ce qui compte : SKU,
  EAN-13 par variante, fiche technique, description. `extract.py` le lit plutôt
  que de gratter le HTML.
* **Le même produit est libellé différemment selon le format** : « RAL 3020 » /
  « RAL3020 » / rien, un « 3D » isolé, un préfixe « fil » ou « bobine de fil »
  sur la plupart des annonces 2,3 kg, « Metal » dans les recharges là où les
  bobines disent « métallisé ».
* **Une incohérence non tranchée** : l'annonce `2624` est classée en 8 kg mais
  son titre et son poids net disent 2,3 kg ; seuls son SKU et sa catégorie
  disent 8 kg. Un seul package est écrit, et `build.py` le signale à chaque
  exécution.

## Outillage

```
tools/arianeplast/
├── crawl.py        crawl piloté par le sitemap, limité aux catégories données
├── cache.py        cache disque : 1 requête par URL, TTL 30 j, délai 2 s
├── extract.py      pages en cache -> enregistrements structurés (hors ligne)
├── reconcile.py    regroupe les annonces en produits, confronte à data/
├── build.py        seul outil qui écrit dans data/
├── decisions.yaml  les arbitrages, en données plutôt qu'en code
├── analyze_db.py   audit hors ligne de l'existant
├── search_cache.py recherche regex dans le cache
├── findings.md     ce que le fabricant documente, et ce qu'il ne dit pas
└── merge_plan.yaml **périmé** — proposition de la session 2, remplacée par
                    decisions.yaml et par le rapport de reconcile.py
```

Chaîne complète :

```bash
python3 tools/arianeplast/crawl.py                       # ~344 pages, ~12 min
python3 tools/arianeplast/extract.py -o extracted.yaml
python3 tools/arianeplast/reconcile.py --records extracted.yaml -o report.yaml
python3 tools/arianeplast/build.py --report report.yaml --dry-run
python3 tools/arianeplast/build.py --report report.yaml
make validate
```

**Attention à l'ordre** : `reconcile.py` lit `data/`. Le relancer après un
`build.py` produit un rapport qui décrit l'état construit, pas l'état de départ.

Note d'environnement : le `python3` du conteneur est en 3.11, le projet exige
3.12+. Utiliser `python3.13` ou `venv/bin/python`.

## Ce qui reste ouvert

* **Les 5 filaments de marquage laser** (`3d-filaments-marquage-laser-`) : le
  site ne nomme jamais leur polymère. Hors périmètre tant que ce n'est pas
  tranché.
* **Les couleurs.** 45 fiches n'ont pas de `primary_color` faute de source, et
  les 10 valeurs partagées par des produits distincts restent suspectes. Le
  fabricant ne publie aucun code couleur : il faudrait le lui demander.
* **Les gammes chargées huître et moule** exigent une buse ≥ 0,5 mm d'après la
  fiche technique (`min_nozzle_diameter: 500`), ce que le build ne pose pas
  encore.
* **Le séchage** n'est documenté que pour la gamme carbone (60 °C).
* Les **fiches de sécurité** (MSDS) n'ont pas été dépouillées.
