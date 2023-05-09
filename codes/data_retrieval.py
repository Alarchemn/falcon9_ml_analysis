# import necessary libraries to get and manipulate the data
import requests
import numpy as np
import pandas as pd
import datetime

# Endpoint for the V5 version
ENDPOINT = 'https://api.spacexdata.com/v4'

# Request the data
response = requests.get(url=ENDPOINT + '/launches/past')
print("HTML Code: ", response)

# Convert the raw data (JSON Anidade) into pandas dataframe
data = pd.json_normalize(response.json())

# Take a relevant subset of the original data
data = data[['rocket', 'payloads', 'launchpad', 'cores', 'flight_number', 'date_utc']]

# Select only launches with 1 payload and 1 core (1 rocket)
data = data[data['payloads'].str.len() == 1]
data = data[data['cores'].str.len() == 1]

# Check the result
# print(data['payloads'].str.len().value_counts())
# print('-'*30)
# print(data['cores'].str.len().value_counts())

# transform the list type object of payloads and cores into single string
data['payloads'] = data['payloads'].str[0]
data['cores'] = data['cores'].str[0]

# Format the date (short format)
data['date'] = pd.to_datetime(data['date_utc']).dt.date

# Using the date we will restrict the dates of the launches (the rate of success after 2020 is very high)
data = data[data['date'] <= datetime.date(2020, 11, 13)]

# ----------------- DECODE AND RETRIEVAL FUNCTIONS --------------------------------------------------------------------

# Declare list for the rocket relevant parameters
boosterName = []
# Declare lists for the payloads relevant parameters
payloadMass = []
payloadOrbit = []
payloadReused = []
# Declare lists for the launchpad relevant parameters
launchName = []
launchLat = []
launchLon = []
launSuccRatio = []
# Information already in the dataset
flights = []
legs = []
reused = []
landingPad = []
gridFins = []
Outcome = []
# Information to request to the API (only if core exist)
coreReuseCount = []
coreSerial = []
coreBlock = []


# Declare a function to get all rocket relevant parameters
def getBoosterInfo(id):
    response = requests.get(url=ENDPOINT + '/rockets/' + str(id))
    json = response.json()
    boosterName.append(json['name'])


# Declare function to get all relevant payload parameters
def getPayloadInfo(id):
    response = requests.get(url=ENDPOINT + '/payloads/' + str(id))
    json = response.json()
    payloadMass.append(json['mass_kg'])
    payloadOrbit.append(json['orbit'])
    payloadReused.append(json['reused'])


# Declare function to get all launchpad relevant parameters
def getLaunchInfo(id):
    response = requests.get(url=ENDPOINT + '/launchpads/' + str(id))
    json = response.json()
    launchName.append(json['name'])
    launchLat.append(json['latitude'])
    launchLon.append(json['longitude'])
    launSuccRatio.append(np.round(json['launch_successes'] / json['launch_attempts'], 4))


# Declare function to get all Core relevant parameters
def getCoreInfo(coredict):
    # Append data only if core exist in the launch mission
    if coredict['core'] is not None:
        response = requests.get(url=ENDPOINT + '/cores/' + str(coredict['core']))
        json = response.json()
        coreReuseCount.append(json['reuse_count'])
        coreSerial.append(json['serial'])
        coreBlock.append(json['block'])
    # None if there is no core
    else:
        coreReuseCount.append(None)
        coreSerial.append(None)
        coreBlock.append(None)
    # Append data that is already in the data set (no request is necessary)
    flights.append(coredict['flight'])
    legs.append(coredict['legs'])
    reused.append(coredict['reused'])
    landingPad.append(coredict['landpad'])
    gridFins.append(coredict['gridfins'])
    Outcome.append(str(coredict['landing_success']) + ' ' + str(coredict['landing_type']))


# Declare function to get the mane of the landigpad based on the code
def getLandigPadInfo(id):
    # Request only if there is a code
    if id is not None:
        response = requests.get(url=ENDPOINT + '/landpads/' + str(id))
        json = response.json()
        return json['name']
    else:
        return np.nan


# ---------------------------------------------------------------------------------------------------------------------

# Execute the function getBoosterInfo for every element
for rocket in data['rocket']:
    getBoosterInfo(rocket)

# Execute the function getPayloadInfo for every element
for payload in data['payloads']:
    getPayloadInfo(payload)

# Execute the function getLaunchInfo for every element
for launch in data['launchpad']:
    getLaunchInfo(launch)

# Execute the function getCoreInfo for every element
for core in data['cores']:
    getCoreInfo(core)

# NOTE: This procedure is extremely inefficient because 94 requests are made
# when there are only 4 different codes.
# ALTERNATIVE: formulate a dictionary and replace the codes (only 4 requests are required)
# Replace the landigpad code with their redable name
for index in range(0, len(landingPad)):
    landingPad[index] = getLandigPadInfo(landingPad[index])

# Create a dictionary for the Dataframe with all the previusly opbtained data
spacex_dict = {'FlightNumber': list(data['flight_number']),
               'Date': list(data['date']),
               'BoosterVersion': boosterName,
               'PayloadMass': payloadMass,
               'Orbit': payloadOrbit,
               'PayloadReused': payloadReused,
               'LaunchSite': launchName,
               'Latitude': launchLat,
               'Longitude': launchLon,
               'PlatformSuccessRatio': launSuccRatio,
               'Flights': flights,
               'Legs': legs,
               'Reused': reused,
               'LandingPad': landingPad,
               'GridFins': gridFins,
               'CoreReusedCount': coreReuseCount,
               'Serial': coreSerial,
               'Block': coreBlock,
               'Outcome': Outcome}

# Create the new Dataframe
falcon9_data = pd.DataFrame(spacex_dict)

# Select only falcon 9 rockets
falcon9_data = falcon9_data[falcon9_data['BoosterVersion'] == 'Falcon 9']

# Reset the index and update the flight number from 1 to len(feature)+1
falcon9_data.reset_index(inplace=True, drop=True)
falcon9_data['FlightNumber'] = list(range(1, len(falcon9_data['FlightNumber']) + 1))

# Fill empty payload with the mean of the entire dataset
falcon9_data['PayloadMass'].fillna(falcon9_data['PayloadMass'].mean(), inplace=True)

# Get All different values in "outcome" and save them
outcome_values = falcon9_data['Outcome'].unique()

# All values in Outcome variable (target)
# ----------------------------------------
# 0   None None
# 1   False Ocean
# 2   True Ocean
# 3   False ASDS
# 4   None ASDS
# 5   True RTLS
# 6   True ASDS
# 7   False RTLS

# List comprehension to save the failures
failure = list(outcome_values[i] for i in [0, 1, 3, 4, 7])

# Apply function to binary result (0: failure, 1: success)
falcon9_data['Success'] = falcon9_data['Outcome'].apply(lambda x: 0 if x in failure else 1)

# Save all the data into a CVS file. Please uncomment if you corrected or added some data
falcon9_data.to_csv('../database/falcon9_launches2.csv', index=False)