from pathlib import Path
import pandas as pd
import numpy as np
from scipy.stats import ks_2samp
    

def calculate_psi(expected, actual, bins=10):

    breakpoints = np.percentile(
        expected,
        np.arange(0, 101, 100 / bins)
    )

    expected_counts = np.histogram(
        expected,
        breakpoints
    )[0]

    actual_counts = np.histogram(
        actual,
        breakpoints
    )[0]

    expected_perc = expected_counts / len(expected)
    actual_perc = actual_counts / len(actual)

    expected_perc = np.where(expected_perc == 0, 0.0001, expected_perc)
    actual_perc = np.where(actual_perc == 0, 0.0001, actual_perc)

    psi = np.sum(
        (actual_perc - expected_perc)
        * np.log(actual_perc / expected_perc)
    )

    return psi

def calculate_ksi(train, prod, col_name):

    statistic, p_value = ks_2samp(
        train[col_name],
        prod[col_name]
    )

    return statistic, p_value