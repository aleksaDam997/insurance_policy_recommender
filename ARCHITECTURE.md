TOK IZVRSAVANJA

main.py
    ↓
Pipeline
    ↓
Configuration Manager
    ↓
config.yaml / params.yaml / schema.yaml
    ↓
Entity objekti
    ↓
Components
    ↓
Model / Dataset / Rezultati

STRUKTURA

project/
│
├── config/
│   ├── config.yaml
│   ├── schema.yaml
│   └── params.yaml
│
├── src/
│   ├── entity/
│   │   └── config_entity.py
│   │
│   ├── config/
│   │   └── configuration.py
│   │
│   ├── components/
│   │   ├── data_ingestion.py
│   │   ├── data_validation.py
│   │   ├── data_transformation.py
│   │   ├── model_trainer.py
│   │   └── model_evaluation.py
│   │
│   └── pipeline/
│       ├── stage_01_ingestion.py
│       ├── stage_02_validation.py
│       ├── stage_03_transformation.py
│       ├── stage_04_training.py
│       └── stage_05_evaluation.py
│
└── main.py