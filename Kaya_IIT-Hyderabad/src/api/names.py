"""Fictional Indian names for the synthetic demo patients (matched to each patient's sex and age).

The names are invented for the demo and do not refer to real people.
"""

NAMES = {
    1789: "Padmavathi Reddy", 62: "Harpreet Singh", 1217: "Pooja Deshmukh", 1102: "Mohammed Rafiq", 1688: "Venkatesh Rao",
    302: "Basavaraj Hiremath", 1008: "Ramakrishnan Iyer", 800: "Arjun Malhotra", 496: "Divya Chatterjee", 1705: "Rukmini Nair",
    1132: "Shobha Patil", 1091: "Anil Kulkarni", 308: "Prakash Naik", 7: "Sanjay Gupta", 1520: "Karthik Subramanian",
    1527: "Meenakshi Pillai", 507: "Srinivas Murthy", 1974: "Imran Qureshi", 1357: "Rajesh Bhatt", 814: "Dilip Banerjee",
    1128: "Manoj Tiwari", 1636: "Kavya Gowda", 750: "Gopal Krishnan", 430: "Anjali Sharma",
}

# The two patients used in the live demo, chosen for contrast.
DEMO_TAGS = {1688: "Demo: complex case", 1636: "Demo: well controlled"}


def name_of(pid: int) -> str:
    return NAMES.get(int(pid), f"Patient {pid}")
