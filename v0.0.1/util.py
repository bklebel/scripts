from LakeShore350 import LakeShore350
import time
from uncertainties import ufloat


class LS350(LakeShore350):
    """docstring for LS350"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def sensA(self):
        return self.SensorUnitsInputReadingQuery('A')[0]

    @property
    def sensB(self):
        return self.SensorUnitsInputReadingQuery('B')[0]

    @property
    def tempA(self):
        return self.KelvinReadingQuery('A')[0]

    @property
    def tempB(self):
        return self.KelvinReadingQuery('B')[0]


def geomfactor(cs1, cs2, length, **kwargs):
    '''convert units (including sample geometries) so that [Ohm] becomes [Ohm m]
    cs1 and cs2 are the sides making up the cross-section:
        Area of cross section: A = cs1 * cs2
    length is the length of the path the current takes, as in:
    R = \rho * Length / A
    \rho = R * A / Length
    all units to be given in [mm]
    for other units ([Ohm cm]), the unit conversion
        needs to be applied 'inversly'
        [Ohm m] to [Ohm cm] has a factor of 1e2
    returns: factor to be applied to the resistance
    '''
    # area in mm^2
    Amm2 = cs1 * cs2
    # area in m^2
    Am2 = Amm2 * 1e-6
    # length in m
    le = length * 1e-3
    fac = Am2 / le
    return fac


def pressure(pcs1, pcs2, deformation=0, forceN=0, gas_pressure=0, gas_uncertainty=0, **kwargs):
    '''calculate the resulting pressure at a certain deformation

    deformation is the deformation of the spring in
        the mechanical pressure cell, as measured under
        the microscope
        can be supplied as a ufloat instance
        given in [mm] (milli metre)

    forceN is a known force, in case such a force is known
        given in [N] (Newton)

    gaspressure is the pressure in the gas-driven pressure cell,
        where 1 bar corresponds to 53 N
        given in [bar]

    pcs1 & pcs2 are the sides making up the cross section,
        to which the force is applied
        given in [mm] (milli metre)

    returns: pressure in [MPa] (Megapascal)

    '''
    # Sample:
    # area in mm^2
    Amm2 = pcs1 * pcs2
    # area in m^2
    Am2 = Amm2 * 1e-6

    # Spring (from 'Calibration_Iza (1)'):
    slope = ufloat(47.95423, 3)
    intercept = ufloat(-0.41599, 1.5)
    # force [N]
    if not forceN:
        if not gas_pressure:
            forceN = intercept + slope * abs(deformation)
        else:
            forceN = ufloat(gas_pressure, gas_uncertainty) * 15.4

    # pressure in Pascal
    pressPa = forceN / Am2

    # returning pressure in Megapascal (1 MPa = 1e6 Pa)
    return pressPa * 1e-6


def measure_tempres(LS, SAMPLE_DIMENSIONS=None) -> dict:
    if SAMPLE_DIMENSIONS is None:
        SAMPLE_DIMENSIONS = dict(cs1=1e3, cs2=1e3)

    rho = LS.sensB

    return dict(rho=rho,
                temp=LS.tempA,
                tempres=LS.sensA,
                resistivity=geomfactor(**SAMPLE_DIMENSIONS) * rho)


def measure_pressure_lockin(SRlockin, goal_pressure, inlet_pressure, n) -> dict:
    volt = goal_pressure / 1.7898
    # volt_max = inlet_pressure / 1.7898

    SRlockin.dac3 = volt
    time.sleep(1)

    for no_mes in range(n):
        read_voltage = SRlockin.adc3
        read_pressure = (read_voltage - 1.008) / 0.3924
        set_pressure = SRlockin.dac3 * 1.7898
        x = SRlockin.x
        y = SRlockin.y
        frequency = SRlockin.frequency
        sine_voltage = SRlockin.sine_voltage
        dac3 = SRlockin.dac3
        yield dict(set_pressure=set_pressure, read_pressure=read_pressure, dac3=dac3, read_voltage=read_voltage, x=x, y=y, frequency=frequency, sine_voltage=sine_voltage)

    # set_pressure = np.mean(np.array(set_pressure))
    # read_pressure = np.mean(np.array(read_pressure))
    # dac3 = np.mean(np.array(dac3))
    # read_voltage = np.mean(np.array(read_voltage))
    # x = np.mean(np.array(x))
    # y = np.mean(np.array(y))
    # frequency = np.mean(np.array(frequency))
    # sine_voltage = np.mean(np.array(sine_voltage))


def measure_pressure_multimeter(KTmult, SAMPLE_DIMENSIONS=None) -> dict:
    if SAMPLE_DIMENSIONS is None:
        SAMPLE_DIMENSIONS = dict(pcs1=1e3, pcs2=1e3, forceN=0)

    read_voltage = KTmult.voltage
    read_pressure = (read_voltage - 1.008) / 0.3924
    return dict(read_pressure=read_pressure, read_pvoltage=read_voltage, pressure_sample=pressure(**SAMPLE_DIMENSIONS, gas_pressure=read_pressure).nominal_value)
