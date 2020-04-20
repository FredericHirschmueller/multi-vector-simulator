"""
Convert csv files to json file as input for the simulation.

The default input csv files are stored in "/inputs/elements/csv".
Otherwise their path is provided by the user.

The user can change parameters of the simulation of of the energy system in the csv files.

Storage: The "energyStorage.csv" contains information about all storages.
For each storage there needs to be another file named exactly after each storage-column in the
"energyStorage.csv" file. For the default file this is "storage_01", "storage_02" etc.
Please stick to this convention.

The function "create_input_json()" reads all csv files that are stored
in the given input folder (input_directory) and creates one json input file for mvs_tool.

Functions of this module (that need to be tested)
- read all necessary input files (allowed files) from folder inputs
- display error message if Json already in csv_elements
- read all parameters in CSV
- parse parameter that is given as a timeseries with input file name and header
- parse parameter that is given as a list
- check that parameter that is given as a list results and subsequent other parameters to be given as list e.g. if we have two output flows in conversion assets there should be two efficiencies to operational costs (this is not implemented in code yet)
- only necessary parameters should be transferred to json dict, error message with additonal parameters
- parse data from csv according to intended types - string, boolean, float, int, dict, list!
"""

import os
import json
import logging
import pandas as pd

from src.constants import (
    CSV_FNAME,
    CSV_SEPARATORS,
    REQUIRED_CSV_FILES,
    REQUIRED_CSV_PARAMETERS,
)


def create_input_json(
    input_directory, pass_back=True,
):
    """Convert csv files to json file as input for the simulation.

    Looks at all csv-files in `input_directory` and compile the information they contain
    into a json file. The json file is then saved within the `input_directory`
    with the filename `CSV_FNAME`.
    While reading the csv files, it is checked, whether all required parameters
    for each component are provided. Missing parameters will return a warning message.

    Parameters
    ----------
    input_directory, str
        path of the directory where the input csv files can be found
    pass_back, bool, optional
        if True the final json dict is returned. Otherwise it is only saved
    Returns
    -------
        None or dict
    """

    logging.info(
        "loading and converting all csv's from %s" % input_directory + " into one json"
    )

    output_filename = os.path.join(input_directory, CSV_FNAME)

    if os.path.exists(output_filename):
        raise FileExistsError(
            f"The mvs json config file {CSV_FNAME} already exists in the input "
            f"folder {input_directory}. This is likely due to an aborted "
            f"previous run. Please make sure no such file is located within "
            f"the folder prior to run a new simulation"
        )

    input_json = {}

    # Read all csv files from path input directory
    list_assets = []
    for f in os.listdir(input_directory):
        filename = str(f[:-4])
        if filename in REQUIRED_CSV_FILES:
            list_assets.append(filename)
            parameters = REQUIRED_CSV_PARAMETERS[filename]
            single_dict = create_json_from_csv(
                input_directory, filename, parameters=parameters
            )
            input_json.update(single_dict)
        elif "storage_" in filename:
            list_assets.append(filename)
            # TODO
            pass
        else:
            logging.error(
                "The file %s" % f + " is not recognized as input file for mvs "
                "check %s",
                input_directory + "for correct " "file names.",
            )

    # check if all required files are available
    extra = list(set(list_assets) ^ set(REQUIRED_CSV_FILES))

    for i in extra:
        if i in REQUIRED_CSV_FILES:
            logging.error(
                "Required input file %s is missing! Please add it"
                "into %s." % (i, os.path.join(input_directory))
            )
        elif "storage_" in i:
            pass
        else:
            logging.debug(
                "File %s" % i + ".csv is an unknown filename and"
                " will not be processed."
            )

    # store generated json file to file in input_directory.
    # This json will be used in the simulation.
    with open(output_filename, "w") as outfile:
        json.dump(input_json, outfile, skipkeys=True, sort_keys=True, indent=4)
    logging.info(
        "Json file created successully from csv's and stored into "
        "%s" % output_filename + "\n"
    )
    logging.debug("Json created successfully from csv.")
    if pass_back:
        return outfile.name


def create_json_from_csv(input_directory, filename, parameters, storage=False):

    """
    One csv file is loaded and it's parameters are checked. The csv file is
    then converted to a dictionary; the name of the csv file is used as the
    main key of the dictionary. Exceptions are made for the files
    ["economic_data", "project", "project_data", "simulation_settings"], here
    no main key is added. Another exception is made for the file
    "energyStorage". When this file is processed, the according "storage_"
    files (names of the "storage_"-columns in "energyStorage" are called and
    added to the energyStorage Dictionary.


    :param input_directory: str
        path of the directory where the input csv files can be found
    :param filename: str
        name of the input file that is transformed into a json, without
        extension
    :param parameters: list
        List of parameters names that are required
    :param storage: bool
        default value is False. If the function is called by
        add_storage_components() the
        parameter is set to True
    :return: dict
        the converted dictionary
    """

    logging.debug("Loading input data from csv: %s", filename)

    # allow different separators for csv files, take the first one which works
    seperator_unknown = True

    idx = 0
    while seperator_unknown is True and idx < len(CSV_SEPARATORS):
        df = pd.read_csv(
            os.path.join(input_directory, "%s.csv" % filename),
            sep=CSV_SEPARATORS[idx],
            header=0,
            index_col=0,
        )

        if len(df.columns) > 0:
            seperator_unknown = False
        else:
            idx = idx + 1

    if seperator_unknown is True:
        raise ValueError(
            "The csv file {} has a separator for values which is not one of the "
            "following: {}. The file was therefore unparsable".format(
                os.path.join(input_directory, "%s.csv" % filename), CSV_SEPARATORS
            )
        )

    # check wether parameter maximumCap is availavle                             #todo in next version: add maximumCap to hardcoded parameter list above
    new_parameter = "maximumCap"
    if new_parameter in df.index:
        parameters.append(new_parameter)
    else:
        logging.warning(
            "You are not using the parameter %s for asset group %s, which allows setting a maximum capacity for an asset that is being capacity optimized (Values: None/Float). In the upcoming version of the MVS, this parameter will be required.",
            new_parameter,
            filename,
        )

    # check parameters
    if storage is False:
        extra = list(set(parameters) ^ set(df.index))
        if len(extra) > 0:
            for i in extra:
                if i in parameters:
                    logging.error(
                        "In the file %s.csv" % filename
                        + " the parameter "
                        + str(i)
                        + " is missing. "
                        "check %s",
                        input_directory + " for correct parameter names.",
                    )
                else:
                    logging.error(
                        "In the file %s.csv" % filename
                        + " the parameter "
                        + str(i)
                        + " is not recognized. \n"
                        "check %s",
                        input_directory + " for correct parameter names.",
                    )

    # convert csv to json
    single_dict2 = {}
    single_dict = {}
    asset_name_string = ""
    if len(df.columns) == 1:
        logging.debug(
            "No %s" % filename + " assets are added because all "
            "columns of the csv file are empty."
        )
    df_copy = df.copy()
    for column in df_copy:
        if column != "unit":
            column_dict = {}
            # the storage columns are checked for the right parameters,
            # Nan values that are not needed are deleted
            if storage == True:
                # check if all three columns are available
                if len(df_copy.columns) < 4 or len(df_copy.columns) > 4:
                    logging.error(
                        f"The file {filename}.csv requires "
                        f"three columns, you have inserted {len(df_copy.columns)}"
                        "columns."
                    )
                # add column specific parameters
                if column == "storage capacity":
                    extra = ["soc_initial", "soc_max", "soc_min"]
                elif column == "input power" or column == "output power":
                    extra = ["c_rate", "opex_var"]
                else:
                    logging.error(
                        f"The column name {column} in The file {filename}.csv"
                        " is not valid. Please use the column names: "
                        "'storage capacity', 'input power' and "
                        "'output power'."
                    )
                column_parameters = parameters + extra
                # check if required parameters are missing
                for i in set(column_parameters) - set(df_copy.index):
                    logging.warning(
                        f"In file {filename}.csv the parameter {str(i)}"
                        f" in column {column} is missing."
                    )
                for i in df_copy.index:
                    if i not in column_parameters:
                        # check if not required parameters are set to Nan and
                        # if not, set them to Nan
                        if i not in [
                            "c_rate",
                            "opex_var",
                            "soc_initial",
                            "soc_max",
                            "soc_min",
                        ]:
                            logging.warning(
                                f"The storage parameter {str(i)} of the file "
                                f"{filename}.csv is not recognized. It will not be "
                                "considered in the simulation."
                            )
                            df_copy.loc[[i], [column]] = "NaN"

                        elif pd.isnull(df_copy.at[i, column]) is False:
                            logging.warning(
                                f"The storage parameter {str(i)} in column "
                                f" {column} of the file {filename}.csv should "
                                "be set to NaN. It will not be considered in the "
                                "simulation"
                            )
                            df_copy.loc[[i], [column]] = "NaN"
                        else:
                            logging.debug(
                                f"In file {filename}.csv the parameter {str(i)}"
                                f" in column {column} is NaN. This is correct; "
                                f"the parameter will not be considered."
                            )
                    # check if all other values have a value unequal to Nan
                    elif pd.isnull(df_copy.at[i, column]) is True:
                        logging.warning(
                            f"In file {filename}.csv the parameter {str(i)}"
                            f" in column {column} is NaN. Please insert a value "
                            "of 0 or int. For this "
                            "simulation the value is set to 0 "
                            "automatically."
                        )
                        df_copy.loc[[i], [column]] = 0
                # delete not required rows in column
                df = df_copy[df_copy[column].notna()]
            for i, row in df.iterrows():
                if i == "label":
                    asset_name_string = asset_name_string + row[column] + ", "

                # Find type of input value (csv file is read into df as an object)
                if isinstance(row[column], str) and (
                    "[" in row[column] or "]" in row[column]
                ):
                    if "[" not in row[column] or "]" not in row[column]:
                        logging.warning(
                            "In file %s, asset %s for parameter %s either '[' or ']' is missing.",
                            filename,
                            column,
                            i,
                        )
                    else:
                        # Define list of efficiencies by efficiency,factor,"[1;2]"
                        value_string = row[column].replace("[", "").replace("]", "")
                        value_list = value_string.split(";")
                        for item in range(0, len(value_list)):
                            column_dict = conversion(
                                filename, column_dict, row, i, column, value_list[item],
                            )
                            if row["unit"] != "str":
                                if "value" in column_dict[i]:
                                    # if wrapped in list is a scalar
                                    value_list[item] = column_dict[i]["value"]
                                else:
                                    # if wrapped in list is a dictionary (ie. timeseries)
                                    value_list[item] = column_dict[i]

                            else:
                                # if wrapped in list is a string
                                value_list[item] = column_dict[i]

                        if row["unit"] != "str":
                            column_dict.update(
                                {i: {"value": value_list, "unit": row["unit"]}}
                            )
                        else:
                            column_dict.update({i: value_list})
                        logging.info(
                            "Parameter %s of asset %s is defined as a list.", i, column,
                        )
                else:
                    column_dict = conversion(
                        filename, column_dict, row, i, column, row[column]
                    )

            single_dict.update({column: column_dict})
            # add exception for energyStorage
            if filename == "energyStorage":
                storage_dict = add_storage_components(
                    df.loc["storage_filename"][column][:-4], input_directory
                )
                single_dict[column].update(storage_dict)

    logging.info(
        "From file %s following assets are added to the energy system: %s",
        filename,
        asset_name_string[:-2],
    )

    # add exception for single dicts
    if filename in [
        "economic_data",
        "project_data",
        "simulation_settings",
    ]:
        return single_dict
    elif storage is True:
        return single_dict
    else:
        single_dict2.update({filename: single_dict})
        return single_dict2
    return


def conversion(filename, column_dict, row, i, column, value):
    if isinstance(value, str) and ("{" in value or "}" in value):
        # if parameter defined as dictionary
        # example: input,str,"{'file_name':'pv_gen_merra2_2014_eff1_tilt40_az180.csv','header':'kW','unit':'kW'}"
        # todo this would not include [value, dict] eg. for multiple busses with one fix and one timeseries efficiency
        if "{" not in value or "}" not in value:
            logging.warning(
                "In file %s, asset %s for parameter %s either '{' or '}' is missing.",
                filename,
                column,
                i,
            )
        else:
            dict_string = value.replace("'", '"')
            value_dict = json.loads(dict_string)
            column_dict.update({i: value_dict})
            logging.info(
                "Parameter %s of asset %s is defined as a timeseries.", i, column
            )

    elif row["unit"] == "str":
        column_dict.update({i: value})

    else:
        if row["unit"] == "bool":
            if value in ["True", "true", "t"]:
                value = True
            elif value in ["False", "false", "F"]:
                value = False
            else:
                logging.warning(
                    "Parameter %s of asset %s is not a boolean value "
                    "(True/T/true or False/F/false."
                )
        else:
            if value == "None":
                value = None
            else:
                try:
                    value = int(value)
                except:
                    value = float(value)

        column_dict.update({i: {"value": value, "unit": row["unit"]}})
    return column_dict


def add_storage_components(storage_filename, input_directory):

    """
    loads the csv of a the specific storage listed as column in
    "energyStorage.csv", checks for complete set of parameters and creates a
    json dictionary.
    :param storage_filename: str
        name of storage, given by the column name in "energyStorage.csv
    :param input_directory: str
        path of the input directory
    :return: dict
        dictionary containing the storage parameters
    """

    if not os.path.exists(os.path.join(input_directory, f"{storage_filename}.csv")):
        logging.error(f"The storage file {storage_filename}.csv is missing!")
    else:
        # hardcoded parameterlist of common parameters in all columns
        parameters = [
            "age_installed",
            "capex_fix",
            "capex_var",
            "efficiency",
            "installedCap",
            "label",
            "lifetime",
            "opex_fix",
            "unit",
        ]
        single_dict = create_json_from_csv(
            input_directory,
            filename=storage_filename,
            parameters=parameters,
            storage=True,
        )
        return single_dict
