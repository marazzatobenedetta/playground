from rocketpy import Environment, SolidMotor, Rocket, Flight, EnvironmentAnalysis, Function
import datetime
import matplotlib.pyplot as plt
import numpy



Env = Environment(
    latitude = 39.39005,
    longitude =-8.28929,
    elevation = 160,#LoadedEnv["elevation"],
    datum="WGS84"
          )
date = datetime.datetime(2024,11,10,10)
Env.set_date(date=date,timezone='UTC')


#Env.set_atmospheric_model(type='Forecast', file='GFS')
Env.set_atmospheric_model(type='Windy', file= 'ECMWF')




# ROCKET MOTOR'S DESIGN
M1790 = SolidMotor(   #TODO: TO CHECK
    thrust_source = "M1790.csv",
    burn_time=4.5, #ok
    grain_number=4, #ok
    grain_separation=0.001, #okkk
    grain_density= 939.36, # OK
    grain_outer_radius=49/1000,  #OKK
    grain_initial_inner_radius=11.375/1000, #LAB
    grain_initial_height=175.5/1000,#ok 702/4 grains
    nozzle_radius= 68.5/2000, #ok
    nozzle_position=-480/1000,#ok
    center_of_dry_mass_position=0,
    dry_mass=3567/1000, #OK
    dry_inertia=(0.14832,0.14832,0.00534),  #OK
    grains_center_of_mass_position=0)
#M1790.all_info()


# ROCKET'S DESIGN
payload = 1.172 # estimated rocket mass 17.241kg (without payload and motor hardware and propellant)
VES = Rocket(
    mass =17.54+payload, # Determined mass for target apogee of 3km 17.24kg 16.99 as defined in the excel file
    radius = 134/2000,
    inertia = (19.31, 19.31, 0.06983),
    power_off_drag = "drag_VES_noairbrakes_09-08-24.csv",
    power_on_drag = "drag_VES_noairbrakes_09-08-24.csv",
    center_of_mass_without_motor = 1.8458, #TODO: TO CHECK BEFORE LAUNCH
    coordinate_system_orientation = "nose_to_tail"
)

VES.add_motor(M1790, position=3.42-943/2000-4/100+0.02)

#VES.set_rail_buttons(3,1.7,angular_position=45)

# ADDING aerodynamics surfaces
VES.add_nose(
    length = 45.4/100,
    kind = "parabolic",
    position = 0,
)

VES.add_tail(
    top_radius = 13.4/200,
    bottom_radius = 11/200,
    length = 4/100,
    position = 3.42-4/100,
)

VES.add_trapezoidal_fins(
    n = 4,
    root_chord = 344/1000,
    tip_chord = 50.75/1000,
    span = 134/1000,
    position =  3.029, #THIS VALUE HAS BEEN CHANGED IN DELFT, CHECK AGAIN STATIC MARGIN
    sweep_length= 237/1000
)


def controller(time,sampling_rate,state,state_history,observed_variables,airbrakes):
    # state = [x, y, z, vx, vy, vz, e0, e1, e2, e3, wx, wy, wz]
    altitude_ASL = state[2]
    altitude_AGL = altitude_ASL - Env.elevation
    vx, vy, vz = state[3], state[4], state[5]

    # Get winds in x and y directions
    wind_x, wind_y = Env.wind_velocity_x(altitude_ASL), Env.wind_velocity_y(altitude_ASL)

    # Calculate Mach number
    free_stream_speed = (
                                (wind_x - vx) ** 2 + (wind_y - vy) ** 2 + (vz) ** 2
                        ) ** 0.5
    mach_number = free_stream_speed / Env.speed_of_sound(altitude_ASL)

    # Get previous state from state_history
    # previous_state = state_history[-1]
    # previous_vz = previous_state[5]

    # If we wanted to we could get the returned values from observed_variables:
    # returned_time, deployment_level, drag_coefficient = observed_variables[-1]

    # Check if the rocket has reached burnout

    # If below 1500 meters above ground level, air_brakes are not deployed

    if altitude_AGL < 2250:
        airbrakes.deployment_level = 0

    # Else calculate the deployment level
    else:
        # Controller logic
        #new_deployment_level = (
        #        air_brakes.deployment_level + 0.1 * vz + 0.01 * previous_vz ** 2
        #)

        # Limiting the speed of the air_brakes to 0.2 per second
        # Since this function is called every 1/sampling_rate seconds
        # the max change in deployment level per call is 0.2/sampling_rate
        #max_change = 0.2 / sampling_rate
        #lower_bound = air_brakes.deployment_level - max_change
        #upper_bound = air_brakes.deployment_level + max_change
        #new_deployment_level = min(max(new_deployment_level, lower_bound), upper_bound)
        new_deployment_level =0
        airbrakes.deployment_level = new_deployment_level

    # Return variables of interest to be saved in the observed_variables list
    return (
        time,
        airbrakes.deployment_level,
        airbrakes.drag_coefficient(airbrakes.deployment_level, mach_number),
    )

airbrakes = VES.add_air_brakes(
    drag_coefficient_curve="cd_mc.txt",
    controller_function=controller,
    sampling_rate=10,
    clamp=True,
    reference_area=None,
    override_rocket_drag=True,
)
#airbrakes.all_info()


#Calculation of the Cd_S given cd and diameter in inches.
cd= 2.2
diameter_in = 84
r= diameter_in/(2*39.37) # division by 39.37 is the conversion inches-> meters
area = (3.1415*(r**2))
#print("area",area)
cds_m = cd*area
print("cds",cds_m)

# ADDING parachutes
def mainTrigger(p,h,y):
    # p = pressure
    # y = [x, y, z, vx, vy, vz, e0, e1, e2, e3, w1, w2, w3]
    # activate main when vz < 0 m/s and z < 300 + 1400 m (+1400 due to surface elevation).
    return True if y[5] < 0 and y[2] < (350 + Env.elevation) else False


main = VES.add_parachute(
    name="main",
    cd_s=cds_m,
    trigger=mainTrigger,      # ejection altitude in meters
    sampling_rate=105,
    lag=1.5,
    noise=(0, 8.3, 0.5),
)

#Calculation of the Cd_S given cd and diameter in inches.
cd= 1.55
diameter_in = 30
r= diameter_in/(2*39.37)
area = (3.1415*(r**2))
print("area",area)
cds_d = cd*area
print("cds",cds_d)

drogue = VES.add_parachute(
    name="drogue",
    cd_s=cds_d,
    trigger="apogee",  # ejection at apogee
    sampling_rate=105,
    lag=1.5,
    noise=(0, 8.3, 0.5),
)

#PLOTS AND CALCULATIONS

TestFlight = Flight(rocket = VES, environment = Env, inclination = 85, rail_length = 12, heading=133)

VES.draw()