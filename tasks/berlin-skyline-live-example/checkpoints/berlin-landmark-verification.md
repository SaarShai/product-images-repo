# Berlin Landmark Verification

Date: 2026-06-16

Purpose: record the lookup behind the first element-sheet correction after user
feedback on `outputs/generated/20260616-berlin-elements-v1.png`.

## Verified Elements

- Berlin Cathedral / Berliner Dom:
  - Use as the central domed building.
  - Source note: visitBerlin describes the Cathedral Church as dominated by a
    monumental dome with a lantern and golden cross, flanked by four towers.
  - Source: https://www.visitberlin.de/en/berlin-cathedral

- Kaiser Wilhelm Memorial Church:
  - Use as the central damaged/old tower or spire-like church element.
  - Source note: Berlin.de describes it as one of Berlin's famous landmarks;
    the old church ruin was converted into a war memorial, and the striking
    ruined tower rises into the sky.
  - Source:
    https://www.berlin.de/en/attractions-and-sights/3561433-3104052-kaiser-wilhelm-memorial-church.en.html

- Oberbaum Bridge:
  - Use only as an Oberbaum-inspired bridge/viaduct arch if a recognizable
    named bridge is needed.
  - Source note: Berlin.de describes the red-brick Oberbaum Bridge as a
    double-deck bridge with two middle-arch towers; the subway also runs over
    it.
  - Source:
    https://www.berlin.de/en/attractions-and-sights/3559975-3104052-oberbaum-bridge.en.html
  - Task note: the user's render also shows Potsdamer Platz/Beisheim context,
    so the bridge in the reference should be treated as a stylized Berlin
    bridge/viaduct motif unless the user specifically wants literal Oberbaum
    Bridge.

- Ritz-Carlton / Beisheim Center / Potsdamer Platz:
  - Use as the right-side hotel/high-rise element, with full lower podium/wing,
    not only the tall tower shaft.
  - Source note: Beisheim Center includes the five-star Ritz-Carlton and Berlin
    Marriott at Potsdamer Platz; the ensemble is described as a key urban
    ensemble with a striking Ritz-Carlton/Tower Apartments silhouette.
  - Source: https://www.tih.berlin/en/immobilien/beisheim-center-2/
  - Source: https://www.ritzcarlton.com/en/hotels/berzt-the-ritz-carlton-berlin/overview/

## Prompt Consequences

- Regenerate the element sheet rather than locally patching v1.
- The right-side high-rise must include the lower section/podium/wing visible in
  the user's Ritz/Beisheim reference photo.
- Keep the green Potsdamer traffic-light/clock tower excluded from the first
  candidate.
- Make the middle elements explicitly Berliner Dom and Kaiser Wilhelm Memorial
  Church.
- Keep the bridge as a separate simplified Berlin bridge/viaduct arch. If
  literal naming helps style, make it Oberbaum-inspired, with no readable
  signage.
