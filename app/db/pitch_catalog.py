"""Public pitch directory for Casablanca — seeded reference data.

Sourced from a Google Places export of the city's football venues (72 entries, each with real
coordinates). These belong to no team: they are inserted with `team_id=None` and `is_neutral=True`
so any negotiation can pick one, unlike a venue a captain registers for their own team.

`price_per_hour` is deliberately absent — the source has no rates, and the broadcast wizard hides
its cost callout for a pitch whose price is unknown rather than showing an invented figure. Fill
these in as real prices are confirmed.

Regenerate from a new export rather than editing by hand; `place_id` is the stable key that makes
re-seeding idempotent.
"""

CITY = "Casablanca"

# One row per pitch, kept on a single line so the file stays diffable against a fresh export.
# fmt: off
# (place_id, name, district, latitude, longitude, phone, maps_url)
CASABLANCA_PITCHES: list[tuple[str, str, str | None, float, float, str | None, str | None]] = [
    ("ChIJYTuNexXNpw0RNecYHVN_mSw", "Terrain de foot de proximite Derb Milan", "Sidi Othmane", 33.5652175, -7.5800542, None, "https://www.google.com/maps/search/?api=1&query=33.5652175,-7.5800542&query_place_id=ChIJYTuNexXNpw0RNecYHVN_mSw"),
    ("ChIJJYh7iCvNpw0RA3ytCAae4MA", "Terrain de foot de proximite Sidi Othmane", "Sidi Othmane", 33.5655505, -7.5768436, None, "https://www.google.com/maps/search/?api=1&query=33.5655505,-7.5768436&query_place_id=ChIJJYh7iCvNpw0RA3ytCAae4MA"),
    ("ChIJKQexjqgzpg0RNzFwHdUL4hQ", "Terrain de foot de proximite Sidi Othmane (Av. Mohamed Bouziane)", "Sidi Othmane", 33.5565255, -7.5667923, None, "https://www.google.com/maps/search/?api=1&query=33.5565255,-7.5667923&query_place_id=ChIJKQexjqgzpg0RNzFwHdUL4hQ"),
    ("ChIJ_ZA6K7nLpw0RLciyCBes6z4", "Stade de proximite Ain Sebaa", "Ain Sebaa", 33.5953946, -7.52044, "+212 661 61 23 02", "https://www.google.com/maps/search/?api=1&query=33.5953946,-7.52044&query_place_id=ChIJ_ZA6K7nLpw0RLciyCBes6z4"),
    ("ChIJ3blmbinNpw0R7mtzI2ehI7Y", "Terrain de proximite Avenue C", "Hay Mohammadi", 33.5855482, -7.5688928, None, "https://www.google.com/maps/search/?api=1&query=33.5855482,-7.5688928&query_place_id=ChIJ3blmbinNpw0R7mtzI2ehI7Y"),
    ("ChIJuU2AHUrNpw0R3Ks7j7AJDaA", "Melab Al Qorb Diar Al Wafaa", "Roches Noires / Diar Al Wafaa", 33.5772494, -7.5551669, None, "https://www.google.com/maps/search/?api=1&query=33.5772494,-7.5551669&query_place_id=ChIJuU2AHUrNpw0R3Ks7j7AJDaA"),
    ("ChIJWXmR1A0zpg0RrUVCxxJv_NU", "Melab Al Qorb Yasmina", "Sidi Othmane / Yasmina", 33.540359, -7.5794265, "+212 662 61 58 52", "https://www.google.com/maps/search/?api=1&query=33.540359,-7.5794265&query_place_id=ChIJWXmR1A0zpg0RrUVCxxJv_NU"),
    ("ChIJs5yDpKwtpg0RdUKVvVT4REQ", "Stade Municipal Sidi Maarouf", "Sidi Maarouf", 33.5091962, -7.6538122, "+212 674 38 18 19", "https://www.google.com/maps/search/?api=1&query=33.5091962,-7.6538122&query_place_id=ChIJs5yDpKwtpg0RdUKVvVT4REQ"),
    ("ChIJ1X-X_7Qspg0RnaGV-FhfWN0", "Sports Complex El Oulfa", "Hay Hassani / Oulfa", 33.5554122, -7.6796048, None, "https://www.google.com/maps/search/?api=1&query=33.5554122,-7.6796048&query_place_id=ChIJ1X-X_7Qspg0RnaGV-FhfWN0"),
    ("ChIJiQ2INADTpw0R1Px5jsSyFEI", "Complexe Socio-Sportif Derb Ghalef", "Derb Ghalef / Maarif", 33.5736009, -7.6282131, None, "https://www.google.com/maps/search/?api=1&query=33.5736009,-7.6282131&query_place_id=ChIJiQ2INADTpw0R1Px5jsSyFEI"),
    ("ChIJMdh563Uzpg0RK2mXlnXInJA", "Complexe Socio Sportif Ain Chock", "Ain Chock", 33.5301344, -7.6002304, "+212 675 46 40 75", "https://www.google.com/maps/search/?api=1&query=33.5301344,-7.6002304&query_place_id=ChIJMdh563Uzpg0RK2mXlnXInJA"),
    ("ChIJLQBttNXTpw0R13M4h3Mq8Fg", "Complexe Sportif Tawassol", "Ain Sebaa / Rue Argana", 33.5986441, -7.6284566, None, "https://www.google.com/maps/search/?api=1&query=33.5986441,-7.6284566&query_place_id=ChIJLQBttNXTpw0R13M4h3Mq8Fg"),
    ("ChIJceY7RhHNpw0RjCSHnLN8q2E", "Complexe Sportif Essoukhour Assawda", "Essoukhour Assawda", 33.5736504, -7.5710975, None, "https://www.google.com/maps/search/?api=1&query=33.5736504,-7.5710975&query_place_id=ChIJceY7RhHNpw0RjCSHnLN8q2E"),
    ("ChIJqRQQgNrMpw0RYii23VEMpBk", "Espace Sportif Roches Noires", "Roches Noires", 33.5768108, -7.5598846, None, "https://www.google.com/maps/search/?api=1&query=33.5768108,-7.5598846&query_place_id=ChIJqRQQgNrMpw0RYii23VEMpBk"),
    ("ChIJh7ZIkmjLpw0RY6yLfM6PTzE", "Sports Complex Sidi Moumen", "Sidi Moumen", 33.5943765, -7.5128185, None, "https://www.google.com/maps/search/?api=1&query=33.5943765,-7.5128185&query_place_id=ChIJh7ZIkmjLpw0RY6yLfM6PTzE"),
    ("ChIJK7zGu57Mpw0R-htZoXwuYFg", "Complexe Sportif Sidi Mohamed", "Ain Sebaa", 33.5943548, -7.5292346, "+212 698 53 21 48", "https://www.google.com/maps/search/?api=1&query=33.5943548,-7.5292346&query_place_id=ChIJK7zGu57Mpw0R-htZoXwuYFg"),
    ("ChIJtYWBkjvLpw0Rfvaf0e_waKI", "Espace Sportif Al Qods Sidi Bernoussi", "Sidi Bernoussi", 33.6112312, -7.489472, None, "https://www.google.com/maps/search/?api=1&query=33.6112312,-7.489472&query_place_id=ChIJtYWBkjvLpw0Rfvaf0e_waKI"),
    ("ChIJh47qZnLLpw0RtMxPSEzO4-E", "Stade Sidi Bernoussi", "Sidi Bernoussi", 33.6040561, -7.5049757, None, "https://www.google.com/maps/search/?api=1&query=33.6040561,-7.5049757&query_place_id=ChIJh47qZnLLpw0RtMxPSEzO4-E"),
    ("ChIJ25eqfDnLpw0RBiSdVy66AxI", "Complexe Ahmed Ahras Sidi Bernoussi", "Sidi Bernoussi", 33.6033415, -7.5063021, None, "https://www.google.com/maps/search/?api=1&query=33.6033415,-7.5063021&query_place_id=ChIJ25eqfDnLpw0RBiSdVy66AxI"),
    ("ChIJDRD_cwUtpg0RkSWq0INwSR4", "Club Socio Sportif Sidi Maarouf", "Sidi Maarouf", 33.5245795, -7.6450065, None, "https://www.google.com/maps/search/?api=1&query=33.5245795,-7.6450065&query_place_id=ChIJDRD_cwUtpg0RkSWq0INwSR4"),
    ("ChIJJRpg-5wtpg0R1KDBYoZR3rk", "Espace Sportif Al Madina Sidi Maarouf", "Sidi Maarouf", 33.5267485, -7.6509804, "+212 706 81 57 41", "https://www.google.com/maps/search/?api=1&query=33.5267485,-7.6509804&query_place_id=ChIJJRpg-5wtpg0R1KDBYoZR3rk"),
    ("ChIJi0AVEssypg0R7NolA0s8sM8", "Complexe Omar Ibn Khattab", "Ben Msik / Sbata", 33.562116, -7.5859091, None, "https://www.google.com/maps/search/?api=1&query=33.562116,-7.5859091&query_place_id=ChIJi0AVEssypg0R7NolA0s8sM8"),
    ("ChIJ40pm6AXNpw0RCkPulVQGQ18", "Espace Sportif Essoukhour Assawda Al Manzah (Zouidane)", "Essoukhour Assawda", 33.5724956, -7.5670668, None, "https://www.google.com/maps/search/?api=1&query=33.5724956,-7.5670668&query_place_id=ChIJ40pm6AXNpw0RCkPulVQGQ18"),
    ("ChIJ900dAQDNpw0RzofH_Db_ZqU", "Stade TAS - Al Hafra", "Hay Mohammadi", 33.590046, -7.5654553, None, "https://www.google.com/maps/search/?api=1&query=33.590046,-7.5654553&query_place_id=ChIJ900dAQDNpw0RzofH_Db_ZqU"),
    ("ChIJIZjqO98tpg0RhHnGo-v1JjM", "Parc Sportif Californie", "Californie", 33.5264285, -7.6123028, None, "https://www.google.com/maps/search/?api=1&query=33.5264285,-7.6123028&query_place_id=ChIJIZjqO98tpg0RhHnGo-v1JjM"),
    ("ChIJfz2WOUbTpw0RUY2wSMDFoEA", "Terrain De Football (Oulfa)", "Hay Hassani / Oulfa", 33.5704851, -7.680019, None, "https://www.google.com/maps/search/?api=1&query=33.5704851,-7.680019&query_place_id=ChIJfz2WOUbTpw0RUY2wSMDFoEA"),
    ("ChIJ_fTMj_Espg0RgVZvimMYGzE", "Terrain de Football (Lissasfa sud)", "Lissasfa", 33.5234981, -7.6704684, "+212 772 14 96 78", "https://www.google.com/maps/search/?api=1&query=33.5234981,-7.6704684&query_place_id=ChIJ_fTMj_Espg0RgVZvimMYGzE"),
    ("ChIJ-S_WYwDTpw0RG5bmLFJ-TfE", "Terrain de Football Rue Socrate", "Maarif / Racine", 33.582044, -7.6492967, None, "https://www.google.com/maps/search/?api=1&query=33.582044,-7.6492967&query_place_id=ChIJ-S_WYwDTpw0RG5bmLFJ-TfE"),
    ("ChIJp5FPVwAtpg0RLCTJnMRSSVw", "PUMA Playground of African Football", "Maarif / Bd Modibo Keita", 33.5531394, -7.6281214, None, "https://www.google.com/maps/search/?api=1&query=33.5531394,-7.6281214&query_place_id=ChIJp5FPVwAtpg0RLCTJnMRSSVw"),
    ("ChIJuYLL28LNpw0RbvLnQE_LbnU", "Soccer Field of Ain Sbaa", "Ain Sebaa", 33.5934036, -7.5275794, "+212 668 17 28 72", "https://www.google.com/maps/search/?api=1&query=33.5934036,-7.5275794&query_place_id=ChIJuYLL28LNpw0RbvLnQE_LbnU"),
    ("ChIJv9mAr1_Lpw0RB-6xoGlPc-c", "Terrain Mini-Foot Saada", "Ain Sebaa", 33.5879209, -7.522684, None, "https://www.google.com/maps/search/?api=1&query=33.5879209,-7.522684&query_place_id=ChIJv9mAr1_Lpw0RB-6xoGlPc-c"),
    ("ChIJ-Xzqq2HLpw0Rahn_Ww4dtGs", "Destination Field", "Ain Sebaa / Beausite", 33.593243, -7.5222726, "+212 671 59 38 52", "https://www.google.com/maps/search/?api=1&query=33.593243,-7.5222726&query_place_id=ChIJ-Xzqq2HLpw0Rahn_Ww4dtGs"),
    ("ChIJC9ZjxRzLpw0RFTKxMpSKgPs", "Terrain Aljazira de Football", "Sidi Bernoussi", 33.6028782, -7.4849048, "+212 609 61 23 84", "https://www.google.com/maps/search/?api=1&query=33.6028782,-7.4849048&query_place_id=ChIJC9ZjxRzLpw0RFTKxMpSKgPs"),
    ("ChIJu9ru8-DLpw0RlqRF6lk5Kuw", "Adesl - Terrains Al Qods", "Sidi Bernoussi", 33.6049426, -7.4854752, "+212 664 50 23 04", "https://www.google.com/maps/search/?api=1&query=33.6049426,-7.4854752&query_place_id=ChIJu9ru8-DLpw0RlqRF6lk5Kuw"),
    ("ChIJvfFsu5bLpw0RHXBw8uNbCwM", "1/5 Stadium", "Sidi Bernoussi", 33.5985752, -7.4871367, None, "https://www.google.com/maps/search/?api=1&query=33.5985752,-7.4871367&query_place_id=ChIJvfFsu5bLpw0RHXBw8uNbCwM"),
    ("ChIJi5D6BQDLpw0RL7G0CasfJso", "Terrain Mini-Football El Saada (Bernoussi)", "Sidi Bernoussi", 33.6134455, -7.4946291, None, "https://www.google.com/maps/search/?api=1&query=33.6134455,-7.4946291&query_place_id=ChIJi5D6BQDLpw0RL7G0CasfJso"),
    ("ChIJbf4uVODLpw0RnHkPpi5tCYw", "Terrain de Foot Toma", "Sidi Moumen", 33.5919025, -7.5152558, None, "https://www.google.com/maps/search/?api=1&query=33.5919025,-7.5152558&query_place_id=ChIJbf4uVODLpw0RnHkPpi5tCYw"),
    ("ChIJ53gkRBjLpw0RlIQXNnbFHRk", "Soccer Field Sidi Moumen", "Sidi Moumen", 33.5939021, -7.4907017, "+212 603 97 82 36", "https://www.google.com/maps/search/?api=1&query=33.5939021,-7.4907017&query_place_id=ChIJ53gkRBjLpw0RlIQXNnbFHRk"),
    ("ChIJ8ZUUcLXMpw0RSuvfkOvJukc", "Terrain De Mini-Foot Moulay Rachid", "Moulay Rachid", 33.5686704, -7.5456437, None, "https://www.google.com/maps/search/?api=1&query=33.5686704,-7.5456437&query_place_id=ChIJ8ZUUcLXMpw0RSuvfkOvJukc"),
    ("ChIJ6UAxPzgzpg0RO178nCQiyio", "Terrains de foot (Ben Msik)", "Ben Msik", 33.5596913, -7.5721342, None, "https://www.google.com/maps/search/?api=1&query=33.5596913,-7.5721342&query_place_id=ChIJ6UAxPzgzpg0RO178nCQiyio"),
    ("ChIJV9x5JjHNpw0Rc3D8XEaSceI", "MALAIB", "Sidi Othmane / Derb Sultan", 33.5722012, -7.5835107, "+212 602 04 39 36", "https://www.google.com/maps/search/?api=1&query=33.5722012,-7.5835107&query_place_id=ChIJV9x5JjHNpw0Rc3D8XEaSceI"),
    ("ChIJBylBP8oypg0RDpNetVcoSlA", "Minifoot Ben Msik", "Ben Msik", 33.559653, -7.5881088, None, "https://www.google.com/maps/search/?api=1&query=33.559653,-7.5881088&query_place_id=ChIJBylBP8oypg0RDpNetVcoSlA"),
    ("ChIJq5AWLQDNpw0RqqefkrlXHU0", "Terrain Al Joulane", "Route Oulad Ziane", 33.5690889, -7.577327, "+212 666 58 31 12", "https://www.google.com/maps/search/?api=1&query=33.5690889,-7.577327&query_place_id=ChIJq5AWLQDNpw0RqqefkrlXHU0"),
    ("ChIJm5__F9bNpw0RJo4CCAoHykY", "Terrain Minifoot Ouled Herras", "Hay Mohammadi", 33.5775266, -7.5678414, None, "https://www.google.com/maps/search/?api=1&query=33.5775266,-7.5678414&query_place_id=ChIJm5__F9bNpw0RJo4CCAoHykY"),
    ("ChIJ8d_lbzozpg0RmsbLtwZInqk", "Mini Foot (Moulay Rachid est)", "Moulay Rachid", 33.554091, -7.5537525, None, "https://www.google.com/maps/search/?api=1&query=33.554091,-7.5537525&query_place_id=ChIJ8d_lbzozpg0RmsbLtwZInqk"),
    ("ChIJq6q6Fc0ypg0RjckjjJ_EjK8", "Minifoot Local (Derb Sultan)", "Derb Sultan", 33.5628499, -7.5804641, None, "https://www.google.com/maps/search/?api=1&query=33.5628499,-7.5804641&query_place_id=ChIJq6q6Fc0ypg0RjckjjJ_EjK8"),
    ("ChIJf8yb9yjNpw0RGqJYKpCr_UE", "Stade de Football Essoukhour Assawda", "Essoukhour Assawda", 33.573925, -7.5711294, None, "https://www.google.com/maps/search/?api=1&query=33.573925,-7.5711294&query_place_id=ChIJf8yb9yjNpw0RGqJYKpCr_UE"),
    ("ChIJ__-_TuYypg0RFPZCVvTnGng", "Terrain Jamaa", "Sidi Othmane sud", 33.5390918, -7.5771193, None, "https://www.google.com/maps/search/?api=1&query=33.5390918,-7.5771193&query_place_id=ChIJ__-_TuYypg0RFPZCVvTnGng"),
    ("ChIJB8UjbT_Npw0RfAsbFY_G_qA", "Football Field OFPPT", "Ben Msik / Hay Mohammadi", 33.582516, -7.5884531, None, "https://www.google.com/maps/search/?api=1&query=33.582516,-7.5884531&query_place_id=ChIJB8UjbT_Npw0RfAsbFY_G_qA"),
    ("ChIJXUKlRN8zpg0RC89ybCgR41g", "Terrain Mini-Foot Homan", "Bouskoura nord", 33.5007785, -7.5895163, None, "https://www.google.com/maps/search/?api=1&query=33.5007785,-7.5895163&query_place_id=ChIJXUKlRN8zpg0RC89ybCgR41g"),
    ("ChIJ9eAexusspg0RFYAj_6Udfa8", "Soccer Field Lissasfa Route Nationale", "Lissasfa", 33.5329863, -7.6721693, None, "https://www.google.com/maps/search/?api=1&query=33.5329863,-7.6721693&query_place_id=ChIJ9eAexusspg0RFYAj_6Udfa8"),
    ("ChIJg9vhuB4tpg0RZZAKBifbeH4", "Stade Bachkou", "Bachkou / Maarif sud", 33.5335315, -7.6513231, "+212 665 61 67 44", "https://www.google.com/maps/search/?api=1&query=33.5335315,-7.6513231&query_place_id=ChIJg9vhuB4tpg0RZZAKBifbeH4"),
    ("ChIJE4J87dLLpw0RsUiKTX5C1ns", "Terrain Foot (Bernoussi nord)", "Sidi Bernoussi", 33.6243925, -7.4978974, None, "https://www.google.com/maps/search/?api=1&query=33.6243925,-7.4978974&query_place_id=ChIJE4J87dLLpw0RsUiKTX5C1ns"),
    ("ChIJncufBMctpg0Ry1zlLzrtHdA", "Terrain Kahrama Ancien", "Bd de La Mecque", 33.5370005, -7.6313956, None, "https://www.google.com/maps/search/?api=1&query=33.5370005,-7.6313956&query_place_id=ChIJncufBMctpg0Ry1zlLzrtHdA"),
    ("ChIJh3BnCOHTpw0Ruezjkmbz5DM", "Terrain Rahal", "Anfa / Bd d'Anfa", 33.5954629, -7.6259545, "+212 614 39 14 69", "https://www.google.com/maps/search/?api=1&query=33.5954629,-7.6259545&query_place_id=ChIJh3BnCOHTpw0Ruezjkmbz5DM"),
    ("ChIJqVZXOVvNpw0RnocqW6297Go", "Olympe Mini Foot (ex Arena Soccer)", "Bd de la Plage / Ain Sebaa", 33.6170224, -7.5406317, None, "https://www.google.com/maps/search/?api=1&query=33.6170224,-7.5406317&query_place_id=ChIJqVZXOVvNpw0RnocqW6297Go"),
    ("ChIJHZ1195otpg0RmQW0kydHxbA", "Espace Sportif El Medina", "Sidi Maarouf / Attaoufik", 33.5268227, -7.6510287, None, "https://www.google.com/maps/search/?api=1&query=33.5268227,-7.6510287&query_place_id=ChIJHZ1195otpg0RmQW0kydHxbA"),
    ("ChIJEwYKUiczpg0R4cIDDq8AMJ8", "Football Stadium Ba Mohamed", "Moulay Rachid / Sbata", 33.5487539, -7.5673833, "+212 660 31 41 51", "https://www.google.com/maps/search/?api=1&query=33.5487539,-7.5673833&query_place_id=ChIJEwYKUiczpg0R4cIDDq8AMJ8"),
    ("ChIJFfJRWwAzpg0Rl3Yt_pNycT8", "Academy Point Sport", "Moulay Rachid / Sidi Othmane", 33.5343654, -7.5552158, "+212 691 03 25 15", "https://www.google.com/maps/search/?api=1&query=33.5343654,-7.5552158&query_place_id=ChIJFfJRWwAzpg0Rl3Yt_pNycT8"),
    ("ChIJtTdP20ktpg0RsgeIi_eB9H8", "City Foot 5", "Oasis", 33.549968, -7.636353, "+212 522 99 44 98", "https://www.google.com/maps/search/?api=1&query=33.549968,-7.636353&query_place_id=ChIJtTdP20ktpg0RsgeIi_eB9H8"),
    ("ChIJ18to_t3Spw0R-zl4lsp3A5c", "Ginga Foot Casablanca", "Complexe Mohammed V / Rue Socrate", 33.5820758, -7.6492581, "+212 669 89 22 44", "https://www.google.com/maps/search/?api=1&query=33.5820758,-7.6492581&query_place_id=ChIJ18to_t3Spw0R-zl4lsp3A5c"),
    ("ChIJ39df8X4tpg0RaZyQbDVfZ68", "Etoile 5", "Beausejour", 33.5579923, -7.6497805, "+212 653 36 83 58", "https://www.google.com/maps/search/?api=1&query=33.5579923,-7.6497805&query_place_id=ChIJ39df8X4tpg0RaZyQbDVfZ68"),
    ("ChIJF4ZOP1TSpw0RsKpWlzsPXxw", "Atlantique Football Club", "El Hank / Corniche", 33.6081983, -7.6504453, "+212 666 02 52 90", "https://www.google.com/maps/search/?api=1&query=33.6081983,-7.6504453&query_place_id=ChIJF4ZOP1TSpw0RsKpWlzsPXxw"),
    ("ChIJE4qFK-kspg0RlpvSfbprzr0", "Mirofoot Athletic Club", "Lissasfa / Route El Jadida", 33.5311853, -7.6683634, "+212 666 04 00 62", "https://www.google.com/maps/search/?api=1&query=33.5311853,-7.6683634&query_place_id=ChIJE4qFK-kspg0RlpvSfbprzr0"),
    ("ChIJu5WK6uUspg0R1Ihd_P0ZDck", "FCC Casablanca", "Sidi Maarouf", 33.5094472, -7.6533298, None, "https://www.google.com/maps/search/?api=1&query=33.5094472,-7.6533298&query_place_id=ChIJu5WK6uUspg0R1Ihd_P0ZDck"),
    ("ChIJU3StwOUspg0RmItrt4FBC9E", "Campus Sport", "Route El Jadida / Dali", 33.5300388, -7.6639768, "+212 522 91 12 05", "https://www.google.com/maps/search/?api=1&query=33.5300388,-7.6639768&query_place_id=ChIJU3StwOUspg0RmItrt4FBC9E"),
    ("ChIJw-Tog0Ytpg0RzCie_pef0kI", "Area Sports & Events Center", "Dar Bouazza axis / sud-ouest", 33.502546, -7.6838098, "+212 664 66 69 40", "https://www.google.com/maps/search/?api=1&query=33.502546,-7.6838098&query_place_id=ChIJw-Tog0Ytpg0RzCie_pef0kI"),
    ("ChIJdZn7DZstpg0Rm4bW4AIgj94", "Green Sports Park", "Bouskoura", 33.4800223, -7.6359558, "+212 666 70 55 38", "https://www.google.com/maps/search/?api=1&query=33.4800223,-7.6359558&query_place_id=ChIJdZn7DZstpg0Rm4bW4AIgj94"),
    ("ChIJz3t-IQAzpg0RCy6PwOqIldc", "Arena Ville Verte", "Bouskoura", 33.4870476, -7.5779506, "+212 625 90 90 90", "https://www.google.com/maps/search/?api=1&query=33.4870476,-7.5779506&query_place_id=ChIJz3t-IQAzpg0RCy6PwOqIldc"),
    ("ChIJKWXODM0spg0RJpF4OsLQtV4", "Etoile Football Academie (EFA)", "Beausejour", 33.5585748, -7.6508212, "+212 708 30 30 39", "https://www.google.com/maps/search/?api=1&query=33.5585748,-7.6508212&query_place_id=ChIJKWXODM0spg0RJpF4OsLQtV4"),
    ("ChIJhX7Aazktpg0Rfp-9sdLp4Ow", "Sport Plazza", "Bd Panoramique / Route de la Mecque", 33.5462905, -7.631457, "+212 522 52 37 02", "https://www.google.com/maps/search/?api=1&query=33.5462905,-7.631457&query_place_id=ChIJhX7Aazktpg0Rfp-9sdLp4Ow"),
    ("ChIJneCg7Lwtpg0R77qasosJYKo", "Complexe Sportif Kahrama", "Bd de La Mecque", 33.5369611, -7.6307891, "+212 522 87 20 87", "https://www.google.com/maps/search/?api=1&query=33.5369611,-7.6307891&query_place_id=ChIJneCg7Lwtpg0R77qasosJYKo"),
]
# fmt: on
