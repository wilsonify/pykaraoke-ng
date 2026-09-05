"""PyScript bridge: expose the karaoke engine to app.js.

Loaded as ``<script type="py" src="bridge.py">`` by PyScript.  Builds a
:class:`pykaraoke.webapp.KaraokeApp` and publishes a single JSON-friendly
dispatcher to ``window.pykaraoke_api``.

Boundary rules:

* JS ``Uint8Array`` arguments arrive as Python ``bytes``/``memoryview``
  (Pyodide auto-conversion), which the engine accepts directly.
* JS objects/arrays are converted deeply with ``to_py()`` so the engine
  sees plain dicts/lists.
* Return values are Python objects; app.js converts PyProxies with
  ``toJs()``.  ``None`` becomes JS ``undefined`` automatically.
"""

from js import window

from pykaraoke.webapp import KaraokeApp

app = KaraokeApp()


def _to_py(value):
    """Deep-convert a JS value into a plain Python value."""
    if hasattr(value, "to_py"):
        return value.to_py()
    return value


def api(name, *args):
    """Call ``app.<name>(*args)`` with converted arguments."""
    return getattr(app, name)(*[_to_py(a) for a in args])


window.pykaraoke_api = api