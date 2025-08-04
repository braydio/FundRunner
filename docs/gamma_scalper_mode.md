# Gamma Scalper Mode

The gamma scalper mode uses option delta values to keep a position close to
delta-neutral.  When the combined delta of a symbol's option positions drifts
beyond a threshold, the bot hedges by buying or selling shares of the
underlying stock through Alpaca's order API.

Run the mode from the main menu and specify a symbol to hedge.  The mode uses
the existing portfolio and trade managers and therefore shares configuration
and risk controls with other trading modes.
