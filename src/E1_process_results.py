r"""
Module E1 process results
-------------------------
Module E1 processes the oemof results.
- receive time series per bus for all assets
- write time series to dictionary
- get optimal capacity of optimized assets
- add the evaluation of time series

"""

import logging
import pandas as pd


def get_timeseries_per_bus(dict_values, bus_data):
    r"""
    Reads simulation results of all busses and stores time series.

    Parameters
    ----------
    dict_values : dict
        Contains all input data of the simulation.
    bus_data : dict
        Contains information about all busses in a nested dict.
        1st level keys: bus names;
        2nd level keys:
            'scalars': (pd.Series) (does not exist in all dicts)
            'sequences': (pd.DataFrame) - contains flows between components and busses

    Returns
    -------
    Indirectly updated `dict_values` with 'optimizedFlows' - one data frame for each bus.

    """
    bus_data_timeseries = {}
    for bus in bus_data.keys():
        bus_data_timeseries.update(
            {bus: pd.DataFrame(index=dict_values["simulation_settings"]["time_index"])}
        )

        # obtain flows that flow into the bus
        to_bus = {
            key[0][0]: key
            for key in bus_data[bus]["sequences"].keys()
            if key[0][1] == bus and key[1] == "flow"
        }
        for asset in to_bus:
            bus_data_timeseries[bus][asset] = bus_data[bus]["sequences"][to_bus[asset]]

        # obtain flows that flow out of the bus
        from_bus = {
            key[0][1]: key
            for key in bus_data[bus]["sequences"].keys()
            if key[0][0] == bus and key[1] == "flow"
        }
        for asset in from_bus:
            bus_data_timeseries[bus][asset] = -bus_data[bus]["sequences"][
                from_bus[asset]
            ]

    dict_values.update({"optimizedFlows": bus_data_timeseries})
    return


def get_storage_results(settings, storage_bus, dict_asset):
    r"""
    Reads storage results of simulation and stores them in `dict_asset`.

    Parameters
    ----------
    settings : dict
        Contains simulation settings from `simulation_settings.csv` with
        additional information like the amount of time steps simulated in the
        optimization ('periods').
    storage_bus : dict
        Contains information about the storage bus. Information about the scalars
        like investment or initial capacity in key 'scalars' (pd.Series) and the
        flows between the component and the busses in key 'sequences' (pd.DataFrame).
    dict_asset : dict
        Contains information about the storage like capacity, charging power, etc.

    Returns
    -------
    Indirectly updates `dict_asset` with simulation results concerning the
    storage.

    """
    power_charge = storage_bus["sequences"][
        ((dict_asset["input_bus_name"], dict_asset["label"]), "flow")
    ]
    add_info_flows(settings, dict_asset["input power"], power_charge)

    power_discharge = storage_bus["sequences"][
        ((dict_asset["label"], dict_asset["output_bus_name"]), "flow")
    ]
    add_info_flows(settings, dict_asset["output power"], power_discharge)

    capacity = storage_bus["sequences"][((dict_asset["label"], "None"), "capacity")]
    add_info_flows(settings, dict_asset["storage capacity"], capacity)

    if "optimizeCap" in dict_asset:
        if dict_asset["optimizeCap"]["value"] == True:
            power_charge = storage_bus["scalars"][
                ((dict_asset["input_bus_name"], dict_asset["label"]), "invest")
            ]
            dict_asset["input power"].update(
                {
                    "optimizedAddCap": {
                        "value": power_charge,
                        "unit": dict_asset["input power"]["unit"],
                    }
                }
            )
            logging.debug(
                "Accessed optimized capacity of asset %s: %s",
                dict_asset["input power"]["label"],
                power_charge,
            )

            power_discharge = storage_bus["scalars"][
                ((dict_asset["label"], dict_asset["output_bus_name"]), "invest")
            ]
            dict_asset["output power"].update(
                {
                    "optimizedAddCap": {
                        "value": power_discharge,
                        "unit": dict_asset["output power"]["unit"],
                    }
                }
            )
            logging.debug(
                "Accessed optimized capacity of asset %s: %s",
                dict_asset["output power"]["label"],
                power_discharge,
            )

            capacity = storage_bus["scalars"][((dict_asset["label"], "None"), "invest")]
            dict_asset["storage capacity"].update(
                {
                    "optimizedAddCap": {
                        "value": capacity,
                        "unit": dict_asset["storage capacity"]["unit"],
                    }
                }
            )
            logging.debug(
                "Accessed optimized capacity of asset %s: %s",
                dict_asset["storage capacity"]["label"],
                capacity,
            )

        else:
            dict_asset["input power"].update(
                {
                    "optimizedAddCap": {
                        "value": 0,
                        "unit": dict_asset["storage capacity"]["unit"],
                    }
                }
            )
            dict_asset["output power"].update(
                {
                    "optimizedAddCap": {
                        "value": 0,
                        "unit": dict_asset["storage capacity"]["unit"],
                    }
                }
            )
            dict_asset["storage capacity"].update(
                {
                    "optimizedAddCap": {
                        "value": 0,
                        "unit": dict_asset["storage capacity"]["unit"],
                    }
                }
            )

    dict_asset.update(  # todo: this could be a separate function for testing.
        {
            "timeseries_soc": dict_asset["storage capacity"]["flow"]
            / (
                dict_asset["storage capacity"]["installedCap"]["value"]
                + dict_asset["storage capacity"]["optimizedAddCap"]["value"]
            )
        }
    )
    return


def get_results(settings, bus_data, dict_asset):
    r"""
    Reads results of the asset defined in `dict_asset` and stores them in `dict_asset`.

    Parameters
    ----------
    settings : dict
        Contains simulation settings from `simulation_settings.csv` with
        additional information like the amount of time steps simulated in the
        optimization ('periods').
    bus_data : dict
        Contains information about all busses in a nested dict.
        1st level keys: bus names;
        2nd level keys:
            'scalars': (pd.Series) (does not exist in all dicts)
            'sequences': (pd.DataFrame) - contains flows between components and busses
    dict_asset : dict
        Contains information about the asset.

    Returns
    -------
    Indirectly updates `dict_asset` with results.

    """
    # Check if the component has multiple input or output busses
    if "input_bus_name" in dict_asset:
        input_name = dict_asset["input_bus_name"]
        if not isinstance(input_name, list):
            get_flow(
                settings,
                bus_data[input_name],
                dict_asset,
                input_name,
                direction="input",
            )
        else:
            for bus in input_name:
                get_flow(settings, bus_data[bus], dict_asset, bus, direction="input")

    if "output_bus_name" in dict_asset:
        output_name = dict_asset["output_bus_name"]
        if not isinstance(output_name, list):
            get_flow(
                settings,
                bus_data[output_name],
                dict_asset,
                output_name,
                direction="output",
            )
        else:
            for bus in output_name:
                get_flow(settings, bus_data[bus], dict_asset, bus, direction="output")

    # definie capacities. Check if the component has multiple input or output busses
    if "output_bus_name" in dict_asset and "input_bus_name" in dict_asset:
        if not isinstance(output_name, list):
            get_optimal_cap(bus_data[output_name], dict_asset, output_name, "output")
        else:
            for bus in output_name:
                get_optimal_cap(bus_data[bus], dict_asset, bus, "output")

    elif "input_bus_name" in dict_asset:
        if not isinstance(input_name, list):
            get_optimal_cap(bus_data[input_name], dict_asset, input_name, "input")
        else:
            for bus in input_name:
                get_optimal_cap(bus_data[bus], dict_asset, bus, "input")

    elif "output_bus_name" in dict_asset:
        if not isinstance(output_name, list):
            get_optimal_cap(bus_data[output_name], dict_asset, output_name, "output")
        else:
            for bus in output_name:
                get_optimal_cap(bus_data[bus], dict_asset, bus, "output")
    return


def get_optimal_cap(bus, dict_asset, bus_name, direction):
    r"""
    Retrieves optimized capacity of asset specified in `dict_asset`.

    Parameters
    ----------
    bus : dict
        Contains information about the busses linked to the asset specified in
        `dict_asset`. Information about the scalars like investment or initial
        capacity in key 'scalars' (pd.Series) and the flows between the
        component and the busses in key 'sequences' (pd.DataFrame).
    dict_asset : dict
        Contains information about the asset.
    bus_name : str
        Name of `bus`.
    direction : str
        Direction of flow. Options: 'input', 'output'.

    possible todos
    --------------
    * direction as optimal parameter or with default value None (direction is
        not needed if 'optimizeCap' is not in `dict_asset` or if it's value is False

    Returns
    -------
    Indirectly updated `dict_asset` with optimal capacity to be added
    ('optimizedAddCap').

    """
    if "optimizeCap" in dict_asset:
        if dict_asset["optimizeCap"]["value"] == True:
            if direction == "input":
                optimal_capacity = bus["scalars"][
                    ((bus_name, dict_asset["label"]), "invest")
                ]
            elif direction == "output":
                optimal_capacity = bus["scalars"][
                    ((dict_asset["label"], bus_name), "invest")
                ]
            else:
                raise ValueError(
                    f"`direction` should be 'input' or 'output' but is {direction}."
                )

            if "timeseries_peak" in dict_asset:
                if dict_asset["timeseries_peak"]["value"] > 0:
                    dict_asset.update(
                        {
                            "optimizedAddCap": {
                                "value": optimal_capacity
                                / dict_asset["timeseries_peak"]["value"],
                                "unit": dict_asset["unit"],
                            }
                        }
                    )
                else:
                    logging.warning(
                        "Time series peak of asset %s negative or zero! Check timeseries. No optimized capacity derived.",
                        dict_asset["label"],
                    )
                    pass
            else:
                dict_asset.update(
                    {
                        "optimizedAddCap": {
                            "value": optimal_capacity,
                            "unit": dict_asset["unit"],
                        }
                    }
                )
            logging.debug(
                "Accessed optimized capacity of asset %s: %s",
                dict_asset["label"],
                optimal_capacity,
            )
        else:
            dict_asset.update(
                {"optimizedAddCap": {"value": 0, "unit": dict_asset["unit"]}}
            )

    return


def get_flow(settings, bus, dict_asset, bus_name, direction):
    r"""
    Adds flow of `bus` and total flow amongst other information to `dict_asset`.

    Depending on `direction` the input or the output flow is used.

    Parameters
    ----------
    settings : dict
        Contains simulation settings from `simulation_settings.csv` with
        additional information like the amount of time steps simulated in the
        optimization ('periods').
    bus : dict
        Contains information about a specific bus. Information about the scalars, if they exist,
            like investment or initial capacity in key 'scalars' (pd.Series) and the
            flows between the component and the bus(ses) in key 'sequences' (pd.DataFrame).
    dict_asset : dict
        Contains information about the asset.
    bus_name : str
        Name of `bus`.
    direction : str
        Direction of flow. Options: 'input', 'output'.

    Returns
    -------
    Indirectly updates `dict_asset` with the flow of `bus`, the total flow, the annual
    total flow, the maximum of the flow ('peak_flow') and the average value of
    the flow ('average_flow').

    """
    if direction == "input":
        flow = bus["sequences"][((bus_name, dict_asset["label"]), "flow")]
    elif direction == "output":
        flow = bus["sequences"][((dict_asset["label"], bus_name), "flow")]

    else:
        raise ValueError(
            f"`direction` should be 'input' or 'output' but is {direction}."
        )
    add_info_flows(settings, dict_asset, flow)

    logging.debug(
        "Accessed simulated timeseries of asset %s (total sum: %s)",
        dict_asset["label"],
        round(dict_asset["total_flow"]["value"]),
    )
    return


def add_info_flows(settings, dict_asset, flow):
    r"""
    Adds `flow` and total flow amongst other information to `dict_asset`.

    Parameters
    ----------
    settings : dict
        Contains simulation settings from `simulation_settings.csv` with
        additional information like the amount of time steps simulated in the
        optimization ('periods').
    dict_asset : dict
        Contains information about the asset `flow` belongs to.
    flow : pd.Series
        Time series of the flow.

    Returns
    -------
    Indirectly updates `dict_asset` with the `flow`, the total flow, the annual
    total flow, the maximum of the flow ('peak_flow') and the average value of
    the flow ('average_flow').

    """
    total_flow = sum(flow)
    dict_asset.update(
        {
            "flow": flow,
            "total_flow": {"value": total_flow, "unit": "kWh"},
            "annual_total_flow": {
                "value": total_flow * 365 / settings["evaluated_period"]["value"],
                "unit": "kWh",
            },
            "peak_flow": {"value": max(flow), "unit": "kW"},
            "average_flow": {"value": total_flow / len(flow), "unit": "kW"},
        }
    )
    return
