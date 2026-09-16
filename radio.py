# ==================================================
# Tamil Radio Stations
# ==================================================

RADIO_STATIONS = {
    "hello_fm": {
        "name": "Hello FM 106.4",
        "url": "https://strw1.openstream.co/1313?aw_0_1st.collectionid%3D4428%26stationId%3D4428%26publisherId%3D1337%26k%3D1692506589",
    },
    
    "radio_2": {
        "name": "Tamil Radio 2",
        "url": "https://radio.lotustechnologieslk.net:8006/;stream.mp3",
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
