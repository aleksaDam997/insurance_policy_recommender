# Stacking Meta-Model — Dokumentacija

## Što je Stacking?

Stacking (ili *Stacked Generalization*) je tehnika ansambla gdje se **predikcije više modela koriste kao ulazni featurei za novi, "meta" model**. Umjesto da ručno određuješ koliki udio svaki model dobija u finalnom blend-u (npr. `w_lgbm=0.5, w_xgb=0.3`), stacking **uči te weightove iz podataka**.

```
Ulazni podaci (X_train, X_val)
        │
        ├──► LGBMRanker ──► lgbm_score ──┐
        ├──► XGBRanker  ──► xgb_score  ──┼──► LogisticRegression ──► finalni score
        ├──► CatBoost   ──► cat_score  ──┤         (meta-model)
        └──► Markov     ──► markov     ──┘
```

---

## Zašto Out-of-Fold (OOF) predikcije?

Ovo je najvažniji detalj stacking arhitekture. **Ne možeš trenirati meta-model na istim podacima na kojima su trenirani base modeli** — to bi bio direktan leakage jer bi meta-model vidio "odgovore" koje su base modeli zapamtili, ne generalizovali.

Rješenje je **Out-of-Fold (OOF)** pristup:

```
Fold 1: treniraj LGBM/XGB/CAT na foldovima 2,3,4,5,6 → predikcije na foldu 1
Fold 2: treniraj LGBM/XGB/CAT na foldovima 1,3,4,5,6 → predikcije na foldu 2
...itd
```

Ali u tvojem slučaju koristiš **expanding window CV** (ne k-fold), pa je logika drugačija:

```
Fold 3: treniraj na train_3 → predikcije na val_3
Fold 4: treniraj na train_4 → predikcije na val_4
Fold 5: treniraj na train_5 → predikcije na val_5
Fold 6: treniraj na train_6 → predikcije na val_6
                                        │
                              sve se spajaju (vstack)
                                        │
                              meta-model se trenira na ovome
```

Svaki val set je **temporalno odvojen** od svog train seta — nema leakage.

---

## Zašto LogisticRegression kao meta-model?

### Prednosti

**1. Interpretabilnost** — koeficijenti su direktno čitljivi kao weightovi:
```
lgbm_coef=2.1, xgb_coef=1.8, markov_coef=0.9
→ LGBM je najkorisniji, Markov doprinosi ali manje
```

**2. Regularizacija** — sprečava overfitting na malom broju meta-featurea (4-5 kolona). Ridge regularizacija (C parametar) kontroliše koliko agresivno meta-model može "povjerovati" jednom od base modela.

**3. Brzina** — trenira se u milisekundama na OOF predikcijama.

**4. Probabilistički output** — `predict_proba[:, 1]` vraća vjerovatnoću label=1 koja se direktno koristi za ranking unutar grupe.

### Ograničenja

LogisticRegression **ne zna za grupnu strukturu** — tretira svaki red nezavisno. To znači da meta-model uči "koji score je asociran sa label=1 generalno", ali ne "koji score je relativno visok unutar ove konkretne grupe klijenata". Zato `predict_proba[:, 1]` koristiš kao **ranking signal**, ne kao kalibriranu vjerovatnoću.

### Alternativa

Ako logreg ne poboljša metrike — zamijeni ga sa `RidgeClassifier` ili direktno sa `LinearRegression` (koja optimizira MSE umjesto log-loss, ponekad bolje za ranking).

---

## Ključni parametri

```python
LogisticRegression(
    C=10.0,              # Slaba regularizacija — ulazni featurei su već [0,1]
                         # Visok C = model može slobodnije učiti weightove
                         # Nizak C = weightovi su prisiljeni biti slični (konzervativno)
    
    max_iter=1000,       # Dovoljno iteracija za konvergenciju
    
    fit_intercept=False, # Ne želimo bias — meta-model samo uči relativne weightove
                         # Intercept bi pomijerio sve predikcije jednako,
                         # što ne pomaže rankingu unutar grupe
    
    class_weight='balanced'  # label=0 je ~13x češći od label=1 (14 kandidata, 1 tačan)
                             # Bez ovoga meta-model bi naučio "uvijek predvidi 0"
)
```

---

## Kako se `fit_intercept=False` uklapa sa rankingom?

U ranking problemu bitna je **relativna razlika** između scoreova unutar grupe, ne apsolutna vrijednost. Ako intercept pomakne sve scoreove za +0.3, ranking ostaje isti. Dakle intercept ne pomaže — bolje ga isključiti da meta-model fokus stavi isključivo na težine pojedinih modela.

---

## Tok podataka korak po korak

```
1. Za svaki fold u cv_folds_for_optuna:
   
   a) Treniraj LGBM na fd['X_train'] → predikcije na fd['X_val']
   b) Treniraj XGB  na fd['X_train'] → predikcije na fd['X_val']
   c) Treniraj CAT  na fd['X_train'] → predikcije na fd['X_val']  (ako USE_CATBOOST)
   
   d) Normalizuj svaku predikciju po grupi (0-1 unutar svake ponude)
      → normalize_by_group(lgbm_scores, group_val)
   
   e) Spoji u meta_X matricu oblika (n_val_rows, 4 ili 5):
      [lgbm_norm | xgb_norm | cat_norm | markov_norm | apriori_norm]
   
   f) Spremi (meta_X, y_val) za ovaj fold

2. Spoji sve foldove:
   X_meta = vstack([meta_X_fold3, meta_X_fold4, meta_X_fold5, meta_X_fold6])
   y_meta = concat([y_val_fold3,  y_val_fold4,  y_val_fold5,  y_val_fold6])

3. Treniraj LogisticRegression na (X_meta, y_meta)
   → meta_model.coef_[0] = naučeni weightovi

4. Predikcija na holdoutu:
   predict_proba(meta_X_holdout)[:, 1] → ranking score
```

---

## Zašto `normalize_by_group` prije meta-modela?

Base modeli (LGBM, XGB, CatBoost) vraćaju raw scores koji nisu uporedivi između grupa:

```
Grupa A: [0.8, 0.3, 0.1, 0.05]   ← LGBM outputi za grupu A
Grupa B: [2.1, 1.9, 1.8, 1.7]   ← LGBM outputi za grupu B (drugačija skala!)
```

Ako meta-model direktno vidi `2.1` i `0.8`, naučit će da "visoki LGBM score → label=1" generalno, ali neće znati da `0.8` u grupi A i `2.1` u grupi B su oba #1 rankovi — dakle oba su podjednako "dobri" predikcije.

Nakon `normalize_by_group`:
```
Grupa A: [1.0, 0.25, 0.05, 0.0]  ← normalizovano na [0,1] unutar grupe
Grupa B: [1.0, 0.5,  0.25, 0.0]  ← normalizovano na [0,1] unutar grupe
```

Sada meta-model vidi konzistentne signale — `1.0` uvijek znači "#1 rank u svojoj grupi".

---

## Ocjena trenutnog koda

### Što je dobro ✅

- **Arhitektura je ispravna** — OOF predikcije na temporalnim foldovima, nema leakage
- **`normalize_by_group` se primjenjuje** — konzistentni inputi za meta-model
- **`predict_proba[:, 1]` se koristi za ranking** — ispravno
- **Konstante su organizovane** — `USE_CATBOOST`, flagovi su čitljivi
- **CatBoost integracija u `optuna_objective` i `train_and_evaluate_best`** je ispravna sa `Pool` objektom i early stopping
- **Weight suma u Optuni** je ispravno implementovana sa `remaining` logikom
- **`class_weight='balanced'`** — ispravno, riješava imbalance problem

### Problemi ⚠️

| # | Problem | Lokacija | Efekt |
|---|---|---|---|
| 1 | `build_stacking_meta_model` trenira CatBoost bez `Pool` | `cat.fit(fd['X_train'], ...)` | CatBoost ignorira `cat_features`, sporiji trening |
| 2 | Nema `USE_CATBOOST` provjere unutar funkcije | Cijela funkcija | `cat_params={}` → crash ako `USE_CATBOOST=False` |
| 3 | `realistic_folds` i dalje koristi `fold > 1` umjesto Optuna filter | CV summary | Fold 2 (dist_diff=0.20) ulazi u reporting |
| 4 | `weights` se ne normalizuju nakon Optune | `weights = (w_lgbm, w_xgb, ...)` | Suma weightova možda nije 1.0 zbog floating point |
| 5 | `xgb eval_metric="ndcg@5"` u `train_and_evaluate_best` | XGBRanker init | Trebalo bi biti `"ndcg@1"` konzistentno sa Optunom |

### Popravke za probleme 3 i 4

```python
# Problem 3 — konzistentan filter
optuna_fold_ids = {fd['fold'] for fd in cv_folds_for_optuna}
realistic_folds = cv_df[cv_df['fold'].isin(optuna_fold_ids)]

# Problem 4 — eksplicitna normalizacija
total   = w_lgbm + w_xgb + w_cat + w_markov + w_apriori
weights = (w_lgbm/total, w_xgb/total, w_cat/total, w_markov/total, w_apriori/total)
```

---

## Kada stacking pomaže, kada ne?

**Pomaže kada:**
- Base modeli prave različite greške (diversity) — LGBM i XGB su slični, CatBoost dodaje diversity
- Ima dovoljno OOF podataka za treniranje meta-modela (tvoj slučaj: 4 folda × ~20k redova = ok)

**Ne pomaže kada:**
- Svi base modeli su visoko korelirani (prave iste greške)
- Meta-model se overfittuje na malom broju OOF foldova

**Kako provjeriti:** usporedi `meta_model.coef_[0]` sa manuelnim `weights` iz Optune. Ako su slični — stacking nije naučio ništa novo. Ako su različiti — stacking je pronašao bolji blend.
