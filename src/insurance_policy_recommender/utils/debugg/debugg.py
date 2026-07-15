import psutil
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd 
import numpy as np
import os


# ============================================================
# POMOCNE FUNKCIJE
# ============================================================
process = psutil.Process(os.getpid())

def get_ram_mb():
    return process.memory_info().rss / 1024 / 1024

def print_duplicates(df, subset):
    print(f"\n### DUPLICATES: {subset} ###")

    # Po defaultu je keep='first'
    print(f"Dupliranih redova: {df.duplicated(subset=subset, keep='first').sum()}")
    print(f"Jedinstvenih duplikata: {df.groupby(subset).size().gt(1).sum()}")
    print(f"Ukupno redova u dupliranim grupama: {df.duplicated(subset=subset, keep=False).sum()}")

def show_cli_policy_distribution(df):
    
    sns.set_style("darkgrid")
    
    policy_counts = df.groupby('klijent_id').size()
    
    data = {"Only 1 policy": (policy_counts == 1).sum(),
            "More than 1 policy": (policy_counts > 1).sum()}
    
    plot_df = pd.DataFrame({"category": list(data.keys()), "value": list(data.values())})
    
    plt.figure(figsize=(8, 6))
    
    ax = sns.barplot(data=plot_df, x="category", y="value", hue="category",
                     palette=["#4C78A8", "#F58518"], legend=False)
    
    for p in ax.patches:
        ax.annotate(f'{int(p.get_height()):,}',
                    (p.get_x() + p.get_width() / 2., p.get_height()),
                    ha='center', va='bottom', fontsize=11)
        
    plt.title("Distribution of Clients by Number of Policies",
              fontsize=14,
              weight='bold')

    plt.tight_layout()

    plt.savefig(
        "policy_distribution.png",
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()

    os.startfile("policy_distribution.png")

# Procentualna popunjenost izabranih kolona
def plot_column_fill_rate(df, cols):

    # notna vraca masku True/False sto je u pythonu 1 i 0
    # Pa u sustini kod radi zbir 1 / zbir koliko ima redova odnosno redova ukupno
    fill_rate = df[cols].notna().mean() * 100

    plt.figure(figsize=(8, 6))

    ax = sns.barplot(
        x=fill_rate.values,
        y=fill_rate.index
    )

    ax.set_xlabel('Popunjenost (%)')
    ax.set_ylabel('Kolona')
    ax.set_title('Procenat popunjenosti kolona')

    plt.tight_layout()
    #plt.show()

    plt.savefig(
        "column_distribution.png",
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()

    os.startfile("column_distribution.png")