# External Dependencies
from embit.bip39 import mnemonic_to_bytes
from embit.bip39 import mnemonic_from_bytes
from embit import bip39
import time

# Internal file class dependencies
from view import View
from buttons import B

class SeedToolsView(View):

    SEEDWORDS = ["abandon", "ability", "able", "about", "above", "absent", "absorb", "abstract", "absurd", "abuse", "access", "accident", "account", "accuse", "achieve", "acid", "acoustic", "acquire", "across", "act", "action", "actor", "actress", "actual", "adapt", "add", "addict", "address", "adjust", "admit", "adult", "advance", "advice", "aerobic", "affair", "afford", "afraid", "again", "age", "agent", "agree", "ahead", "aim", "air", "airport", "aisle", "alarm", "album", "alcohol", "alert", "alien", "all", "alley", "allow", "almost", "alone", "alpha", "already", "also", "alter", "always", "amateur", "amazing", "among", "amount", "amused", "analyst", "anchor", "ancient", "anger", "angle", "angry", "animal", "ankle", "announce", "annual", "another", "answer", "antenna", "antique", "anxiety", "any", "apart", "apology", "appear", "apple", "approve", "april", "arch", "arctic", "area", "arena", "argue", "arm", "armed", "armor", "army", "around", "arrange", "arrest", "arrive", "arrow", "art", "artefact", "artist", "artwork", "ask", "aspect", "assault", "asset", "assist", "assume", "asthma", "athlete", "atom", "attack", "attend", "attitude", "attract", "auction", "audit", "august", "aunt", "author", "auto", "autumn", "average", "avocado", "avoid", "awake", "aware", "away", "awesome", "awful", "awkward", "axis", "baby", "bachelor", "bacon", "badge", "bag", "balance", "balcony", "ball", "bamboo", "banana", "banner", "bar", "barely", "bargain", "barrel", "base", "basic", "basket", "battle", "beach", "bean", "beauty", "because", "become", "beef", "before", "begin", "behave", "behind", "believe", "below", "belt", "bench", "benefit", "best", "betray", "better", "between", "beyond", "bicycle", "bid", "bike", "bind", "biology", "bird", "birth", "bitter", "black", "blade", "blame", "blanket", "blast", "bleak", "bless", "blind", "blood", "blossom", "blouse", "blue", "blur", "blush", "board", "boat", "body", "boil", "bomb", "bone", "bonus", "book", "boost", "border", "boring", "borrow", "boss", "bottom", "bounce", "box", "boy", "bracket", "brain", "brand", "brass", "brave", "bread", "breeze", "brick", "bridge", "brief", "bright", "bring", "brisk", "broccoli", "broken", "bronze", "broom", "brother", "brown", "brush", "bubble", "buddy", "budget", "buffalo", "build", "bulb", "bulk", "bullet", "bundle", "bunker", "burden", "burger", "burst", "bus", "business", "busy", "butter", "buyer", "buzz", "cabbage", "cabin", "cable", "cactus", "cage", "cake", "call", "calm", "camera", "camp", "can", "canal", "cancel", "candy", "cannon", "canoe", "canvas", "canyon", "capable", "capital", "captain", "car", "carbon", "card", "cargo", "carpet", "carry", "cart", "case", "cash", "casino", "castle", "casual", "cat", "catalog", "catch", "category", "cattle", "caught", "cause", "caution", "cave", "ceiling", "celery", "cement", "census", "century", "cereal", "certain", "chair", "chalk", "champion", "change", "chaos", "chapter", "charge", "chase", "chat", "cheap", "check", "cheese", "chef", "cherry", "chest", "chicken", "chief", "child", "chimney", "choice", "choose", "chronic", "chuckle", "chunk", "churn", "cigar", "cinnamon", "circle", "citizen", "city", "civil", "claim", "clap", "clarify", "claw", "clay", "clean", "clerk", "clever", "click", "client", "cliff", "climb", "clinic", "clip", "clock", "clog", "close", "cloth", "cloud", "clown", "club", "clump", "cluster", "clutch", "coach", "coast", "coconut", "code", "coffee", "coil", "coin", "collect", "color", "column", "combine", "come", "comfort", "comic", "common", "company", "concert", "conduct", "confirm", "congress", "connect", "consider", "control", "convince", "cook", "cool", "copper", "copy", "coral", "core", "corn", "correct", "cost", "cotton", "couch", "country", "couple", "course", "cousin", "cover", "coyote", "crack", "cradle", "craft", "cram", "crane", "crash", "crater", "crawl", "crazy", "cream", "credit", "creek", "crew", "cricket", "crime", "crisp", "critic", "crop", "cross", "crouch", "crowd", "crucial", "cruel", "cruise", "crumble", "crunch", "crush", "cry", "crystal", "cube", "culture", "cup", "cupboard", "curious", "current", "curtain", "curve", "cushion", "custom", "cute", "cycle", "dad", "damage", "damp", "dance", "danger", "daring", "dash", "daughter", "dawn", "day", "deal", "debate", "debris", "decade", "december", "decide", "decline", "decorate", "decrease", "deer", "defense", "define", "defy", "degree", "delay", "deliver", "demand", "demise", "denial", "dentist", "deny", "depart", "depend", "deposit", "depth", "deputy", "derive", "describe", "desert", "design", "desk", "despair", "destroy", "detail", "detect", "develop", "device", "devote", "diagram", "dial", "diamond", "diary", "dice", "diesel", "diet", "differ", "digital", "dignity", "dilemma", "dinner", "dinosaur", "direct", "dirt", "disagree", "discover", "disease", "dish", "dismiss", "disorder", "display", "distance", "divert", "divide", "divorce", "dizzy", "doctor", "document", "dog", "doll", "dolphin", "domain", "donate", "donkey", "donor", "door", "dose", "double", "dove", "draft", "dragon", "drama", "drastic", "draw", "dream", "dress", "drift", "drill", "drink", "drip", "drive", "drop", "drum", "dry", "duck", "dumb", "dune", "during", "dust", "dutch", "duty", "dwarf", "dynamic", "eager", "eagle", "early", "earn", "earth", "easily", "east", "easy", "echo", "ecology", "economy", "edge", "edit", "educate", "effort", "egg", "eight", "either", "elbow", "elder", "electric", "elegant", "element", "elephant", "elevator", "elite", "else", "embark", "embody", "embrace", "emerge", "emotion", "employ", "empower", "empty", "enable", "enact", "end", "endless", "endorse", "enemy", "energy", "enforce", "engage", "engine", "enhance", "enjoy", "enlist", "enough", "enrich", "enroll", "ensure", "enter", "entire", "entry", "envelope", "episode", "equal", "equip", "era", "erase", "erode", "erosion", "error", "erupt", "escape", "essay", "essence", "estate", "eternal", "ethics", "evidence", "evil", "evoke", "evolve", "exact", "example", "excess", "exchange", "excite", "exclude", "excuse", "execute", "exercise", "exhaust", "exhibit", "exile", "exist", "exit", "exotic", "expand", "expect", "expire", "explain", "expose", "express", "extend", "extra", "eye", "eyebrow", "fabric", "face", "faculty", "fade", "faint", "faith", "fall", "false", "fame", "family", "famous", "fan", "fancy", "fantasy", "farm", "fashion", "fat", "fatal", "father", "fatigue", "fault", "favorite", "feature", "february", "federal", "fee", "feed", "feel", "female", "fence", "festival", "fetch", "fever", "few", "fiber", "fiction", "field", "figure", "file", "film", "filter", "final", "find", "fine", "finger", "finish", "fire", "firm", "first", "fiscal", "fish", "fit", "fitness", "fix", "flag", "flame", "flash", "flat", "flavor", "flee", "flight", "flip", "float", "flock", "floor", "flower", "fluid", "flush", "fly", "foam", "focus", "fog", "foil", "fold", "follow", "food", "foot", "force", "forest", "forget", "fork", "fortune", "forum", "forward", "fossil", "foster", "found", "fox", "fragile", "frame", "frequent", "fresh", "friend", "fringe", "frog", "front", "frost", "frown", "frozen", "fruit", "fuel", "fun", "funny", "furnace", "fury", "future", "gadget", "gain", "galaxy", "gallery", "game", "gap", "garage", "garbage", "garden", "garlic", "garment", "gas", "gasp", "gate", "gather", "gauge", "gaze", "general", "genius", "genre", "gentle", "genuine", "gesture", "ghost", "giant", "gift", "giggle", "ginger", "giraffe", "girl", "give", "glad", "glance", "glare", "glass", "glide", "glimpse", "globe", "gloom", "glory", "glove", "glow", "glue", "goat", "goddess", "gold", "good", "goose", "gorilla", "gospel", "gossip", "govern", "gown", "grab", "grace", "grain", "grant", "grape", "grass", "gravity", "great", "green", "grid", "grief", "grit", "grocery", "group", "grow", "grunt", "guard", "guess", "guide", "guilt", "guitar", "gun", "gym", "habit", "hair", "half", "hammer", "hamster", "hand", "happy", "harbor", "hard", "harsh", "harvest", "hat", "have", "hawk", "hazard", "head", "health", "heart", "heavy", "hedgehog", "height", "hello", "helmet", "help", "hen", "hero", "hidden", "high", "hill", "hint", "hip", "hire", "history", "hobby", "hockey", "hold", "hole", "holiday", "hollow", "home", "honey", "hood", "hope", "horn", "horror", "horse", "hospital", "host", "hotel", "hour", "hover", "hub", "huge", "human", "humble", "humor", "hundred", "hungry", "hunt", "hurdle", "hurry", "hurt", "husband", "hybrid", "ice", "icon", "idea", "identify", "idle", "ignore", "ill", "illegal", "illness", "image", "imitate", "immense", "immune", "impact", "impose", "improve", "impulse", "inch", "include", "income", "increase", "index", "indicate", "indoor", "industry", "infant", "inflict", "inform", "inhale", "inherit", "initial", "inject", "injury", "inmate", "inner", "innocent", "input", "inquiry", "insane", "insect", "inside", "inspire", "install", "intact", "interest", "into", "invest", "invite", "involve", "iron", "island", "isolate", "issue", "item", "ivory", "jacket", "jaguar", "jar", "jazz", "jealous", "jeans", "jelly", "jewel", "job", "join", "joke", "journey", "joy", "judge", "juice", "jump", "jungle", "junior", "junk", "just", "kangaroo", "keen", "keep", "ketchup", "key", "kick", "kid", "kidney", "kind", "kingdom", "kiss", "kit", "kitchen", "kite", "kitten", "kiwi", "knee", "knife", "knock", "know", "lab", "label", "labor", "ladder", "lady", "lake", "lamp", "language", "laptop", "large", "later", "latin", "laugh", "laundry", "lava", "law", "lawn", "lawsuit", "layer", "lazy", "leader", "leaf", "learn", "leave", "lecture", "left", "leg", "legal", "legend", "leisure", "lemon", "lend", "length", "lens", "leopard", "lesson", "letter", "level", "liar", "liberty", "library", "license", "life", "lift", "light", "like", "limb", "limit", "link", "lion", "liquid", "list", "little", "live", "lizard", "load", "loan", "lobster", "local", "lock", "logic", "lonely", "long", "loop", "lottery", "loud", "lounge", "love", "loyal", "lucky", "luggage", "lumber", "lunar", "lunch", "luxury", "lyrics", "machine", "mad", "magic", "magnet", "maid", "mail", "main", "major", "make", "mammal", "man", "manage", "mandate", "mango", "mansion", "manual", "maple", "marble", "march", "margin", "marine", "market", "marriage", "mask", "mass", "master", "match", "material", "math", "matrix", "matter", "maximum", "maze", "meadow", "mean", "measure", "meat", "mechanic", "medal", "media", "melody", "melt", "member", "memory", "mention", "menu", "mercy", "merge", "merit", "merry", "mesh", "message", "metal", "method", "middle", "midnight", "milk", "million", "mimic", "mind", "minimum", "minor", "minute", "miracle", "mirror", "misery", "miss", "mistake", "mix", "mixed", "mixture", "mobile", "model", "modify", "mom", "moment", "monitor", "monkey", "monster", "month", "moon", "moral", "more", "morning", "mosquito", "mother", "motion", "motor", "mountain", "mouse", "move", "movie", "much", "muffin", "mule", "multiply", "muscle", "museum", "mushroom", "music", "must", "mutual", "myself", "mystery", "myth", "naive", "name", "napkin", "narrow", "nasty", "nation", "nature", "near", "neck", "need", "negative", "neglect", "neither", "nephew", "nerve", "nest", "net", "network", "neutral", "never", "news", "next", "nice", "night", "noble", "noise", "nominee", "noodle", "normal", "north", "nose", "notable", "note", "nothing", "notice", "novel", "now", "nuclear", "number", "nurse", "nut", "oak", "obey", "object", "oblige", "obscure", "observe", "obtain", "obvious", "occur", "ocean", "october", "odor", "off", "offer", "office", "often", "oil", "okay", "old", "olive", "olympic", "omit", "once", "one", "onion", "online", "only", "open", "opera", "opinion", "oppose", "option", "orange", "orbit", "orchard", "order", "ordinary", "organ", "orient", "original", "orphan", "ostrich", "other", "outdoor", "outer", "output", "outside", "oval", "oven", "over", "own", "owner", "oxygen", "oyster", "ozone", "pact", "paddle", "page", "pair", "palace", "palm", "panda", "panel", "panic", "panther", "paper", "parade", "parent", "park", "parrot", "party", "pass", "patch", "path", "patient", "patrol", "pattern", "pause", "pave", "payment", "peace", "peanut", "pear", "peasant", "pelican", "pen", "penalty", "pencil", "people", "pepper", "perfect", "permit", "person", "pet", "phone", "photo", "phrase", "physical", "piano", "picnic", "picture", "piece", "pig", "pigeon", "pill", "pilot", "pink", "pioneer", "pipe", "pistol", "pitch", "pizza", "place", "planet", "plastic", "plate", "play", "please", "pledge", "pluck", "plug", "plunge", "poem", "poet", "point", "polar", "pole", "police", "pond", "pony", "pool", "popular", "portion", "position", "possible", "post", "potato", "pottery", "poverty", "powder", "power", "practice", "praise", "predict", "prefer", "prepare", "present", "pretty", "prevent", "price", "pride", "primary", "print", "priority", "prison", "private", "prize", "problem", "process", "produce", "profit", "program", "project", "promote", "proof", "property", "prosper", "protect", "proud", "provide", "public", "pudding", "pull", "pulp", "pulse", "pumpkin", "punch", "pupil", "puppy", "purchase", "purity", "purpose", "purse", "push", "put", "puzzle", "pyramid", "quality", "quantum", "quarter", "question", "quick", "quit", "quiz", "quote", "rabbit", "raccoon", "race", "rack", "radar", "radio", "rail", "rain", "raise", "rally", "ramp", "ranch", "random", "range", "rapid", "rare", "rate", "rather", "raven", "raw", "razor", "ready", "real", "reason", "rebel", "rebuild", "recall", "receive", "recipe", "record", "recycle", "reduce", "reflect", "reform", "refuse", "region", "regret", "regular", "reject", "relax", "release", "relief", "rely", "remain", "remember", "remind", "remove", "render", "renew", "rent", "reopen", "repair", "repeat", "replace", "report", "require", "rescue", "resemble", "resist", "resource", "response", "result", "retire", "retreat", "return", "reunion", "reveal", "review", "reward", "rhythm", "rib", "ribbon", "rice", "rich", "ride", "ridge", "rifle", "right", "rigid", "ring", "riot", "ripple", "risk", "ritual", "rival", "river", "road", "roast", "robot", "robust", "rocket", "romance", "roof", "rookie", "room", "rose", "rotate", "rough", "round", "route", "royal", "rubber", "rude", "rug", "rule", "run", "runway", "rural", "sad", "saddle", "sadness", "safe", "sail", "salad", "salmon", "salon", "salt", "salute", "same", "sample", "sand", "satisfy", "satoshi", "sauce", "sausage", "save", "say", "scale", "scan", "scare", "scatter", "scene", "scheme", "school", "science", "scissors", "scorpion", "scout", "scrap", "screen", "script", "scrub", "sea", "search", "season", "seat", "second", "secret", "section", "security", "seed", "seek", "segment", "select", "sell", "seminar", "senior", "sense", "sentence", "series", "service", "session", "settle", "setup", "seven", "shadow", "shaft", "shallow", "share", "shed", "shell", "sheriff", "shield", "shift", "shine", "ship", "shiver", "shock", "shoe", "shoot", "shop", "short", "shoulder", "shove", "shrimp", "shrug", "shuffle", "shy", "sibling", "sick", "side", "siege", "sight", "sign", "silent", "silk", "silly", "silver", "similar", "simple", "since", "sing", "siren", "sister", "situate", "six", "size", "skate", "sketch", "ski", "skill", "skin", "skirt", "skull", "slab", "slam", "sleep", "slender", "slice", "slide", "slight", "slim", "slogan", "slot", "slow", "slush", "small", "smart", "smile", "smoke", "smooth", "snack", "snake", "snap", "sniff", "snow", "soap", "soccer", "social", "sock", "soda", "soft", "solar", "soldier", "solid", "solution", "solve", "someone", "song", "soon", "sorry", "sort", "soul", "sound", "soup", "source", "south", "space", "spare", "spatial", "spawn", "speak", "special", "speed", "spell", "spend", "sphere", "spice", "spider", "spike", "spin", "spirit", "split", "spoil", "sponsor", "spoon", "sport", "spot", "spray", "spread", "spring", "spy", "square", "squeeze", "squirrel", "stable", "stadium", "staff", "stage", "stairs", "stamp", "stand", "start", "state", "stay", "steak", "steel", "stem", "step", "stereo", "stick", "still", "sting", "stock", "stomach", "stone", "stool", "story", "stove", "strategy", "street", "strike", "strong", "struggle", "student", "stuff", "stumble", "style", "subject", "submit", "subway", "success", "such", "sudden", "suffer", "sugar", "suggest", "suit", "summer", "sun", "sunny", "sunset", "super", "supply", "supreme", "sure", "surface", "surge", "surprise", "surround", "survey", "suspect", "sustain", "swallow", "swamp", "swap", "swarm", "swear", "sweet", "swift", "swim", "swing", "switch", "sword", "symbol", "symptom", "syrup", "system", "table", "tackle", "tag", "tail", "talent", "talk", "tank", "tape", "target", "task", "taste", "tattoo", "taxi", "teach", "team", "tell", "ten", "tenant", "tennis", "tent", "term", "test", "text", "thank", "that", "theme", "then", "theory", "there", "they", "thing", "this", "thought", "three", "thrive", "throw", "thumb", "thunder", "ticket", "tide", "tiger", "tilt", "timber", "time", "tiny", "tip", "tired", "tissue", "title", "toast", "tobacco", "today", "toddler", "toe", "together", "toilet", "token", "tomato", "tomorrow", "tone", "tongue", "tonight", "tool", "tooth", "top", "topic", "topple", "torch", "tornado", "tortoise", "toss", "total", "tourist", "toward", "tower", "town", "toy", "track", "trade", "traffic", "tragic", "train", "transfer", "trap", "trash", "travel", "tray", "treat", "tree", "trend", "trial", "tribe", "trick", "trigger", "trim", "trip", "trophy", "trouble", "truck", "true", "truly", "trumpet", "trust", "truth", "try", "tube", "tuition", "tumble", "tuna", "tunnel", "turkey", "turn", "turtle", "twelve", "twenty", "twice", "twin", "twist", "two", "type", "typical", "ugly", "umbrella", "unable", "unaware", "uncle", "uncover", "under", "undo", "unfair", "unfold", "unhappy", "uniform", "unique", "unit", "universe", "unknown", "unlock", "until", "unusual", "unveil", "update", "upgrade", "uphold", "upon", "upper", "upset", "urban", "urge", "usage", "use", "used", "useful", "useless", "usual", "utility", "vacant", "vacuum", "vague", "valid", "valley", "valve", "van", "vanish", "vapor", "various", "vast", "vault", "vehicle", "velvet", "vendor", "venture", "venue", "verb", "verify", "version", "very", "vessel", "veteran", "viable", "vibrant", "vicious", "victory", "video", "view", "village", "vintage", "violin", "virtual", "virus", "visa", "visit", "visual", "vital", "vivid", "vocal", "voice", "void", "volcano", "volume", "vote", "voyage", "wage", "wagon", "wait", "walk", "wall", "walnut", "want", "warfare", "warm", "warrior", "wash", "wasp", "waste", "water", "wave", "way", "wealth", "weapon", "wear", "weasel", "weather", "web", "wedding", "weekend", "weird", "welcome", "west", "wet", "whale", "what", "wheat", "wheel", "when", "where", "whip", "whisper", "wide", "width", "wife", "wild", "will", "win", "window", "wine", "wing", "wink", "winner", "winter", "wire", "wisdom", "wise", "wish", "witness", "wolf", "woman", "wonder", "wood", "wool", "word", "work", "world", "worry", "worth", "wrap", "wreck", "wrestle", "wrist", "write", "wrong", "yard", "year", "yellow", "you", "young", "youth", "zebra", "zero", "zone", "zoo"]

    ALPHABET = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z"]

    def __init__(self, controller) -> None:
        View.__init__(self, controller)

        # Gather words and seed display information
        self.words = []
        self.letters = []
        self.possible_alphabet = []
        self.possible_words = []
        self.seed_length = 12     # Default to 12, Valid values are 11, 12, 23 and 24

        # Dice information
        self.roll_number = 1
        self.dice_selected = 0
        self.roll_data = ""
        self.dice_seed_phrase = []

    ###
    ### Display Gather Words Screen
    ###

    def display_gather_words_screen(self, num_of_words, slot_num = 0) -> []:
        self.seed_length = num_of_words

        self.reset()
        self.draw_gather_words()

        # Wait for Button Input (specifically menu selection/press)
        while True:
            input = self.buttons.wait_for([B.KEY_UP, B.KEY_DOWN, B.KEY_PRESS, B.KEY_RIGHT, B.KEY_LEFT, B.KEY1, B.KEY2, B.KEY3], True, [B.KEY_PRESS, B.KEY_RIGHT, B.KEY_LEFT, B.KEY1, B.KEY2, B.KEY3])
            if input == B.KEY_UP:
                ret_val = self.gather_words_up()
            elif input == B.KEY_DOWN:
                ret_val = self.gather_words_down()
            elif input == B.KEY_RIGHT:
                ret_val = self.gather_words_right()
            elif input == B.KEY_LEFT:
                ret_val = self.gather_words_left()
            elif input == B.KEY_PRESS:
                ret_val = self.gather_words_press()
            elif input == B.KEY1:
                ret_val = self.gather_words_a()
            elif input == B.KEY2:
                ret_val = self.gather_words_b()
            elif input == B.KEY3:
                ret_val = self.gather_words_c()

            if ret_val == False:
                return []

            if len(self.words) == self.seed_length:
                return self.words[:]

            self.draw_gather_words()

    def gather_words_up(self):
        View.draw.polygon([(8 + ((len(self.letters)-1)*30), 85) , (14 + ((len(self.letters)-1)*30), 69) , (20 + ((len(self.letters)-1)*30), 85 )], outline="ORANGE", fill="ORANGE")
        View.DispShowImage()

        self.calc_possible_alphabet()
        if self.letters[len(self.letters)-1] == self.possible_alphabet[0]:
            self.letters[len(self.letters)-1] = self.possible_alphabet[-1]
        else:
            try:
                idx = self.possible_alphabet.index(self.letters[len(self.letters)-1])
                self.letters[len(self.letters)-1] = self.possible_alphabet[idx-1]
            except (ValueError, IndexError):
                print("not found error")

    def gather_words_down(self):
        View.draw.polygon([(8 + ((len(self.letters)-1)*30), 148), (14 + ((len(self.letters)-1)*30), 164), (20 + ((len(self.letters)-1)*30), 148)], outline="ORANGE", fill="ORANGE")
        View.DispShowImage()

        self.calc_possible_alphabet()
        if self.letters[len(self.letters)-1] == self.possible_alphabet[-1]:
            self.letters[len(self.letters)-1] = self.possible_alphabet[0]
        else:
            try:
                idx = self.possible_alphabet.index(self.letters[len(self.letters)-1])
                self.letters[len(self.letters)-1] = self.possible_alphabet[idx+1]
            except (ValueError, IndexError):
                print("not found error")

    def gather_words_right(self):
        if len(self.letters) < 4:
            self.calc_possible_alphabet(True)
            self.letters.append(self.possible_alphabet[0])

    def gather_words_left(self) -> bool:
        if len(self.letters) == 1:
            if len(self.words) == 0:
                return False
            else:
                self.words.pop()
        else:
            self.letters.pop()
        return True

    def gather_words_press(self):
        self.gather_words_right()

    def gather_words_a(self):
        if len(self.possible_words) >= 1: # skip everything if there is no word next to the button
            self.letters.clear()
            self.words.append(self.possible_words[0])
            if len(self.words) < self.seed_length:
                self.possible_alphabet = SeedToolsView.ALPHABET[:]
                self.letters.append(self.possible_alphabet[0])
                return
            else:
                self.letters.append(SeedToolsView.ALPHABET[0])
        else:
            return

    def gather_words_b(self):
        if len(self.possible_words) >= 2: # skip everything if there is no word next to the button
            self.letters.clear()
            self.words.append(self.possible_words[1])
            if len(self.words) < self.seed_length:
                self.possible_alphabet = SeedToolsView.ALPHABET[:]
                self.letters.append(self.possible_alphabet[0])
                return
            else:
                self.letters.append(SeedToolsView.ALPHABET[0])
        else:
            return

    def gather_words_c(self):
        if len(self.possible_words) >= 3: # skip everything if there is no word next to the button
            self.letters.clear()
            self.words.append(self.possible_words[2])
            if len(self.words) < self.seed_length:
                self.possible_alphabet = SeedToolsView.ALPHABET[:]
                self.letters.append(self.possible_alphabet[0])
                return
            else:
                self.letters.append(SeedToolsView.ALPHABET[0])
        else:
            return

    def draw_gather_words(self):

        View.draw.rectangle((0, 0, View.canvas_width, View.canvas_height), outline=0, fill=0)
        View.draw.text((75, 2), "Seed Word: " + str(len(self.words)+1), fill="ORANGE", font=View.IMPACT18)
        View.draw.text((15, 210), "(choose from words on right)", fill="ORANGE", font=View.IMPACT18)

        # draw possible words (3 at most)
        self.possible_words = [i for i in SeedToolsView.SEEDWORDS if i.startswith("".join(self.letters))]
        if len(self.possible_words) >= 1:
            for idx, word in enumerate(self.possible_words, start=0):
                word_offset = 223 - View.IMPACT25.getsize(word)[0]
                View.draw.text((word_offset, 39 + (60*idx)), word + " -", fill="ORANGE", font=View.IMPACT25)
                if idx >= 2:
                    break

        # draw letter and arrows
        for idx, letter in enumerate(self.letters, start=0):
            tw, th = View.draw.textsize(letter, font=View.IMPACT35)
            View.draw.text((((idx*30)+((30-tw)/2)), 92), letter, fill="ORANGE", font=View.IMPACT35)
            if idx+1 == len(self.letters):
                # draw arrows only above last/active letter
                View.draw.polygon([(8 + (idx*30), 85) , (14 + (idx*30), 69) , (20 + (idx*30), 85 )], outline="ORANGE", fill="BLACK")
                View.draw.polygon([(8 + (idx*30), 148), (14 + (idx*30), 164), (20 + (idx*30), 148)], outline="ORANGE", fill="BLACK")

        View.DispShowImage()

        return

    ###
    ### Display Last Word
    ###

    def display_last_word(self, partial_seed_phrase) -> list:
        print("display last word")

        stringphrase = " ".join(partial_seed_phrase).strip() + " abandon"
        bytes = mnemonic_to_bytes(stringphrase, ignore_checksum=True)
        finalseed = mnemonic_from_bytes(bytes)
        splitseed = finalseed.split()
        last_word = splitseed[-1]

        self.draw.rectangle((0, 0, View.canvas_width, View.canvas_height), outline=0, fill=0)
        tw, th = self.draw.textsize("The final word is :", font=View.IMPACT23)
        self.draw.text(((240 - tw) / 2, 60), "The final word is :", fill="ORANGE", font=View.IMPACT23)
        tw, th = self.draw.textsize(last_word, font=View.IMPACT50)
        self.draw.text(((240 - tw) / 2, 90), last_word, fill="ORANGE", font=View.IMPACT50)
        self.draw.text((73, 210), "Right to Continue", fill="ORANGE", font=View.IMPACT18)
        View.DispShowImage()

        input = self.buttons.wait_for([B.KEY_RIGHT])
        return splitseed[:]

    ###
    ### Display Seed from Dice
    ###

    def display_generate_seed_from_dice(self):
        self.roll_number = 1
        self.dice_selected = 0
        self.roll_data = ""

        self.draw_dice(1)
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
                self.dice_seed_phrase = self.calc_seed_from_dice()
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
        self.roll_number = self.roll_number + 1
        if self.dice_selected == 6:
            self.roll_data = self.roll_data + str(0).strip()
        else:
            self.roll_data = self.roll_data + str(self.dice_selected).strip()
        self.dice_selected = 1
        if self.roll_number < 100:
            self.draw_dice(self.dice_selected)

        return True

    def draw_dice(self, dice_selected):

        self.draw.rectangle((0, 0, View.canvas_width, View.canvas_height), outline=0, fill=0)
        self.draw.text((45, 5), "Dice roll: " + str(self.roll_number) + "/99", fill="ORANGE", font=View.IMPACT26)

        # when dice is selected, rect fill will be orange and ellipse will be black, ellipse outline will be the black
        # when dice is not selected, rect will will be black and ellipse will be orange, ellipse outline will be orange

        # dice 1
        if dice_selected == 1:
            self.draw.rectangle((5, 50, 75, 120),   outline="ORANGE", fill="ORANGE")
            self.draw.ellipse([(34, 79), (46, 91)], outline="BLACK",  fill="BLACK")
        else:
            self.draw.rectangle((5, 50, 75, 120),   outline="ORANGE", fill="BLACK")
            self.draw.ellipse([(34, 79), (46, 91)], outline="ORANGE", fill="ORANGE")

        # dice 2
        if dice_selected == 2:
            self.draw.rectangle((85, 50, 155, 120), outline="ORANGE", fill="ORANGE")
            self.draw.ellipse([(100, 60), (112, 72)], outline="BLACK", fill="BLACK")
            self.draw.ellipse([(128, 98), (140, 110)], outline="BLACK", fill="BLACK")
        else:
            self.draw.rectangle((85, 50, 155, 120), outline="ORANGE", fill="BLACK")
            self.draw.ellipse([(100, 60), (112, 72)], outline="ORANGE", fill="ORANGE")
            self.draw.ellipse([(128, 98), (140, 110)], outline="ORANGE", fill="ORANGE")

        # dice 3
        if dice_selected == 3:
            self.draw.rectangle((165, 50, 235, 120), outline="ORANGE", fill="ORANGE")
            self.draw.ellipse([(180, 60), (192, 72)], outline="BLACK", fill="BLACK")
            self.draw.ellipse([(194, 79), (206, 91)], outline="BLACK", fill="BLACK")
            self.draw.ellipse([(208, 98), (220, 110)], outline="BLACK", fill="BLACK")
        else:
            self.draw.rectangle((165, 50, 235, 120), outline="ORANGE", fill="BLACK")
            self.draw.ellipse([(180, 60), (192, 72)], outline="ORANGE", fill="ORANGE")
            self.draw.ellipse([(194, 79), (206, 91)], outline="ORANGE", fill="ORANGE")
            self.draw.ellipse([(208, 98), (220, 110)], outline="ORANGE", fill="ORANGE")

        # dice 4
        if dice_selected == 4:
            self.draw.rectangle((5, 130, 75, 200), outline="ORANGE", fill="ORANGE")
            self.draw.ellipse([(20, 140), (32, 152)], outline="BLACK", fill="BLACK")
            self.draw.ellipse([(20, 174), (32, 186)], outline="BLACK", fill="BLACK")
            self.draw.ellipse([(48, 140), (60, 152)], outline="BLACK", fill="BLACK")
            self.draw.ellipse([(48, 174), (60, 186)], outline="BLACK", fill="BLACK")
        else:
            self.draw.rectangle((5, 130, 75, 200), outline="ORANGE", fill="BLACK")
            self.draw.ellipse([(20, 140), (32, 152)], outline="ORANGE", fill="ORANGE")
            self.draw.ellipse([(20, 174), (32, 186)], outline="ORANGE", fill="ORANGE")
            self.draw.ellipse([(48, 140), (60, 152)], outline="ORANGE", fill="ORANGE")
            self.draw.ellipse([(48, 174), (60, 186)], outline="ORANGE", fill="ORANGE")

        # dice 5
        if dice_selected == 5:
            self.draw.rectangle((85, 130, 155, 200), outline="ORANGE", fill="ORANGE")
            self.draw.ellipse([(100, 140), (112, 152)], outline="BLACK", fill="BLACK")
            self.draw.ellipse([(100, 178), (112, 190)], outline="BLACK", fill="BLACK")
            self.draw.ellipse([(114, 159), (126, 171)], outline="BLACK", fill="BLACK")
            self.draw.ellipse([(128, 140), (140, 152)], outline="BLACK", fill="BLACK")
            self.draw.ellipse([(128, 178), (140, 190)], outline="BLACK", fill="BLACK")
        else:
            self.draw.rectangle((85, 130, 155, 200), outline="ORANGE", fill="BLACK")
            self.draw.ellipse([(100, 140), (112, 152)], outline="ORANGE", fill="ORANGE")
            self.draw.ellipse([(100, 178), (112, 190)], outline="ORANGE", fill="ORANGE")
            self.draw.ellipse([(114, 159), (126, 171)], outline="ORANGE", fill="ORANGE")
            self.draw.ellipse([(128, 140), (140, 152)], outline="ORANGE", fill="ORANGE")
            self.draw.ellipse([(128, 178), (140, 190)], outline="ORANGE", fill="ORANGE")

        # dice 6
        if dice_selected == 6:
            self.draw.rectangle((165, 130, 235, 200), outline="ORANGE", fill="ORANGE")
            self.draw.ellipse([(180, 140), (192, 152)], outline="BLACK", fill="BLACK")
            self.draw.ellipse([(180, 157), (192, 169)], outline="BLACK", fill="BLACK")
            self.draw.ellipse([(180, 174), (192, 186)], outline="BLACK", fill="BLACK")
            self.draw.ellipse([(208, 140), (220, 152)], outline="BLACK", fill="BLACK")
            self.draw.ellipse([(208, 157), (220, 169)], outline="BLACK", fill="BLACK")
            self.draw.ellipse([(208, 174), (220, 186)], outline="BLACK", fill="BLACK")
        else:
            self.draw.rectangle((165, 130, 235, 200), outline="ORANGE", fill="BLACK")
            self.draw.ellipse([(180, 140), (192, 152)], outline="ORANGE", fill="ORANGE")
            self.draw.ellipse([(180, 157), (192, 169)], outline="ORANGE", fill="ORANGE")
            self.draw.ellipse([(180, 174), (192, 186)], outline="ORANGE", fill="ORANGE")
            self.draw.ellipse([(208, 140), (220, 152)], outline="ORANGE", fill="ORANGE")
            self.draw.ellipse([(208, 157), (220, 169)], outline="ORANGE", fill="ORANGE")
            self.draw.ellipse([(208, 174), (220, 186)], outline="ORANGE", fill="ORANGE")

        # bottom text
        self.draw.text((18, 210), "Press Control Stick to Select", fill="ORANGE", font=View.IMPACT18)
        View.DispShowImage()

        self.dice_selected = dice_selected

    def calc_seed_from_dice(self):
        entropyinteger = int(self.roll_data, 6)
        entropyinbytes = entropyinteger.to_bytes(32, byteorder="little")
        badseedphrase_str = mnemonic_from_bytes(entropyinbytes)
        badseedphrase_list = badseedphrase_str.split()
        badseedphrase_list.pop(-1)
        calclastwordphrasestr = " ".join(badseedphrase_list) + " abandon"
        goodphrasebytes = mnemonic_to_bytes(calclastwordphrasestr, ignore_checksum=True)
        goodseedphrasestr = mnemonic_from_bytes(goodphrasebytes)
        seed_phrase = goodseedphrasestr.split()

        return seed_phrase

    ###
    ### Display Seed Phrase
    ###

    def display_seed_phrase(self, seed_phrase, bottom = "RIGHT to EXIT") -> bool:
        ret_val = ""

        while True:
            if len(seed_phrase) in (11,12):
                ret_val = self.display_seed_phrase_12(seed_phrase, bottom)
                if ret_val == "right":
                    return True
                else:
                    return False
            elif len(seed_phrase) in (23,24):
                if ret_val == "":
                    ret_val = self.display_seed_phrase_24_1(seed_phrase, bottom) #first run
                elif ret_val == "right-1":
                    ret_val = self.display_seed_phrase_24_2(seed_phrase, bottom) #first screen to second screen
                elif ret_val == "left-2":
                    ret_val = self.display_seed_phrase_24_1(seed_phrase, bottom) #second screen back to first screen
                elif ret_val == "left-1":
                    return False
                elif ret_val == "right-2":
                    return True

    def display_seed_phrase_12(self, seed_phrase, bottom = "Right to Exit"):
        self.draw.rectangle((0, 0, View.canvas_width, View.canvas_height), outline=0, fill=0)

        tw, th = View.draw.textsize("Selected Words", font=View.IMPACT18)
        self.draw.text(((240 - tw) / 2, 2), "Selected Words", fill="ORANGE", font=View.IMPACT18)

        self.draw.text((2, 40), "1: "     + seed_phrase[0] , fill="ORANGE", font=View.IMPACT23)
        self.draw.text((2, 65), "2: "     + seed_phrase[1] , fill="ORANGE", font=View.IMPACT23)
        self.draw.text((2, 90), "3: "     + seed_phrase[2] , fill="ORANGE", font=View.IMPACT23)
        self.draw.text((2, 115), "4: "    + seed_phrase[3] , fill="ORANGE", font=View.IMPACT23)
        self.draw.text((2, 140), "5: "    + seed_phrase[4] , fill="ORANGE", font=View.IMPACT23)
        self.draw.text((2, 165), "6: "    + seed_phrase[5] , fill="ORANGE", font=View.IMPACT23)
        self.draw.text((120, 40), " 7: "  + seed_phrase[6] , fill="ORANGE", font=View.IMPACT23)
        self.draw.text((120, 65), " 8: "  + seed_phrase[7] , fill="ORANGE", font=View.IMPACT23)
        self.draw.text((120, 90), " 9: "  + seed_phrase[8] , fill="ORANGE", font=View.IMPACT23)
        self.draw.text((120, 115), "10: " + seed_phrase[9] , fill="ORANGE", font=View.IMPACT23)
        self.draw.text((120, 140), "11: " + seed_phrase[10], fill="ORANGE", font=View.IMPACT23)
        if len(seed_phrase) >= 12:
            self.draw.text((120, 165), "12: " + seed_phrase[11], fill="ORANGE", font=View.IMPACT23)

        tw, th = View.draw.textsize(bottom, font=View.IMPACT18)
        self.draw.text(((240 - tw) / 2, 210), bottom, fill="ORANGE", font=View.IMPACT18)
        View.DispShowImage()

        input = self.buttons.wait_for([B.KEY_RIGHT, B.KEY_LEFT])
        if input == B.KEY_RIGHT:
            return "right"
        elif input == B.KEY_LEFT:
            return "left"

    def display_seed_phrase_24_1(self, seed_phrase, bottom = "Right to Exit"):
        self.draw.rectangle((0, 0, View.canvas_width, View.canvas_height), outline=0, fill=0)

        tw, th = View.draw.textsize("Selected Words (1/2)", font=View.IMPACT18)
        self.draw.text(((240 - tw) / 2, 2), "Selected Words (1/2)", fill="ORANGE", font=View.IMPACT18)

        self.draw.text((2, 40), "1: "     + seed_phrase[0] , fill="ORANGE", font=View.IMPACT23)
        self.draw.text((2, 65), "2: "     + seed_phrase[1] , fill="ORANGE", font=View.IMPACT23)
        self.draw.text((2, 90), "3: "     + seed_phrase[2] , fill="ORANGE", font=View.IMPACT23)
        self.draw.text((2, 115), "4: "    + seed_phrase[3] , fill="ORANGE", font=View.IMPACT23)
        self.draw.text((2, 140), "5: "    + seed_phrase[4] , fill="ORANGE", font=View.IMPACT23)
        self.draw.text((2, 165), "6: "    + seed_phrase[5] , fill="ORANGE", font=View.IMPACT23)
        self.draw.text((120, 40), " 7: "  + seed_phrase[6] , fill="ORANGE", font=View.IMPACT23)
        self.draw.text((120, 65), " 8: "  + seed_phrase[7] , fill="ORANGE", font=View.IMPACT23)
        self.draw.text((120, 90), " 9: "  + seed_phrase[8] , fill="ORANGE", font=View.IMPACT23)
        self.draw.text((120, 115), "10: " + seed_phrase[9] , fill="ORANGE", font=View.IMPACT23)
        self.draw.text((120, 140), "11: " + seed_phrase[10], fill="ORANGE", font=View.IMPACT23)
        self.draw.text((120, 165), "12: " + seed_phrase[11], fill="ORANGE", font=View.IMPACT23)
        tw, th = View.draw.textsize("Right to Continue", font=View.IMPACT18)
        self.draw.text(((240 - tw) / 2, 210), "Right to Continue", fill="ORANGE", font=View.IMPACT18)
        View.DispShowImage()

        input = self.buttons.wait_for([B.KEY_RIGHT, B.KEY_LEFT])
        if input == B.KEY_RIGHT:
            return "right-1"
        elif input == B.KEY_LEFT:
            return "left-1"

    def display_seed_phrase_24_2(self, seed_phrase, bottom):
        self.draw.rectangle((0, 0, View.canvas_width, View.canvas_height), outline=0, fill=0)
        
        tw, th = View.draw.textsize("Selected Words (2/2)", font=View.IMPACT18)
        self.draw.text(((240 - tw) / 2, 2), "Selected Words (2/2)", fill="ORANGE", font=View.IMPACT18)

        self.draw.text((2, 40), "13: "     + seed_phrase[12] , fill="ORANGE", font=View.IMPACT23)
        self.draw.text((2, 65), "14: "     + seed_phrase[13] , fill="ORANGE", font=View.IMPACT23)
        self.draw.text((2, 90), "15: "     + seed_phrase[14] , fill="ORANGE", font=View.IMPACT23)
        self.draw.text((2, 115), "16: "    + seed_phrase[15] , fill="ORANGE", font=View.IMPACT23)
        self.draw.text((2, 140), "17: "    + seed_phrase[16] , fill="ORANGE", font=View.IMPACT23)
        self.draw.text((2, 165), "18: "    + seed_phrase[17] , fill="ORANGE", font=View.IMPACT23)
        self.draw.text((120, 40), "19: "  + seed_phrase[18] , fill="ORANGE", font=View.IMPACT23)
        self.draw.text((120, 65), "20: "  + seed_phrase[19] , fill="ORANGE", font=View.IMPACT23)
        self.draw.text((120, 90), "21: "  + seed_phrase[20] , fill="ORANGE", font=View.IMPACT23)
        self.draw.text((120, 115), "22: " + seed_phrase[21] , fill="ORANGE", font=View.IMPACT23)
        self.draw.text((120, 140), "23: " + seed_phrase[22], fill="ORANGE", font=View.IMPACT23)
        if len(seed_phrase) >= 24:
            self.draw.text((120, 165), "24: " + seed_phrase[23], fill="ORANGE", font=View.IMPACT23)
        tw, th = View.draw.textsize(bottom, font=View.IMPACT18)
        self.draw.text(((240 - tw) / 2, 210), bottom, fill="ORANGE", font=View.IMPACT18)
        View.DispShowImage()

        input = self.buttons.wait_for([B.KEY_RIGHT, B.KEY_LEFT])
        if input == B.KEY_RIGHT:
            return "right-2"
        elif input == B.KEY_LEFT:
            return "left-2"

    ###
    ### Utility Methods
    ###

    def reset(self):
        self.words.clear()
        self.possible_alphabet = SeedToolsView.ALPHABET[:]
        self.letters.clear()
        self.letters.append(self.possible_alphabet[0])
        self.possible_words.clear()

        return

    def calc_possible_alphabet(self, new_letter = False):
        if (len(self.letters) > 1 and new_letter == False) or (len(self.letters) > 0 and new_letter == True):
            search_letters = self.letters[:]
            if new_letter == False:
                search_letters.pop()
            possible_words = [i for i in SeedToolsView.SEEDWORDS if i.startswith("".join(search_letters))]
            letter_num = len(search_letters)
            possible_letters = []
            for word in possible_words:
                if len(word)-1 >= letter_num:
                    possible_letters.append(word[letter_num])
            # remove duplicates and keep order
            self.possible_alphabet = list(dict.fromkeys(possible_letters))[:]
        else:
            self.possible_alphabet = SeedToolsView.ALPHABET[:]
