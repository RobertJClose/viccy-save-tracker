"""One-shot setup tasks deriving player bonuses from in-game research.

Each module builds reference data from the game install's technologies,
inventions and westernisation reforms: the exhaustive modifier-name
list plus one matrix task per modifier category. All tasks are run via
``python -m setup.initialise``.
"""