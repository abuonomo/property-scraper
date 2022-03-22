import logging
import os
from pathlib import Path

import pandas as pd

import transactions

LOGLEVEL = os.environ.get("LOGLEVEL", "WARNING").upper()
logging.basicConfig(level=LOGLEVEL)
LOG = logging.getLogger(__name__)
LOG.setLevel(logging.INFO)


def main():
    rdir = Path("../data/records")
    LOG.info(f"Reading from {rdir}")
    dfs = []
    for f in rdir.iterdir():
        dfs.append(transactions.read_jsonl(f))
    total_df = pd.concat(dfs).reindex()
    col_map = {
        "estateName": "Development",
        "buildingName": "Block",
        "yAxis": "Floor",
        "xAxis": "Units",
        "transactionPrice": "Price",
        "regDate": "regDate",
        "insDate": "insDate",
    }
    sm_df = total_df.loc[:, col_map.keys()].rename(columns=col_map)
    outfile = "../data/summary_data.csv"
    LOG.info(f"Writing to {outfile}")
    sm_df.to_csv(outfile)


if __name__ == "__main__":
    main()
