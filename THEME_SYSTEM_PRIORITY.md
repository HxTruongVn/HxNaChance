# NaChance Theme System Priority

## Rule

Workshop content and workflow are not modified by the host theme.

The NaChance system theme has priority for **UI chrome only**:
- window background
- panels/cards
- labels and other UI text
- buttons
- borders
- hover/active states
- standard controls

Workshop-owned **content/data** remains untouched:
- user-selected colors
- image/pipeline data
- values entered by the user
- preview data
- workshop labels and business wording
- workshop workflow and layout logic

A workshop must consume the theme supplied by the host system rather than define a competing application theme.

## Priority

NaChance system theme
  -> Workshop host/window
     -> Workshop UI chrome

Workshop content/data
  -> remains under Workshop/user control
