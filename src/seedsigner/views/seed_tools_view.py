# External Dependencies
from embit import bip39
from embit.bip39 import mnemonic_to_bytes, mnemonic_from_bytes
from PIL import ImageDraw, Image
from PIL.ImageOps import autocontrast
import hashlib
import math
import os
import time

# Internal file class dependencies
from . import View
from seedsigner.helpers import B, QR, Keyboard, TextEntryDisplay, mnemonic_generation
from seedsigner.models import DecodeQR, DecodeQRStatus, QRType, EncodeQR


class SeedToolsView(View):

    SEEDWORDS = ["abandon", "ability", "able", "about", "above", "absent", "absorb", "abstract", "absurd", "abuse", "access", "accident", "account", "accuse", "achieve", "acid", "acoustic", "acquire", "across", "act", "action", "actor", "actress", "actual", "adapt", "add", "addict", "address", "adjust", "admit", "adult", "advance", "advice", "aerobic", "affair", "afford", "afraid", "again", "age", "agent", "agree", "ahead", "aim", "air", "airport", "aisle", "alarm", "album", "alcohol", "alert", "alien", "all", "alley", "allow", "almost", "alone", "alpha", "already", "also", "alter", "always", "amateur", "amazing", "among", "amount", "amused", "analyst", "anchor", "ancient", "anger", "angle", "angry", "animal", "ankle", "announce", "annual", "another", "answer", "antenna", "antique", "anxiety", "any", "apart", "apology", "appear", "apple", "approve", "april", "arch", "arctic", "area", "arena", "argue", "arm", "armed", "armor", "army", "around", "arrange", "arrest", "arrive", "arrow", "art", "artefact", "artist", "artwork", "ask", "aspect", "assault", "asset", "assist", "assume", "asthma", "athlete", "atom", "attack", "attend", "attitude", "attract", "auction", "audit", "august", "aunt", "author", "auto", "autumn", "average", "avocado", "avoid", "awake", "aware", "away", "awesome", "awful", "awkward", "axis", "baby", "bachelor", "bacon", "badge", "bag", "balance", "balcony", "ball", "bamboo", "banana", "banner", "bar", "barely", "bargain", "barrel", "base", "basic", "basket", "battle", "beach", "bean", "beauty", "because", "become", "beef", "before", "begin", "behave", "behind", "believe", "below", "belt", "bench", "benefit", "best", "betray", "better", "between", "beyond", "bicycle", "bid", "bike", "bind", "biology", "bird", "birth", "bitter", "black", "blade", "blame", "blanket", "blast", "bleak", "bless", "blind", "blood", "blossom", "blouse", "blue", "blur", "blush", "board", "boat", "body", "boil", "bomb", "bone", "bonus", "book", "boost", "border", "boring", "borrow", "boss", "bottom", "bounce", "box", "boy", "bracket", "brain", "brand", "brass", "brave", "bread", "breeze", "brick", "bridge", "brief", "bright", "bring", "brisk", "broccoli", "broken", "bronze", "broom", "brother", "brown", "brush", "bubble", "buddy", "budget", "buffalo", "build", "bulb", "bulk", "bullet", "bundle", "bunker", "burden", "burger", "burst", "bus", "business", "busy", "butter", "buyer", "buzz", "cabbage", "cabin", "cable", "cactus", "cage", "cake", "call", "calm", "camera", "camp", "can", "canal", "cancel", "candy", "cannon", "canoe", "canvas", "canyon", "capable", "capital", "captain", "car", "carbon", "card", "cargo", "carpet", "carry", "cart", "case", "cash", "casino", "castle", "casual", "cat", "catalog", "catch", "category", "cattle", "caught", "cause", "caution", "cave", "ceiling", "celery", "cement", "census", "century", "cereal", "certain", "chair", "chalk", "champion", "change", "chaos", "chapter", "charge", "chase", "chat", "cheap", "check", "cheese", "chef", "cherry", "chest", "chicken", "chief", "child", "chimney", "choice", "choose", "chronic", "chuckle", "chunk", "churn", "cigar", "cinnamon", "circle", "citizen", "city", "civil", "claim", "clap", "clarify", "claw", "clay", "clean", "clerk", "clever", "click", "client", "cliff", "climb", "clinic", "clip", "clock", "clog", "close", "cloth", "cloud", "clown", "club", "clump", "cluster", "clutch", "coach", "coast", "coconut", "code", "coffee", "coil", "coin", "collect", "color", "column", "combine", "come", "comfort", "comic", "common", "company", "concert", "conduct", "confirm", "congress", "connect", "consider", "control", "convince", "cook", "cool", "copper", "copy", "coral", "core", "corn", "correct", "cost", "cotton", "couch", "country", "couple", "course", "cousin", "cover", "coyote", "crack", "cradle", "craft", "cram", "crane", "crash", "crater", "crawl", "crazy", "cream", "credit", "creek", "crew", "cricket", "crime", "crisp", "critic", "crop", "cross", "crouch", "crowd", "crucial", "cruel", "cruise", "crumble", "crunch", "crush", "cry", "crystal", "cube", "culture", "cup", "cupboard", "curious", "current", "curtain", "curve", "cushion", "custom", "cute", "cycle", "dad", "damage", "damp", "dance", "danger", "daring", "dash", "daughter", "dawn", "day", "deal", "debate", "debris", "decade", "december", "decide", "decline", "decorate", "decrease", "deer", "defense", "define", "defy", "degree", "delay", "deliver", "demand", "demise", "denial", "dentist", "deny", "depart", "depend", "deposit", "depth", "deputy", "derive", "describe", "desert", "design", "desk", "despair", "destroy", "detail", "detect", "develop", "device", "devote", "diagram", "dial", "diamond", "diary", "dice", "diesel", "diet", "differ", "digital", "dignity", "dilemma", "dinner", "dinosaur", "direct", "dirt", "disagree", "discover", "disease", "dish", "dismiss", "disorder", "display", "distance", "divert", "divide", "divorce", "dizzy", "doctor", "document", "dog", "doll", "dolphin", "domain", "donate", "donkey", "donor", "door", "dose", "double", "dove", "draft", "dragon", "drama", "drastic", "draw", "dream", "dress", "drift", "drill", "drink", "drip", "drive", "drop", "drum", "dry", "duck", "dumb", "dune", "during", "dust", "dutch", "duty", "dwarf", "dynamic", "eager", "eagle", "early", "earn", "earth", "easily", "east", "easy", "echo", "ecology", "economy", "edge", "edit", "educate", "effort", "egg", "eight", "either", "elbow", "elder", "electric", "elegant", "element", "elephant", "elevator", "elite", "else", "embark", "embody", "embrace", "emerge", "emotion", "employ", "empower", "empty", "enable", "enact", "end", "endless", "endorse", "enemy", "energy", "enforce", "engage", "engine", "enhance", "enjoy", "enlist", "enough", "enrich", "enroll", "ensure", "enter", "entire", "entry", "envelope", "episode", "equal", "equip", "era", "erase", "erode", "erosion", "error", "erupt", "escape", "essay", "essence", "estate", "eternal", "ethics", "evidence", "evil", "evoke", "evolve", "exact", "example", "excess", "exchange", "excite", "exclude", "excuse", "execute", "exercise", "exhaust", "exhibit", "exile", "exist", "exit", "exotic", "expand", "expect", "expire", "explain", "expose", "express", "extend", "extra", "eye", "eyebrow", "fabric", "face", "faculty", "fade", "faint", "faith", "fall", "false", "fame", "family", "famous", "fan", "fancy", "fantasy", "farm", "fashion", "fat", "fatal", "father", "fatigue", "fault", "favorite", "feature", "february", "federal", "fee", "feed", "feel", "female", "fence", "festival", "fetch", "fever", "few", "fiber", "fiction", "field", "figure", "file", "film", "filter", "final", "find", "fine", "finger", "finish", "fire", "firm", "first", "fiscal", "fish", "fit", "fitness", "fix", "flag", "flame", "flash", "flat", "flavor", "flee", "flight", "flip", "float", "flock", "floor", "flower", "fluid", "flush", "fly", "foam", "focus", "fog", "foil", "fold", "follow", "food", "foot", "force", "forest", "forget", "fork", "fortune", "forum", "forward", "fossil", "foster", "found", "fox", "fragile", "frame", "frequent", "fresh", "friend", "fringe", "frog", "front", "frost", "frown", "frozen", "fruit", "fuel", "fun", "funny", "furnace", "fury", "future", "gadget", "gain", "galaxy", "gallery", "game", "gap", "garage", "garbage", "garden", "garlic", "garment", "gas", "gasp", "gate", "gather", "gauge", "gaze", "general", "genius", "genre", "gentle", "genuine", "gesture", "ghost", "giant", "gift", "giggle", "ginger", "giraffe", "girl", "give", "glad", "glance", "glare", "glass", "glide", "glimpse", "globe", "gloom", "glory", "glove", "glow", "glue", "goat", "goddess", "gold", "good", "goose", "gorilla", "gospel", "gossip", "govern", "gown", "grab", "grace", "grain", "grant", "grape", "grass", "gravity", "great", "green", "grid", "grief", "grit", "grocery", "group", "grow", "grunt", "guard", "guess", "guide", "guilt", "guitar", "gun", "gym", "habit", "hair", "half", "hammer", "hamster", "hand", "happy", "harbor", "hard", "harsh", "harvest", "hat", "have", "hawk", "hazard", "head", "health", "heart", "heavy", "hedgehog", "height", "hello", "helmet", "help", "hen", "hero", "hidden", "high", "hill", "hint", "hip", "hire", "history", "hobby", "hockey", "hold", "hole", "holiday", "hollow", "home", "honey", "hood", "hope", "horn", "horror", "horse", "hospital", "host", "hotel", "hour", "hover", "hub", "huge", "human", "humble", "humor", "hundred", "hungry", "hunt", "hurdle", "hurry", "hurt", "husband", "hybrid", "ice", "icon", "idea", "identify", "idle", "ignore", "ill", "illegal", "illness", "image", "imitate", "immense", "immune", "impact", "impose", "improve", "impulse", "inch", "include", "income", "increase", "index", "indicate", "indoor", "industry", "infant", "inflict", "inform", "inhale", "inherit", "initial", "inject", "injury", "inmate", "inner", "innocent", "input", "inquiry", "insane", "insect", "inside", "inspire", "install", "intact", "interest", "into", "invest", "invite", "involve", "iron", "island", "isolate", "issue", "item", "ivory", "jacket", "jaguar", "jar", "jazz", "jealous", "jeans", "jelly", "jewel", "job", "join", "joke", "journey", "joy", "judge", "juice", "jump", "jungle", "junior", "junk", "just", "kangaroo", "keen", "keep", "ketchup", "key", "kick", "kid", "kidney", "kind", "kingdom", "kiss", "kit", "kitchen", "kite", "kitten", "kiwi", "knee", "knife", "knock", "know", "lab", "label", "labor", "ladder", "lady", "lake", "lamp", "language", "laptop", "large", "later", "latin", "laugh", "laundry", "lava", "law", "lawn", "lawsuit", "layer", "lazy", "leader", "leaf", "learn", "leave", "lecture", "left", "leg", "legal", "legend", "leisure", "lemon", "lend", "length", "lens", "leopard", "lesson", "letter", "level", "liar", "liberty", "library", "license", "life", "lift", "light", "like", "limb", "limit", "link", "lion", "liquid", "list", "little", "live", "lizard", "load", "loan", "lobster", "local", "lock", "logic", "lonely", "long", "loop", "lottery", "loud", "lounge", "love", "loyal", "lucky", "luggage", "lumber", "lunar", "lunch", "luxury", "lyrics", "machine", "mad", "magic", "magnet", "maid", "mail", "main", "major", "make", "mammal", "man", "manage", "mandate", "mango", "mansion", "manual", "maple", "marble", "march", "margin", "marine", "market", "marriage", "mask", "mass", "master", "match", "material", "math", "matrix", "matter", "maximum", "maze", "meadow", "mean", "measure", "meat", "mechanic", "medal", "media", "melody", "melt", "member", "memory", "mention", "menu", "mercy", "merge", "merit", "merry", "mesh", "message", "metal", "method", "middle", "midnight", "milk", "million", "mimic", "mind", "minimum", "minor", "minute", "miracle", "mirror", "misery", "miss", "mistake", "mix", "mixed", "mixture", "mobile", "model", "modify", "mom", "moment", "monitor", "monkey", "monster", "month", "moon", "moral", "more", "morning", "mosquito", "mother", "motion", "motor", "mountain", "mouse", "move", "movie", "much", "muffin", "mule", "multiply", "muscle", "museum", "mushroom", "music", "must", "mutual", "myself", "mystery", "myth", "naive", "name", "napkin", "narrow", "nasty", "nation", "nature", "near", "neck", "need", "negative", "neglect", "neither", "nephew", "nerve", "nest", "net", "network", "neutral", "never", "news", "next", "nice", "night", "noble", "noise", "nominee", "noodle", "normal", "north", "nose", "notable", "note", "nothing", "notice", "novel", "now", "nuclear", "number", "nurse", "nut", "oak", "obey", "object", "oblige", "obscure", "observe", "obtain", "obvious", "occur", "ocean", "october", "odor", "off", "offer", "office", "often", "oil", "okay", "old", "olive", "olympic", "omit", "once", "one", "onion", "online", "only", "open", "opera", "opinion", "oppose", "option", "orange", "orbit", "orchard", "order", "ordinary", "organ", "orient", "original", "orphan", "ostrich", "other", "outdoor", "outer", "output", "outside", "oval", "oven", "over", "own", "owner", "oxygen", "oyster", "ozone", "pact", "paddle", "page", "pair", "palace", "palm", "panda", "panel", "panic", "panther", "paper", "parade", "parent", "park", "parrot", "party", "pass", "patch", "path", "patient", "patrol", "pattern", "pause", "pave", "payment", "peace", "peanut", "pear", "peasant", "pelican", "pen", "penalty", "pencil", "people", "pepper", "perfect", "permit", "person", "pet", "phone", "photo", "phrase", "physical", "piano", "picnic", "picture", "piece", "pig", "pigeon", "pill", "pilot", "pink", "pioneer", "pipe", "pistol", "pitch", "pizza", "place", "planet", "plastic", "plate", "play", "please", "pledge", "pluck", "plug", "plunge", "poem", "poet", "point", "polar", "pole", "police", "pond", "pony", "pool", "popular", "portion", "position", "possible", "post", "potato", "pottery", "poverty", "powder", "power", "practice", "praise", "predict", "prefer", "prepare", "present", "pretty", "prevent", "price", "pride", "primary", "print", "priority", "prison", "private", "prize", "problem", "process", "produce", "profit", "program", "project", "promote", "proof", "property", "prosper", "protect", "proud", "provide", "public", "pudding", "pull", "pulp", "pulse", "pumpkin", "punch", "pupil", "puppy", "purchase", "purity", "purpose", "purse", "push", "put", "puzzle", "pyramid", "quality", "quantum", "quarter", "question", "quick", "quit", "quiz", "quote", "rabbit", "raccoon", "race", "rack", "radar", "radio", "rail", "rain", "raise", "rally", "ramp", "ranch", "random", "range", "rapid", "rare", "rate", "rather", "raven", "raw", "razor", "ready", "real", "reason", "rebel", "rebuild", "recall", "receive", "recipe", "record", "recycle", "reduce", "reflect", "reform", "refuse", "region", "regret", "regular", "reject", "relax", "release", "relief", "rely", "remain", "remember", "remind", "remove", "render", "renew", "rent", "reopen", "repair", "repeat", "replace", "report", "require", "rescue", "resemble", "resist", "resource", "response", "result", "retire", "retreat", "return", "reunion", "reveal", "review", "reward", "rhythm", "rib", "ribbon", "rice", "rich", "ride", "ridge", "rifle", "right", "rigid", "ring", "riot", "ripple", "risk", "ritual", "rival", "river", "road", "roast", "robot", "robust", "rocket", "romance", "roof", "rookie", "room", "rose", "rotate", "rough", "round", "route", "royal", "rubber", "rude", "rug", "rule", "run", "runway", "rural", "sad", "saddle", "sadness", "safe", "sail", "salad", "salmon", "salon", "salt", "salute", "same", "sample", "sand", "satisfy", "satoshi", "sauce", "sausage", "save", "say", "scale", "scan", "scare", "scatter", "scene", "scheme", "school", "science", "scissors", "scorpion", "scout", "scrap", "screen", "script", "scrub", "sea", "search", "season", "seat", "second", "secret", "section", "security", "seed", "seek", "segment", "select", "sell", "seminar", "senior", "sense", "sentence", "series", "service", "session", "settle", "setup", "seven", "shadow", "shaft", "shallow", "share", "shed", "shell", "sheriff", "shield", "shift", "shine", "ship", "shiver", "shock", "shoe", "shoot", "shop", "short", "shoulder", "shove", "shrimp", "shrug", "shuffle", "shy", "sibling", "sick", "side", "siege", "sight", "sign", "silent", "silk", "silly", "silver", "similar", "simple", "since", "sing", "siren", "sister", "situate", "six", "size", "skate", "sketch", "ski", "skill", "skin", "skirt", "skull", "slab", "slam", "sleep", "slender", "slice", "slide", "slight", "slim", "slogan", "slot", "slow", "slush", "small", "smart", "smile", "smoke", "smooth", "snack", "snake", "snap", "sniff", "snow", "soap", "soccer", "social", "sock", "soda", "soft", "solar", "soldier", "solid", "solution", "solve", "someone", "song", "soon", "sorry", "sort", "soul", "sound", "soup", "source", "south", "space", "spare", "spatial", "spawn", "speak", "special", "speed", "spell", "spend", "sphere", "spice", "spider", "spike", "spin", "spirit", "split", "spoil", "sponsor", "spoon", "sport", "spot", "spray", "spread", "spring", "spy", "square", "squeeze", "squirrel", "stable", "stadium", "staff", "stage", "stairs", "stamp", "stand", "start", "state", "stay", "steak", "steel", "stem", "step", "stereo", "stick", "still", "sting", "stock", "stomach", "stone", "stool", "story", "stove", "strategy", "street", "strike", "strong", "struggle", "student", "stuff", "stumble", "style", "subject", "submit", "subway", "success", "such", "sudden", "suffer", "sugar", "suggest", "suit", "summer", "sun", "sunny", "sunset", "super", "supply", "supreme", "sure", "surface", "surge", "surprise", "surround", "survey", "suspect", "sustain", "swallow", "swamp", "swap", "swarm", "swear", "sweet", "swift", "swim", "swing", "switch", "sword", "symbol", "symptom", "syrup", "system", "table", "tackle", "tag", "tail", "talent", "talk", "tank", "tape", "target", "task", "taste", "tattoo", "taxi", "teach", "team", "tell", "ten", "tenant", "tennis", "tent", "term", "test", "text", "thank", "that", "theme", "then", "theory", "there", "they", "thing", "this", "thought", "three", "thrive", "throw", "thumb", "thunder", "ticket", "tide", "tiger", "tilt", "timber", "time", "tiny", "tip", "tired", "tissue", "title", "toast", "tobacco", "today", "toddler", "toe", "together", "toilet", "token", "tomato", "tomorrow", "tone", "tongue", "tonight", "tool", "tooth", "top", "topic", "topple", "torch", "tornado", "tortoise", "toss", "total", "tourist", "toward", "tower", "town", "toy", "track", "trade", "traffic", "tragic", "train", "transfer", "trap", "trash", "travel", "tray", "treat", "tree", "trend", "trial", "tribe", "trick", "trigger", "trim", "trip", "trophy", "trouble", "truck", "true", "truly", "trumpet", "trust", "truth", "try", "tube", "tuition", "tumble", "tuna", "tunnel", "turkey", "turn", "turtle", "twelve", "twenty", "twice", "twin", "twist", "two", "type", "typical", "ugly", "umbrella", "unable", "unaware", "uncle", "uncover", "under", "undo", "unfair", "unfold", "unhappy", "uniform", "unique", "unit", "universe", "unknown", "unlock", "until", "unusual", "unveil", "update", "upgrade", "uphold", "upon", "upper", "upset", "urban", "urge", "usage", "use", "used", "useful", "useless", "usual", "utility", "vacant", "vacuum", "vague", "valid", "valley", "valve", "van", "vanish", "vapor", "various", "vast", "vault", "vehicle", "velvet", "vendor", "venture", "venue", "verb", "verify", "version", "very", "vessel", "veteran", "viable", "vibrant", "vicious", "victory", "video", "view", "village", "vintage", "violin", "virtual", "virus", "visa", "visit", "visual", "vital", "vivid", "vocal", "voice", "void", "volcano", "volume", "vote", "voyage", "wage", "wagon", "wait", "walk", "wall", "walnut", "want", "warfare", "warm", "warrior", "wash", "wasp", "waste", "water", "wave", "way", "wealth", "weapon", "wear", "weasel", "weather", "web", "wedding", "weekend", "weird", "welcome", "west", "wet", "whale", "what", "wheat", "wheel", "when", "where", "whip", "whisper", "wide", "width", "wife", "wild", "will", "win", "window", "wine", "wing", "wink", "winner", "winter", "wire", "wisdom", "wise", "wish", "witness", "wolf", "woman", "wonder", "wood", "wool", "word", "work", "world", "worry", "worth", "wrap", "wreck", "wrestle", "wrist", "write", "wrong", "yard", "year", "yellow", "you", "young", "youth", "zebra", "zero", "zone", "zoo"]

    ALPHABET = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z"]

    def __init__(self) -> None:
        View.__init__(self)

        # Gather words and seed display information
        self.words = []
        self.letters = []
        self.possible_alphabet = []
        self.possible_words = []
        self.selected_possible_words_index = 0
        self.seed_length = 12     # Default to 12, Valid values are 11, 12, 23 and 24
        self.seed_qr_image = None
        self.seed_entropy_image = None

        # Dice information
        self.roll_number = 1
        self.dice_selected = 0
        self.roll_data = ""
        self.dice_seed_phrase = []

        # Gather passphrase display information
        self.passphrase = ""
        self.pass_lower = "abcdefghijklmnopqrstuvwxyz"
        self.pass_upper = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        self.pass_number = "0123456789"
        self.pass_symbol = "!\"#$%&'()*+,=./;:<>?@[]|-_`~"
        self.pass_letter = ""
        self.pass_case_toggle = "lower"

    ###
    ### Display Gather Words Screen
    ###

    def display_manual_seed_entry(self, num_words):
        self.seed_length = num_words
        self.reset()

        cur_word = 1
        while len(self.words) < self.seed_length:
            initial_letters = ["a"]
            if len(self.words) >= cur_word:
                initial_letters = list(self.words[cur_word - 1])  # zero-indexed

            ret_val = self.draw_seed_word_keyboard_entry(num_word=cur_word, initial_letters=initial_letters)

            if ret_val == Keyboard.KEY_PREVIOUS_PAGE:
                # Reload previous word
                cur_word -= 1
                if cur_word == 0:
                    # Exit this UI
                    return []
                else:
                    # We've backed `cur_word` up, so re-enter loop
                    continue

            if len(self.words) < cur_word:
                self.words.append(ret_val.strip())
            else:
                self.words[cur_word - 1] = ret_val.strip()
            cur_word += 1

        return self.words


    def draw_seed_word_keyboard_entry(self, num_word, initial_letters=["a"]):
        def render_possible_matches(highlight_word=None):
            """ Internal helper method to render the KEY 1, 2, 3 word candidates.
                (has access to all vars in the parent's context)
            """
            # Clear the right panel
            View.draw.rectangle((keyboard_width, text_entry_display_height, View.canvas_width, View.canvas_height), fill="black")

            if not self.possible_words:
                return

            row_height = 26
            x = keyboard_width + 10
            y = text_entry_display_height - int(row_height / 2)

            highlighted_row = 3
            num_possible_rows = 11

            list_starting_index = self.selected_possible_words_index - highlighted_row

            word_font = View.ROBOTOCONDENSED_REGULAR_22
            for row, i in enumerate(range(list_starting_index, list_starting_index + num_possible_rows)):
                if i < 0:
                    # We're near the top of the list, not enough items to fill above the highlighted row
                    continue
                if row == highlighted_row:
                    # Leave the highlighted row to be rendered below
                    continue

                if len(self.possible_words) <= i:
                    break

                View.draw.text((x, y + row * row_height), self.possible_words[i], fill=View.color, font=word_font)

            # Render the SELECT outline
            if highlight_word:
                fill_color = View.color
                font_color = "black"
            else:
                fill_color = "#111"
                font_color = View.color
            View.draw.rounded_rectangle((keyboard_width + 4, y + (3 * row_height) - 2, 250, y + (4 * row_height) + 2), outline=View.color, fill=fill_color, radius=5, width=1)

            if self.possible_words:
                word_font = View.ROBOTOCONDENSED_BOLD_24
                View.draw.text((x, y + 3 * row_height), self.possible_words[self.selected_possible_words_index], fill=font_color, font=word_font)

            render_possible_matches_arrows()


        def render_possible_matches_arrows():
            # Render the up/down arrow buttons for KEY1 and KEY3
            row_height = 26
            arrow_button_width = 25
            arrow_padding = 5
            key_x = View.canvas_width - arrow_button_width
            key_y = text_entry_display_height - int(row_height / 2) + int(0.75 * row_height)
            background_color = "#111"
            arrow_color = View.color
            if arrow_up_is_active:
                background_color = View.color
                arrow_color = "#111"
            View.draw.rounded_rectangle((key_x, key_y, 250, key_y + row_height), outline=View.color, fill=background_color, radius=5, width=1)
            View.draw.polygon(
                [(key_x + int(arrow_button_width)/2 + 1, key_y + arrow_padding),  # centered top point
                (View.canvas_width - arrow_padding + 1, key_y + row_height - arrow_padding),  # bottom right point
                (key_x + arrow_padding + 1, key_y + row_height - arrow_padding)],  # bottom left point
                fill=arrow_color
            )

            background_color = "#111"
            arrow_color = View.color
            if arrow_down_is_active:
                background_color = View.color
                arrow_color = "#111"
            key_y = text_entry_display_height - int(row_height / 2) + int(5.25 * row_height)
            View.draw.rounded_rectangle((key_x, key_y, 250, key_y + row_height), outline=View.color, fill=background_color, radius=5, width=1)
            View.draw.polygon(
                [(key_x + int(arrow_button_width)/2 + 1, key_y + row_height - arrow_padding),  # bottom centered point
                (View.canvas_width - arrow_padding + 1, key_y + arrow_padding),  # right top point
                (key_x + arrow_padding + 1, key_y + arrow_padding)], # left top point
                fill=arrow_color
            )


        # Clear the screen
        View.draw.rectangle((0,0, View.canvas_width,View.canvas_height), fill="black")

        self.render_previous_button()
        previous_button_is_active = False
        arrow_up_is_active = False
        arrow_down_is_active = False

        # Have to ensure that we don't carry any effects from a previous run
        # TODO: This shouldn't be a member var
        self.possible_alphabet = "abcdefghijklmnopqrstuvwxyz"

        # Set up the keyboard params
        keyboard_width = 120
        text_entry_display_height = 39

        # TODO: support other BIP39 languages/charsets
        keyboard = Keyboard(View.draw,
                            charset=self.possible_alphabet,
                            rows=5,
                            cols=6,
                            rect=(0,text_entry_display_height + 1, keyboard_width,240),
                            auto_wrap=[Keyboard.WRAP_LEFT, Keyboard.WRAP_RIGHT])

        # Render the top text entry display
        self.letters = initial_letters
        text_entry_display = TextEntryDisplay(
            View.draw,
            rect=(self.previous_button_width,0, View.canvas_width,text_entry_display_height),
            font=View.ROBOTOCONDENSED_BOLD_26,
            font_color=View.color,
            cur_text=f"{num_word}: " + "".join(self.letters)
        )
        text_entry_display.render()

        # Initialize the current matches
        self.possible_words = []
        if len(self.letters) > 1:
            self.letters.append(" ")    # "Lock in" the last letter as if KEY_PRESS
            self.calc_possible_alphabet()
            keyboard.update_active_keys(active_keys=self.possible_alphabet)
            keyboard.set_selected_key(selected_letter=self.letters[-2])
        else:
            keyboard.set_selected_key(selected_letter=self.letters[-1])
        keyboard.render_keys()
        render_possible_matches()

        View.DispShowImage()

        # Start the interactive update loop
        while True:
            input = View.buttons.wait_for(
                [B.KEY_UP, B.KEY_DOWN, B.KEY_RIGHT, B.KEY_LEFT, B.KEY_PRESS, B.KEY1, B.KEY2, B.KEY3],
                check_release=True,
                release_keys=[B.KEY_PRESS, B.KEY2]
            )

            if previous_button_is_active:
                if input == B.KEY_PRESS:
                    # User clicked the "back" arrow
                    return Keyboard.KEY_PREVIOUS_PAGE
                elif input == B.KEY_UP:
                    input = Keyboard.ENTER_BOTTOM
                    # Re-render it without the highlight
                    previous_button_is_active = False
                    self.render_previous_button()

                elif input == B.KEY_DOWN:
                    input = Keyboard.ENTER_TOP
                    # Re-render it without the highlight
                    previous_button_is_active = False
                    self.render_previous_button()

                elif input in [B.KEY_RIGHT, B.KEY_LEFT]:
                    # no action in this context
                    continue

            ret_val = keyboard.update_from_input(input)

            if ret_val in Keyboard.EXIT_DIRECTIONS:
                self.render_previous_button(highlight=True)
                previous_button_is_active = True

            elif ret_val in Keyboard.ADDITIONAL_KEYS:
                if input == B.KEY_PRESS and ret_val == Keyboard.KEY_BACKSPACE["code"]:
                    self.letters = self.letters[:-2]
                    self.letters.append(" ")

                    # Reactivate keys after deleting last letter
                    self.calc_possible_alphabet()
                    keyboard.update_active_keys(active_keys=self.possible_alphabet)
                    keyboard.render_keys()
                        
                    # Update the right-hand possible matches area
                    render_possible_matches()

                elif ret_val == Keyboard.KEY_BACKSPACE["code"]:
                    # We're just hovering over DEL but haven't clicked. Show blank (" ")
                    #   in the live text entry display at the top.
                    self.letters = self.letters[:-1]
                    self.letters.append(" ")

            # Has the user made a final selection of a candidate word?
            final_selection = None
            if input == B.KEY1 and self.possible_words:
                # Scroll the list up
                self.selected_possible_words_index -= 1
                if self.selected_possible_words_index < 0:
                    self.selected_possible_words_index = 0

                if not arrow_up_is_active:
                    # Flash the up arrow as selected
                    arrow_up_is_active = True

                # Update the right-hand possible matches area
                render_possible_matches()

            elif input == B.KEY2:
                if self.possible_words:
                    final_selection = self.possible_words[self.selected_possible_words_index]

            elif input == B.KEY3 and self.possible_words:
                # Scroll the list down
                self.selected_possible_words_index += 1
                if self.selected_possible_words_index >= len(self.possible_words):
                    self.selected_possible_words_index = len(self.possible_words) - 1

                if not arrow_down_is_active:
                    # Flash the down arrow as selected
                    arrow_down_is_active = True

                # Update the right-hand possible matches area
                render_possible_matches()

            if input is not B.KEY1 and arrow_up_is_active:
                # Deactivate the arrow and redraw
                arrow_up_is_active = False
                render_possible_matches_arrows()

            if input is not B.KEY3 and arrow_down_is_active:
                # Deactivate the arrow and redraw
                arrow_down_is_active = False
                render_possible_matches_arrows()

            if final_selection:
                # Animate the selection storage, then return the word to the caller
                self.letters = list(final_selection + " ")
                render_possible_matches(highlight_word=final_selection)
                text_entry_display.render(f"{num_word}: " + "".join(self.letters))
                View.DispShowImage()

                return final_selection

            elif input == B.KEY_PRESS and ret_val in self.possible_alphabet:
                # User has locked in the current letter
                if self.letters[-1] != " ":
                    # We'll save that locked in letter next but for now update the
                    # live text entry display with blank (" ") so that we don't try
                    # to autocalc matches against a second copy of the letter they
                    # just selected. e.g. They KEY_PRESS on "s" to build "mus". If
                    # we advance the live block cursor AND display "s" in it, the
                    # current word would then be "muss" with no matches. If "mus"
                    # can get us to our match, we don't want it to disappear right
                    # as we KEY_PRESS.
                    self.letters.append(" ")
                else:
                    # clicked same letter twice in a row. Because of the above, an
                    # immediate second click of the same letter would lock in "ap "
                    # (note the space) instead of "app". So we replace that trailing
                    # space with the correct repeated letter and then, as above,
                    # append a trailing blank.
                    self.letters = self.letters[:-1]
                    self.letters.append(ret_val)
                    self.letters.append(" ")

                # Recalc and deactivate keys after advancing
                self.calc_possible_alphabet()
                keyboard.update_active_keys(active_keys=self.possible_alphabet)
                    
                # Update the right-hand possible matches area
                render_possible_matches()

                if len(self.possible_alphabet) == 1:
                    # If there's only one possible letter left, select it
                    keyboard.set_selected_key(self.possible_alphabet[0])

                keyboard.render_keys()

            elif input in [B.KEY_RIGHT, B.KEY_LEFT, B.KEY_UP, B.KEY_DOWN] and ret_val in self.possible_alphabet:
                # Live joystick movement; haven't locked this new letter in yet.
                # Replace the last letter w/the currently selected one. But don't
                # call `calc_possible_alphabet()` because we want to still be able
                # to freely float to a different letter; only update the active
                # keyboard keys when a selection has been locked in (KEY_PRESS) or
                # removed ("del").
                self.letters = self.letters[:-1]
                self.letters.append(ret_val)
                self.calc_possible_words()  # live update our matches as we move

                # Update the right-hand possible matches area
                render_possible_matches()

            # Render the text entry display and cursor block
            text_entry_display.render(f"{num_word}: " + "".join(self.letters))

            View.DispShowImage()


    def draw_passphrase_keyboard_entry(self, existing_passphrase = ""):
        def render_right_panel(button1_text="ABC", button2_text="123"):
            # Render the up/down arrow buttons for KEY1 and KEY3
            row_height = 28
            right_button_left_margin = 10
            right_button_width = right_panel_buttons_width - right_button_left_margin
            font_padding_right = 2
            font_padding_top = 1
            key_x = View.canvas_width - right_button_width
            key_y = int(View.canvas_height - row_height) / 2 - 1 - 60

            background_color = "#111"
            font_color = View.color
            font = View.ROBOTOCONDENSED_BOLD_24
            tw, th = font.getsize(button1_text)
            if button1_is_active:
                background_color = View.color
                font_color = "#111"
            View.draw.rounded_rectangle((key_x, key_y, 250, key_y + row_height), outline=View.color, fill=background_color, radius=5, width=1)
            View.draw.text((View.canvas_width - tw - font_padding_right, key_y + font_padding_top), font=font, text=button1_text, fill=font_color)

            background_color = "#111"
            font_color = View.color
            tw, th = font.getsize(button2_text)
            if button2_is_active:
                background_color = View.color
                font_color = "#111"
            key_y = int(View.canvas_height - row_height) / 2 - 1
            View.draw.rounded_rectangle((key_x, key_y, 250, key_y + row_height), outline=View.color, fill=background_color, radius=5, width=1)
            View.draw.text((View.canvas_width - tw - font_padding_right, key_y + font_padding_top), font=font, text=button2_text, fill=font_color)

            background_color = "#111"
            font_color = View.color
            button3_text = "Save"
            tw, th = font.getsize(button3_text)
            if button3_is_active:
                background_color = View.color
                font_color = "#111"
            key_y = int(View.canvas_height - row_height) / 2 - 1 + 60
            View.draw.rounded_rectangle((key_x, key_y, 250, key_y + row_height), outline=View.color, fill=background_color, radius=5, width=1)
            View.draw.text((View.canvas_width - tw - font_padding_right, key_y + font_padding_top), font=font, text=button3_text, fill=font_color)

        # Clear the screen
        View.draw.rectangle((0,0, View.canvas_width,View.canvas_height), fill="black")

        self.render_previous_button()
        previous_button_is_active = False

        # Have to ensure that we don't carry any effects from a previous run
        # TODO: This shouldn't be a member var
        if existing_passphrase:
            self.passphrase = existing_passphrase
        else:
            self.passphrase = ""

        # Set up the keyboard params
        right_panel_buttons_width = 60

        # render top title banner
        font = View.ROBOTOCONDENSED_REGULAR_20
        title = "Enter Passphrase"
        title_top_padding = 0
        title_bottom_padding = 10
        tw, th = font.getsize(title)
        View.draw.text((int(View.canvas_width - tw) / 2, title_top_padding), text=title, font=font, fill=View.color)
        title_height = th + title_top_padding + title_bottom_padding

        # Render the live text entry display
        font = View.ROBOTOCONDENSED_REGULAR_28
        tw, th = font.getsize("!\"#$%&'()*+,=./;:<>?@[]|-_`~ ABCDEFGHIJKLMNOPQRSTUVWXYZ abcdefghijklmnopqrstuvwxyz 1234567890")  # All possible chars for max range
        text_entry_side_padding = 0
        text_entry_top_padding = 1
        text_entry_bottom_padding = 10
        text_entry_top_y = title_height + text_entry_top_padding
        text_entry_bottom_y = text_entry_top_y + 3 + th + 3
        text_entry_display = TextEntryDisplay(
            View.draw,
            rect=(text_entry_side_padding,text_entry_top_y, View.canvas_width - right_panel_buttons_width - 1, text_entry_bottom_y),
            font=font,
            font_color=View.color,
            cursor_mode=TextEntryDisplay.CURSOR_MODE__BAR,
            is_centered=False,
            has_outline=True,
            cur_text=''.join(self.passphrase)
        )
        text_entry_display.render()
        cursor_position = len(self.passphrase)

        keyboard_start_y = text_entry_bottom_y + text_entry_bottom_padding
        keyboard_abc = Keyboard(
            View.draw,
            charset="".join(SeedToolsView.ALPHABET),
            rows=4,
            cols=9,
            rect=(0, keyboard_start_y, View.canvas_width - right_panel_buttons_width, View.canvas_height),
            additional_keys=[Keyboard.KEY_SPACE_5, Keyboard.KEY_CURSOR_LEFT, Keyboard.KEY_CURSOR_RIGHT, Keyboard.KEY_BACKSPACE],
            auto_wrap=[Keyboard.WRAP_LEFT, Keyboard.WRAP_RIGHT]
        )

        keyboard_ABC = Keyboard(
            View.draw,
            charset="".join(SeedToolsView.ALPHABET).upper(),
            rows=4,
            cols=9,
            rect=(0, keyboard_start_y, View.canvas_width - right_panel_buttons_width, View.canvas_height),
            additional_keys=[Keyboard.KEY_SPACE_5, Keyboard.KEY_CURSOR_LEFT, Keyboard.KEY_CURSOR_RIGHT, Keyboard.KEY_BACKSPACE],
            auto_wrap=[Keyboard.WRAP_LEFT, Keyboard.WRAP_RIGHT],
            render_now=False
        )

        keyboard_digits = Keyboard(
            View.draw,
            charset="1234567890",
            rows=3,
            cols=5,
            rect=(0, keyboard_start_y, View.canvas_width - right_panel_buttons_width, View.canvas_height),
            additional_keys=[Keyboard.KEY_CURSOR_LEFT, Keyboard.KEY_CURSOR_RIGHT, Keyboard.KEY_BACKSPACE],
            auto_wrap=[Keyboard.WRAP_LEFT, Keyboard.WRAP_RIGHT],
            render_now=False
        )

        keyboard_symbols = Keyboard(
            View.draw,
            charset="!@#$%^&*()-+_=[]{}\\|;:'\",.<>/?`~",
            rows=4,
            cols=10,
            rect=(0, keyboard_start_y, View.canvas_width - right_panel_buttons_width, View.canvas_height),
            additional_keys=[Keyboard.KEY_SPACE_4, Keyboard.KEY_CURSOR_LEFT, Keyboard.KEY_CURSOR_RIGHT, Keyboard.KEY_BACKSPACE],
            auto_wrap=[Keyboard.WRAP_LEFT, Keyboard.WRAP_RIGHT],
            render_now=False
        )

        button1_is_active = False
        button2_is_active = False
        button3_is_active = False
        KEYBOARD__LOWERCASE = 0
        KEYBOARD__UPPERCASE = 1
        KEYBOARD__DIGITS = 2
        KEYBOARD__SYMBOLS = 3
        KEYBOARD__LOWERCASE_BUTTON_TEXT = "abc"
        KEYBOARD__UPPERCASE_BUTTON_TEXT = "ABC"
        KEYBOARD__DIGITS_BUTTON_TEXT = "123"
        KEYBOARD__SYMBOLS_BUTTON_TEXT = "!@#"
        cur_keyboard = keyboard_abc
        cur_button1_text = KEYBOARD__UPPERCASE_BUTTON_TEXT
        cur_button2_text = KEYBOARD__DIGITS_BUTTON_TEXT
        render_right_panel()

        View.DispShowImage()

        # Start the interactive update loop
        while True:
            input = View.buttons.wait_for(
                [B.KEY_UP, B.KEY_DOWN, B.KEY_RIGHT, B.KEY_LEFT, B.KEY_PRESS, B.KEY1, B.KEY2, B.KEY3],
                check_release=True,
                release_keys=[B.KEY_PRESS, B.KEY1, B.KEY2, B.KEY3]
            )

            keyboard_swap = False

            # Check our two possible exit conditions
            if input == B.KEY3:
                # Save!
                if len(self.passphrase) > 0:
                    return self.passphrase.strip()

            elif input == B.KEY_PRESS and previous_button_is_active:
                # Prev button clicked; return empty string to signal cancel.
                return ""

            # Check for keyboard swaps
            if input == B.KEY1:
                # Return to the same button2 keyboard, if applicable
                if cur_keyboard == keyboard_digits:
                    cur_button2_text = KEYBOARD__DIGITS_BUTTON_TEXT
                elif cur_keyboard == keyboard_symbols:
                    cur_button2_text = KEYBOARD__SYMBOLS_BUTTON_TEXT

                if cur_button1_text == KEYBOARD__LOWERCASE_BUTTON_TEXT:
                    keyboard_abc.set_selected_key_indices(x=cur_keyboard.selected_key["x"], y=cur_keyboard.selected_key["y"])
                    cur_keyboard = keyboard_abc
                    cur_button1_text = KEYBOARD__UPPERCASE_BUTTON_TEXT
                    render_right_panel(button1_text=cur_button1_text, button2_text=cur_button2_text)
                else:
                    keyboard_ABC.set_selected_key_indices(x=cur_keyboard.selected_key["x"], y=cur_keyboard.selected_key["y"])
                    cur_keyboard = keyboard_ABC
                    cur_button1_text = KEYBOARD__LOWERCASE_BUTTON_TEXT
                    render_right_panel(button1_text=cur_button1_text, button2_text=cur_button2_text)
                cur_keyboard.render_keys()
                keyboard_swap = True
                ret_val = None

            elif input == B.KEY2:
                # Return to the same button1 keyboard, if applicable
                if cur_keyboard == keyboard_abc:
                    cur_button1_text = KEYBOARD__LOWERCASE_BUTTON_TEXT
                elif cur_keyboard == keyboard_ABC:
                    cur_button1_text = KEYBOARD__UPPERCASE_BUTTON_TEXT

                if cur_button2_text == KEYBOARD__DIGITS_BUTTON_TEXT:
                    keyboard_digits.set_selected_key_indices(x=cur_keyboard.selected_key["x"], y=cur_keyboard.selected_key["y"])
                    cur_keyboard = keyboard_digits
                    cur_keyboard.render_keys()
                    cur_button2_text = KEYBOARD__SYMBOLS_BUTTON_TEXT
                    render_right_panel(button1_text=cur_button1_text, button2_text=cur_button2_text)
                else:
                    keyboard_symbols.set_selected_key_indices(x=cur_keyboard.selected_key["x"], y=cur_keyboard.selected_key["y"])
                    cur_keyboard = keyboard_symbols
                    cur_keyboard.render_keys()
                    cur_button2_text = KEYBOARD__DIGITS_BUTTON_TEXT
                    render_right_panel(button1_text=cur_button1_text, button2_text=cur_button2_text)
                cur_keyboard.render_keys()
                keyboard_swap = True
                ret_val = None

            else:
                # Process normal input
                if input in [B.KEY_UP, B.KEY_DOWN] and previous_button_is_active:
                    # We're navigating off the previous button
                    previous_button_is_active = False
                    self.render_previous_button(highlight=False)

                    # Override the actual input w/an ENTER signal for the Keyboard
                    if input == B.KEY_DOWN:
                        input = Keyboard.ENTER_TOP
                    else:
                        input = Keyboard.ENTER_BOTTOM
                elif input in [B.KEY_LEFT, B.KEY_RIGHT] and previous_button_is_active:
                    # ignore
                    continue

                ret_val = cur_keyboard.update_from_input(input)

            # Now process the result from the keyboard
            if ret_val in Keyboard.EXIT_DIRECTIONS:
                self.render_previous_button(highlight=True)
                previous_button_is_active = True

            elif ret_val in Keyboard.ADDITIONAL_KEYS and input == B.KEY_PRESS:
                if ret_val == Keyboard.KEY_BACKSPACE["code"]:
                    if cursor_position == 0:
                        pass
                    elif cursor_position == len(self.passphrase):
                        self.passphrase = self.passphrase[:-1]
                    else:
                        self.passphrase = self.passphrase[:cursor_position - 1] + self.passphrase[cursor_position:]

                    cursor_position -= 1

                elif ret_val == Keyboard.KEY_CURSOR_LEFT["code"]:
                    cursor_position -= 1
                    if cursor_position < 0:
                        cursor_position = 0

                elif ret_val == Keyboard.KEY_CURSOR_RIGHT["code"]:
                    cursor_position += 1
                    if cursor_position > len(self.passphrase):
                        cursor_position = len(self.passphrase)

                elif ret_val == Keyboard.KEY_SPACE["code"]:
                    if cursor_position == len(self.passphrase):
                        self.passphrase += " "
                    else:
                        self.passphrase = self.passphrase[:cursor_position] + " " + self.passphrase[cursor_position:]
                    cursor_position += 1

                # Update the text entry display and cursor
                text_entry_display.render(self.passphrase, cursor_position)

            elif input == B.KEY_PRESS and ret_val not in Keyboard.ADDITIONAL_KEYS:
                # User has locked in the current letter
                if cursor_position == len(self.passphrase):
                    self.passphrase += ret_val
                else:
                    self.passphrase = self.passphrase[:cursor_position] + ret_val + self.passphrase[cursor_position:]
                cursor_position += 1

                # Update the text entry display and cursor
                text_entry_display.render(self.passphrase, cursor_position)

            elif input in [B.KEY_RIGHT, B.KEY_LEFT, B.KEY_UP, B.KEY_DOWN] or keyboard_swap:
                # Live joystick movement; haven't locked this new letter in yet.
                # Leave current spot blank for now. Only update the active keyboard keys
                # when a selection has been locked in (KEY_PRESS) or removed ("del").
                pass

            View.DispShowImage()

    ###
    ### Display Last Word
    ###

    def display_last_word(self, partial_seed_phrase) -> list:
        finalseed = mnemonic_generation.calculate_checksum(partial_seed_phrase)
        last_word = finalseed[-1]

        self.draw.rectangle((0, 0, View.canvas_width, View.canvas_height), outline=0, fill=0)
        tw, th = self.draw.textsize("The final word is :", font=View.IMPACT23)
        self.draw.text(((240 - tw) / 2, 60), "The final word is :", fill=View.color, font=View.IMPACT23)
        tw, th = self.draw.textsize(last_word, font=View.IMPACT50)
        self.draw.text(((240 - tw) / 2, 90), last_word, fill=View.color, font=View.IMPACT50)

        tw, th = View.draw.textsize("Right to Continue", font=View.IMPACT18)
        View.draw.text(((240 - tw) / 2, 210), "Right to Continue", fill=View.color, font=View.IMPACT18)

        View.DispShowImage()

        input = self.buttons.wait_for([B.KEY_RIGHT])
        return finalseed

    ###
    ### Display Seed from Dice
    ###

    def display_generate_seed_from_dice(self):
        self.roll_number = 1
        self.dice_selected = 5
        self.roll_data = ""

        self.draw_dice(self.dice_selected)
        time.sleep(1) # pause for 1 second before accepting input

        # Wait for Button Input (specifically menu selection/press)
        while True:
            input = self.buttons.wait_for([B.KEY_UP, B.KEY_DOWN, B.KEY_PRESS, B.KEY_RIGHT, B.KEY_LEFT])
            if input == B.KEY_UP:
                ret_val = self.dice_arrow_up()
            elif input == B.KEY_DOWN:
                ret_val = self.dice_arrow_down()
            elif input == B.KEY_RIGHT:
                ret_val = self.dice_arrow_right()
            elif input == B.KEY_LEFT:
                ret_val = self.dice_arrow_left()
            elif input == B.KEY_PRESS:
                ret_val = self.dice_arrow_press()

            if ret_val == False:
                return []

            if self.roll_number >= 100:
                self.dice_seed_phrase = mnemonic_generation.generate_mnemonic_from_dice(self.roll_data)
                return self.dice_seed_phrase[:]

    def dice_arrow_up(self):
        new_selection = 0
        if self.dice_selected == 4:
            new_selection = 1
        elif self.dice_selected == 5:
            new_selection = 2
        elif self.dice_selected == 6:
            new_selection = 3

        if self.dice_selected != new_selection and new_selection != 0:
            self.draw_dice(new_selection)

        return True

    def dice_arrow_down(self):
        new_selection = 0
        if self.dice_selected == 1:
            new_selection = 4
        elif self.dice_selected == 2:
            new_selection = 5
        elif self.dice_selected == 3:
            new_selection = 6

        if self.dice_selected != new_selection and new_selection != 0:
            self.draw_dice(new_selection)

        return True

    def dice_arrow_right(self):
        new_selection = 0
        if self.dice_selected == 1:
            new_selection = 2
        elif self.dice_selected == 2:
            new_selection = 3
        elif self.dice_selected == 4:
            new_selection = 5
        elif self.dice_selected == 5:
            new_selection = 6

        if self.dice_selected != new_selection and new_selection != 0:
            self.draw_dice(new_selection)

        return True

    def dice_arrow_left(self):
        if self.dice_selected == 1:
            self.draw_prompt_custom("Undo ", "Cancel ", "Exit ", ["Action:  ", "", ""])
            input = self.buttons.wait_for([B.KEY1, B.KEY2, B.KEY3])
            if input == B.KEY1: #Undo
                self.roll_number = self.roll_number - 1
                self.roll_data = self.roll_data[:-1] # remove last character from string
                if self.roll_number >= 1:
                    self.draw_dice(self.dice_selected)
                    return True
                else:
                    return False
            elif input == B.KEY2: # Cancel
                self.draw_dice(self.dice_selected)
                return True
            elif input == B.KEY3: # Exit
                return False

        new_selection = 0
        if self.dice_selected == 3:
            new_selection = 2
        elif self.dice_selected == 2:
            new_selection = 1
        elif self.dice_selected == 6:
            new_selection = 5
        elif self.dice_selected == 5:
            new_selection = 4

        if self.dice_selected != new_selection and new_selection != 0:
            self.draw_dice(new_selection)

        return True

    def dice_arrow_press(self):
        self.roll_number += 1
        if self.dice_selected == 6:
            self.roll_data += "0"
        else:
            self.roll_data += str(self.dice_selected)

        # Reset for the next UI render
        self.dice_selected = 5
        if self.roll_number < 100:
            self.draw_dice(self.dice_selected)

        return True

    def draw_dice(self, dice_selected):

        self.draw.rectangle((0, 0, View.canvas_width, View.canvas_height), outline=0, fill=0)
        self.draw.text((45, 5), "Dice roll: " + str(self.roll_number) + "/99", fill=View.color, font=View.IMPACT26)

        # when dice is selected, rect fill will be orange and ellipse will be black, ellipse outline will be the black
        # when dice is not selected, rect will will be black and ellipse will be orange, ellipse outline will be orange

        # dice 1
        if dice_selected == 1:
            self.draw.rectangle((5, 50, 75, 120),   outline=View.color, fill=View.color)
            self.draw.ellipse([(34, 79), (46, 91)], outline="BLACK",  fill="BLACK")
        else:
            self.draw.rectangle((5, 50, 75, 120),   outline=View.color, fill="BLACK")
            self.draw.ellipse([(34, 79), (46, 91)], outline=View.color, fill=View.color)

        # dice 2
        if dice_selected == 2:
            self.draw.rectangle((85, 50, 155, 120), outline=View.color, fill=View.color)
            self.draw.ellipse([(100, 60), (112, 72)], outline="BLACK", fill="BLACK")
            self.draw.ellipse([(128, 98), (140, 110)], outline="BLACK", fill="BLACK")
        else:
            self.draw.rectangle((85, 50, 155, 120), outline=View.color, fill="BLACK")
            self.draw.ellipse([(100, 60), (112, 72)], outline=View.color, fill=View.color)
            self.draw.ellipse([(128, 98), (140, 110)], outline=View.color, fill=View.color)

        # dice 3
        if dice_selected == 3:
            self.draw.rectangle((165, 50, 235, 120), outline=View.color, fill=View.color)
            self.draw.ellipse([(180, 60), (192, 72)], outline="BLACK", fill="BLACK")
            self.draw.ellipse([(194, 79), (206, 91)], outline="BLACK", fill="BLACK")
            self.draw.ellipse([(208, 98), (220, 110)], outline="BLACK", fill="BLACK")
        else:
            self.draw.rectangle((165, 50, 235, 120), outline=View.color, fill="BLACK")
            self.draw.ellipse([(180, 60), (192, 72)], outline=View.color, fill=View.color)
            self.draw.ellipse([(194, 79), (206, 91)], outline=View.color, fill=View.color)
            self.draw.ellipse([(208, 98), (220, 110)], outline=View.color, fill=View.color)

        # dice 4
        if dice_selected == 4:
            self.draw.rectangle((5, 130, 75, 200), outline=View.color, fill=View.color)
            self.draw.ellipse([(20, 140), (32, 152)], outline="BLACK", fill="BLACK")
            self.draw.ellipse([(20, 174), (32, 186)], outline="BLACK", fill="BLACK")
            self.draw.ellipse([(48, 140), (60, 152)], outline="BLACK", fill="BLACK")
            self.draw.ellipse([(48, 174), (60, 186)], outline="BLACK", fill="BLACK")
        else:
            self.draw.rectangle((5, 130, 75, 200), outline=View.color, fill="BLACK")
            self.draw.ellipse([(20, 140), (32, 152)], outline=View.color, fill=View.color)
            self.draw.ellipse([(20, 174), (32, 186)], outline=View.color, fill=View.color)
            self.draw.ellipse([(48, 140), (60, 152)], outline=View.color, fill=View.color)
            self.draw.ellipse([(48, 174), (60, 186)], outline=View.color, fill=View.color)

        # dice 5
        if dice_selected == 5:
            self.draw.rectangle((85, 130, 155, 200), outline=View.color, fill=View.color)
            self.draw.ellipse([(100, 140), (112, 152)], outline="BLACK", fill="BLACK")
            self.draw.ellipse([(100, 178), (112, 190)], outline="BLACK", fill="BLACK")
            self.draw.ellipse([(114, 159), (126, 171)], outline="BLACK", fill="BLACK")
            self.draw.ellipse([(128, 140), (140, 152)], outline="BLACK", fill="BLACK")
            self.draw.ellipse([(128, 178), (140, 190)], outline="BLACK", fill="BLACK")
        else:
            self.draw.rectangle((85, 130, 155, 200), outline=View.color, fill="BLACK")
            self.draw.ellipse([(100, 140), (112, 152)], outline=View.color, fill=View.color)
            self.draw.ellipse([(100, 178), (112, 190)], outline=View.color, fill=View.color)
            self.draw.ellipse([(114, 159), (126, 171)], outline=View.color, fill=View.color)
            self.draw.ellipse([(128, 140), (140, 152)], outline=View.color, fill=View.color)
            self.draw.ellipse([(128, 178), (140, 190)], outline=View.color, fill=View.color)

        # dice 6
        if dice_selected == 6:
            self.draw.rectangle((165, 130, 235, 200), outline=View.color, fill=View.color)
            self.draw.ellipse([(180, 140), (192, 152)], outline="BLACK", fill="BLACK")
            self.draw.ellipse([(180, 157), (192, 169)], outline="BLACK", fill="BLACK")
            self.draw.ellipse([(180, 174), (192, 186)], outline="BLACK", fill="BLACK")
            self.draw.ellipse([(208, 140), (220, 152)], outline="BLACK", fill="BLACK")
            self.draw.ellipse([(208, 157), (220, 169)], outline="BLACK", fill="BLACK")
            self.draw.ellipse([(208, 174), (220, 186)], outline="BLACK", fill="BLACK")
        else:
            self.draw.rectangle((165, 130, 235, 200), outline=View.color, fill="BLACK")
            self.draw.ellipse([(180, 140), (192, 152)], outline=View.color, fill=View.color)
            self.draw.ellipse([(180, 157), (192, 169)], outline=View.color, fill=View.color)
            self.draw.ellipse([(180, 174), (192, 186)], outline=View.color, fill=View.color)
            self.draw.ellipse([(208, 140), (220, 152)], outline=View.color, fill=View.color)
            self.draw.ellipse([(208, 157), (220, 169)], outline=View.color, fill=View.color)
            self.draw.ellipse([(208, 174), (220, 186)], outline=View.color, fill=View.color)

        # bottom text
        self.draw.text((18, 210), "Press Control Stick to Select", fill=View.color, font=View.IMPACT18)
        View.DispShowImage()

        self.dice_selected = dice_selected

    ###
    ### Display Seed Phrase
    ###

    def display_seed_phrase(self, seed_phrase, passphrase=None, bottom="Right to Main Menu", show_qr_option=False) -> bool:
        ret_val = ""

        def display_seed_phrase_page(draw, seed_phrase, passphrase=None, bottom=bottom, page_num=1):
            """ Internal helper method to render 12 words of the seed phrase """
            draw.rectangle((0, 0, View.canvas_width, View.canvas_height), outline=0, fill=0)

            word_positions = [
                # Left column
                (2, 40),     (2, 63),   (2, 86),   (2, 109),   (2, 132),   (2, 155),
                # Right column
                (120, 40), (120, 63), (120, 86), (120, 109), (120, 132), (120, 155)
            ]

            title = "Seed Phrase"
            word_index_offset = 0
            max_range = len(seed_phrase)    # handles 11 or 12; 23 or 24
            if len(seed_phrase) > 12:
                max_range -= 12  # we'll iterate up to max_range words on this page
                if page_num == 1:
                    title = "Seed Phrase (1/2)"
                    bottom = "Right to Page 2"
                else:
                    title = "Seed Phrase (2/2)"
                    word_index_offset = 12  # Skip ahead one page worth of words

            tw, th = View.draw.textsize(title, font=View.IMPACT18)
            draw.text(((240 - tw) / 2, 2), title, fill=View.color, font=View.IMPACT18)

            for i in range(0, max_range):
                draw.text(word_positions[i], f"{i + 1 + word_index_offset}: " + seed_phrase[i + word_index_offset] , fill=View.color, font=View.IMPACT22)

            if passphrase and ((len(seed_phrase) > 12 and page_num == 2) or (len(seed_phrase) <= 12 and page_num == 1)):
                disp_passphrase = "Passphrase: ************"
                tw, th = View.draw.textsize(disp_passphrase, font=View.IMPACT18)
                draw.text(((240 - tw) / 2, 185), disp_passphrase, fill=View.color, font=View.IMPACT18)

            tw, th = View.draw.textsize(bottom, font=View.IMPACT18)
            draw.text(((240 - tw) / 2, 212), bottom, fill=View.color, font=View.IMPACT18)
            View.DispShowImage()


        wait_for_buttons = [B.KEY_RIGHT, B.KEY_LEFT]
        if show_qr_option:
            # In this context there's no next step; just display seed phrase and
            #   offer to show it as a human-transcribable QR.
            bottom = "Click to Exit; Right for QR Export"
            wait_for_buttons.append(B.KEY_PRESS)

        cur_page = 1
        while True:
            if len(seed_phrase) in (11,12):
                display_seed_phrase_page(self.draw, seed_phrase, passphrase, bottom)
                ret_val = self.buttons.wait_for(wait_for_buttons)

                if ret_val == B.KEY_LEFT:
                    # "Cancel" in contexts that support it / no-op otherwise
                    return False

                elif show_qr_option and ret_val == B.KEY_RIGHT:
                    # Show the resulting seed as a transcribable QR code
                    self.seed_phrase_as_qr(seed_phrase)

                    # Signal success to move forward
                    return True

                elif ret_val == B.KEY_RIGHT or (show_qr_option and ret_val == B.KEY_PRESS):
                    # Signal success to move forward
                    return True

            elif len(seed_phrase) in (23,24):
                display_seed_phrase_page(self.draw, seed_phrase, passphrase, bottom, page_num=cur_page)
                ret_val = self.buttons.wait_for(wait_for_buttons)

                if cur_page == 1:
                    if ret_val == B.KEY_LEFT:
                        # "Cancel" in contexts that support it / no-op otherwise
                        return False

                    elif ret_val == B.KEY_RIGHT:
                        cur_page = 2  # advance to second screen

                else:
                    if ret_val == B.KEY_LEFT:
                        cur_page = 1  # second screen back to first screen

                    elif show_qr_option and ret_val == B.KEY_RIGHT:
                        # Show the resulting seed as a transcribable QR code
                        self.seed_phrase_as_qr(seed_phrase)

                        # Signal success to move forward
                        return True

                    elif ret_val == B.KEY_RIGHT or (show_qr_option and ret_val == B.KEY_PRESS):
                        # Signal success to move forward
                        return True
            else:
                return True


    def seed_phrase_as_qr(self, seed_phrase):
        e = EncodeQR(seed_phrase=seed_phrase, qr_type=QRType.SEEDSSQR)
        image = e.nextPartImage(240, 240, 3)
        View.DispShowImageWithText(image, "click to zoom, right to exit", font=View.IMPACT18, text_color="BLACK", text_background="ORANGE")

        input = self.buttons.wait_for([B.KEY_RIGHT, B.KEY_PRESS])
        if input == B.KEY_RIGHT:
            return

        elif input == B.KEY_PRESS:
            # Render an oversized QR code that we can view up close
            pixels_per_block = 24
            qr_border = 4
            width = (qr_border + 25 + qr_border) * pixels_per_block
            height = width
            if len(seed_phrase) == 24:
                width = (qr_border + 29 + qr_border) * pixels_per_block
                height = width
            data = e.nextPart()
            qr = QR()
            image = qr.qrimage(data, width=width, height=height, border=qr_border).convert("RGBA")

            # Render gridlines but leave the 1-block border as-is
            draw = ImageDraw.Draw(image)
            for i in range(qr_border, math.floor(width/pixels_per_block) - qr_border):
                draw.line((i * pixels_per_block, qr_border * pixels_per_block, i * pixels_per_block, height - qr_border * pixels_per_block), fill="#bbb")
                draw.line((qr_border * pixels_per_block, i * pixels_per_block, width - qr_border * pixels_per_block, i * pixels_per_block), fill="#bbb")

            # Prep the semi-transparent mask overlay
            # make a blank image for the overlay, initialized to transparent
            block_mask = Image.new("RGBA", (View.canvas_width, View.canvas_height), (255,255,255,0))
            draw = ImageDraw.Draw(block_mask)

            mask_width = int((View.canvas_width - 5 * pixels_per_block)/2)
            mask_height = int((View.canvas_height - 5 * pixels_per_block)/2)
            mask_rgba = (0, 0, 0, 226)
            draw.rectangle((0, 0, View.canvas_width, mask_height), fill=mask_rgba)
            draw.rectangle((0, View.canvas_height - mask_height - 1, View.canvas_width, View.canvas_height), fill=mask_rgba)
            draw.rectangle((0, mask_height, mask_width, View.canvas_height - mask_height), fill=mask_rgba)
            draw.rectangle((View.canvas_width - mask_width - 1, mask_height, View.canvas_width, View.canvas_height - mask_height), fill=mask_rgba)

            # Draw a box around the cutout portion of the mask for better visibility
            draw.line((mask_width, mask_height, mask_width, View.canvas_height - mask_height), fill=View.color)
            draw.line((View.canvas_width - mask_width, mask_height, View.canvas_width - mask_width, View.canvas_height - mask_height), fill=View.color)
            draw.line((mask_width, mask_height, View.canvas_width - mask_width, mask_height), fill=View.color)
            draw.line((mask_width, View.canvas_height - mask_height, View.canvas_width - mask_width, View.canvas_height - mask_height), fill=View.color)

            msg = "click to exit"
            tw, th = draw.textsize(msg, font=View.IMPACT18)
            draw.text(((View.canvas_width - tw) / 2, View.canvas_height - th - 2), msg, fill=View.color, font=View.IMPACT18)

            def draw_block_labels(cur_block_x, cur_block_y):
                # Create overlay for block labels (e.g. "D-5")
                block_labels_x = ["1", "2", "3", "4", "5", "6"]
                block_labels_y = ["A", "B", "C", "D", "E", "F"]

                block_labels = Image.new("RGBA", (View.canvas_width, View.canvas_height), (255,255,255,0))
                draw = ImageDraw.Draw(block_labels)
                draw.rectangle((mask_width, 0, View.canvas_width - mask_width, pixels_per_block), fill=View.color)
                draw.rectangle((0, mask_height, pixels_per_block, View.canvas_height - mask_height), fill=View.color)

                label_font = View.COURIERNEW24
                x_label = block_labels_x[cur_block_x]
                tw, th = draw.textsize(x_label, font=label_font)
                draw.text(((View.canvas_width - tw) / 2, (pixels_per_block - th) / 2), x_label, fill="BLACK", font=label_font)

                y_label = block_labels_y[cur_block_y]
                tw, th = draw.textsize(y_label, font=label_font)
                draw.text(((pixels_per_block - tw) / 2, (View.canvas_height - th) / 2), y_label, fill="BLACK", font=label_font)

                return block_labels

            block_labels = draw_block_labels(0, 0)

            # Track our current coordinates for the upper left corner of our view
            cur_block_x = 0
            cur_block_y = 0
            cur_x = qr_border * pixels_per_block - mask_width
            cur_y = qr_border * pixels_per_block - mask_height
            next_x = cur_x
            next_y = cur_y

            View.DispShowImage(
                image.crop((cur_x, cur_y, cur_x + View.canvas_width, cur_y + View.canvas_height)),
                alpha_overlay=Image.alpha_composite(block_mask, block_labels)
            )

            while True:
                # View.draw_text_over_image("click to exit", font=View.IMPACT18, text_color="BLACK", text_background="ORANGE")

                input = self.buttons.wait_for([B.KEY_RIGHT, B.KEY_LEFT, B.KEY_UP, B.KEY_DOWN, B.KEY_PRESS])
                if input == B.KEY_RIGHT:
                    next_x = cur_x + 5 * pixels_per_block
                    cur_block_x += 1
                    if next_x > width - View.canvas_width:
                        next_x = cur_x
                        cur_block_x -= 1
                elif input == B.KEY_LEFT:
                    next_x = cur_x - 5 * pixels_per_block
                    cur_block_x -= 1
                    if next_x < 0:
                        next_x = cur_x
                        cur_block_x += 1
                elif input == B.KEY_DOWN:
                    next_y = cur_y + 5 * pixels_per_block
                    cur_block_y += 1
                    if next_y > height - View.canvas_height:
                        next_y = cur_y
                        cur_block_y -= 1
                elif input == B.KEY_UP:
                    next_y = cur_y - 5 * pixels_per_block
                    cur_block_y -= 1
                    if next_y < 0:
                        next_y = cur_y
                        cur_block_y += 1
                elif input == B.KEY_PRESS:
                    return

                # Create overlay for block labels (e.g. "D-5")
                block_labels = draw_block_labels(cur_block_x, cur_block_y)

                if cur_x != next_x or cur_y != next_y:
                    View.disp_show_image_pan(
                        image,
                        cur_x, cur_y, next_x, next_y,
                        rate=pixels_per_block,
                        alpha_overlay=Image.alpha_composite(block_mask, block_labels)
                    )
                    cur_x = next_x
                    cur_y = next_y

    def read_seed_phrase_qr(self):
        self.draw_modal(["Scanning..."], "Seed QR" ,"Right to Exit")
        try:
            self.controller.camera.start_video_stream_mode(resolution=(480, 480), framerate=12, format="rgb")
            decoder = DecodeQR()
            while True:
                frame = self.controller.camera.read_video_stream(as_image=True)
                if frame is not None:
                    View.DispShowImageWithText(frame.resize((240,240)), "Scan Seed QR", font=View.IMPACT22, text_color=View.color, text_background=(0,0,0,225))
                    status = decoder.addImage(frame)

                    if status in (DecodeQRStatus.COMPLETE, DecodeQRStatus.INVALID):
                        break
                    
                    if self.buttons.check_for_low(B.KEY_RIGHT) or self.buttons.check_for_low(B.KEY_LEFT):
                        self.controller.camera.stop_video_stream_mode()
                        self.words = []
                        return self.words[:]

            if decoder.isComplete() and decoder.isSeed():
                self.words = decoder.getSeedPhrase()
            elif not decoder.isPSBT():
                self.draw_modal(["Not a valid Seed QR"], "", "Right to Exit")
                input = self.buttons.wait_for([B.KEY_RIGHT])
            else:
                self.draw_modal(["QR Parsing Failed"], "", "Right to Exit")
                input = self.buttons.wait_for([B.KEY_RIGHT])
                self.words = []

        finally:
            self.controller.camera.stop_video_stream_mode()

        return self.words[:]

    def seed_phrase_from_camera_image(self):
        reshoot = False

        self.controller.menu_view.draw_modal(["Initializing Camera..."])
        self.controller.camera.start_video_stream_mode(resolution=(240, 240), framerate=24, format="rgb")

        # save preview image frames to use as additional entropy below
        preview_images = []
        max_entropy_frames = 50

        while True:
            frame = self.controller.camera.read_video_stream(as_image=True)
            if frame is not None:
                View.DispShowImageWithText(frame, "click joystick", text_color=View.color, text_background=(0,0,0,225))
                if len(preview_images) < max_entropy_frames:
                    preview_images.append(frame)

            if self.buttons.check_for_low(B.KEY_LEFT):
                self.words = []
                self.controller.camera.stop_video_stream_mode()
                return (reshoot, self.words)

            elif self.buttons.check_for_low(B.KEY_PRESS):
                self.controller.camera.stop_video_stream_mode()
                break

        self.controller.camera.start_single_frame_mode(resolution=(720, 480))
        time.sleep(0.25)
        seed_entropy_image = self.controller.camera.capture_frame()
        self.controller.camera.stop_single_frame_mode()

        # Prep a copy of the image for display. The actual image data is 720x480
        # Present just a center crop and resize it to fit the screen and to keep some of
        #   the data hidden.
        display_version = autocontrast(
            seed_entropy_image,
            cutoff=2
        ).rotate(
            90
        ).crop(
            (120, 0, 600, 480)
        ).resize(
            (View.canvas_width, View.canvas_height), Image.BICUBIC
        )

        View.DispShowImageWithText(
            display_version,
            text=" < reshoot  |  accept > ",
            font=View.ROBOTOCONDENSED_REGULAR_22,
            text_color=View.color,
            text_background=(0,0,0,225)
        )

        input = self.buttons.wait_for([B.KEY_LEFT, B.KEY_RIGHT])
        if input == B.KEY_LEFT:
            reshoot = True

        else:
            # Build in some hardware-level uniqueness via CPU unique Serial num
            try:
                stream = os.popen("cat /proc/cpuinfo | grep Serial")
                output = stream.read()
                serial_num = output.split(":")[-1].strip().encode('utf-8')
                serial_hash = hashlib.sha256(serial_num)
                hash_bytes = serial_hash.digest()
            except Exception as e:
                print(repr(e))
                hash_bytes = b'0'

            # Build in modest entropy via millis since power on
            millis_hash = hashlib.sha256(hash_bytes + str(time.time()).encode('utf-8'))
            hash_bytes = millis_hash.digest()

            # Build in better entropy by chaining the preview frames
            for frame in preview_images:
                img_hash = hashlib.sha256(hash_bytes + frame.tobytes())
                hash_bytes = img_hash.digest()

            # Finally build in our headline entropy via the new full-res image
            final_hash = hashlib.sha256(hash_bytes + seed_entropy_image.tobytes())
            self.words = mnemonic_generation.generate_mnemonic_from_bytes(final_hash.digest())

            # Image should never get saved nor stick around in memory
            seed_entropy_image = None
            preview_images = None
            final_hash = None
            hash_bytes = None

        # self.buttons.trigger_override(True)
        return (reshoot, self.words)


    ###
    ### Utility Methods
    ###

    def reset(self):
        self.words.clear()
        self.possible_alphabet = SeedToolsView.ALPHABET[:]
        self.letters.clear()
        self.letters.append(self.possible_alphabet[0])
        self.possible_words.clear()
        self.passphrase = ""

        return


    def calc_possible_alphabet(self, new_letter = False):
        if (self.letters and len(self.letters) > 1 and new_letter == False) or (len(self.letters) > 0 and new_letter == True):
            search_letters = self.letters[:]
            if new_letter == False:
                search_letters.pop()
            self.calc_possible_words()
            letter_num = len(search_letters)
            possible_letters = []
            for word in self.possible_words:
                if len(word)-1 >= letter_num:
                    possible_letters.append(word[letter_num])
            # remove duplicates and keep order
            self.possible_alphabet = list(dict.fromkeys(possible_letters))[:]
        else:
            self.possible_alphabet = SeedToolsView.ALPHABET[:]
            self.possible_words = []


    def calc_possible_words(self):
        self.possible_words = [i for i in SeedToolsView.SEEDWORDS if i.startswith("".join(self.letters).strip())]
        self.selected_possible_words_index = 0        
