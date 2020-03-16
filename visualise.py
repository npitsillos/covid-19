import argparse
import os
import random
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

sns.set()

DATAPATH = os.path.abspath("data")

def preprocess(dataframes):
    # Clean up data
    # Fill province/state with corresponding country if NaN
    # Melt dataframes to create single column Date renaming columns
    # Convert Date column to datetime
    for key in dataframes.keys():
        dataframes[key]["Province/State"].fillna(value=dataframes[key]["Country/Region"], inplace=True)
        dataframes[key] = pd.melt(dataframes[key], id_vars=["Province/State", "Country/Region", "Lat", "Long"], var_name="Date", value_name=key)
        dataframes[key]["Date"] = pd.to_datetime(dataframes[key]["Date"])
    
    return dataframes

def merge_datasets(dataframes):
    # Data is cumulative: day by day shows total not new
    # so need to create a column to hold new cases per day

    confirmed_deaths = dataframes["confirmed"].merge(
                            dataframes["deaths"][["Province/State", "Country/Region", "Date", "deaths"]],
                            how="outer",
                            on=["Province/State", "Country/Region", "Date"])
    complete_dataset = confirmed_deaths.merge(
                            dataframes["recovered"][["Province/State", "Country/Region", "Date", "recovered"]],
                            how="outer",
                            on=["Province/State", "Country/Region", "Date"])

    complete_dataset_minus_one = complete_dataset.copy()
    complete_dataset_minus_one["Date-1"] = complete_dataset_minus_one["Date"] + pd.Timedelta(days=1)
    complete_dataset_minus_one = complete_dataset_minus_one.rename(columns={"confirmed": "confirmed-1", "deaths": "deaths-1",
                                                                    "recovered": "recovered-1",
                                                                    "Date": "Date Minus 1"})
    
    final_dataset = complete_dataset.merge(complete_dataset_minus_one[["Province/State", "Country/Region",
                                                                        "confirmed-1", "deaths-1", "recovered-1",
                                                                        "Date-1", "Date Minus 1"]], how="left",
                                                                        left_on=["Province/State", "Country/Region", "Date"],
                                                                        right_on=["Province/State", "Country/Region", "Date-1"])
    
    final_dataset["confirmed new"] = final_dataset["confirmed"] - final_dataset["confirmed-1"]
    final_dataset["deaths new"] = final_dataset["deaths"] - final_dataset["deaths-1"]
    final_dataset["recovered new"] = final_dataset["recovered"] - final_dataset["recovered-1"]
    
    final_dataset["confirmed new"].loc[final_dataset["Date"] == "2020-01-22"] = final_dataset["confirmed"]
    final_dataset["deaths new"].loc[final_dataset["Date"] == "2020-01-22"] = final_dataset["deaths"]
    final_dataset["recovered new"].loc[final_dataset["Date"] == "2020-01-22"] = final_dataset["recovered"]
    
    del final_dataset["confirmed-1"]
    del final_dataset["deaths-1"]
    del final_dataset["recovered-1"]
    del final_dataset["Date-1"]
    del final_dataset["Date Minus 1"]
    
    final_dataset["Date"] = final_dataset["Date"].astype(str)
    
    return final_dataset

def get_total_cases_per_day(dataset):
    # Returns the sum of cases per day
    return dataset.groupby(["Date"], as_index=False)[["confirmed", "deaths", "recovered", "confirmed new", "deaths new", "recovered new"]].sum()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Visualisation of Covid-19 confirmed cases, deaths and recoveries.")
    parser.add_argument("--country", help="Desired country for which to display visualisations", default=None)

    args = parser.parse_args()

    # Read files
    dataframes = {}
    for csv_file in next(os.walk(DATAPATH))[2]:
        if "dataset" in csv_file:
            continue
        dataframes[csv_file.split('.')[0]] = pd.read_csv(os.path.join(DATAPATH, csv_file))

    dataframes = preprocess(dataframes)
    
    final_dataset = merge_datasets(dataframes)
    final_dataset.to_csv(os.path.join(DATAPATH, "dataset.csv"))
    total_cases_per_day = get_total_cases_per_day(final_dataset)
    figsize = (20,20)
    ax = total_cases_per_day.plot(kind="line", x="Date", y="confirmed new", rot=45, figsize=figsize)
    total_cases_per_day.plot(kind="line", x="Date", y="deaths new", ax=ax, rot=45, figsize=figsize)
    total_cases_per_day.plot(kind="line", x="Date", y="recovered new", ax=ax, rot=45, figsize=figsize)
    plt.title("Total New Cases per Day")
    # plt.show()
    
    # ax = total_cases_per_day.plot(kind="bar", x="Date", y="confirmed", rot=90, color='b', figsize=figsize)
    # total_cases_per_day.plot(kind="bar", x="Date", y="deaths", ax=ax, rot=90, color='r', figsize=figsize)
    # total_cases_per_day.plot(kind="bar", x="Date", y="recovered", ax=ax, rot=90, color='g', figsize=figsize)
    # # ticks = ax.xaxis.get_ticklocs()
    # # ticklabels = [l.get_text() for l in ax.xaxis.get_ticklabels()]
    # # ax.xaxis.set_ticks(ticks[::3])
    # # ax.xaxis.set_ticklabels(ticklabels[::3])
    # plt.title("Total Cumulative Cases per Day")
    # plt.show()

    total_row = total_cases_per_day.iloc[total_cases_per_day.index[-1]]
    df = pd.DataFrame({"num": [total_row["confirmed"] - (total_row["recovered"] + total_row["deaths"]), total_row["deaths"], total_row["recovered"]]},
                        index=["infected", "deaths", "recovered"])
    print(df.plot.pie(y="num"))
    plt.show()
    print(total_row)
    print(sum([total_row["confirmed"] - (total_row["recovered"] + total_row["deaths"]), total_row["deaths"], total_row["recovered"]]))