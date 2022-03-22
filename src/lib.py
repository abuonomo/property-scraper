import atexit
import json
import logging
import os
from pathlib import Path
from time import sleep

import pandas as pd
import requests
from selenium import webdriver
from selenium.common.exceptions import (ElementClickInterceptedException,
                                        NoSuchElementException)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from tqdm import tqdm

LOGLEVEL = os.environ.get("LOGLEVEL", "WARNING").upper()
logging.basicConfig(level=LOGLEVEL)
LOG = logging.getLogger(__name__)
LOG.setLevel(logging.INFO)

tqdm.pandas()


class PropertyScraper:
    def __init__(self, driver_path: Path) -> None:
        self.driver_path = driver_path
        self.driver = self.get_driver(driver_path)
        self.driver.implicitly_wait(10)

    @staticmethod
    def get_driver(driver_path):
        capabilities = DesiredCapabilities.CHROME
        # capabilities["loggingPrefs"] = {"performance": "ALL"}  # chromedriver < ~75
        capabilities["goog:loggingPrefs"] = {"performance": "ALL"}  # chromedriver 75+
        driver = webdriver.Chrome(
            driver_path,
            desired_capabilities=capabilities,
        )
        atexit.register(lambda: driver.quit())
        return driver

    def get_log(self, url, wait_time=2):
        LOG.info(f"Going to {url}")
        self.driver.get(url)
        LOG.info(f"Clicking transaction detail button")
        th_btn = self.driver.find_element(
            By.CSS_SELECTOR, "#Category2 > div > div:nth-child(5) > div"
        )
        sleep(wait_time)
        for _ in range(3):  # Try to click 5 times
            try:
                th_btn.click()
            except ElementClickInterceptedException:
                sleep(0.5)
                continue
        sleep(wait_time)
        # try:
        #     self.click_through_menu()
        # except NoSuchElementException:
        #     LOG.info("Only one block")
        LOG.info(f"Extracting logs")
        log = self.driver.get_log("performance")
        return log

    def click_through_menu(self):
        msel = "#__layout > div > div.property-details.layout-main-content > div.el-dialog__wrapper.floor-dialog-info > div > div.el-dialog__body > div.flex.select-wrap > div > div > div.el-input.el-input--suffix > input"  # fmt: skip
        lsel = "body > div.el-select-dropdown.el-popper > div.el-scrollbar > div.el-select-dropdown__wrap.el-scrollbar__wrap.el-scrollbar__wrap--hidden-default > ul"  # fmt: skip
        i = 0
        while True:
            menu = self.driver.find_element(By.CSS_SELECTOR, msel)
            menu.click()
            sleep(0.5)
            blocks = self.driver.find_element(By.CSS_SELECTOR, lsel)
            lis = blocks.find_elements(By.CSS_SELECTOR, "li")
            if i == len(lis):
                break
            LOG.info(lis[i].text)
            lis[i].click()
            i += 1


def get_typecodes(url, driver_path):
    scraper = PropertyScraper(driver_path)
    log = scraper.get_log(url)
    scraper.driver.quit()
    if "ConsumptionTableEstateMenu" in str(log):
        LOG.info("Getting typecodes for each block.")
        recs = get_typecodes_for_each_block(log)
    elif "ConsumptionTable" in str(log):
        LOG.info("No blocks, getting typecode for whole estate")
        recs = get_typecode_for_whole_estate(log)
    else:
        raise Exception("Should have some kind of ConsumptionTable")
    return recs


def get_typecode_for_whole_estate(log):
    LOG.info(f"Parsing logs to get consumption table url.")
    cl = [l for l in log if "ConsumptionTable" in str(l)]
    cl0 = [l for l in cl if "response" in json.loads(l["message"])["message"]["params"]]
    if len(cl0) != 1:
        raise Exception("There should only be one valid request.")
    msg = json.loads(cl0[0]["message"])
    ct_url = msg["message"]["params"]["response"]["url"]
    tc = ct_url.split("?")[1].split("&")[0].split("=")[1]
    recs = [
        {
            "name": "",
            "typeCode": tc,
        }
    ]
    return recs


def put_url_in_tcs(r):
    tcs = r["tcs"].copy()
    for tc in tcs:
        tc["url"] = r["Data Source"]
    return tcs


def get_typecodes_for_each_block(log):
    req = get_request_info(log)
    response = requests.get(
        req["url"],
        headers=req["headers"],
    )
    data = json.loads(response.text)
    recs = data["menuItems"]
    return recs


def get_request_info(log):
    cl = [
        json.loads(l["message"]) for l in log if "ConsumptionTableEstateMenu" in str(l)
    ]
    for l in cl:
        if l["message"]["method"] == "Network.requestWillBeSent":
            req = l["message"]["params"]["request"]
            break
    else:
        raise Exception("Did not find right request")
    return req


def get_consumption_table(url, typecode):
    headers = {
        "Accept-Language": "en-US,en;q=0.5",
        "Lang": "en",
        "Referer": url,
    }
    params = {
        "typecode": typecode,
        "firstOrSecondHand": "SecondHand",
    }
    response = requests.get(
        "https://hk.centanet.com/findproperty/api/Transaction/ConsumptionTable",
        headers=headers,
        params=params,
    )
    data = json.loads(response.text)
    return data


def get_ccs(ct_data):
    records = []
    missed_records = []
    property = ct_data["menuItem"]["name"]
    for floor_dct in ct_data["floors"]:
        floor = floor_dct["yAxis"]
        units = floor_dct["units"]
        for unit in units:
            try:
                unit_name = unit["xAxis"]
                cc = unit["cuntcode"]
            except KeyError as e:
                LOG.warning(
                    f"Skipping {property} | {floor} | {unit_name} because of {e}"
                )
                missed_record = {
                    "property": property,
                    "floor": floor,
                    "unit": unit_name,
                    "cuntcode": None,
                }
                missed_records.append(missed_record)
            record = {
                "property": property,
                "floor": floor,
                "unit": unit_name,
                "cuntcode": cc,
            }
            records.append(record)
    return records, missed_records


def get_c_info(tc_df):
    all_records = []
    all_missed_recs = []
    for _, row in tc_df.iterrows():
        ct_data = row["ct_data"]
        url = row["url"]
        recs, missed_recs = get_ccs(ct_data)
        for r in recs:
            r["url"] = url
        for r in missed_recs:
            r["url"] = url
        all_records = all_records + recs
        all_missed_recs = all_missed_recs + missed_recs
    df = pd.DataFrame(all_records)
    mdf = pd.DataFrame(all_missed_recs)
    return df, mdf


def get_ct_url(url, driver_path):
    scraper = PropertyScraper(driver_path)
    ct_url = scraper.get_consumption_table_url(url)
    scraper.driver.close()
    return ct_url


def get_ct_data(tc_df):
    tc_df = tc_df.copy()
    all_ct_data = []
    pbar = tqdm(tc_df.iterrows(), total=tc_df.shape[0])
    for _, row in pbar:
        purl = row.loc["url"]
        tc = row.loc["typeCode"]
        ct_data = get_consumption_table(purl, typecode=tc)
        property = ct_data["menuItem"]["name"]
        pbar.set_description(property)
        all_ct_data.append(ct_data)
    tc_df["ct_data"] = all_ct_data
    return tc_df


def main():
    infile = Path("../data/Dissertation_Data.xlsx")
    driver_path = Path("../chromedriver")
    df = pd.read_excel(infile, sheet_name="Summary")

    df0 = df[~df["Data Source"].isna()]
    tcs = df0["Data Source"].progress_apply(get_typecodes, driver_path=driver_path)
    df0["tcs"] = tcs

    tcs_w_url = df0.apply(put_url_in_tcs, axis=1)
    tc_df = pd.DataFrame(tcs_w_url.explode().tolist())
    tc_df = tc_df.pipe(get_ct_data)

    df, mdf = get_c_info(tc_df)
    LOG.info("Writing unit codes and missing unit codes to csvs.")
    df.to_csv("../data/unit_codes.csv")
    mdf.to_csv("../data/units_require_manual_gather.csv")


if __name__ == "__main__":
    main()
