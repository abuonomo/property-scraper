import json
import logging
import os
from pathlib import Path
from time import sleep

import pandas as pd
import requests
from tqdm import tqdm

LOGLEVEL = os.environ.get("LOGLEVEL", "WARNING").upper()
logging.basicConfig(level=LOGLEVEL)
LOG = logging.getLogger(__name__)
LOG.setLevel(logging.INFO)


def to_jsonl(df, outfile):
    records = df.to_dict(orient="records")
    with open(outfile, "w") as f0:
        for r in records:
            f0.write(json.dumps(r))
            f0.write("\n")
    return outfile


def read_jsonl(infile):
    with open(infile, "r") as f0:
        recs = [json.loads(l) for l in f0.readlines()]
    df = pd.DataFrame(recs)
    return df


def _get_transactions(cc, property_url):

    headers = {
        "Accept-Language": "en-US,en;q=0.5",
        "Lang": "en",
        "Referer": property_url,
    }
    json_data = {
        "cuntcodes": [
            cc,
        ],
    }
    response = requests.post(
        "https://hk.centanet.com/findproperty/api/Transaction/Search",
        headers=headers,
        json=json_data,
    )
    data = json.loads(response.text)
    return data


def get_transactions(cc, property_url):
    trans_data = _get_transactions(cc, property_url)
    if "error" in trans_data:
        raise Exception("Hit API limit!")
    records = []
    for d in trans_data["data"]:
        records.append(d)
    return records


def main():
    df = pd.read_csv("../data/unit_codes.csv", index_col=0)
    nsl = Path("../data/next_start.txt")
    if nsl.exists():
        with open(nsl, "r") as f0:
            next_start_index = int(f0.read())
    else:
        next_start_index = 0
    next_start_index

    LOG.info(f"Starting with index {next_start_index}")
    rdf = df.loc[next_start_index:]
    pbar = tqdm(rdf.iterrows(), total=rdf.shape[0])
    all_ts = []
    for index, r in pbar:
        pbar.set_description(f"{r['property']} | {r['floor']} | {r['unit']}")
        cc = r["cuntcode"]
        url = r["url"]
        try:
            ts = get_transactions(cc, property_url=url)
        except Exception as e:
            LOG.warning(f"Returning what we have because of {e}.")
            next_start_index = index
            break
        if ts is None:
            print(next_start_index)
            break
        if isinstance(ts, list):
            all_ts = all_ts + ts
        else:
            raise Exception("Should be list!")
    atdf = pd.DataFrame(all_ts)

    LOG.info(f"Total Completed: {next_start_index - 1}/{df.shape[0]}")
    LOG.info(f"Writing out the next start index: {next_start_index}")
    with open("../data/next_start.txt", "w") as f0:
        f0.write(str(next_start_index))

    out_path = f"../data/records/record{next_start_index}.jsonl"
    LOG.info(f"Writing results from this batch to {out_path}")
    to_jsonl(atdf, out_path)

    if next_start_index >= df.iloc[0].name:
        return True
    else:
        return False


if __name__ == "__main__":
    while True:
        done = main()
        LOG.info("Waiting for a minute and then restarting")
        if done:
            break
        sleep(60)
