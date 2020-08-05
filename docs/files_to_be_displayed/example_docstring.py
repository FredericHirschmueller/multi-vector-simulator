import pandas as pd


def example_function(arg1, argN):
    r"""
    One line no more that 80 character explaining very shortly what the function does

    More detailed explanation about the function,
    can have several lines

    Parameters
    ----------
    arg1 : str or list(str)
        description of arg1
        Default: <default value here>.

    ...

    argN : str or list(str)
        description of argN
        Default: <default value here>.

    Returns
    -------
    :pandas:`pandas.DataFrame<frame>`
        here comes the description

    Notes
    -----
    You can cite the references below using [1]_ or [2]_  add maths equations like this:

    .. math:: P=\frac{1}{8}\cdot\rho_{hub}\cdot d_{rotor}^{2}
        \cdot\pi\cdot v_{wind}^{3}\cdot cp\left(v_{wind}\right)

    with:
        P: power [W], :math:`\rho`: density [kg/m³], d: diameter [m],
        v: wind speed [m/s], cp: power coefficient

    References
    ----------
    .. [1] paper 1
    .. [2] paper 2

    Examples
    --------
    # Here you can write some basic python code that is tested with pytest
    >>> from mvs_eland import C0_data_processing
    >>> from C0_data_processing import simulation_settings
    >>> simulation_settings(simulation_settings=XYZ)
    simulation_settings  # this is the expected return of the line above

    """
    return pd.DataFrame([arg1, argN], axis=1)