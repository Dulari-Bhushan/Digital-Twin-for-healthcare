"""Fictional North Indian names for the synthetic demo patients (matched to each patient's sex and age).

The names are invented for the demo and do not refer to real people.
"""

NAMES = {
    1789: "Kamla Devi", 62: "Harpreet Singh", 1217: "Pooja Verma", 1102: "Mohammed Rafiq", 1688: "Rajesh Sharma",
    302: "Brijmohan Yadav", 1008: "Ramprasad Mishra", 800: "Arjun Malhotra", 496: "Neha Chauhan", 1705: "Savitri Devi",
    1132: "Sunita Agarwal", 1091: "Anil Saxena", 308: "Prakash Joshi", 7: "Sanjay Gupta", 1520: "Vikram Rathore",
    1527: "Meena Tiwari", 507: "Surendra Pratap Singh", 1974: "Imran Qureshi", 1357: "Rakesh Bhatt", 814: "Dilip Pandey",
    1128: "Manoj Dubey", 1636: "Priya Kashyap", 750: "Gopal Chaudhary", 430: "Anjali Mehra",
}

# The two patients used in the live demo, chosen for contrast.
DEMO_TAGS = {1688: "Demo: complex case", 1636: "Demo: well controlled"}


def name_of(pid: int) -> str:
    return NAMES.get(int(pid), f"Patient {pid}")
