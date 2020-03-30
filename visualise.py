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

def get_total_cases_per_day(dataset, country=None):
    # Returns the sum of cases per day
    if country is not None:
        dataset = dataset.loc[dataset["Country/Region"] == country]
    return dataset.groupby(["Date"], as_index=False)[["confirmed", "deaths", "recovered", "confirmed new", "deaths new", "recovered new"]].sum()

def plot_data_per_date(data, total=True, kind=None, country=None):
    
    figsize = (20,20)
    ax = plt.subplot()
    base_kwargs = {"kind": kind, "x": "Date", "rot": 45, "figsize":figsize, "ax": ax}
    
    if kind is None:
        kind = "line"
    y_data_str = ""
    if not total:
        y_data_str = " new"

    kwargs_confirmed = base_kwargs.copy()
    kwargs_deaths = base_kwargs.copy()
    kwargs_recovered = base_kwargs.copy()

    kwargs_confirmed["y"] = "confirmed{}".format(y_data_str)
    kwargs_deaths["y"] = "deaths{}".format(y_data_str)
    kwargs_recovered["y"] = "recovered{}".format(y_data_str)

    if kind == "bar":
        kwargs_confirmed["color"] = 'b'
        kwargs_deaths["color"] = 'r'
        kwargs_recovered["color"] = 'g'
    
    data.plot(**kwargs_confirmed)
    data.plot(**kwargs_deaths)
    data.plot(**kwargs_recovered)
    
    if country:
        title = country
    else:
        if len(y_data_str) == 0:
            title = "Cumulative"
        else:
            title = "New"
    plt.title(title + " Cases per Day")
    plt.ylabel("Number of Cases")
    plt.show()

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
    
    # Show a line plot of new cases per day
    plot_data_per_date(total_cases_per_day, kind="line")
    # Show a bar plot of cumulative cases per day
    plot_data_per_date(total_cases_per_day, total=False, kind="bar")

    # Create a df for holding information for a pie plot
    total_row = total_cases_per_day.iloc[total_cases_per_day.index[-1]]
    pie_data = pd.DataFrame({"num": [total_row["confirmed"] - (total_row["recovered"] + total_row["deaths"]), total_row["deaths"], total_row["recovered"]]},
                        index=["infected", "deaths", "recovered"])
    pie_data.plot.pie(y="num", autopct="%1.1f%%")
    plt.show()
   
    # china = get_total_cases_per_day(final_dataset, country="China")
    # ax = china.plot(kind="line", x="Date", y="confirmed", rot=45, figsize=figsize)
    # china.plot(kind="line", x="Date", y="deaths", ax=ax, rot=45, figsize=figsize)
    # china.plot(kind="line", x="Date", y="recovered", ax=ax, rot=45, figsize=figsize)
    # plt.title("China Cumulative Cases")
    # plt.ylabel("Cumulative Cases")
    # plt.show()

    # cyprus = get_total_cases_per_day(final_dataset, country="Cyprus")

    # ax = cyprus.plot(kind="line", x="Date", y="confirmed", rot=45, figsize=figsize)
    # cyprus.plot(kind="line", x="Date", y="deaths", ax=ax, rot=45, figsize=figsize)
    # cyprus.plot(kind="line", x="Date", y="recovered", ax=ax, rot=45, figsize=figsize)
    # plt.title("Cyprus Cumulative Cases")
    # plt.ylabel("Cumulative Cases")
    # plt.show()

    uk = get_total_cases_per_day(final_dataset, country="United Kingdom")
    ax = uk.plot(kind="line", x="Date", y="confirmed", rot=45, figsize=(20,20))
    uk.plot(kind="line", x="Date", y="deaths", ax=ax, rot=45, figsize=(20,20))
    uk.plot(kind="line", x="Date", y="recovered", ax=ax, rot=45, figsize=(20,20))
    plt.title("UK Cumulative Cases")
    plt.ylabel("Cumulative Cases")
    plt.show()

    ax = uk.plot(kind="bar", x="Date", y="confirmed new", rot=45, figsize=(20,20), color='b')
    uk.plot(kind="bar", x="Date", y="deaths new", ax=ax, rot=45, figsize=(20,20), color='r')
    uk.plot(kind="bar", x="Date", y="recovered new", ax=ax, rot=45, figsize=(20,20), color='g')
    plt.title("UK Cumulative Cases")
    plt.ylabel("Cumulative Cases")
    plt.show()