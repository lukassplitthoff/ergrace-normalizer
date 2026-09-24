"""
ERGrace - composition-fair rowing races.

Pick the class that matches the race:

* :class:`RelayRace` -- a team takes turns on ONE ergometer (any team size/mix).
* :class:`MixedRace` -- individuals of different categories, one ergometer each.
* :class:`CrewRace`  -- boats of different classes with mixed crews, on the water.

Each takes ``time=`` or ``distance=``, computes handicaps before the race
(staggered starts or target distances) and a power score after it.
:class:`ERGNormalizer` is the original men/women timed-relay interface used in
the RRC 2026 report; it gives the same scores as :class:`RelayRace`.
"""

from .normalizer import ERGNormalizer
from .references import BoatReferences, References, format_time, parse_time
from .races import CrewRace, MixedRace, RelayRace

__version__ = "0.2.0"
__all__ = ["RelayRace", "MixedRace", "CrewRace", "References", "BoatReferences", "ERGNormalizer",
           "parse_time", "format_time"]
