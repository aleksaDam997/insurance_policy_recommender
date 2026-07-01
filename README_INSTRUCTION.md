## INITIALIZE ENVIRONMENT BASH

conda create -n venv python==3.10
conda activate venv
conda env export > environment.yml
conda env create -f environment.yml
conda activate venv

## INSTALL DEPENDENCIES

pip install -r requirements.txt