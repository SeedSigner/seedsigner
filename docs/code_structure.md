# Code Structure

SeedSigner roughly follows a Model-View-Controller approach. Like in a typical web app (e.g. Flask), the `View`s can be called as needed like individual web URLs. After completing display and interaction with the user, the `View` then decides where to route the user next, analogous to a web app returning a `response.redirect(URL)`.

The `Controller` then ends up being quite stripped down. For example, there's no need for a web app's `urls.py` since there are no mappings from URL to `View` to maintain since we're not actually using a URL/HTTP routing approach.

`View`s have to handle user interaction, so there are `while True` loops that cycle between waiting for user input, gathering data, and then updating the UI components accordingly. You wouldn't find this kind of cycle in a web app because this sort of interactive user input is handled in the browser at the HTML/CSS/JS level.

* `Model`s: Store the persistent settings, the in-memory seeds, current wallet information, etc.
* `Controller`: Manages the state of the world and controls access to global resources.
* `View`s: Implementation of each screen. Prepares relevant data for display. Must also instantiate the display objects that will actually render the UI.
* `gui.screens`: Reusable formatted UI renderers.
* `gui.components`: Basic individual UI elements that are used by the `templates` such as the top nav, buttons, button lists, text displays.

In a typical web server context, the `View` would send data to an HTML template (e.g. Jinja) which would then dynamically populate the page with HTML elements like `<input>`, `<button>`, `<img>`, etc. This is analogous to our `gui.screens` constructing a UI renderer by piecing together various `gui.components` as needed.

`Controller` is a global singleton that any `View` can access and update as needed.
