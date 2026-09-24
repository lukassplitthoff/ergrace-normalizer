"""
ERGrace - composition-fair rowing races.

Pick the class that matches the race:

* :class:`RelayRace` -- a team takes turns on ONE ergometer (any team size/mix).
* :class:`MixedRace` -- individuals of different categories, one ergometer each.
* :class:`CrewRace`  -- boats of different classes with mixed crews, on the water.

Each takes ``time=`` or ``distance=``, computes handicaps before the race
(staggered starts or target distances) and a power score after it.
:class:`ERGNormalizer` (men/women timed relay) and :class:`HandicapRace`
(on-water staggered start) are the earlier interfaces, kept for compatibility.
"""

from .normalizer import ERGNormalizer
from .handicap import HandicapRace
from .references import BoatReferences, References, format_time, parse_time
from .races import CrewRace, MixedRace, RelayRace

__version__ = "0.2.0"
__all__ = ["RelayRace", "MixedRace", "CrewRace", "References", "BoatReferences", "ERGNormalizer", "HandicapRace",
           "parse_time", "format_time"]
