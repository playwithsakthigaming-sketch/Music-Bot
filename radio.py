# ==================================================
# Tamil Radio Stations
# ==================================================

RADIO_STATIONS = {
    "radio_1": {
        "name": "Tamil Radio 1",
        "url": "http://163.172.158.94:8048/;stream.mp3",
    },

    "radio_2": {
        "name": "Tamil Radio 2",
        "url": "YOUR_DIRECT_STREAM_URL_2",
    },

    "radio_3": {
        "name": "Tamil Radio 3",
        "url": "YOUR_DIRECT_STREAM_URL_3",
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
