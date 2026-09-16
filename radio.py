# ==================================================
# Tamil Radio Stations
# ==================================================

RADIO_STATIONS = {
    "suriyan_fm": {
        "name": "Suriyan FM 93.5",
        "url": "https://tamil.crabdance.com:8002/2",
    },
    
    "radio_2": {
        "name": "Tamil Radio 2",
        "url": "https://radio.lotustechnologieslk.net:8006/;stream.mp3",
    },

    "Radio_city": {
        "name": "Radio City 91.1",
        "url": "http://163.172.158.94:8064/;stream.mp3",
    },

    "radio_4": {
        "name": "Tamil Radio 4",
        "url": "YOUR_DIRECT_STREAM_URL_4",
    },

    "radio_5": {
        "name": "Tamil Radio 5",
        "url": "YOUR_DIRECT_STREAM_URL_5",
    },

    "radio_6": {
        "name": "Tamil Radio 6",
        "url": "YOUR_DIRECT_STREAM_URL_6",
    },
}


def get_radio_station(
    station_id: str,
):
    return RADIO_STATIONS.get(station_id)


def get_radio_stations():
    return RADIO_STATIONS
