"""
Patterns for matching property descriptors.
See https://spacy.io/usage/rule-based-matching#entityruler
for info on entity rulers
"""

ABSORPTIVITY_PATTERNS = [
    {"label": "PROP", "pattern": [{"LEMMA": "absorptivity"}], "id": "absorptivity"},
    {
        "label": "PROP",
        "pattern": [
            {"LEMMA": "molar"},
            {"LEMMA": {"IN": ["absorption", "absorptivity"]}},
        ],
        "id": "absorptivity",
    },
    {
        "label": "FORMULA",
        "pattern": [{"TEXT": "A"}, {"LOWER": "="}],
        "id": "absorptivity",
    },
    {
        "label": "FORMULA",
        "pattern": [{"TEXT": "A="}],
        "id": "absorptivity",
    },
]

VACUUM_PATTERNS = [
    {
        "label": "PROP",
        "pattern": [
            {"LOWER": "vacuum"},
            {"LEMMA": {"IN": ["stability", "decay"]}},
        ],
        "id": "vaccum",
    },
]

ENTHALPY_PATTERNS = [
    {
        "label": "PROP",
        "pattern": [
            {"LEMMA": "molar", "OP": "?"},
            {"LEMMA": "enthalpy"},
            {"LOWER": "of"},
            {
                "LEMMA": {
                    "IN": [
                        "combustion",
                        "formation",
                        "explosion",
                        "sublimation",
                        "detonation",
                        "decomposition",
                    ]
                }
            },
        ],
        "id": "enthalpy",
    },
    {
        "label": "PROP",
        "pattern": [
            {"LEMMA": "molar", "OP": "?"},
            {
                "LEMMA": {
                    "IN": [
                        "combustion",
                        "formation",
                        "explosion",
                        "sublimation",
                        "detonation",
                        "decomposition",
                    ]
                }
            },
            {"LEMMA": "enthalpy"},
        ],
        "id": "enthalpy",
    },
    {
        "label": "PROP",
        "pattern": [
            {"LEMMA": "molar", "OP": "?"},
            {"LEMMA": "heat"},
            {"LOWER": "of"},
            {
                "LEMMA": {
                    "IN": [
                        "combustion",
                        "formation",
                        "explosion",
                        "sublimation",
                        "detonation",
                        "decomposition",
                    ]
                }
            },
        ],
        "id": "enthalpy",
    },
    {
        "label": "PROP",
        "pattern": [
            {"LEMMA": "molar", "OP": "?"},
            {
                "LEMMA": {
                    "IN": [
                        "combustion",
                        "formation",
                        "explosion",
                        "sublimation",
                        "detonation",
                        "decomposition",
                    ]
                }
            },
            {"LEMMA": "heat"},
        ],
        "id": "enthalpy",
    },
    {
        "label": "FORMULA",
        "pattern": [
            {"TEXT": "Δ"},
            {"TEXT": "H"},
            {"LOWER": "sub", "OP": "?"},
            {"LOWER": "fus", "OP": "?"},
            {"LOWER": "vap", "OP": "?"},
            {"LOWER": "f", "OP": "?"},
            {"LOWER": "exp", "OP": "?"},
            {"LOWER": "d", "OP": "?"},
            {"LOWER": "dec", "OP": "?"},
        ],
        "id": "enthalpy",
    },
    {
        "label": "FORMULA",
        "pattern": [
            {"TEXT": "ΔH"},
            {"LOWER": "sub", "OP": "?"},
            {"LOWER": "fus", "OP": "?"},
            {"LOWER": "vap", "OP": "?"},
            {"LOWER": "f", "OP": "?"},
            {"LOWER": "exp", "OP": "?"},
            {"LOWER": "d", "OP": "?"},
            {"LOWER": "dec", "OP": "?"},
        ],
        "id": "enthalpy",
    },
]

ENERGY_PATTERNS = [
    {
        "label": "PROP",
        "pattern": [
            {"LEMMA": "energy"},
            {"LOWER": "of"},
            {
                "LEMMA": {
                    "IN": [
                        "combustion",
                        "formation",
                        "explosion",
                        "dissociation",
                        "activation",
                    ]
                }
            },
        ],
        "id": "energy",
    },
    {
        "label": "PROP",
        "pattern": [
            {"LEMMA": "molar", "OP": "?"},
            {"LEMMA": "bond", "OP": "?"},
            {
                "LEMMA": {
                    "IN": [
                        "combustion",
                        "formation",
                        "explosion",
                        "dissociation",
                        "activation",
                    ]
                }
            },
            {"LEMMA": "energy"},
        ],
        "id": "energy",
    },
    {
        "label": "FORMULA",
        "pattern": [
            {"TEXT": "Δ"},
            {"TEXT": "G"},
        ],
        "id": "energy",
    },
    {
        "label": "FORMULA",
        "pattern": [
            {"TEXT": "ΔG"},
        ],
        "id": "energy",
    },
    {
        "label": "FORMULA",
        "pattern": [
            {"LOWER": "bde"},
        ],
        "id": "energy",
    },
]

POINT_PATTERNS = [
    {
        "label": "PROP",
        "pattern": [
            {
                "LEMMA": {
                    "IN": [
                        "flash",
                        "boil",
                        "melt",
                        "heat",
                        "freeze",
                        "decomposition",
                        "sublimation",
                        "dec.",
                    ]
                }
            },
            {"LEMMA": "point"},
        ],
        "id": "temperature",
    },
    {
        "label": "PROP",
        "pattern": [
            {"LEMMA": "decompose"},
            {"LEMMA": "at"},
        ],
        "id": "temperature",
    },
    {
        "label": "PROP",
        "pattern": [
            {"LEMMA": "be"},
            {"LEMMA": "stable"},
            {"LEMMA": "at"},
        ],
        "id": "temperature",
    },
    {
        "label": "PROP",
        "pattern": [
            {"LEMMA": "explode"},
            {"LEMMA": "at"},
        ],
        "id": "temperature",
    },
    {
        "label": "PROP",
        "pattern": [
            {"LEMMA": "be"},
            {"LEMMA": "stable"},
            {"LEMMA": "up"},
            {"LEMMA": "to"},
        ],
        "id": "temperature",
    },
    {
        "label": "PROP",
        "pattern": [
            {
                "LEMMA": {
                    "IN": [
                        "heat",
                        "boil",
                        "melt",
                        "heat",
                        "freeze",
                        "calorific",
                        "sublimation",
                        "decomposition",
                    ]
                }
            },
            {"LEMMA": "value"},
        ],
        "id": "temperature",
    },
]

PRESSURE_PATTERNS = [
    {
        "label": "PROP",
        "pattern": [
            {
                "LEMMA": {
                    "IN": [
                        "critical",
                        "vapor",
                        "vapour",
                        "heat",
                        "freeze",
                        "calorific",
                        "detonation",
                    ]
                }
            },
            {"LEMMA": "pressure"},
        ],
        "id": "pressure",
    },
]

TEMPERATURE_PATTERNS = [
    {
        "label": "PROP",
        "pattern": [
            {"LEMMA": {"IN": ["critical", "ignition", "decomposition", "detonation"]}},
            {"LEMMA": "temperature"},
        ],
        "id": "temperature",
    },
    {
        "label": "FORMULA",
        "pattern": [{"TEXT": "T"}, {"TEXT": "c"}, {"TEXT": "="}],
        "id": "temperature",
    },
    {
        "label": "FORMULA",
        "pattern": [{"TEXT": "Tc"}, {"TEXT": "="}],
        "id": "temperature",
    },
    {
        "label": "FORMULA",
        "pattern": [{"TEXT": "T"}, {"TEXT": "c="}],
        "id": "temperature",
    },
    {
        "label": "FORMULA",
        "pattern": [{"TEXT": "Tc="}],
        "id": "temperature",
    },
    {
        "label": "FORMULA",
        "pattern": [{"TEXT": "T"}, {"TEXT": "dec"}, {"TEXT": "="}],
        "id": "temperature",
    },
    {
        "label": "FORMULA",
        "pattern": [{"TEXT": "Tdec"}, {"TEXT": "="}],
        "id": "temperature",
    },
    {
        "label": "FORMULA",
        "pattern": [{"TEXT": "T"}, {"TEXT": "dec="}],
        "id": "temperature",
    },
    {
        "label": "FORMULA",
        "pattern": [{"TEXT": "Tdec="}],
        "id": "temperature",
    },
]

DENSITY_PATTERNS = [
    {
        "label": "PROP",
        "pattern": [
            {"LEMMA": {"IN": ["density", "solubility"]}},
        ],
        "id": "density",
    },
    {
        "label": "PROP",
        "pattern": [
            {"LOWER": {"IN": ["density", "solubility"]}},
        ],
        "id": "density",
    },
    {
        "label": "FORMULA",
        "pattern": [
            {"TEXT": "ρ"},
        ],
        "id": "density",
    },
]

OTHER_PATTERNS = [
    {
        "label": "PROP",
        "pattern": [{"LEMMA": "heat"}, {"LEMMA": "capacity"}],
        "id": "heat capacity",
    },
    {
        "label": "PROP",
        "pattern": [
            {"LEMMA": "toxicity"},
        ],
        "id": "toxicity",
    },
    {
        "label": "PROP",
        "pattern": [
            {"LEMMA": "viscosity"},
        ],
        "id": "viscosity",
    },
    {
        "label": "FORMULA",
        "pattern": [
            {"TEXT": "η"},
            {"TEXT": "="},
        ],
        "id": "viscosity",
    },
    {
        "label": "FORMULA",
        "pattern": [
            {"TEXT": "η="},
        ],
        "id": "viscosity",
    },
    {
        "label": "PROP",
        "pattern": [
            {"LEMMA": "thermal"},
            {"LEMMA": {"IN": ["stability", "conductivity", "diffusivity"]}},
        ],
        "id": "thermal",
    },
    {
        "label": "FORMULA",
        "pattern": [
            {"LOWER": "t1/2"},
            {"TEXT": "=", "OP": "?"},
        ],
        "id": "thermal",
    },
    {
        "label": "PROP",
        "pattern": [
            {"LEMMA": "detonation"},
            {"LEMMA": "velocity"},
        ],
        "id": "velocity",
    },
    {
        "label": "PROP",
        "pattern": [
            {"LEMMA": "formula"},
            {"LEMMA": "weight"},
        ],
        "id": "formula weight",
    },
    {
        "label": "PROP",
        "pattern": [
            {"LEMMA": {"IN": ["impact", "friction", "ESD", "electrostatic"]}},
            {"LEMMA": {"IN": ["sensibility", "sensitivity"]}},
        ],
        "id": "sensibility",
    },
    {
        "label": "PROP",
        "pattern": [
            {"LEMMA": "electrostatic"},
            {"LEMMA": "discharge"},
            {"LEMMA": {"IN": ["sensibility", "sensitivity"]}},
        ],
        "id": "sensibility",
    },
    {
        "label": "PROP",
        "pattern": [
            {"LEMMA": "sensitive"},
            {"LEMMA": "to"},
            {"LEMMA": {"IN": ["impact", "friction", "ESD", "electrostatic"]}},
        ],
        "id": "sensibility",
    },
]

PROPERTY_PATTERNS = (
    ABSORPTIVITY_PATTERNS
    + VACUUM_PATTERNS
    + ENTHALPY_PATTERNS
    + ENERGY_PATTERNS
    + POINT_PATTERNS
    + PRESSURE_PATTERNS
    + TEMPERATURE_PATTERNS
    + DENSITY_PATTERNS
    + OTHER_PATTERNS
)
