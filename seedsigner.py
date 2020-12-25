# -*- coding:utf-8 -*-
import ST7789
import spidev as SPI
import RPi.GPIO as GPIO

import time
import subprocess

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

from embit.bip39 import mnemonic_to_bytes
from embit.bip39 import mnemonic_from_bytes

from subprocess import call

# alphabet reference
alphabet = [
    "a",
    "b",
    "c",
    "d",
    "e",
    "f",
    "g",
    "h",
    "i",
    "j",
    "k",
    "l",
    "m",
    "n",
    "o",
    "p",
    "q",
    "r",
    "s",
    "t",
    "u",
    "v",
    "w",
    "x",
    "y",
    "z"]

# seed reference
seedwords = [
    "abandon",
    "ability",
    "able",
    "about",
    "above",
    "absent",
    "absorb",
    "abstract",
    "absurd",
    "abuse",
    "access",
    "accident",
    "account",
    "accuse",
    "achieve",
    "acid",
    "acoustic",
    "acquire",
    "across",
    "act",
    "action",
    "actor",
    "actress",
    "actual",
    "adapt",
    "add",
    "addict",
    "address",
    "adjust",
    "admit",
    "adult",
    "advance",
    "advice",
    "aerobic",
    "affair",
    "afford",
    "afraid",
    "again",
    "age",
    "agent",
    "agree",
    "ahead",
    "aim",
    "air",
    "airport",
    "aisle",
    "alarm",
    "album",
    "alcohol",
    "alert",
    "alien",
    "all",
    "alley",
    "allow",
    "almost",
    "alone",
    "alpha",
    "already",
    "also",
    "alter",
    "always",
    "amateur",
    "amazing",
    "among",
    "amount",
    "amused",
    "analyst",
    "anchor",
    "ancient",
    "anger",
    "angle",
    "angry",
    "animal",
    "ankle",
    "announce",
    "annual",
    "another",
    "answer",
    "antenna",
    "antique",
    "anxiety",
    "any",
    "apart",
    "apology",
    "appear",
    "apple",
    "approve",
    "april",
    "arch",
    "arctic",
    "area",
    "arena",
    "argue",
    "arm",
    "armed",
    "armor",
    "army",
    "around",
    "arrange",
    "arrest",
    "arrive",
    "arrow",
    "art",
    "artefact",
    "artist",
    "artwork",
    "ask",
    "aspect",
    "assault",
    "asset",
    "assist",
    "assume",
    "asthma",
    "athlete",
    "atom",
    "attack",
    "attend",
    "attitude",
    "attract",
    "auction",
    "audit",
    "august",
    "aunt",
    "author",
    "auto",
    "autumn",
    "average",
    "avocado",
    "avoid",
    "awake",
    "aware",
    "away",
    "awesome",
    "awful",
    "awkward",
    "axis",
    "baby",
    "bachelor",
    "bacon",
    "badge",
    "bag",
    "balance",
    "balcony",
    "ball",
    "bamboo",
    "banana",
    "banner",
    "bar",
    "barely",
    "bargain",
    "barrel",
    "base",
    "basic",
    "basket",
    "battle",
    "beach",
    "bean",
    "beauty",
    "because",
    "become",
    "beef",
    "before",
    "begin",
    "behave",
    "behind",
    "believe",
    "below",
    "belt",
    "bench",
    "benefit",
    "best",
    "betray",
    "better",
    "between",
    "beyond",
    "bicycle",
    "bid",
    "bike",
    "bind",
    "biology",
    "bird",
    "birth",
    "bitter",
    "black",
    "blade",
    "blame",
    "blanket",
    "blast",
    "bleak",
    "bless",
    "blind",
    "blood",
    "blossom",
    "blouse",
    "blue",
    "blur",
    "blush",
    "board",
    "boat",
    "body",
    "boil",
    "bomb",
    "bone",
    "bonus",
    "book",
    "boost",
    "border",
    "boring",
    "borrow",
    "boss",
    "bottom",
    "bounce",
    "box",
    "boy",
    "bracket",
    "brain",
    "brand",
    "brass",
    "brave",
    "bread",
    "breeze",
    "brick",
    "bridge",
    "brief",
    "bright",
    "bring",
    "brisk",
    "broccoli",
    "broken",
    "bronze",
    "broom",
    "brother",
    "brown",
    "brush",
    "bubble",
    "buddy",
    "budget",
    "buffalo",
    "build",
    "bulb",
    "bulk",
    "bullet",
    "bundle",
    "bunker",
    "burden",
    "burger",
    "burst",
    "bus",
    "business",
    "busy",
    "butter",
    "buyer",
    "buzz",
    "cabbage",
    "cabin",
    "cable",
    "cactus",
    "cage",
    "cake",
    "call",
    "calm",
    "camera",
    "camp",
    "can",
    "canal",
    "cancel",
    "candy",
    "cannon",
    "canoe",
    "canvas",
    "canyon",
    "capable",
    "capital",
    "captain",
    "car",
    "carbon",
    "card",
    "cargo",
    "carpet",
    "carry",
    "cart",
    "case",
    "cash",
    "casino",
    "castle",
    "casual",
    "cat",
    "catalog",
    "catch",
    "category",
    "cattle",
    "caught",
    "cause",
    "caution",
    "cave",
    "ceiling",
    "celery",
    "cement",
    "census",
    "century",
    "cereal",
    "certain",
    "chair",
    "chalk",
    "champion",
    "change",
    "chaos",
    "chapter",
    "charge",
    "chase",
    "chat",
    "cheap",
    "check",
    "cheese",
    "chef",
    "cherry",
    "chest",
    "chicken",
    "chief",
    "child",
    "chimney",
    "choice",
    "choose",
    "chronic",
    "chuckle",
    "chunk",
    "churn",
    "cigar",
    "cinnamon",
    "circle",
    "citizen",
    "city",
    "civil",
    "claim",
    "clap",
    "clarify",
    "claw",
    "clay",
    "clean",
    "clerk",
    "clever",
    "click",
    "client",
    "cliff",
    "climb",
    "clinic",
    "clip",
    "clock",
    "clog",
    "close",
    "cloth",
    "cloud",
    "clown",
    "club",
    "clump",
    "cluster",
    "clutch",
    "coach",
    "coast",
    "coconut",
    "code",
    "coffee",
    "coil",
    "coin",
    "collect",
    "color",
    "column",
    "combine",
    "come",
    "comfort",
    "comic",
    "common",
    "company",
    "concert",
    "conduct",
    "confirm",
    "congress",
    "connect",
    "consider",
    "control",
    "convince",
    "cook",
    "cool",
    "copper",
    "copy",
    "coral",
    "core",
    "corn",
    "correct",
    "cost",
    "cotton",
    "couch",
    "country",
    "couple",
    "course",
    "cousin",
    "cover",
    "coyote",
    "crack",
    "cradle",
    "craft",
    "cram",
    "crane",
    "crash",
    "crater",
    "crawl",
    "crazy",
    "cream",
    "credit",
    "creek",
    "crew",
    "cricket",
    "crime",
    "crisp",
    "critic",
    "crop",
    "cross",
    "crouch",
    "crowd",
    "crucial",
    "cruel",
    "cruise",
    "crumble",
    "crunch",
    "crush",
    "cry",
    "crystal",
    "cube",
    "culture",
    "cup",
    "cupboard",
    "curious",
    "current",
    "curtain",
    "curve",
    "cushion",
    "custom",
    "cute",
    "cycle",
    "dad",
    "damage",
    "damp",
    "dance",
    "danger",
    "daring",
    "dash",
    "daughter",
    "dawn",
    "day",
    "deal",
    "debate",
    "debris",
    "decade",
    "december",
    "decide",
    "decline",
    "decorate",
    "decrease",
    "deer",
    "defense",
    "define",
    "defy",
    "degree",
    "delay",
    "deliver",
    "demand",
    "demise",
    "denial",
    "dentist",
    "deny",
    "depart",
    "depend",
    "deposit",
    "depth",
    "deputy",
    "derive",
    "describe",
    "desert",
    "design",
    "desk",
    "despair",
    "destroy",
    "detail",
    "detect",
    "develop",
    "device",
    "devote",
    "diagram",
    "dial",
    "diamond",
    "diary",
    "dice",
    "diesel",
    "diet",
    "differ",
    "digital",
    "dignity",
    "dilemma",
    "dinner",
    "dinosaur",
    "direct",
    "dirt",
    "disagree",
    "discover",
    "disease",
    "dish",
    "dismiss",
    "disorder",
    "display",
    "distance",
    "divert",
    "divide",
    "divorce",
    "dizzy",
    "doctor",
    "document",
    "dog",
    "doll",
    "dolphin",
    "domain",
    "donate",
    "donkey",
    "donor",
    "door",
    "dose",
    "double",
    "dove",
    "draft",
    "dragon",
    "drama",
    "drastic",
    "draw",
    "dream",
    "dress",
    "drift",
    "drill",
    "drink",
    "drip",
    "drive",
    "drop",
    "drum",
    "dry",
    "duck",
    "dumb",
    "dune",
    "during",
    "dust",
    "dutch",
    "duty",
    "dwarf",
    "dynamic",
    "eager",
    "eagle",
    "early",
    "earn",
    "earth",
    "easily",
    "east",
    "easy",
    "echo",
    "ecology",
    "economy",
    "edge",
    "edit",
    "educate",
    "effort",
    "egg",
    "eight",
    "either",
    "elbow",
    "elder",
    "electric",
    "elegant",
    "element",
    "elephant",
    "elevator",
    "elite",
    "else",
    "embark",
    "embody",
    "embrace",
    "emerge",
    "emotion",
    "employ",
    "empower",
    "empty",
    "enable",
    "enact",
    "end",
    "endless",
    "endorse",
    "enemy",
    "energy",
    "enforce",
    "engage",
    "engine",
    "enhance",
    "enjoy",
    "enlist",
    "enough",
    "enrich",
    "enroll",
    "ensure",
    "enter",
    "entire",
    "entry",
    "envelope",
    "episode",
    "equal",
    "equip",
    "era",
    "erase",
    "erode",
    "erosion",
    "error",
    "erupt",
    "escape",
    "essay",
    "essence",
    "estate",
    "eternal",
    "ethics",
    "evidence",
    "evil",
    "evoke",
    "evolve",
    "exact",
    "example",
    "excess",
    "exchange",
    "excite",
    "exclude",
    "excuse",
    "execute",
    "exercise",
    "exhaust",
    "exhibit",
    "exile",
    "exist",
    "exit",
    "exotic",
    "expand",
    "expect",
    "expire",
    "explain",
    "expose",
    "express",
    "extend",
    "extra",
    "eye",
    "eyebrow",
    "fabric",
    "face",
    "faculty",
    "fade",
    "faint",
    "faith",
    "fall",
    "false",
    "fame",
    "family",
    "famous",
    "fan",
    "fancy",
    "fantasy",
    "farm",
    "fashion",
    "fat",
    "fatal",
    "father",
    "fatigue",
    "fault",
    "favorite",
    "feature",
    "february",
    "federal",
    "fee",
    "feed",
    "feel",
    "female",
    "fence",
    "festival",
    "fetch",
    "fever",
    "few",
    "fiber",
    "fiction",
    "field",
    "figure",
    "file",
    "film",
    "filter",
    "final",
    "find",
    "fine",
    "finger",
    "finish",
    "fire",
    "firm",
    "first",
    "fiscal",
    "fish",
    "fit",
    "fitness",
    "fix",
    "flag",
    "flame",
    "flash",
    "flat",
    "flavor",
    "flee",
    "flight",
    "flip",
    "float",
    "flock",
    "floor",
    "flower",
    "fluid",
    "flush",
    "fly",
    "foam",
    "focus",
    "fog",
    "foil",
    "fold",
    "follow",
    "food",
    "foot",
    "force",
    "forest",
    "forget",
    "fork",
    "fortune",
    "forum",
    "forward",
    "fossil",
    "foster",
    "found",
    "fox",
    "fragile",
    "frame",
    "frequent",
    "fresh",
    "friend",
    "fringe",
    "frog",
    "front",
    "frost",
    "frown",
    "frozen",
    "fruit",
    "fuel",
    "fun",
    "funny",
    "furnace",
    "fury",
    "future",
    "gadget",
    "gain",
    "galaxy",
    "gallery",
    "game",
    "gap",
    "garage",
    "garbage",
    "garden",
    "garlic",
    "garment",
    "gas",
    "gasp",
    "gate",
    "gather",
    "gauge",
    "gaze",
    "general",
    "genius",
    "genre",
    "gentle",
    "genuine",
    "gesture",
    "ghost",
    "giant",
    "gift",
    "giggle",
    "ginger",
    "giraffe",
    "girl",
    "give",
    "glad",
    "glance",
    "glare",
    "glass",
    "glide",
    "glimpse",
    "globe",
    "gloom",
    "glory",
    "glove",
    "glow",
    "glue",
    "goat",
    "goddess",
    "gold",
    "good",
    "goose",
    "gorilla",
    "gospel",
    "gossip",
    "govern",
    "gown",
    "grab",
    "grace",
    "grain",
    "grant",
    "grape",
    "grass",
    "gravity",
    "great",
    "green",
    "grid",
    "grief",
    "grit",
    "grocery",
    "group",
    "grow",
    "grunt",
    "guard",
    "guess",
    "guide",
    "guilt",
    "guitar",
    "gun",
    "gym",
    "habit",
    "hair",
    "half",
    "hammer",
    "hamster",
    "hand",
    "happy",
    "harbor",
    "hard",
    "harsh",
    "harvest",
    "hat",
    "have",
    "hawk",
    "hazard",
    "head",
    "health",
    "heart",
    "heavy",
    "hedgehog",
    "height",
    "hello",
    "helmet",
    "help",
    "hen",
    "hero",
    "hidden",
    "high",
    "hill",
    "hint",
    "hip",
    "hire",
    "history",
    "hobby",
    "hockey",
    "hold",
    "hole",
    "holiday",
    "hollow",
    "home",
    "honey",
    "hood",
    "hope",
    "horn",
    "horror",
    "horse",
    "hospital",
    "host",
    "hotel",
    "hour",
    "hover",
    "hub",
    "huge",
    "human",
    "humble",
    "humor",
    "hundred",
    "hungry",
    "hunt",
    "hurdle",
    "hurry",
    "hurt",
    "husband",
    "hybrid",
    "ice",
    "icon",
    "idea",
    "identify",
    "idle",
    "ignore",
    "ill",
    "illegal",
    "illness",
    "image",
    "imitate",
    "immense",
    "immune",
    "impact",
    "impose",
    "improve",
    "impulse",
    "inch",
    "include",
    "income",
    "increase",
    "index",
    "indicate",
    "indoor",
    "industry",
    "infant",
    "inflict",
    "inform",
    "inhale",
    "inherit",
    "initial",
    "inject",
    "injury",
    "inmate",
    "inner",
    "innocent",
    "input",
    "inquiry",
    "insane",
    "insect",
    "inside",
    "inspire",
    "install",
    "intact",
    "interest",
    "into",
    "invest",
    "invite",
    "involve",
    "iron",
    "island",
    "isolate",
    "issue",
    "item",
    "ivory",
    "jacket",
    "jaguar",
    "jar",
    "jazz",
    "jealous",
    "jeans",
    "jelly",
    "jewel",
    "job",
    "join",
    "joke",
    "journey",
    "joy",
    "judge",
    "juice",
    "jump",
    "jungle",
    "junior",
    "junk",
    "just",
    "kangaroo",
    "keen",
    "keep",
    "ketchup",
    "key",
    "kick",
    "kid",
    "kidney",
    "kind",
    "kingdom",
    "kiss",
    "kit",
    "kitchen",
    "kite",
    "kitten",
    "kiwi",
    "knee",
    "knife",
    "knock",
    "know",
    "lab",
    "label",
    "labor",
    "ladder",
    "lady",
    "lake",
    "lamp",
    "language",
    "laptop",
    "large",
    "later",
    "latin",
    "laugh",
    "laundry",
    "lava",
    "law",
    "lawn",
    "lawsuit",
    "layer",
    "lazy",
    "leader",
    "leaf",
    "learn",
    "leave",
    "lecture",
    "left",
    "leg",
    "legal",
    "legend",
    "leisure",
    "lemon",
    "lend",
    "length",
    "lens",
    "leopard",
    "lesson",
    "letter",
    "level",
    "liar",
    "liberty",
    "library",
    "license",
    "life",
    "lift",
    "light",
    "like",
    "limb",
    "limit",
    "link",
    "lion",
    "liquid",
    "list",
    "little",
    "live",
    "lizard",
    "load",
    "loan",
    "lobster",
    "local",
    "lock",
    "logic",
    "lonely",
    "long",
    "loop",
    "lottery",
    "loud",
    "lounge",
    "love",
    "loyal",
    "lucky",
    "luggage",
    "lumber",
    "lunar",
    "lunch",
    "luxury",
    "lyrics",
    "machine",
    "mad",
    "magic",
    "magnet",
    "maid",
    "mail",
    "main",
    "major",
    "make",
    "mammal",
    "man",
    "manage",
    "mandate",
    "mango",
    "mansion",
    "manual",
    "maple",
    "marble",
    "march",
    "margin",
    "marine",
    "market",
    "marriage",
    "mask",
    "mass",
    "master",
    "match",
    "material",
    "math",
    "matrix",
    "matter",
    "maximum",
    "maze",
    "meadow",
    "mean",
    "measure",
    "meat",
    "mechanic",
    "medal",
    "media",
    "melody",
    "melt",
    "member",
    "memory",
    "mention",
    "menu",
    "mercy",
    "merge",
    "merit",
    "merry",
    "mesh",
    "message",
    "metal",
    "method",
    "middle",
    "midnight",
    "milk",
    "million",
    "mimic",
    "mind",
    "minimum",
    "minor",
    "minute",
    "miracle",
    "mirror",
    "misery",
    "miss",
    "mistake",
    "mix",
    "mixed",
    "mixture",
    "mobile",
    "model",
    "modify",
    "mom",
    "moment",
    "monitor",
    "monkey",
    "monster",
    "month",
    "moon",
    "moral",
    "more",
    "morning",
    "mosquito",
    "mother",
    "motion",
    "motor",
    "mountain",
    "mouse",
    "move",
    "movie",
    "much",
    "muffin",
    "mule",
    "multiply",
    "muscle",
    "museum",
    "mushroom",
    "music",
    "must",
    "mutual",
    "myself",
    "mystery",
    "myth",
    "naive",
    "name",
    "napkin",
    "narrow",
    "nasty",
    "nation",
    "nature",
    "near",
    "neck",
    "need",
    "negative",
    "neglect",
    "neither",
    "nephew",
    "nerve",
    "nest",
    "net",
    "network",
    "neutral",
    "never",
    "news",
    "next",
    "nice",
    "night",
    "noble",
    "noise",
    "nominee",
    "noodle",
    "normal",
    "north",
    "nose",
    "notable",
    "note",
    "nothing",
    "notice",
    "novel",
    "now",
    "nuclear",
    "number",
    "nurse",
    "nut",
    "oak",
    "obey",
    "object",
    "oblige",
    "obscure",
    "observe",
    "obtain",
    "obvious",
    "occur",
    "ocean",
    "october",
    "odor",
    "off",
    "offer",
    "office",
    "often",
    "oil",
    "okay",
    "old",
    "olive",
    "olympic",
    "omit",
    "once",
    "one",
    "onion",
    "online",
    "only",
    "open",
    "opera",
    "opinion",
    "oppose",
    "option",
    "orange",
    "orbit",
    "orchard",
    "order",
    "ordinary",
    "organ",
    "orient",
    "original",
    "orphan",
    "ostrich",
    "other",
    "outdoor",
    "outer",
    "output",
    "outside",
    "oval",
    "oven",
    "over",
    "own",
    "owner",
    "oxygen",
    "oyster",
    "ozone",
    "pact",
    "paddle",
    "page",
    "pair",
    "palace",
    "palm",
    "panda",
    "panel",
    "panic",
    "panther",
    "paper",
    "parade",
    "parent",
    "park",
    "parrot",
    "party",
    "pass",
    "patch",
    "path",
    "patient",
    "patrol",
    "pattern",
    "pause",
    "pave",
    "payment",
    "peace",
    "peanut",
    "pear",
    "peasant",
    "pelican",
    "pen",
    "penalty",
    "pencil",
    "people",
    "pepper",
    "perfect",
    "permit",
    "person",
    "pet",
    "phone",
    "photo",
    "phrase",
    "physical",
    "piano",
    "picnic",
    "picture",
    "piece",
    "pig",
    "pigeon",
    "pill",
    "pilot",
    "pink",
    "pioneer",
    "pipe",
    "pistol",
    "pitch",
    "pizza",
    "place",
    "planet",
    "plastic",
    "plate",
    "play",
    "please",
    "pledge",
    "pluck",
    "plug",
    "plunge",
    "poem",
    "poet",
    "point",
    "polar",
    "pole",
    "police",
    "pond",
    "pony",
    "pool",
    "popular",
    "portion",
    "position",
    "possible",
    "post",
    "potato",
    "pottery",
    "poverty",
    "powder",
    "power",
    "practice",
    "praise",
    "predict",
    "prefer",
    "prepare",
    "present",
    "pretty",
    "prevent",
    "price",
    "pride",
    "primary",
    "print",
    "priority",
    "prison",
    "private",
    "prize",
    "problem",
    "process",
    "produce",
    "profit",
    "program",
    "project",
    "promote",
    "proof",
    "property",
    "prosper",
    "protect",
    "proud",
    "provide",
    "public",
    "pudding",
    "pull",
    "pulp",
    "pulse",
    "pumpkin",
    "punch",
    "pupil",
    "puppy",
    "purchase",
    "purity",
    "purpose",
    "purse",
    "push",
    "put",
    "puzzle",
    "pyramid",
    "quality",
    "quantum",
    "quarter",
    "question",
    "quick",
    "quit",
    "quiz",
    "quote",
    "rabbit",
    "raccoon",
    "race",
    "rack",
    "radar",
    "radio",
    "rail",
    "rain",
    "raise",
    "rally",
    "ramp",
    "ranch",
    "random",
    "range",
    "rapid",
    "rare",
    "rate",
    "rather",
    "raven",
    "raw",
    "razor",
    "ready",
    "real",
    "reason",
    "rebel",
    "rebuild",
    "recall",
    "receive",
    "recipe",
    "record",
    "recycle",
    "reduce",
    "reflect",
    "reform",
    "refuse",
    "region",
    "regret",
    "regular",
    "reject",
    "relax",
    "release",
    "relief",
    "rely",
    "remain",
    "remember",
    "remind",
    "remove",
    "render",
    "renew",
    "rent",
    "reopen",
    "repair",
    "repeat",
    "replace",
    "report",
    "require",
    "rescue",
    "resemble",
    "resist",
    "resource",
    "response",
    "result",
    "retire",
    "retreat",
    "return",
    "reunion",
    "reveal",
    "review",
    "reward",
    "rhythm",
    "rib",
    "ribbon",
    "rice",
    "rich",
    "ride",
    "ridge",
    "rifle",
    "right",
    "rigid",
    "ring",
    "riot",
    "ripple",
    "risk",
    "ritual",
    "rival",
    "river",
    "road",
    "roast",
    "robot",
    "robust",
    "rocket",
    "romance",
    "roof",
    "rookie",
    "room",
    "rose",
    "rotate",
    "rough",
    "round",
    "route",
    "royal",
    "rubber",
    "rude",
    "rug",
    "rule",
    "run",
    "runway",
    "rural",
    "sad",
    "saddle",
    "sadness",
    "safe",
    "sail",
    "salad",
    "salmon",
    "salon",
    "salt",
    "salute",
    "same",
    "sample",
    "sand",
    "satisfy",
    "satoshi",
    "sauce",
    "sausage",
    "save",
    "say",
    "scale",
    "scan",
    "scare",
    "scatter",
    "scene",
    "scheme",
    "school",
    "science",
    "scissors",
    "scorpion",
    "scout",
    "scrap",
    "screen",
    "script",
    "scrub",
    "sea",
    "search",
    "season",
    "seat",
    "second",
    "secret",
    "section",
    "security",
    "seed",
    "seek",
    "segment",
    "select",
    "sell",
    "seminar",
    "senior",
    "sense",
    "sentence",
    "series",
    "service",
    "session",
    "settle",
    "setup",
    "seven",
    "shadow",
    "shaft",
    "shallow",
    "share",
    "shed",
    "shell",
    "sheriff",
    "shield",
    "shift",
    "shine",
    "ship",
    "shiver",
    "shock",
    "shoe",
    "shoot",
    "shop",
    "short",
    "shoulder",
    "shove",
    "shrimp",
    "shrug",
    "shuffle",
    "shy",
    "sibling",
    "sick",
    "side",
    "siege",
    "sight",
    "sign",
    "silent",
    "silk",
    "silly",
    "silver",
    "similar",
    "simple",
    "since",
    "sing",
    "siren",
    "sister",
    "situate",
    "six",
    "size",
    "skate",
    "sketch",
    "ski",
    "skill",
    "skin",
    "skirt",
    "skull",
    "slab",
    "slam",
    "sleep",
    "slender",
    "slice",
    "slide",
    "slight",
    "slim",
    "slogan",
    "slot",
    "slow",
    "slush",
    "small",
    "smart",
    "smile",
    "smoke",
    "smooth",
    "snack",
    "snake",
    "snap",
    "sniff",
    "snow",
    "soap",
    "soccer",
    "social",
    "sock",
    "soda",
    "soft",
    "solar",
    "soldier",
    "solid",
    "solution",
    "solve",
    "someone",
    "song",
    "soon",
    "sorry",
    "sort",
    "soul",
    "sound",
    "soup",
    "source",
    "south",
    "space",
    "spare",
    "spatial",
    "spawn",
    "speak",
    "special",
    "speed",
    "spell",
    "spend",
    "sphere",
    "spice",
    "spider",
    "spike",
    "spin",
    "spirit",
    "split",
    "spoil",
    "sponsor",
    "spoon",
    "sport",
    "spot",
    "spray",
    "spread",
    "spring",
    "spy",
    "square",
    "squeeze",
    "squirrel",
    "stable",
    "stadium",
    "staff",
    "stage",
    "stairs",
    "stamp",
    "stand",
    "start",
    "state",
    "stay",
    "steak",
    "steel",
    "stem",
    "step",
    "stereo",
    "stick",
    "still",
    "sting",
    "stock",
    "stomach",
    "stone",
    "stool",
    "story",
    "stove",
    "strategy",
    "street",
    "strike",
    "strong",
    "struggle",
    "student",
    "stuff",
    "stumble",
    "style",
    "subject",
    "submit",
    "subway",
    "success",
    "such",
    "sudden",
    "suffer",
    "sugar",
    "suggest",
    "suit",
    "summer",
    "sun",
    "sunny",
    "sunset",
    "super",
    "supply",
    "supreme",
    "sure",
    "surface",
    "surge",
    "surprise",
    "surround",
    "survey",
    "suspect",
    "sustain",
    "swallow",
    "swamp",
    "swap",
    "swarm",
    "swear",
    "sweet",
    "swift",
    "swim",
    "swing",
    "switch",
    "sword",
    "symbol",
    "symptom",
    "syrup",
    "system",
    "table",
    "tackle",
    "tag",
    "tail",
    "talent",
    "talk",
    "tank",
    "tape",
    "target",
    "task",
    "taste",
    "tattoo",
    "taxi",
    "teach",
    "team",
    "tell",
    "ten",
    "tenant",
    "tennis",
    "tent",
    "term",
    "test",
    "text",
    "thank",
    "that",
    "theme",
    "then",
    "theory",
    "there",
    "they",
    "thing",
    "this",
    "thought",
    "three",
    "thrive",
    "throw",
    "thumb",
    "thunder",
    "ticket",
    "tide",
    "tiger",
    "tilt",
    "timber",
    "time",
    "tiny",
    "tip",
    "tired",
    "tissue",
    "title",
    "toast",
    "tobacco",
    "today",
    "toddler",
    "toe",
    "together",
    "toilet",
    "token",
    "tomato",
    "tomorrow",
    "tone",
    "tongue",
    "tonight",
    "tool",
    "tooth",
    "top",
    "topic",
    "topple",
    "torch",
    "tornado",
    "tortoise",
    "toss",
    "total",
    "tourist",
    "toward",
    "tower",
    "town",
    "toy",
    "track",
    "trade",
    "traffic",
    "tragic",
    "train",
    "transfer",
    "trap",
    "trash",
    "travel",
    "tray",
    "treat",
    "tree",
    "trend",
    "trial",
    "tribe",
    "trick",
    "trigger",
    "trim",
    "trip",
    "trophy",
    "trouble",
    "truck",
    "true",
    "truly",
    "trumpet",
    "trust",
    "truth",
    "try",
    "tube",
    "tuition",
    "tumble",
    "tuna",
    "tunnel",
    "turkey",
    "turn",
    "turtle",
    "twelve",
    "twenty",
    "twice",
    "twin",
    "twist",
    "two",
    "type",
    "typical",
    "ugly",
    "umbrella",
    "unable",
    "unaware",
    "uncle",
    "uncover",
    "under",
    "undo",
    "unfair",
    "unfold",
    "unhappy",
    "uniform",
    "unique",
    "unit",
    "universe",
    "unknown",
    "unlock",
    "until",
    "unusual",
    "unveil",
    "update",
    "upgrade",
    "uphold",
    "upon",
    "upper",
    "upset",
    "urban",
    "urge",
    "usage",
    "use",
    "used",
    "useful",
    "useless",
    "usual",
    "utility",
    "vacant",
    "vacuum",
    "vague",
    "valid",
    "valley",
    "valve",
    "van",
    "vanish",
    "vapor",
    "various",
    "vast",
    "vault",
    "vehicle",
    "velvet",
    "vendor",
    "venture",
    "venue",
    "verb",
    "verify",
    "version",
    "very",
    "vessel",
    "veteran",
    "viable",
    "vibrant",
    "vicious",
    "victory",
    "video",
    "view",
    "village",
    "vintage",
    "violin",
    "virtual",
    "virus",
    "visa",
    "visit",
    "visual",
    "vital",
    "vivid",
    "vocal",
    "voice",
    "void",
    "volcano",
    "volume",
    "vote",
    "voyage",
    "wage",
    "wagon",
    "wait",
    "walk",
    "wall",
    "walnut",
    "want",
    "warfare",
    "warm",
    "warrior",
    "wash",
    "wasp",
    "waste",
    "water",
    "wave",
    "way",
    "wealth",
    "weapon",
    "wear",
    "weasel",
    "weather",
    "web",
    "wedding",
    "weekend",
    "weird",
    "welcome",
    "west",
    "wet",
    "whale",
    "what",
    "wheat",
    "wheel",
    "when",
    "where",
    "whip",
    "whisper",
    "wide",
    "width",
    "wife",
    "wild",
    "will",
    "win",
    "window",
    "wine",
    "wing",
    "wink",
    "winner",
    "winter",
    "wire",
    "wisdom",
    "wise",
    "wish",
    "witness",
    "wolf",
    "woman",
    "wonder",
    "wood",
    "wool",
    "word",
    "work",
    "world",
    "worry",
    "worth",
    "wrap",
    "wreck",
    "wrestle",
    "wrist",
    "write",
    "wrong",
    "yard",
    "year",
    "yellow",
    "you",
    "young",
    "youth",
    "zebra",
    "zero",
    "zone",
    "zoo"]

# GPIO define
RST_PIN = 25
CS_PIN = 8
DC_PIN = 24

KEY_UP_PIN = 6
KEY_DOWN_PIN = 19
KEY_LEFT_PIN = 5
KEY_RIGHT_PIN = 26
KEY_PRESS_PIN = 13

KEY1_PIN = 21
KEY2_PIN = 20
KEY3_PIN = 16

RST = 27
DC = 25
BL = 24
bus = 0
device = 0

# init GPIO
GPIO.setmode(GPIO.BCM)
# Input with pull-up
GPIO.setup(KEY_UP_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(
    KEY_DOWN_PIN,
    GPIO.IN,
    pull_up_down=GPIO.PUD_UP)  # Input with pull-up
GPIO.setup(
    KEY_LEFT_PIN,
    GPIO.IN,
    pull_up_down=GPIO.PUD_UP)  # Input with pull-up
GPIO.setup(
    KEY_RIGHT_PIN,
    GPIO.IN,
    pull_up_down=GPIO.PUD_UP)  # Input with pull-up
GPIO.setup(
    KEY_PRESS_PIN,
    GPIO.IN,
    pull_up_down=GPIO.PUD_UP)  # Input with pull-up
# Input with pull-up
GPIO.setup(KEY1_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
# Input with pull-up
GPIO.setup(KEY2_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
# Input with pull-up
GPIO.setup(KEY3_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# MODULE TO GENERATE WORD 24

# seedphrase variables
seedphrase = [
    "word0",
    "word1",
    "word2",
    "word3",
    "word4",
    "word5",
    "word6",
    "word7",
    "word8",
    "word9",
    "word10",
    "word11",
    "word12",
    "word13",
    "word14",
    "word15",
    "word16",
    "word17",
    "word18",
    "word19",
    "word20",
    "word21",
    "word22",
    "word23"]
wordcounter = 1

# function to get previous letter


def getPrevLetter(letter):
    number = alphabet.index(letter)
    number = number - 1
    if number == -1:
        number = 25
        return alphabet[number]
    else:
        return alphabet[number]

# function to get next letter


def getNextLetter(letter):
    number = alphabet.index(letter)
    number = number + 1
    if number == 26:
        number = 0
        return alphabet[number]
    else:
        return alphabet[number]


# 240x240 display with hardware SPI:
disp = ST7789.ST7789(SPI.SpiDev(bus, device), RST, DC, BL)
disp.Init()

# Create blank image for drawing.
# Make sure to create image with mode '1' for 1-bit color.
width = 240
height = 240
image = Image.new('RGB', (width, height))

# initialize fonts
myfont = ImageFont.truetype(
    '/usr/share/fonts/truetype/msttcorefonts/Impact.ttf', 25)
titlefont = ImageFont.truetype(
    '/usr/share/fonts/truetype/msttcorefonts/Impact.ttf', 18)
singleletterfont = ImageFont.truetype(
    '/usr/share/fonts/truetype/msttcorefonts/Impact.ttf', 35)
displayphrasefont = ImageFont.truetype(
    '/usr/share/fonts/truetype/msttcorefonts/Impact.ttf', 23)
finalwordfont = ImageFont.truetype(
    '/usr/share/fonts/truetype/msttcorefonts/Impact.ttf', 50)

# Get drawing object to draw on image.
draw = ImageDraw.Draw(image)

# Draw a black filled box to clear the image.
draw.rectangle((0, 0, width, height), outline=0, fill=0)
disp.ShowImage(image, 0, 0)

# initialize letters
letterslot1 = "a"
letterslot2 = "a"
letterslot3 = "a"
letterslot4 = "a"

# accept the list output from each of the getletter functions
function1return = []
function2return = []
function3return = []
function4return = []
function5return = []

# function to get FIRST letter


def getletter1(inputletter):
    runstate = 1
    localletter = inputletter
    global wordcounter
    while runstate == 1:
        draw.rectangle((0, 0, width, height), outline=0, fill=0)
        draw.text((75, 2), "Seed Word: " +
                  str(wordcounter), fill="YELLOW", font=titlefont)
        draw.text((15, 210), "(choose from words on right)",
                  fill="YELLOW", font=titlefont)
        draw.text((5, 90), localletter, fill="YELLOW", font=singleletterfont)
        time.sleep(0.1)

        if GPIO.input(KEY_UP_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.1)
            draw.polygon([(8, 85), (14, 69), (20, 85)],
                         outline="YELLOW", fill="YELLOW")
            localletter = getPrevLetter(localletter)
        else:  # button is pressed:
            draw.polygon([(8, 85), (14, 69), (20, 85)],
                         outline="YELLOW", fill=0)

        if GPIO.input(KEY_DOWN_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.1)
            draw.polygon([(8, 148), (14, 164), (20, 148)],
                         outline="YELLOW", fill="YELLOW")
            localletter = getNextLetter(localletter)
        else:  # button is pressed:
            draw.polygon([(8, 148), (14, 164), (20, 148)],
                         outline="YELLOW", fill=0)

        if GPIO.input(KEY_RIGHT_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.1)
            nextslot = 2
            runstate = 0
            return [localletter, nextslot]

        if GPIO.input(KEY_LEFT_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.1)
            nextslot = 0
            runstate = 0
            return [localletter, nextslot]

        possibles = [i for i in seedwords if i.startswith(localletter)]
        if len(possibles) == 1:
            word1width = myfont.getsize(possibles[0])
            offset1 = 223 - word1width[0]
            draw.text(
                (offset1,
                 39),
                possibles[0] +
                " -",
                fill="YELLOW",
                font=myfont)
        elif len(possibles) == 2:
            word1width = myfont.getsize(possibles[0])
            offset1 = 223 - word1width[0]
            draw.text(
                (offset1,
                 39),
                possibles[0] +
                " -",
                fill="YELLOW",
                font=myfont)
            word2width = myfont.getsize(possibles[1])
            offset2 = 223 - word2width[0]
            draw.text(
                (offset2,
                 97),
                possibles[1] +
                " -",
                fill="YELLOW",
                font=myfont)
        elif len(possibles) >= 3:
            word1width = myfont.getsize(possibles[0])
            offset1 = 223 - word1width[0]
            draw.text(
                (offset1,
                 39),
                possibles[0] +
                " -",
                fill="YELLOW",
                font=myfont)
            word2width = myfont.getsize(possibles[1])
            offset2 = 223 - word2width[0]
            draw.text(
                (offset2,
                 97),
                possibles[1] +
                " -",
                fill="YELLOW",
                font=myfont)
            word3width = myfont.getsize(possibles[2])
            offset3 = 223 - word3width[0]
            draw.text(
                (offset3,
                 157),
                possibles[2] + " -",
                fill="YELLOW",
                font=myfont)

        if GPIO.input(KEY1_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.1)
            nextslot = 0
            selectedword = possibles[0]
            seedphrase[wordcounter] = selectedword
            wordcounter = wordcounter + 1
            runstate = 0
            return [localletter, nextslot]

        if GPIO.input(KEY2_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.1)
            nextslot = 0
            selectedword = possibles[1]
            seedphrase[wordcounter] = selectedword
            wordcounter = wordcounter + 1
            runstate = 0
            return [localletter, nextslot]

        if GPIO.input(KEY3_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.1)
            nextslot = 0
            selectedword = possibles[2]
            seedphrase[wordcounter] = selectedword
            wordcounter = wordcounter + 1
            runstate = 0
            return [localletter, nextslot]

        disp.ShowImage(image, 0, 0)

# function to get SECOND letter


def getletter2(inputletter):
    runstate = 1  # just defines whether the current function is still running
    localletter = inputletter  # gathers the letter from the function input
    global wordcounter
    while runstate == 1:
        draw.rectangle((0, 0, width, height), outline=0, fill=0)
        draw.text((75, 2), "Seed Word: " +
                  str(wordcounter), fill="YELLOW", font=titlefont)
        draw.text((18, 210), "(choose from words on right)",
                  fill="YELLOW", font=titlefont)
        draw.text((5, 90), letterslot1, fill="YELLOW", font=singleletterfont)
        draw.text((35, 90), localletter, fill="YELLOW", font=singleletterfont)
        time.sleep(0.1)

        if GPIO.input(KEY_UP_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.1)
            draw.polygon([(38, 85), (44, 69), (50, 85)],
                         outline="YELLOW", fill="YELLOW")
            localletter = getPrevLetter(localletter)
        else:  # button is pressed:
            draw.polygon([(38, 85), (44, 69), (50, 85)],
                         outline="YELLOW", fill=0)

        if GPIO.input(KEY_DOWN_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.1)
            draw.polygon([(38, 148), (44, 164), (50, 148)],
                         outline="YELLOW", fill="YELLOW")
            localletter = getNextLetter(localletter)
        else:  # button is pressed:
            draw.polygon([(38, 148), (44, 164), (50, 148)],
                         outline="YELLOW", fill=0)

        if GPIO.input(KEY_LEFT_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.1)
            nextslot = 1
            runstate = 0
            return [localletter, nextslot]

        if GPIO.input(KEY_RIGHT_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.1)
            nextslot = 3
            runstate = 0
            return [localletter, nextslot]

        possibles = [
            i for i in seedwords if i.startswith(
                letterslot1 + localletter)]
        if len(possibles) == 1:
            word1width = myfont.getsize(possibles[0])
            offset1 = 223 - word1width[0]
            draw.text(
                (offset1,
                 39),
                possibles[0] +
                " -",
                fill="YELLOW",
                font=myfont)
        elif len(possibles) == 2:
            word1width = myfont.getsize(possibles[0])
            offset1 = 223 - word1width[0]
            draw.text(
                (offset1,
                 39),
                possibles[0] +
                " -",
                fill="YELLOW",
                font=myfont)
            word2width = myfont.getsize(possibles[1])
            offset2 = 223 - word2width[0]
            draw.text(
                (offset2,
                 97),
                possibles[1] +
                " -",
                fill="YELLOW",
                font=myfont)
        elif len(possibles) >= 3:
            word1width = myfont.getsize(possibles[0])
            offset1 = 223 - word1width[0]
            draw.text(
                (offset1,
                 39),
                possibles[0] +
                " -",
                fill="YELLOW",
                font=myfont)
            word2width = myfont.getsize(possibles[1])
            offset2 = 223 - word2width[0]
            draw.text(
                (offset2,
                 97),
                possibles[1] +
                " -",
                fill="YELLOW",
                font=myfont)
            word3width = myfont.getsize(possibles[2])
            offset3 = 223 - word3width[0]
            draw.text(
                (offset3,
                 157),
                possibles[2] + " -",
                fill="YELLOW",
                font=myfont)

        if GPIO.input(KEY1_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.1)
            nextslot = 0
            selectedword = possibles[0]
            seedphrase[wordcounter] = selectedword
            wordcounter = wordcounter + 1
            runstate = 0
            return [localletter, nextslot]

        if GPIO.input(KEY2_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.1)
            nextslot = 0
            selectedword = possibles[1]
            seedphrase[wordcounter] = selectedword
            wordcounter = wordcounter + 1
            runstate = 0
            return [localletter, nextslot]

        if GPIO.input(KEY3_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.1)
            nextslot = 0
            selectedword = possibles[2]
            seedphrase[wordcounter] = selectedword
            wordcounter = wordcounter + 1
            runstate = 0
            return [localletter, nextslot]

        disp.ShowImage(image, 0, 0)

# function to get THIRD letter


def getletter3(inputletter):
    runstate = 1
    localletter = inputletter
    global wordcounter
    while runstate == 1:
        draw.rectangle((0, 0, width, height), outline=0, fill=0)
        draw.text((75, 2), "Seed Word: " +
                  str(wordcounter), fill="YELLOW", font=titlefont)
        draw.text((18, 210), "(choose from words on right)",
                  fill="YELLOW", font=titlefont)
        draw.text((5, 90), letterslot1, fill="YELLOW", font=singleletterfont)
        draw.text((35, 90), letterslot2, fill="YELLOW", font=singleletterfont)
        draw.text((65, 90), localletter, fill="YELLOW", font=singleletterfont)
        time.sleep(0.1)

        if GPIO.input(KEY_UP_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.1)
            draw.polygon([(68, 85), (74, 69), (80, 85)],
                         outline="YELLOW", fill="YELLOW")
            localletter = getPrevLetter(localletter)
        else:  # button is pressed:
            draw.polygon([(68, 85), (74, 69), (80, 85)],
                         outline="YELLOW", fill=0)

        if GPIO.input(KEY_DOWN_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.1)
            draw.polygon([(68, 148), (74, 162), (80, 148)],
                         outline="YELLOW", fill="YELLOW")
            localletter = getNextLetter(localletter)
        else:  # button is pressed:
            draw.polygon([(68, 148), (74, 162), (80, 148)],
                         outline="YELLOW", fill=0)

        if GPIO.input(KEY_LEFT_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.1)
            nextslot = 2
            runstate = 0
            return [localletter, nextslot]

        if GPIO.input(KEY_RIGHT_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.1)
            nextslot = 4
            runstate = 0
            return [localletter, nextslot]

        possibles = [
            i for i in seedwords if i.startswith(
                letterslot1 +
                letterslot2 +
                localletter)]
        if len(possibles) == 1:
            word1width = myfont.getsize(possibles[0])
            offset1 = 223 - word1width[0]
            draw.text(
                (offset1,
                 39),
                possibles[0] +
                " -",
                fill="YELLOW",
                font=myfont)
        elif len(possibles) == 2:
            word1width = myfont.getsize(possibles[0])
            offset1 = 223 - word1width[0]
            draw.text(
                (offset1,
                 39),
                possibles[0] +
                " -",
                fill="YELLOW",
                font=myfont)
            word2width = myfont.getsize(possibles[1])
            offset2 = 223 - word2width[0]
            draw.text(
                (offset2,
                 97),
                possibles[1] +
                " -",
                fill="YELLOW",
                font=myfont)
        elif len(possibles) >= 3:
            word1width = myfont.getsize(possibles[0])
            offset1 = 223 - word1width[0]
            draw.text(
                (offset1,
                 39),
                possibles[0] +
                " -",
                fill="YELLOW",
                font=myfont)
            word2width = myfont.getsize(possibles[1])
            offset2 = 223 - word2width[0]
            draw.text(
                (offset2,
                 97),
                possibles[1] +
                " -",
                fill="YELLOW",
                font=myfont)
            word3width = myfont.getsize(possibles[2])
            offset3 = 223 - word3width[0]
            draw.text(
                (offset3,
                 157),
                possibles[2] + " -",
                fill="YELLOW",
                font=myfont)

        if GPIO.input(KEY1_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.1)
            nextslot = 0
            selectedword = possibles[0]
            seedphrase[wordcounter] = selectedword
            wordcounter = wordcounter + 1
            runstate = 0
            return [localletter, nextslot]

        if GPIO.input(KEY2_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.1)
            nextslot = 0
            selectedword = possibles[1]
            seedphrase[wordcounter] = selectedword
            wordcounter = wordcounter + 1
            runstate = 0
            return [localletter, nextslot]

        if GPIO.input(KEY3_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.1)
            nextslot = 0
            selectedword = possibles[2]
            seedphrase[wordcounter] = selectedword
            wordcounter = wordcounter + 1
            runstate = 0
            return [localletter, nextslot]

        disp.ShowImage(image, 0, 0)

# function to get FOURTH letter


def getletter4(inputletter):
    runstate = 1
    localletter = inputletter
    global wordcounter
    while runstate == 1:
        draw.rectangle((0, 0, width, height), outline=0, fill=0)
        draw.text((75, 2), "Seed Word: " +
                  str(wordcounter), fill="YELLOW", font=titlefont)
        draw.text((18, 210), "(choose from words on right)",
                  fill="YELLOW", font=titlefont)
        draw.text((5, 90), letterslot1, fill="YELLOW", font=singleletterfont)
        draw.text((35, 90), letterslot2, fill="YELLOW", font=singleletterfont)
        draw.text((65, 90), letterslot3, fill="YELLOW", font=singleletterfont)
        draw.text((95, 90), localletter, fill="YELLOW", font=singleletterfont)
        time.sleep(0.1)

        if GPIO.input(KEY_UP_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.1)
            draw.polygon([(98, 85), (104, 69), (110, 85)],
                         outline="YELLOW", fill="YELLOW")
            localletter = getPrevLetter(localletter)
        else:  # button is pressed:
            draw.polygon([(98, 85), (104, 69), (110, 85)],
                         outline="YELLOW", fill=0)

        if GPIO.input(KEY_DOWN_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.1)
            draw.polygon([(98, 148), (104, 162), (110, 148)],
                         outline="YELLOW", fill="YELLOW")
            localletter = getNextLetter(localletter)
        else:  # button is pressed:
            draw.polygon([(98, 148), (104, 162), (110, 148)],
                         outline="YELLOW", fill=0)

        if GPIO.input(KEY_LEFT_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.1)
            nextslot = 3
            runstate = 0
            return [localletter, nextslot]

        # nothing shoudl happen if right is pressed on fourth letter
        # if GPIO.input(KEY_RIGHT_PIN) == GPIO.LOW:  # button is released
            # time.sleep(0.1)
            # nextslot = 0
            # runstate = 0
            # return [localletter, nextslot]

        possibles = [
            i for i in seedwords if i.startswith(
                letterslot1 +
                letterslot2 +
                letterslot3 +
                localletter)]
        if len(possibles) == 1:
            word1width = myfont.getsize(possibles[0])
            offset1 = 223 - word1width[0]
            draw.text(
                (offset1,
                 39),
                possibles[0] +
                " -",
                fill="YELLOW",
                font=myfont)
        elif len(possibles) == 2:
            word1width = myfont.getsize(possibles[0])
            offset1 = 223 - word1width[0]
            draw.text(
                (offset1,
                 39),
                possibles[0] +
                " -",
                fill="YELLOW",
                font=myfont)
            word2width = myfont.getsize(possibles[1])
            offset2 = 223 - word2width[0]
            draw.text(
                (offset2,
                 97),
                possibles[1] +
                " -",
                fill="YELLOW",
                font=myfont)
        elif len(possibles) >= 3:
            word1width = myfont.getsize(possibles[0])
            offset1 = 223 - word1width[0]
            draw.text(
                (offset1,
                 39),
                possibles[0] +
                " -",
                fill="YELLOW",
                font=myfont)
            word2width = myfont.getsize(possibles[1])
            offset2 = 223 - word2width[0]
            draw.text(
                (offset2,
                 97),
                possibles[1] +
                " -",
                fill="YELLOW",
                font=myfont)
            word3width = myfont.getsize(possibles[2])
            offset3 = 223 - word3width[0]
            draw.text(
                (offset3,
                 157),
                possibles[2] + " -",
                fill="YELLOW",
                font=myfont)

        if GPIO.input(KEY1_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.1)
            nextslot = 0
            selectedword = possibles[0]
            seedphrase[wordcounter] = selectedword
            wordcounter = wordcounter + 1
            runstate = 0
            return [localletter, nextslot]

        if GPIO.input(KEY2_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.1)
            nextslot = 0
            selectedword = possibles[1]
            seedphrase[wordcounter] = selectedword
            wordcounter = wordcounter + 1
            runstate = 0
            return [localletter, nextslot]

        if GPIO.input(KEY3_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.1)
            nextslot = 0
            selectedword = possibles[2]
            seedphrase[wordcounter] = selectedword
            wordcounter = wordcounter + 1
            runstate = 0
            return [localletter, nextslot]

        disp.ShowImage(image, 0, 0)


def getword():
    global letterslot1
    global letterslot2
    global letterslot3
    global letterslot4

    # defines the which letter is being currently gathered
    letterstate = 1
    allowedletterstates = [1, 2, 3, 4]

    # manages the movement between the letter entry slots
    while letterstate in allowedletterstates:
        if letterstate == 1:
            function1return = getletter1(letterslot1)
            letterslot1 = function1return[0]
            letterstate = function1return[1]
        elif letterstate == 2:
            function2return = getletter2(letterslot2)
            letterslot2 = function2return[0]
            letterstate = function2return[1]
        elif letterstate == 3:
            function3return = getletter3(letterslot3)
            letterslot3 = function3return[0]
            letterstate = function3return[1]
        elif letterstate == 4:
            function4return = getletter4(letterslot4)
            letterslot4 = function4return[0]
            letterstate = function4return[1]


def showverify1():
    draw.rectangle((0, 0, width, height), outline=0, fill=0)

    draw.text((40, 2), "Selected Words (1/2)", fill="YELLOW", font=titlefont)
    draw.text(
        (2,
         40),
        "1: " +
        seedphrase[1],
        fill="YELLOW",
        font=displayphrasefont)
    draw.text(
        (2,
         65),
        "2: " +
        seedphrase[2],
        fill="YELLOW",
        font=displayphrasefont)
    draw.text(
        (2,
         90),
        "3: " +
        seedphrase[3],
        fill="YELLOW",
        font=displayphrasefont)
    draw.text(
        (2,
         115),
        "4: " +
        seedphrase[4],
        fill="YELLOW",
        font=displayphrasefont)
    draw.text(
        (2,
         140),
        "5: " +
        seedphrase[5],
        fill="YELLOW",
        font=displayphrasefont)
    draw.text(
        (2,
         165),
        "6: " +
        seedphrase[6],
        fill="YELLOW",
        font=displayphrasefont)
    draw.text(
        (120,
         40),
        " 7: " +
        seedphrase[7],
        fill="YELLOW",
        font=displayphrasefont)
    draw.text(
        (120,
         65),
        " 8: " +
        seedphrase[8],
        fill="YELLOW",
        font=displayphrasefont)
    draw.text(
        (120,
         90),
        " 9: " +
        seedphrase[9],
        fill="YELLOW",
        font=displayphrasefont)
    draw.text(
        (120,
         115),
        "10: " +
        seedphrase[10],
        fill="YELLOW",
        font=displayphrasefont)
    draw.text(
        (120,
         140),
        "11: " +
        seedphrase[11],
        fill="YELLOW",
        font=displayphrasefont)
    draw.text(
        (120,
         165),
        "12: " +
        seedphrase[12],
        fill="YELLOW",
        font=displayphrasefont)
    draw.text((65, 210), "RIGHT to verify", fill="YELLOW", font=titlefont)

    disp.ShowImage(image, 0, 0)


def showverify2():
    draw.rectangle((0, 0, width, height), outline=0, fill=0)

    draw.text((40, 2), "Selected Words (2/2)", fill="YELLOW", font=titlefont)
    draw.text(
        (2,
         40),
        "13: " +
        seedphrase[13],
        fill="YELLOW",
        font=displayphrasefont)
    draw.text(
        (2,
         65),
        "14: " +
        seedphrase[14],
        fill="YELLOW",
        font=displayphrasefont)
    draw.text(
        (2,
         90),
        "15: " +
        seedphrase[15],
        fill="YELLOW",
        font=displayphrasefont)
    draw.text(
        (2,
         115),
        "16: " +
        seedphrase[16],
        fill="YELLOW",
        font=displayphrasefont)
    draw.text(
        (2,
         140),
        "17: " +
        seedphrase[17],
        fill="YELLOW",
        font=displayphrasefont)
    draw.text(
        (2,
         165),
        "18: " +
        seedphrase[18],
        fill="YELLOW",
        font=displayphrasefont)
    draw.text(
        (120,
         40),
        "19: " +
        seedphrase[19],
        fill="YELLOW",
        font=displayphrasefont)
    draw.text(
        (120,
         65),
        "20: " +
        seedphrase[20],
        fill="YELLOW",
        font=displayphrasefont)
    draw.text(
        (120,
         90),
        "21: " +
        seedphrase[21],
        fill="YELLOW",
        font=displayphrasefont)
    draw.text(
        (120,
         115),
        "22: " +
        seedphrase[22],
        fill="YELLOW",
        font=displayphrasefont)
    draw.text(
        (120,
         140),
        "23: " +
        seedphrase[23],
        fill="YELLOW",
        font=displayphrasefont)
    draw.text((65, 210), "RIGHT to verify", fill="YELLOW", font=titlefont)

    disp.ShowImage(image, 0, 0)


word24 = ""


def getword24():
    seedphrase.pop(0)

    seedphrase.append("abandon")

    stringphrase = " ".join(seedphrase)
    print(stringphrase)

    bytes = mnemonic_to_bytes(stringphrase, ignore_checksum=True)

    finalseed = mnemonic_from_bytes(bytes)

    splitseed = finalseed.split()

    global word24
    word24 = splitseed[-1]

    return word24


def displayfinalword():
    finalwordwidth, finalwordheight = draw.textsize(word24, font=finalwordfont)

    draw.rectangle((0, 0, width, height), outline=0, fill=0)

    draw.text((65, 60), "Word 24 is :", fill="YELLOW", font=displayphrasefont)
    draw.text(((240 - finalwordwidth) / 2, 90), word24,
              fill="YELLOW", font=finalwordfont)

    draw.text((73, 210), "RIGHT to EXIT", fill="YELLOW", font=titlefont)

    disp.ShowImage(image, 0, 0)


def main24wordprogram():
    allowedwordstates = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
                         11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]

    while wordcounter in allowedwordstates:
        getword()
        letterslot1 = "a"
        letterslot2 = "a"
        letterslot3 = "a"
        letterslot4 = "a"
        # print(seedphrase)

    verify1runstate = 1
    while verify1runstate == 1:
        showverify1()
        if GPIO.input(KEY_RIGHT_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.1)
            verify1runstate = 0

    verify2runstate = 1
    while verify2runstate == 1:
        showverify2()
        if GPIO.input(KEY_RIGHT_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.1)
            verify2runstate = 0

    word24 = getword24()

    displayword24runstate = 1
    while displayword24runstate == 1:
        displayfinalword()
        if GPIO.input(KEY_RIGHT_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.1)
            displayword24runstate = 0

    draw.rectangle((0, 0, width, height), outline=0, fill=0)

    disp.ShowImage(image, 0, 0)

    print("You reached the end of the program to generate word 24.")

# MODULE TO GENERATE WORD 24

# MODULE TO TEST IO


def iotestmethod():
    # initialize fonts
    iotestfont = ImageFont.truetype(
        '/usr/share/fonts/truetype/msttcorefonts/Impact.ttf', 18)

    # Get drawing object to draw on image.
    draw = ImageDraw.Draw(image)

    # Draw a black filled box to clear the image.
    draw.rectangle((0, 0, width, height), outline=0, fill=0)

    runstate = 1

    while runstate == 1:

        draw.rectangle((0, 0, width, height), outline=0, fill=0)
        draw.text((45, 5), "Input/Output Check:",
                  fill="YELLOW", font=iotestfont)

        if GPIO.input(KEY_UP_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.1)
            draw.polygon([(61, 89), (80, 46), (99, 89)],
                         outline="YELLOW", fill="YELLOW")
        else:  # button is pressed:
            draw.polygon([(61, 89), (80, 46), (99, 89)],
                         outline="YELLOW", fill=0)

        if GPIO.input(KEY_LEFT_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.1)
            draw.polygon([(51, 100), (8, 119), (51, 138)],
                         outline="YELLOW", fill="YELLOW")
        else:  # button is pressed:
            draw.polygon([(51, 100), (8, 119), (51, 138)],
                         outline="YELLOW", fill=0)

        if GPIO.input(KEY_RIGHT_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.1)
            draw.polygon([(109, 100), (152, 119), (109, 138)],
                         outline="YELLOW", fill="YELLOW")
        else:  # button is pressed:
            draw.polygon([(109, 100), (152, 119), (109, 138)],
                         outline="YELLOW", fill=0)

        if GPIO.input(KEY_DOWN_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.1)
            draw.polygon([(61, 151), (80, 193), (99, 151)],
                         outline="YELLOW", fill="YELLOW")
        else:  # button is pressed:
            draw.polygon([(61, 151), (80, 193), (99, 151)],
                         outline="YELLOW", fill=0)

        if GPIO.input(KEY_PRESS_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.1)
            draw.ellipse([(61, 99), (99, 141)],
                         outline="YELLOW", fill="YELLOW")
        else:  # button is pressed:
            draw.ellipse([(61, 99), (99, 141)], outline="YELLOW", fill=0)

        if GPIO.input(KEY1_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.1)
            draw.ellipse([(198, 40), (238, 80)],
                         outline="YELLOW", fill="YELLOW")
        else:  # button is pressed:
            draw.ellipse([(198, 40), (238, 80)], outline="YELLOW", fill=0)

        if GPIO.input(KEY2_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.1)
            draw.ellipse([(198, 95), (238, 135)],
                         outline="YELLOW", fill="YELLOW")
        else:  # button is pressed:
            draw.ellipse([(198, 95), (238, 135)], outline="YELLOW", fill=0)

        draw.text((200, 160), "EXIT", fill="YELLOW", font=iotestfont)

        if GPIO.input(KEY3_PIN) == GPIO.LOW:  # button is released
            time.sleep(0.4)
            runstate = 0

        disp.ShowImage(image, 0, 0)

    print("You exited the i o test module")

# MODULE TO TEST IO

# MODULE TO GET A SEED FROM DICE


dicefont = ImageFont.truetype(
    '/usr/share/fonts/truetype/msttcorefonts/Impact.ttf', 26)
dicebottomfont = ImageFont.truetype(
    '/usr/share/fonts/truetype/msttcorefonts/Impact.ttf', 18)


def drawdi1selected():
    draw.rectangle((5, 50, 75, 120), outline="YELLOW", fill="YELLOW")
    draw.ellipse([(34, 79), (46, 91)], outline="BLACK", fill="BLACK")
    draw.rectangle((85, 50, 155, 120), outline="YELLOW", fill="BLACK")
    draw.ellipse([(100, 60), (112, 72)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(128, 98), (140, 110)], outline="YELLOW", fill="YELLOW")
    draw.rectangle((165, 50, 235, 120), outline="YELLOW", fill="BLACK")
    draw.ellipse([(180, 60), (192, 72)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(194, 79), (206, 91)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(208, 98), (220, 110)], outline="YELLOW", fill="YELLOW")
    draw.rectangle((5, 130, 75, 200), outline="YELLOW", fill="BLACK")
    draw.ellipse([(20, 140), (32, 152)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(20, 174), (32, 186)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(48, 140), (60, 152)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(48, 174), (60, 186)], outline="YELLOW", fill="YELLOW")
    draw.rectangle((85, 130, 155, 200), outline="YELLOW", fill="BLACK")
    draw.ellipse([(100, 140), (112, 152)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(100, 178), (112, 190)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(114, 159), (126, 171)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(128, 140), (140, 152)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(128, 178), (140, 190)], outline="YELLOW", fill="YELLOW")
    draw.rectangle((165, 130, 235, 200), outline="YELLOW", fill="BLACK")
    draw.ellipse([(180, 140), (192, 152)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(180, 157), (192, 169)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(180, 174), (192, 186)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(208, 140), (220, 152)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(208, 157), (220, 169)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(208, 174), (220, 186)], outline="YELLOW", fill="YELLOW")
    draw.text((18, 210), "Press Control Stick to Select",
              fill="YELLOW", font=dicebottomfont)


def drawdi2selected():
    draw.rectangle((5, 50, 75, 120), outline="YELLOW", fill="BLACK")
    draw.ellipse([(34, 79), (46, 91)], outline="YELLOW", fill="YELLOW")
    draw.rectangle((85, 50, 155, 120), outline="YELLOW", fill="YELLOW")
    draw.ellipse([(100, 60), (112, 72)], outline="BLACK", fill="BLACK")
    draw.ellipse([(128, 98), (140, 110)], outline="BLACK", fill="BLACK")
    draw.rectangle((165, 50, 235, 120), outline="YELLOW", fill="BLACK")
    draw.ellipse([(180, 60), (192, 72)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(194, 79), (206, 91)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(208, 98), (220, 110)], outline="YELLOW", fill="YELLOW")
    draw.rectangle((5, 130, 75, 200), outline="YELLOW", fill="BLACK")
    draw.ellipse([(20, 140), (32, 152)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(20, 174), (32, 186)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(48, 140), (60, 152)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(48, 174), (60, 186)], outline="YELLOW", fill="YELLOW")
    draw.rectangle((85, 130, 155, 200), outline="YELLOW", fill="BLACK")
    draw.ellipse([(100, 140), (112, 152)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(100, 178), (112, 190)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(114, 159), (126, 171)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(128, 140), (140, 152)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(128, 178), (140, 190)], outline="YELLOW", fill="YELLOW")
    draw.rectangle((165, 130, 235, 200), outline="YELLOW", fill="BLACK")
    draw.ellipse([(180, 140), (192, 152)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(180, 157), (192, 169)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(180, 174), (192, 186)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(208, 140), (220, 152)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(208, 157), (220, 169)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(208, 174), (220, 186)], outline="YELLOW", fill="YELLOW")
    draw.text((18, 210), "Press Control Stick to Select",
              fill="YELLOW", font=dicebottomfont)


def drawdi3selected():
    draw.rectangle((5, 50, 75, 120), outline="YELLOW", fill="BLACK")
    draw.ellipse([(34, 79), (46, 91)], outline="YELLOW", fill="YELLOW")
    draw.rectangle((85, 50, 155, 120), outline="YELLOW", fill="BLACK")
    draw.ellipse([(100, 60), (112, 72)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(128, 98), (140, 110)], outline="YELLOW", fill="YELLOW")
    draw.rectangle((165, 50, 235, 120), outline="YELLOW", fill="YELLOW")
    draw.ellipse([(180, 60), (192, 72)], outline="BLACK", fill="BLACK")
    draw.ellipse([(194, 79), (206, 91)], outline="BLACK", fill="BLACK")
    draw.ellipse([(208, 98), (220, 110)], outline="BLACK", fill="BLACK")
    draw.rectangle((5, 130, 75, 200), outline="YELLOW", fill="BLACK")
    draw.ellipse([(20, 140), (32, 152)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(20, 174), (32, 186)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(48, 140), (60, 152)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(48, 174), (60, 186)], outline="YELLOW", fill="YELLOW")
    draw.rectangle((85, 130, 155, 200), outline="YELLOW", fill="BLACK")
    draw.ellipse([(100, 140), (112, 152)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(100, 178), (112, 190)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(114, 159), (126, 171)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(128, 140), (140, 152)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(128, 178), (140, 190)], outline="YELLOW", fill="YELLOW")
    draw.rectangle((165, 130, 235, 200), outline="YELLOW", fill="BLACK")
    draw.ellipse([(180, 140), (192, 152)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(180, 157), (192, 169)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(180, 174), (192, 186)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(208, 140), (220, 152)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(208, 157), (220, 169)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(208, 174), (220, 186)], outline="YELLOW", fill="YELLOW")
    draw.text((18, 210), "Press Control Stick to Select",
              fill="YELLOW", font=dicebottomfont)


def drawdi4selected():
    draw.rectangle((5, 50, 75, 120), outline="YELLOW", fill="BLACK")
    draw.ellipse([(34, 79), (46, 91)], outline="YELLOW", fill="YELLOW")
    draw.rectangle((85, 50, 155, 120), outline="YELLOW", fill="BLACK")
    draw.ellipse([(100, 60), (112, 72)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(128, 98), (140, 110)], outline="YELLOW", fill="YELLOW")
    draw.rectangle((165, 50, 235, 120), outline="YELLOW", fill="BLACK")
    draw.ellipse([(180, 60), (192, 72)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(194, 79), (206, 91)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(208, 98), (220, 110)], outline="YELLOW", fill="YELLOW")
    draw.rectangle((5, 130, 75, 200), outline="YELLOW", fill="YELLOW")
    draw.ellipse([(20, 140), (32, 152)], outline="BLACK", fill="BLACK")
    draw.ellipse([(20, 174), (32, 186)], outline="BLACK", fill="BLACK")
    draw.ellipse([(48, 140), (60, 152)], outline="BLACK", fill="BLACK")
    draw.ellipse([(48, 174), (60, 186)], outline="BLACK", fill="BLACK")
    draw.rectangle((85, 130, 155, 200), outline="YELLOW", fill="BLACK")
    draw.ellipse([(100, 140), (112, 152)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(100, 178), (112, 190)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(114, 159), (126, 171)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(128, 140), (140, 152)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(128, 178), (140, 190)], outline="YELLOW", fill="YELLOW")
    draw.rectangle((165, 130, 235, 200), outline="YELLOW", fill="BLACK")
    draw.ellipse([(180, 140), (192, 152)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(180, 157), (192, 169)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(180, 174), (192, 186)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(208, 140), (220, 152)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(208, 157), (220, 169)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(208, 174), (220, 186)], outline="YELLOW", fill="YELLOW")
    draw.text((18, 210), "Press Control Stick to Select",
              fill="YELLOW", font=dicebottomfont)


def drawdi5selected():
    draw.rectangle((5, 50, 75, 120), outline="YELLOW", fill="BLACK")
    draw.ellipse([(34, 79), (46, 91)], outline="YELLOW", fill="YELLOW")
    draw.rectangle((85, 50, 155, 120), outline="YELLOW", fill="BLACK")
    draw.ellipse([(100, 60), (112, 72)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(128, 98), (140, 110)], outline="YELLOW", fill="YELLOW")
    draw.rectangle((165, 50, 235, 120), outline="YELLOW", fill="BLACK")
    draw.ellipse([(180, 60), (192, 72)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(194, 79), (206, 91)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(208, 98), (220, 110)], outline="YELLOW", fill="YELLOW")
    draw.rectangle((5, 130, 75, 200), outline="YELLOW", fill="BLACK")
    draw.ellipse([(20, 140), (32, 152)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(20, 174), (32, 186)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(48, 140), (60, 152)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(48, 174), (60, 186)], outline="YELLOW", fill="YELLOW")
    draw.rectangle((85, 130, 155, 200), outline="YELLOW", fill="YELLOW")
    draw.ellipse([(100, 140), (112, 152)], outline="BLACK", fill="BLACK")
    draw.ellipse([(100, 178), (112, 190)], outline="BLACK", fill="BLACK")
    draw.ellipse([(114, 159), (126, 171)], outline="BLACK", fill="BLACK")
    draw.ellipse([(128, 140), (140, 152)], outline="BLACK", fill="BLACK")
    draw.ellipse([(128, 178), (140, 190)], outline="BLACK", fill="BLACK")
    draw.rectangle((165, 130, 235, 200), outline="YELLOW", fill="BLACK")
    draw.ellipse([(180, 140), (192, 152)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(180, 157), (192, 169)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(180, 174), (192, 186)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(208, 140), (220, 152)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(208, 157), (220, 169)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(208, 174), (220, 186)], outline="YELLOW", fill="YELLOW")
    draw.text((18, 210), "Press Control Stick to Select",
              fill="YELLOW", font=dicebottomfont)


def drawdi6selected():
    draw.rectangle((5, 50, 75, 120), outline="YELLOW", fill="BLACK")
    draw.ellipse([(34, 79), (46, 91)], outline="YELLOW", fill="YELLOW")
    draw.rectangle((85, 50, 155, 120), outline="YELLOW", fill="BLACK")
    draw.ellipse([(100, 60), (112, 72)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(128, 98), (140, 110)], outline="YELLOW", fill="YELLOW")
    draw.rectangle((165, 50, 235, 120), outline="YELLOW", fill="BLACK")
    draw.ellipse([(180, 60), (192, 72)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(194, 79), (206, 91)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(208, 98), (220, 110)], outline="YELLOW", fill="YELLOW")
    draw.rectangle((5, 130, 75, 200), outline="YELLOW", fill="BLACK")
    draw.ellipse([(20, 140), (32, 152)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(20, 174), (32, 186)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(48, 140), (60, 152)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(48, 174), (60, 186)], outline="YELLOW", fill="YELLOW")
    draw.rectangle((85, 130, 155, 200), outline="YELLOW", fill="BLACK")
    draw.ellipse([(100, 140), (112, 152)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(100, 178), (112, 190)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(114, 159), (126, 171)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(128, 140), (140, 152)], outline="YELLOW", fill="YELLOW")
    draw.ellipse([(128, 178), (140, 190)], outline="YELLOW", fill="YELLOW")
    draw.rectangle((165, 130, 235, 200), outline="YELLOW", fill="YELLOW")
    draw.ellipse([(180, 140), (192, 152)], outline="BLACK", fill="BLACK")
    draw.ellipse([(180, 157), (192, 169)], outline="BLACK", fill="BLACK")
    draw.ellipse([(180, 174), (192, 186)], outline="BLACK", fill="BLACK")
    draw.ellipse([(208, 140), (220, 152)], outline="BLACK", fill="BLACK")
    draw.ellipse([(208, 157), (220, 169)], outline="BLACK", fill="BLACK")
    draw.ellipse([(208, 174), (220, 186)], outline="BLACK", fill="BLACK")
    draw.text((18, 210), "Press Control Stick to Select",
              fill="YELLOW", font=dicebottomfont)


def rollsobtainer():

    rollnumber = 1
    rollcollectorstring = ""
    currentdiselected = 1
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    draw.text((45, 5), "Dice roll: " + str(rollnumber) +
              "/99", fill="YELLOW", font=dicefont)
    drawdi1selected()

    while rollnumber <= 99:
        if GPIO.input(KEY_RIGHT_PIN) == GPIO.LOW:
            time.sleep(0.15)
            if currentdiselected == 2:
                currentdiselected = 3
                drawdi3selected()
            if currentdiselected == 1:
                currentdiselected = 2
                drawdi2selected()
            if currentdiselected == 5:
                currentdiselected = 6
                drawdi6selected()
            if currentdiselected == 4:
                currentdiselected = 5
                drawdi5selected()
        if GPIO.input(KEY_LEFT_PIN) == GPIO.LOW:
            time.sleep(0.15)
            if currentdiselected == 2:
                currentdiselected = 1
                drawdi1selected()
            if currentdiselected == 3:
                currentdiselected = 2
                drawdi2selected()
            if currentdiselected == 5:
                currentdiselected = 4
                drawdi4selected()
            if currentdiselected == 6:
                currentdiselected = 5
                drawdi5selected()
        if GPIO.input(KEY_DOWN_PIN) == GPIO.LOW:
            time.sleep(0.15)
            if currentdiselected == 1:
                currentdiselected = 4
                drawdi4selected()
            if currentdiselected == 2:
                currentdiselected = 5
                drawdi5selected()
            if currentdiselected == 3:
                currentdiselected = 6
                drawdi6selected()
        if GPIO.input(KEY_UP_PIN) == GPIO.LOW:
            time.sleep(0.15)
            if currentdiselected == 4:
                currentdiselected = 1
                drawdi1selected()
            if currentdiselected == 5:
                currentdiselected = 2
                drawdi2selected()
            if currentdiselected == 6:
                currentdiselected = 3
                drawdi3selected()
        if GPIO.input(KEY_PRESS_PIN) == GPIO.LOW:
            draw.rectangle((0, 0, width, height), outline=0, fill=0)
            time.sleep(0.15)
            if currentdiselected == 6:
                rollcollectorstring = rollcollectorstring + "0"
            else:
                rollcollectorstring = rollcollectorstring + \
                    str(currentdiselected)
            print(
                "The roll number is " +
                str(rollnumber) +
                " and the die selections are : " +
                rollcollectorstring)
            rollnumber = rollnumber + 1
            if currentdiselected == 1:
                drawdi1selected()
            if currentdiselected == 2:
                drawdi2selected()
            if currentdiselected == 3:
                drawdi3selected()
            if currentdiselected == 4:
                drawdi4selected()
            if currentdiselected == 5:
                drawdi5selected()
            if currentdiselected == 6:
                drawdi6selected()
        if rollnumber < 100:
            draw.text((45, 5), "Dice roll: " + str(rollnumber) +
                      "/99", fill="YELLOW", font=dicefont)
        disp.ShowImage(image, 0, 0)

    return rollcollectorstring


def showthediceseed():
    titlefont = ImageFont.truetype(
        '/usr/share/fonts/truetype/msttcorefonts/Impact.ttf', 18)
    displayphrasefont = ImageFont.truetype(
        '/usr/share/fonts/truetype/msttcorefonts/Impact.ttf', 23)

    collectedrolls = rollsobtainer()

    entropyinteger = int(collectedrolls, 6)

    rollsinbytes = entropyinteger.to_bytes(32, byteorder="little")

    baddicestring = mnemonic_from_bytes(rollsinbytes)

    wordarray = baddicestring.split()

    wordarray.pop(-1)

    laststring = " ".join(wordarray) + " abandon"

    lastbytes = mnemonic_to_bytes(laststring, ignore_checksum=True)

    correctedlaststring = mnemonic_from_bytes(lastbytes)

    print("The string with the corrected checksum word is:")
    print(correctedlaststring)

    displayarray = correctedlaststring.split()

    print("")
    print(displayarray)

    firstwordset = True

    while firstwordset is True:
        # Display the first 12 words
        draw.rectangle((0, 0, width, height), outline=0, fill=0)
        draw.text((55, 2), "Your Seed Is (1/2):",
                  fill="YELLOW", font=titlefont)
        draw.text(
            (2,
             40),
            "1: " +
            displayarray[0],
            fill="YELLOW",
            font=displayphrasefont)
        draw.text(
            (2,
             65),
            "2: " +
            displayarray[1],
            fill="YELLOW",
            font=displayphrasefont)
        draw.text(
            (2,
             90),
            "3: " +
            displayarray[2],
            fill="YELLOW",
            font=displayphrasefont)
        draw.text(
            (2,
             115),
            "4: " +
            displayarray[3],
            fill="YELLOW",
            font=displayphrasefont)
        draw.text(
            (2,
             140),
            "5: " +
            displayarray[4],
            fill="YELLOW",
            font=displayphrasefont)
        draw.text(
            (2,
             165),
            "6: " +
            displayarray[5],
            fill="YELLOW",
            font=displayphrasefont)
        draw.text(
            (120,
             40),
            " 7: " +
            displayarray[6],
            fill="YELLOW",
            font=displayphrasefont)
        draw.text(
            (120,
             65),
            " 8: " +
            displayarray[7],
            fill="YELLOW",
            font=displayphrasefont)
        draw.text(
            (120,
             90),
            " 9: " +
            displayarray[8],
            fill="YELLOW",
            font=displayphrasefont)
        draw.text(
            (120,
             115),
            "10: " +
            displayarray[9],
            fill="YELLOW",
            font=displayphrasefont)
        draw.text(
            (120,
             140),
            "11: " +
            displayarray[10],
            fill="YELLOW",
            font=displayphrasefont)
        draw.text(
            (120,
             165),
            "12: " +
            displayarray[11],
            fill="YELLOW",
            font=displayphrasefont)
        draw.text((55, 210), "RIGHT to Continue",
                  fill="YELLOW", font=titlefont)
        disp.ShowImage(image, 0, 0)

        if GPIO.input(KEY_RIGHT_PIN) == GPIO.LOW:
            time.sleep(0.25)
            firstwordset = False

    secondwordset = True

    while secondwordset is True:
        # Display the second 12 words
        draw.rectangle((0, 0, width, height), outline=0, fill=0)
        draw.text((55, 2), "Your Seed Is (2/2):",
                  fill="YELLOW", font=titlefont)
        draw.text(
            (2,
             40),
            "13: " +
            displayarray[12],
            fill="YELLOW",
            font=displayphrasefont)
        draw.text(
            (2,
             65),
            "14: " +
            displayarray[13],
            fill="YELLOW",
            font=displayphrasefont)
        draw.text(
            (2,
             90),
            "15: " +
            displayarray[14],
            fill="YELLOW",
            font=displayphrasefont)
        draw.text(
            (2,
             115),
            "16: " +
            displayarray[15],
            fill="YELLOW",
            font=displayphrasefont)
        draw.text(
            (2,
             140),
            "17: " +
            displayarray[16],
            fill="YELLOW",
            font=displayphrasefont)
        draw.text(
            (2,
             165),
            "18: " +
            displayarray[17],
            fill="YELLOW",
            font=displayphrasefont)
        draw.text(
            (120,
             40),
            "19: " +
            displayarray[18],
            fill="YELLOW",
            font=displayphrasefont)
        draw.text(
            (120,
             65),
            "20: " +
            displayarray[19],
            fill="YELLOW",
            font=displayphrasefont)
        draw.text(
            (120,
             90),
            "21: " +
            displayarray[20],
            fill="YELLOW",
            font=displayphrasefont)
        draw.text(
            (120,
             115),
            "22: " +
            displayarray[21],
            fill="YELLOW",
            font=displayphrasefont)
        draw.text(
            (120,
             140),
            "23: " +
            displayarray[22],
            fill="YELLOW",
            font=displayphrasefont)
        draw.text(
            (120,
             165),
            "24: " +
            displayarray[23],
            fill="YELLOW",
            font=displayphrasefont)
        draw.text((70, 210), "RIGHT to EXIT", fill="YELLOW", font=titlefont)
        disp.ShowImage(image, 0, 0)

        if GPIO.input(KEY_RIGHT_PIN) == GPIO.LOW:
            time.sleep(0.25)
            secondwordset = False

# MODULE TO GET A SEED FROM DICE

# MAIN MENU MODULE


mainrunstate = 1
mainmenufont = ImageFont.truetype(
    '/usr/share/fonts/truetype/msttcorefonts/Impact.ttf', 20)
versionfont = ImageFont.truetype(
    '/usr/share/fonts/truetype/msttcorefonts/Impact.ttf', 16)


def option1():
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    draw.rectangle((5, 40, 185, 75), outline=0, fill="YELLOW")
    draw.text((15, 45), "I/O Interface Check", fill="BLACK", font=mainmenufont)
    # draw.rectangle((5, 75, 185, 110), outline=0, fill="YELLOW")
    draw.text((15, 80), "Generate Word 24", fill="YELLOW", font=mainmenufont)
    # draw.rectangle((5, 110, 185, 145), outline=0, fill="YELLOW")
    draw.text((15, 115), "Get a Seed with Dice",
              fill="YELLOW", font=mainmenufont)
    # draw.rectangle((5, 145, 185, 170), outline=0, fill="YELLOW")
    draw.text((15, 150), "Power OFF Device", fill="YELLOW", font=mainmenufont)
    draw.text((35, 2), "SeedSigner - version 0.0.2",
              fill="YELLOW", font=versionfont)
    draw.text((18, 210), "Press Control Stick to Select",
              fill="YELLOW", font=dicebottomfont)


def option2():
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    # draw.rectangle((5, 40, 185, 75), outline=0, fill="YELLOW")
    draw.text((15, 45), "I/O Interface Check",
              fill="YELLOW", font=mainmenufont)
    draw.rectangle((5, 75, 185, 110), outline=0, fill="YELLOW")
    draw.text((15, 80), "Generate Word 24", fill="BLACK", font=mainmenufont)
    # draw.rectangle((5, 110, 185, 145), outline=0, fill="YELLOW")
    draw.text((15, 115), "Get a Seed with Dice",
              fill="YELLOW", font=mainmenufont)
    # draw.rectangle((5, 145, 185, 170), outline=0, fill="YELLOW")
    draw.text((15, 150), "Power OFF Device", fill="YELLOW", font=mainmenufont)
    draw.text((35, 2), "SeedSigner - version 0.0.2",
              fill="YELLOW", font=versionfont)
    draw.text((18, 210), "Press Control Stick to Select",
              fill="YELLOW", font=dicebottomfont)


def option3():
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    # draw.rectangle((5, 40, 185, 75), outline=0, fill="YELLOW")
    draw.text((15, 45), "I/O Interface Check",
              fill="YELLOW", font=mainmenufont)
    # draw.rectangle((5, 75, 185, 110), outline=0, fill="YELLOW")
    draw.text((15, 80), "Generate Word 24", fill="YELLOW", font=mainmenufont)
    draw.rectangle((5, 110, 185, 145), outline=0, fill="YELLOW")
    draw.text((15, 115), "Get a Seed with Dice",
              fill="BLACK", font=mainmenufont)
    # draw.rectangle((5, 145, 185, 170), outline=0, fill="YELLOW")
    draw.text((15, 150), "Power OFF Device", fill="YELLOW", font=mainmenufont)
    draw.text((35, 2), "SeedSigner - version 0.0.2",
              fill="YELLOW", font=versionfont)
    draw.text((18, 210), "Press Control Stick to Select",
              fill="YELLOW", font=dicebottomfont)


def option4():
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    # draw.rectangle((5, 40, 185, 75), outline=0, fill="YELLOW")
    draw.text((15, 45), "I/O Interface Check",
              fill="YELLOW", font=mainmenufont)
    # draw.rectangle((5, 75, 185, 110), outline=0, fill="YELLOW")
    draw.text((15, 80), "Generate Word 24", fill="YELLOW", font=mainmenufont)
    # draw.rectangle((5, 110, 185, 145), outline=0, fill="YELLOW")
    draw.text((15, 115), "Get a Seed with Dice",
              fill="YELLOW", font=mainmenufont)
    draw.rectangle((5, 145, 185, 180), outline=0, fill="YELLOW")
    draw.text((15, 150), "Power OFF Device", fill="BLACK", font=mainmenufont)
    draw.text((35, 2), "SeedSigner - version 0.0.2",
              fill="YELLOW", font=versionfont)
    draw.text((18, 210), "Press Control Stick to Select",
              fill="YELLOW", font=dicebottomfont)


def displayscreenstate():
    if mainrunstate == 1:
        option1()

    if mainrunstate == 2:
        option2()

    if mainrunstate == 3:
        option3()

    if mainrunstate == 4:
        option4()

    disp.ShowImage(image, 0, 0)


def mainmenufunction():
    possiblerunstates = [1, 2, 3, 4]
    global mainrunstate
    global wordcounter
    global letterslot1
    global letterslot2
    global letterslot3
    global letterslot4
    displayscreenstate()

    while mainrunstate in possiblerunstates:

        if GPIO.input(KEY_UP_PIN) == GPIO.LOW:
            if mainrunstate in [2, 3, 4]:
                mainrunstate = mainrunstate - 1
                time.sleep(0.2)
            else:
                mainrunstate = 4
                time.sleep(0.2)
            displayscreenstate()
            print("The runstate is: " + str(mainrunstate))

        if GPIO.input(KEY_DOWN_PIN) == GPIO.LOW:
            if mainrunstate in [1, 2, 3]:
                mainrunstate = mainrunstate + 1
                time.sleep(0.2)
            else:
                mainrunstate = 1
                time.sleep(0.2)
            displayscreenstate()
            print("The runstate is: " + str(mainrunstate))

        if GPIO.input(KEY_PRESS_PIN) == GPIO.LOW:
            if mainrunstate == 1:
                print("Option 1 Selected")
                time.sleep(0.4)
                iotestmethod()
                mainrunstate = 1
                displayscreenstate()

            if mainrunstate == 2:
                print("Option 2 Selected")
                time.sleep(0.4)
                wordcounter = 1
                letterslot1 = "a"
                letterslot2 = "a"
                letterslot3 = "a"
                letterslot4 = "a"
                main24wordprogram()
                mainrunstate = 2
                displayscreenstate()

            if mainrunstate == 3:
                print("Opention 3 Selected")
                time.sleep(0.4)
                mainrunstate = 3
                showthediceseed()
                displayscreenstate()

            if mainrunstate == 4:
                print("Option 4 Selected")
                time.sleep(0.4)
                call("sudo shutdown --poweroff now", shell=True)

    # clear the screen upon exit
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    disp.ShowImage(image, 0, 0)

    print("You reached the end of the program.")


mainmenufunction()

GPIO.cleanup()

# except:
# print("except")
# GPIO.cleanup()
