"""Public football pitch directory for Casablanca — seeded reference data.

Sourced from a Google Places export of the city's football venues (72 entries). A pitch is just a
venue in a city: any team can pick any of these when negotiating, so nothing here is owned by a
team and nothing is priced. The export also carried districts, coordinates, phone numbers and
Google ratings; none of it is kept, because nothing in the product selects on them — venues are
chosen by country and city, then by name.

Names are the identity: `seed_pitches` matches case-insensitively on (name, country, city), so
re-running the seeder never duplicates a row and a captain who adds "stade municipal" by hand lands
on the existing "Stade Municipal".

Regenerate from a fresh export rather than editing by hand.
"""

CITY = "Casablanca"
COUNTRY = "Morocco"

CASABLANCA_PITCHES: list[str] = [
    "Terrain de foot de proximite Derb Milan",
    "Terrain de foot de proximite Sidi Othmane",
    "Terrain de foot de proximite Sidi Othmane (Av. Mohamed Bouziane)",
    "Stade de proximite Ain Sebaa",
    "Terrain de proximite Avenue C",
    "Melab Al Qorb Diar Al Wafaa",
    "Melab Al Qorb Yasmina",
    "Stade Municipal Sidi Maarouf",
    "Sports Complex El Oulfa",
    "Complexe Socio-Sportif Derb Ghalef",
    "Complexe Socio Sportif Ain Chock",
    "Complexe Sportif Tawassol",
    "Complexe Sportif Essoukhour Assawda",
    "Espace Sportif Roches Noires",
    "Sports Complex Sidi Moumen",
    "Complexe Sportif Sidi Mohamed",
    "Espace Sportif Al Qods Sidi Bernoussi",
    "Stade Sidi Bernoussi",
    "Complexe Ahmed Ahras Sidi Bernoussi",
    "Club Socio Sportif Sidi Maarouf",
    "Espace Sportif Al Madina Sidi Maarouf",
    "Complexe Omar Ibn Khattab",
    "Espace Sportif Essoukhour Assawda Al Manzah (Zouidane)",
    "Stade TAS - Al Hafra",
    "Parc Sportif Californie",
    "Terrain De Football (Oulfa)",
    "Terrain de Football (Lissasfa sud)",
    "Terrain de Football Rue Socrate",
    "PUMA Playground of African Football",
    "Soccer Field of Ain Sbaa",
    "Terrain Mini-Foot Saada",
    "Destination Field",
    "Terrain Aljazira de Football",
    "Adesl - Terrains Al Qods",
    "1/5 Stadium",
    "Terrain Mini-Football El Saada (Bernoussi)",
    "Terrain de Foot Toma",
    "Soccer Field Sidi Moumen",
    "Terrain De Mini-Foot Moulay Rachid",
    "Terrains de foot (Ben Msik)",
    "MALAIB",
    "Minifoot Ben Msik",
    "Terrain Al Joulane",
    "Terrain Minifoot Ouled Herras",
    "Mini Foot (Moulay Rachid est)",
    "Minifoot Local (Derb Sultan)",
    "Stade de Football Essoukhour Assawda",
    "Terrain Jamaa",
    "Football Field OFPPT",
    "Terrain Mini-Foot Homan",
    "Soccer Field Lissasfa Route Nationale",
    "Stade Bachkou",
    "Terrain Foot (Bernoussi nord)",
    "Terrain Kahrama Ancien",
    "Terrain Rahal",
    "Olympe Mini Foot (ex Arena Soccer)",
    "Espace Sportif El Medina",
    "Football Stadium Ba Mohamed",
    "Academy Point Sport",
    "City Foot 5",
    "Ginga Foot Casablanca",
    "Etoile 5",
    "Atlantique Football Club",
    "Mirofoot Athletic Club",
    "FCC Casablanca",
    "Campus Sport",
    "Area Sports & Events Center",
    "Green Sports Park",
    "Arena Ville Verte",
    "Etoile Football Academie (EFA)",
    "Sport Plazza",
    "Complexe Sportif Kahrama",
]
