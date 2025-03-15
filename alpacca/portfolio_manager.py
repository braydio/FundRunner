# portfolio_manager.py
from api_client import AlpacaClient
from config import SIMULATION_MODE, SIMULATED_STARTING_CASH

class SimulatedAccount:
    def __init__(self, starting_cash):
        self.cash = starting_cash
        self.buying_power = starting_cash
        self.equity = starting_cash
        self.portfolio_value = starting_cash

    def __str__(self):
        return f"Cash: {self.cash}, Buying Power: {self.buying_power}, Equity: {self.equity}, Portfolio Value: {self.portfolio_value}"

class PortfolioManager:
    def __init__(self):
        if SIMULATION_MODE:
            self.client = None
        else:
            self.client = AlpacaClient()

    def view_account(self):
        if SIMULATION_MODE:
            return SimulatedAccount(SIMULATED_STARTING_CASH)
        return self.client.get_account()

    def view_positions(self):
        if SIMULATION_MODE:
            # For simulation, assume no positions by default.
            return []
        return self.client.list_positions()

    def view_position(self, symbol):
        if SIMULATION_MODE:
            return None
        return self.client.get_position(symbol)

