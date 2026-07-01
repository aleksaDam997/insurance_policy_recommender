# Arhitektura projekta

## config.yaml

Sadrži konfiguraciju projekta:

* putanje do fajlova i foldera
* lokacije za čuvanje artefakata
* URL-ove za preuzimanje podataka

## schema.yaml

Definiše strukturu podataka:

* nazive kolona
* tipove podataka
* target kolonu
* pravila validacije

## params.yaml

Sadrži parametre modela:

* hiperparametre
* parametre treninga
* eksperimentalna podešavanja

## entity

Dataclass objekti koji predstavljaju konfiguraciju učitanu iz YAML fajlova.

Pravilo:

* Nema poslovne logike.
* Samo strukture podataka.

## config

Configuration Manager.

Odgovornost:

* učitavanje YAML konfiguracija
* kreiranje Entity objekata
* prosljeđivanje konfiguracije komponentama

## components

Mjesto gdje se nalazi stvarna logika.

Primjeri:

* Data Ingestion
* Data Validation
* Data Transformation
* Model Trainer
* Model Evaluation

Pravilo:

* Jedna komponenta = jedan poslovni zadatak.

## pipeline

Orkestracija koraka.

Odgovornost:

* pokretanje komponenti
* definisanje redoslijeda izvršavanja

Pravilo:

* Bez poslovne logike.
* Samo pozivanje komponenti.

## main.py

Ulazna tačka aplikacije.

Odgovornost:

* pokretanje svih pipeline faza
* logovanje statusa izvršavanja

Tok izvršavanja:

main.py
→ Pipeline
→ Components
→ Model / Dataset / Artefakti
