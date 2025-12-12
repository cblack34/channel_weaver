"""Default channel and bus configurations for Channel Weaver."""

from .types import ChannelDict, BusDict

# Channel definitions – list of dicts for easy editing and future config file support
# Any missing channels 1–N (where N is detected channel count) are auto-created as "Ch XX" with action=PROCESS
# Log warnings for auto-created channels to alert users
CHANNELS: list[ChannelDict] = [
    {"ch": 1, "name": "Kick"},
    {"ch": 2, "name": "Snare Top", "action": "SKIP"},
    {"ch": 21, "name": "Snare Top", "output_ch": 2},
    {"ch": 3, "name": "Hi-Hat"},
    {"ch": 4, "name": "Tom 1"},
    {"ch": 5, "name": "Tom 2"},
    {"ch": 6, "name": "Snare Bottom"},
    {"ch": 7, "name": "Overhead L", "action": "BUS"},
    {"ch": 8, "name": "Overhead R", "action": "BUS"},
    {"ch": 9, "name": "Bass"},
    {"ch": 10, "name": "AG"},
    {"ch": 11, "name": "EG 1"},
    {"ch": 12, "name": "EG 2"},
    {"ch": 13, "name": "Keys"},
    {"ch": 14, "name": "Vox 1"},
    {"ch": 15, "name": "Vox 2"},
    {"ch": 16, "name": "Vox 3"},
    {"ch": 17, "name": "Click"},
    {"ch": 18, "name": "Guide"},
    {"ch": 19, "name": "Loop Left", "action": "BUS"},
    {"ch": 20, "name": "Loop Right", "action": "BUS"},
    # {"ch": 21, "name": "Audience Left", "action": "SKIP"},
    {"ch": 22, "name": "Audience Right", "action": "SKIP"},
    {"ch": 23, "name": "HandHeld"},
    {"ch": 24, "name": "HeadSet"},
    {"ch": 25, "name": "blank", "action": "SKIP"},
    {"ch": 26, "name": "blank", "action": "SKIP"},
    {"ch": 27, "name": "blank", "action": "SKIP"},
    {"ch": 28, "name": "blank", "action": "SKIP"},
    {"ch": 29, "name": "blank", "action": "SKIP"},
    {"ch": 30, "name": "blank", "action": "SKIP"},
    {"ch": 31, "name": "blank", "action": "SKIP"},
    {"ch": 32, "name": "blank", "action": "SKIP"},
]

# Bus definitions – list of dicts, each owns its slot-to-channel mappings and custom file name
BUSES: list[BusDict] = [
    {
        "file_name": "07_Overheads",
        "type": "STEREO",
        "slots": {"LEFT": 7, "RIGHT": 8},
    },
    {
        "file_name": "19_Loop",
        "type": "STEREO",
        "slots": {"LEFT": 19, "RIGHT": 20},
    },
    # {
    #     "file_name": "21_Audience_Right_Mono",
    #     "type": "STEREO",
    #     "slots": {"LEFT": 21, "RIGHT": 22},
    # }
]