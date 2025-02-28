# Localization (l10n) Developer Notes

## High-level overview
1. Python code indicates text that needs to be translated.
1. Those marked strings are extracted into a master `messages.pot` file.
1. That file is uploaded [Transifex](https://app.transifex.com/seedsigner/seedsigner).
1. Translators work within Transifex on their respective languages.
1. Completed translations are downloaded as `messages.po` files for each language.
1. Python "compiles" them into `messages.mo` files ready for use.
1. The `*.po` and `*.mo` files are written to the [seedsigner-translations](https://github.com/SeedSigner/seedsigner-translations) repo.
1. That repo is linked as a submodule here as `seedsigner.resources.seedsigner-translations`.
1. Python code retrieves a translation on demand.


## "Wrapping" text for translation
Any text that we want to be presented in multiple languages needs to "wrapped".

The CORE CONCEPT to understand is that wrapping is used in TWO different contexts:
1. Pre-translation: This is how we identify text that translators need to translate. Any wrapped string literals will appear in translators' Transifex UI.
2. Post-translation: Return the locale-specific translation for that source string (defaults to the English string if no translation is found).

We have three techniques to wrap code, depending on which of the above contexts we're in and where we are in the code:


#### Technique 1: `ButtonOption`
Most `View` classes will render themselves via some variation of the `ButtonListScreen` which takes a `button_data` list as an input. Each entry in
`button_data` must be a `ButtonOption`. The first argument for `ButtonOption` is the `button_label` string. This is the English string literal that
is displayed in that button. If you look at `setup.cfg` you'll see that `ButtonOption` is listed as a keyword in `extract_messages`. That means
that the first argument for `ButtonOption` -- its `button_label` string -- will be marked for translation (by default the `extract_messages`
integration will only look at the first argument of any method listed in `keywords`).

```python
class SomeView(View):
    # These string literals will be marked for translation
    OPTION_1 = ButtonOption("Option 1!")
    OPTION_2 = ButtonOption("Option 2!")

    def run(self):
        button_data = [self.OPTION_1, self.OPTION_2]

        # No way for `extract_messages` to know what's in `some_var`; won't be marked for
        # translation unless it's specified elsewhere.
        some_var = some_value
        button_data.append(ButtonOption(some_var))
```

These `ButtonOption` values are generally specified in class-level attributes, as in the above example. Classes in python are imported once, after
which class-level attributes are never reinterpreted again; **the value at import time for a class-level attribute is its value for the duration of
the program execution.**

This means that we must assume that `ButtonOption.button_label` strings are ALWAYS the original English string. This is crucial because the English
values are the lookup keys for the translations:

* `ButtonOption.button_label` = "Hello!" in the python code.
* Run the code, the class that contains our `ButtonOption` as a class-level attribute is imported.
* Regardless of language selection, that `ButtonOption` will always return "Hello!".
* `Screen` then uses "Hello!" as a key to find the translation "¡Hola!".
* User sees "¡Hola!".

IF `ButtonOption` were wired to return the translated string, we'd have a problem:
* User sets their language to Spanish and enables persistent settings.
* Launch SeedSigner. At import time the `button_label`'s value is translated to "¡Hola!".
* User sees "¡Hola!" in the UI. All good.
* User changes language to English (or any other language).
* Now the `Screen` must find the matching string in a different translation file.
* But the `button_label` value was fixed at import time; it's still providing "¡Hola!" as the lookup key.
* Since all the translation files map English -> translation, no such "¡Hola!" match exists in any translation file.
* So the translation falls back to just displaying the unmatched key: "¡Hola!"

tldr: `ButtonOption` marks its `button_label` English string literal for translation, but NEVER provides a translated value.

---

#### Technique 2: `seedsigner.helpers.l10n.mark_for_translation`
You'll see that `mark_for_translation` is imported as `_mft` for short.

As far as translations are concerned, `_mft` serves the same purpose as `ButtonOption`. The only difference is that `_mft` is for all other
(non-`button_data`) class-level attributes.

```python
from seedsigner.helpers.l10n import mark_for_translation as _mft

@classmethod
class SomeView(View):
    title: str = _mft("Default Title")
    text: str = _mft("My default body text")

    def run(self):
        self.run_screen(
            SomeScreen,
            title=self.title,
            text=self.text
        )
```

In general we try to avoid using `_mft` at all, but some class-level attributes just can't be avoided.

---

#### Technique 3: `gettext`, aka `_()`
This is the way you'll see text wrapping handled in the vast majority of tutorials.

```python
from gettext import gettext as _

my_text = _("Hello!")

# Specify Spanish
os.environ['LANGUAGE'] = "es"
print(my_text)
>> ¡Hola!

# Specify English
os.environ['LANGUAGE'] = "en"
print(my_text)
>> Hello!
```

This approach marks string literals for translation AND retrieves the translated text.

We do the same in SeedSigner code, but only when the string literal is in a part of the code that is dynamically evaluated:

```python
from gettext import gettext as _

class SomeView(View):
    def __init__(self):
        # Mark string literal for translation AND dynamically retrieve its translated value
        self.some_var = _("I will be dynamically fetched")
```

Though note that there are times when we use `_()` only for the retrieval side:

```python
from seedsigner.helpers.l10n import mark_for_translation as _mft

class SomeView(View):
    message = _mft("Hello!")  # mark for translation, but always return "Hello!"

    def run(self):
        self.run_screen(
            SomeScreen,
            message=self.title
        )
  
# elsewhere...
@dataclass
class SomeScreen(Screen):
    message: str = None

    def __post_init__(self):
        message_display = TextArea(
            text=_(self.message)  # The _() wrapping here now retrieves the translated value, if one is available
        )
```

---

## Basic rules
* English string literals in class-level attributes should be wrapped with either `ButtonOption` (for `button_data` entries) or `_mft` (for misc class-level attrs) so they'll be picked up for translation.
* English string literals anywhere else should be wrapped with `_()` to be marked for translation AND provide the dynamic translated value.
* In general, don't go out of your way to translate text before passing it into `Screen` classes.
  * The `Screen` itself should do most of the `_()` calls to fetch translations for final display.
  * Minor risk of double-translation weirdness otherwise.

Mark for translation in the `View`. Retrieve translated values in the `Screen`. Pass final display text into the basic gui `Component`s.

---

## Provide translation context hints
In many cases the English string literal on its own does not provide enough context for translators to understand how the word is being used.

For example, is "change" referring to altering a value OR is it the amount coming back to you in a transaction?

Whenever necessary, add explanatory context as a comment. This applies to all three ways of marking strings for translation.

The `extract_messages` command is explictly looking for the exact string: `# TRANSLATOR_NOTE:` in comments.

```python
class SeedAddressVerificationView(View):
    # TRANSLATOR_NOTE: Option when scanning for a matching address; skips ten addresses ahead
    SKIP_10 = ButtonOption("Skip 10")
```

Note that the comment MUST be on the preceding line of executable code for it to work:

```python
class SettingsConstants
    # TRANSLATOR_NOTE: QR code density option: Low, Medium, High       <-- ✅ Correct way to add context
    density_low = _mft("Low")

    ALL_DENSITIES = [
        (DENSITY__LOW, density_low),
        # TRANSLATOR_NOTE: QR code density option: Low, Medium, High   <-- ❌ Note will NOT be picked up
        (DENSITY__MEDIUM, "Medium"),
        (DENSITY__HIGH, "High"),
    ]
```

```python
# TRANSLATOR_NOTE: Refers to the user's change output in a psbt
some_var = _("change")
```

---

## `_()` Wrapping syntax details
* Use `.format()` to wrap strings with variable injections. Note that `.format()` is OUTSIDE the `_()` wrapping.
    ```python
    mystr = f"My dad's name is {dad.name} and my name is {self.name}."
    mystr = _("My dad's name is {} and my name is {}").format(dad.name, self.name)
    ```

    The translators will only see: "My dad's name is {} and my name is {}" in Transifex. Often the English string literal is 
    basically incomprehensible on its own so always provide an explanation for what is being injected:

    ```python
    # TRANSLATOR_NOTE: Address verification success message (e.g. "bc1qabc = seed 12345678's receive address #0.")
    text = _("{} = {}'s {} address #{}.").format(...)
    ```

    If there are a lot of variables to inject, placeholder names can be used (TODO: how does Transifex display this?):
    ```python
    mystr = _("My dad's name is {dad_name} and my name is {my_name}").format(dad_name=dad.name, my_name=self.name)
    ```
* Use `ngettext` to dynamically handle singular vs plural forms based on an integer quantity:
    ```python
    n = 1
    print(ngettext("apple", "apples", n))
    >> apple
    
    n = 5
    print(ngettext("apple", "apples", n))
    >> apples
    ```

Transifex will ask translators to provide the singular and plural forms on a language-specific basis (e.g. Arabic as THREE plural forms!).

---

## Set up localization dependencies
```bash
pip install -r l10n/requirements-l10n.txt
```

Make sure that your local repo has fetched the `seedsigner-translations` submodule. It's configured to add it in src/seedsigner/resources.
```bash
# Need --remote in order to respect the target branch listed in .gitmodules
git submodule update --remote
```


### Pre-configured `babel` commands
The `setup.cfg` file in the project root specifies params for the various `babel` commands discussed below.

You should have already added the local code as an editable project in pip:
```bash
# From the repo root
pip install -e .
```


### Rescanning for text that needs translations
Re-generate the `messages.pot` file:

```bash
python setup.py extract_messages
```

This will rescan all wrapped text, picking up new strings as well as updating existings strings that have been edited.

_TODO: Github Action to auto-generate messages.pot and fail a PR update if the PR has an out of date messages.pot?_


### Making new text available to translators
Upload the master `messages.pot` to Transifex. It will automatically update each language with the new or changed source strings.

_TODO: Look into Transifex options to automatically pull updates?_


### Once new translations are complete
The translation file for each language will need to be downloaded via Transifex's "Download for use" option (sends you a `messages.po` file for that language).

This updated `messages.po` should be added to the seedsigner-translations repo in l10n/`{TARGET_LOCALE}`/LC_MESSAGES.


### Compile all the translations
The `messages.po` files must be compiled into `*.mo` files:

```bash
python setup.py compile_catalog

# Or target a specific language code:
python setup.py compile_catalog -l es
```

### Unused babel commands
Transifex eliminates the need for the `init_catalog` and `update_catalog` commands.


## Keep the seedsigner-translations repo up to date
The *.po files for each language and their compiled *.mo files should all be kept up to date in the seedsigner-translations repo.

_TODO: Github Actions automation to regenerate / verify that the *.mo files have been updated after *.po changes._

---

## Generate screenshots in each language
Simply run the screenshot generator:

```bash
pytest tests/screenshot_generator/generator.py

# Or target a specific language code:
pytest tests/screenshot_generator/generator.py --locale es
```
