import os
from decimal import Decimal
from typing import Dict, List, Set

import pandas as pd
from pydantic import Field, validator

from hummingbot.client.config.config_data_types import ClientFieldData
from hummingbot.client.ui.interface_utils import format_df_for_printout
from hummingbot.connector.connector_base import ConnectorBase
from hummingbot.core.clock import Clock
from hummingbot.core.data_type.common import OrderType, PositionAction, PositionMode, PriceType, TradeType
from hummingbot.core.event.events import FundingPaymentCompletedEvent
from hummingbot.data_feed.candles_feed.data_types import CandlesConfig
from hummingbot.strategy.strategy_v2_base import StrategyV2Base, StrategyV2ConfigBase
from hummingbot.strategy_v2.executors.position_executor.data_types import PositionExecutorConfig, TripleBarrierConfig
from hummingbot.strategy_v2.models.executor_actions import CreateExecutorAction, StopExecutorAction


class FundingRateArbitrageConfig(StrategyV2ConfigBase):
    script_file_name: str = Field(default_factory=lambda: os.path.basename(__file__))
    candles_config: List[CandlesConfig] = []
    controllers_config: List[str] = []
    markets: Dict[str, Set[str]] = {}
    leverage: int = Field(
        default=20, gt=0,
        client_data=ClientFieldData(
            prompt=lambda mi: "Enter the leverage (e.g. 20): ",
            prompt_on_new=True))

    min_funding_rate_profitability: Decimal = Field(
        default=0.001,
        client_data=ClientFieldData(
            prompt=lambda mi: "Enter the min funding rate profitability to enter in a position: ",
            prompt_on_new=True
        )
    )
    connectors: Set[str] = Field(
        default="hyperliquid_perpetual,binance_perpetual",
        client_data=ClientFieldData(
            prompt_on_new=True,
            prompt=lambda mi: "Enter the connectors separated by commas:",
        )
    )
    tokens: Set[str] = Field(
        default="WIF,FET",
        client_data=ClientFieldData(
            prompt_on_new=True,
            prompt=lambda mi: "Enter the tokens separated by commas:",
        )
    )
    position_size_quote: Decimal = Field(
        default=100,
        client_data=ClientFieldData(
            prompt_on_new=True,
            prompt=lambda mi: "Enter the position size for each token and exchange (e.g. order amount 100 will open 100 long on hyperliquid and 100 short on binance):",
        )
    )
    profitability_to_take_profit: Decimal = Field(
        default=0.01,
        client_data=ClientFieldData(
            prompt_on_new=True,
            prompt=lambda mi: "Enter the profitability to take profit (including PNL of positions and fundings received): ",
        )
    )
    funding_rate_diff_stop_loss: Decimal = Field(
        default=-0.001,
        client_data=ClientFieldData(
            prompt=lambda mi: "Enter the funding rate difference to stop the position: ",
            prompt_on_new=True
        )
    )
    trade_profitability_condition_to_enter: bool = Field(
        default=False,
        client_data=ClientFieldData(
            prompt=lambda mi: "Create the position if the trade profitability is positive only: ",
            prompt_on_new=True
        ))
    fee_mode: str = Field(
        default="taker",
        client_data=ClientFieldData(
            prompt=lambda mi: "Enter the fee mode (taker/maker/mixed): ",
            prompt_on_new=True))

    @validator("connectors", "tokens", pre=True, allow_reuse=True, always=True)
    def validate_sets(cls, v):
        if isinstance(v, str):
            return set(v.split(","))
        return v


class FundingRateArbitrage(StrategyV2Base):
    quote_markets_map = {
        "hyperliquid_perpetual": "USD",
        "binance_perpetual": "USDT"
    }
    funding_payment_interval_map = {
        "binance_perpetual": 60 * 60 * 8,
        "hyperliquid_perpetual": 60 * 60 * 1
    }
    funding_profitability_interval = 60 * 60 * 24

    @classmethod
    def get_trading_pair_for_connector(cls, token, connector):
        return f"{token}-{cls.quote_markets_map.get(connector, 'USDT')}"

    @classmethod
    def init_markets(cls, config: FundingRateArbitrageConfig):
        markets = {}
        for connector in config.connectors:
            trading_pairs = {cls.get_trading_pair_for_connector(token, connector) for token in config.tokens}
            markets[connector] = trading_pairs
        cls.markets = markets

    def __init__(self, connectors: Dict[str, ConnectorBase], config: FundingRateArbitrageConfig):
        super().__init__(connectors, config)
        self.config = config
        self.active_funding_arbitrages = {}
        self.stopped_funding_arbitrages = {token: [] for token in self.config.tokens}

    async def start(self, clock: Clock, timestamp: float) -> None:
        """
        Start the strategy.
        :param clock: Clock to use.
        :param timestamp: Current time.
        """
        try:
            self._last_timestamp = timestamp
            await self.apply_initial_setting()
            self.ready_to_trade = True
            self.logger().info("Strategy is ready to trade.")
        except Exception as e:
            self.logger().error("Error in start", exc_info=True)

    async def apply_initial_setting(self):
        try:
            for connector_name, connector in self.connectors.items():
                if self.is_perpetual(connector_name):
                    position_mode = PositionMode.ONEWAY if connector_name == "hyperliquid_perpetual" else PositionMode.HEDGE
                    connector.set_position_mode(position_mode)
                    for trading_pair in self.market_data_provider.get_trading_pairs(connector_name):
                        connector.set_leverage(trading_pair, self.config.leverage)
        except Exception as e:
            self.logger().error("Error in apply_initial_setting", exc_info=True)

    async def get_funding_info_by_token(self, token):
        """
        This method provides the funding rates across all the connectors
        """
        try:
            funding_rates = {}
            for connector_name, connector in self.connectors.items():
                trading_pair = self.get_trading_pair_for_connector(token, connector_name)
                funding_rates[connector_name] = connector.get_funding_info(trading_pair)
            return funding_rates
        except Exception as e:
            self.logger().error("Error in get_funding_info_by_token", exc_info=True)

    async def get_current_profitability_after_fees(self, token: str, connector_1: str, connector_2: str, side: TradeType):
        """
        This methods compares the profitability of buying at market in the two exchanges. If the side is TradeType.BUY
        means that the operation is long on connector 1 and short on connector 2.
        """
        try:
            trading_pair_1 = self.get_trading_pair_for_connector(token, connector_1)
            trading_pair_2 = self.get_trading_pair_for_connector(token, connector_2)

            connector_1_price = Decimal(self.market_data_provider.get_price_for_quote_volume(
                connector_name=connector_1,
                trading_pair=trading_pair_1,
                quote_volume=self.config.position_size_quote,
                is_buy=side == TradeType.BUY,
            ).result_price)
            connector_2_price = Decimal(self.market_data_provider.get_price_for_quote_volume(
                connector_name=connector_2,
                trading_pair=trading_pair_2,
                quote_volume=self.config.position_size_quote,
                is_buy=side != TradeType.BUY,
            ).result_price)

            # Determine the fee mode and calculate fees accordingly
            if self.config.fee_mode == "taker":
                is_maker_1 = False
                is_maker_2 = False
            elif self.config.fee_mode == "maker":
                is_maker_1 = True
                is_maker_2 = True
            else:  # mixed
                is_maker_1 = False
                is_maker_2 = True

            estimated_fees_connector_1 = self.connectors[connector_1].get_fee(
                base_currency=trading_pair_1.split("-")[0],
                quote_currency=trading_pair_1.split("-")[1],
                order_type=OrderType.MARKET,
                order_side=TradeType.BUY,
                amount=self.config.position_size_quote / connector_1_price,
                price=connector_1_price,
                is_maker=is_maker_1,
                position_action=PositionAction.OPEN
            ).percent
            estimated_fees_connector_2 = self.connectors[connector_2].get_fee(
                base_currency=trading_pair_2.split("-")[0],
                quote_currency=trading_pair_2.split("-")[1],
                order_type=OrderType.MARKET,
                order_side=TradeType.BUY,
                amount=self.config.position_size_quote / connector_2_price,
                price=connector_2_price,
                is_maker=is_maker_2,
                position_action=PositionAction.OPEN
            ).percent

            if side == TradeType.BUY:
                estimated_trade_pnl_pct = (connector_2_price - connector_1_price) / connector_1_price
            else:
                estimated_trade_pnl_pct = (connector_1_price - connector_2_price) / connector_2_price
            return estimated_trade_pnl_pct - estimated_fees_connector_1 - estimated_fees_connector_2
        except Exception as e:
            self.logger().error("Error in get_current_profitability_after_fees", exc_info=True)

    async def get_most_profitable_combination(self, funding_info_report: Dict):
        try:
            profitable_combinations = []
            for connector_1 in funding_info_report:
                for connector_2 in funding_info_report:
                    if connector_1 != connector_2:
                        rate_connector_1 = self.get_normalized_funding_rate_in_seconds(funding_info_report, connector_1)
                        rate_connector_2 = self.get_normalized_funding_rate_in_seconds(funding_info_report, connector_2)
                        funding_rate_diff = abs(rate_connector_1 - rate_connector_2) * self.funding_profitability_interval
                        if funding_rate_diff > 0:  # Assuming a threshold of 0 for simplicity
                            trade_side = TradeType.BUY if rate_connector_1 < rate_connector_2 else TradeType.SELL
                            profitable_combinations.append((connector_1, connector_2, trade_side, funding_rate_diff))
            # Sort combinations by profitability in descending order
            profitable_combinations.sort(key=lambda x: x[3], reverse=True)
            return profitable_combinations
        except Exception as e:
            self.logger().error("Error in get_most_profitable_combination", exc_info=True)

    async def get_normalized_funding_rate_in_seconds(self, funding_info_report, connector_name):
        try:
            return funding_info_report[connector_name].rate / self.funding_payment_interval_map.get(connector_name, 60 * 60 * 8)
        except Exception as e:
            self.logger().error("Error in get_normalized_funding_rate_in_seconds", exc_info=True)

    async def create_actions_proposal(self) -> List[CreateExecutorAction]:
        """
        In this method we are going to evaluate if a new set of positions has to be created for each of the tokens that
        don't have an active arbitrage.
        More filters can be applied to limit the creation of the positions, since the current logic is only checking for
        positive pnl between funding rate. Is logged and computed the trading profitability at the time for entering
        at market to open the possibilities for other people to create variations like sending limit position executors
        and if one gets filled buy market the other one to improve the entry prices.
        """
        try:
            create_actions = []
            for token in self.config.tokens:
                if token not in self.active_funding_arbitrages:
                    funding_info_report = await self.get_funding_info_by_token(token)
                    best_combinations = await self.get_most_profitable_combination(funding_info_report)
                    for combination in best_combinations:
                        connector_1, connector_2, trade_side, expected_profitability = combination
                        if expected_profitability >= self.config.min_funding_rate_profitability:
                            current_profitability = await self.get_current_profitability_after_fees(
                                token, connector_1, connector_2, trade_side
                            )
                            if self.config.trade_profitability_condition_to_enter:
                                if current_profitability < 0:
                                    self.logger().info(f"Best Combination: {connector_1} | {connector_2} | {trade_side}"
                                                       f"Funding rate profitability: {expected_profitability}"
                                                       f"Trading profitability after fees: {current_profitability}"
                                                       f"Trade profitability is negative, skipping...")
                                    continue
                            self.logger().info(f"Best Combination: {connector_1} | {connector_2} | {trade_side}"
                                               f"Funding rate profitability: {expected_profitability}"
                                               f"Trading profitability after fees: {current_profitability}"
                                               f"Starting executors...")
                            position_executor_config_1, position_executor_config_2 = await self.get_position_executors_config(token, connector_1, connector_2, trade_side)
                            self.active_funding_arbitrages[token] = {
                                "connector_1": connector_1,
                                "connector_2": connector_2,
                                "executors_ids": [position_executor_config_1.id, position_executor_config_2.id],
                                "side": trade_side,
                                "funding_payments": [],
                            }
                            create_actions.extend([CreateExecutorAction(executor_config=position_executor_config_1),
                                                    CreateExecutorAction(executor_config=position_executor_config_2)])
            return create_actions
        except Exception as e:
            self.logger().error("Error in create_actions_proposal", exc_info=True)

    async def stop_actions_proposal(self) -> List[StopExecutorAction]:
        """
        Once the funding rate arbitrage is created we are going to control the funding payments pnl and the current
        pnl of each of the executors at the cost of closing the open position at market.
        If that PNL is greater than the profitability_to_take_profit
        """
        try:
            stop_executor_actions = []
            for token, funding_arbitrage_info in self.active_funding_arbitrages.items():
                executors = self.filter_executors(
                    executors=self.get_all_executors(),
                    filter_func=lambda x: x.id in funding_arbitrage_info["executors_ids"]
                )
                funding_payments_pnl = sum(funding_payment.amount for funding_payment in funding_arbitrage_info["funding_payments"])
                executors_pnl = sum(executor.net_pnl_quote for executor in executors)
                take_profit_condition = executors_pnl + funding_payments_pnl > self.config.profitability_to_take_profit * self.config.position_size_quote
                funding_info_report = await self.get_funding_info_by_token(token)
                if funding_arbitrage_info["side"] == TradeType.BUY:
                    funding_rate_diff = await self.get_normalized_funding_rate_in_seconds(funding_info_report, funding_arbitrage_info["connector_2"]) - await self.get_normalized_funding_rate_in_seconds(funding_info_report, funding_arbitrage_info["connector_1"])
                else:
                    funding_rate_diff = await self.get_normalized_funding_rate_in_seconds(funding_info_report, funding_arbitrage_info["connector_1"]) - await self.get_normalized_funding_rate_in_seconds(funding_info_report, funding_arbitrage_info["connector_2"])
                current_funding_condition = funding_rate_diff * self.funding_profitability_interval < self.config.funding_rate_diff_stop_loss
                if take_profit_condition:
                    self.logger().info("Take profit profitability reached, stopping executors")
                    self.stopped_funding_arbitrages[token].append(funding_arbitrage_info)
                    stop_executor_actions.extend([StopExecutorAction(executor_id=executor.id) for executor in executors])
                elif current_funding_condition:
                    self.logger().info("Funding rate difference reached for stop loss, stopping executors")
                    self.stopped_funding_arbitrages[token].append(funding_arbitrage_info)
                    stop_executor_actions.extend([StopExecutorAction(executor_id=executor.id) for executor in executors])
            return stop_executor_actions
        except Exception as e:
            self.logger().error("Error in stop_actions_proposal", exc_info=True)

    async def did_complete_funding_payment(self, funding_payment_completed_event: FundingPaymentCompletedEvent):
        """
        Based on the funding payment event received, check if one of the active arbitrages matches to add the event
        to the list.
        """
        try:
            token = funding_payment_completed_event.trading_pair.split("-")[0]
            if token in self.active_funding_arbitrages:
                self.active_funding_arbitrages[token]["funding_payments"].append(funding_payment_completed_event)
        except Exception as e:
            self.logger().error("Error in did_complete_funding_payment", exc_info=True)

    async def get_position_executors_config(self, token, connector_1, connector_2, trade_side):
        try:
            price = self.market_data_provider.get_price_by_type(
                connector_name=connector_1,
                trading_pair=self.get_trading_pair_for_connector(token, connector_1),
                price_type=PriceType.MidPrice
            )
            position_amount = self.config.position_size_quote / price

            position_executor_config_1 = PositionExecutorConfig(
                timestamp=self.current_timestamp,
                connector_name=connector_1,
                trading_pair=self.get_trading_pair_for_connector(token, connector_1),
                side=trade_side,
                amount=position_amount,
                leverage=self.config.leverage,
                triple_barrier_config=TripleBarrierConfig(open_order_type=OrderType.MARKET),
            )
            position_executor_config_2 = PositionExecutorConfig(
                timestamp=self.current_timestamp,
                connector_name=connector_2,
                trading_pair=self.get_trading_pair_for_connector(token, connector_2),
                side=TradeType.BUY if trade_side == TradeType.SELL else TradeType.SELL,
                amount=position_amount,
                leverage=self.config.leverage,
                triple_barrier_config=TripleBarrierConfig(open_order_type=OrderType.MARKET),
            )
            return position_executor_config_1, position_executor_config_2
        except Exception as e:
            self.logger().error("Error in get_position_executors_config", exc_info=True)

    async def format_status(self) -> str:
        try:
            original_status = super().format_status()
            funding_rate_status = []
            if self.ready_to_trade:
                all_funding_info = []
                all_best_paths = []
                for token in self.config.tokens:
                    token_info = {"token": token}
                    best_paths_info = {"token": token}
                    funding_info_report = await self.get_funding_info_by_token(token)
                    best_combinations = await self.get_most_profitable_combination(funding_info_report)
                    for connector_name, info in funding_info_report.items():
                        token_info[f"{connector_name} Rate (%)"] = await self.get_normalized_funding_rate_in_seconds(funding_info_report, connector_name) * self.funding_profitability_interval * 100
                    for combination in best_combinations:
                        connector_1, connector_2, side, funding_rate_diff = combination
                        profitability_after_fees = await self.get_current_profitability_after_fees(token, connector_1, connector_2, side)
                        best_paths_info[f"Best Path {combination}"] = f"{connector_1}_{connector_2}"
                        best_paths_info[f"Best Rate Diff (%) {combination}"] = funding_rate_diff * 100
                        best_paths_info[f"Trade Profitability (%) {combination}"] = profitability_after_fees * 100
                        best_paths_info[f"Days Trade Prof {combination}"] = - profitability_after_fees / funding_rate_diff
                        best_paths_info[f"Days to TP {combination}"] = (self.config.profitability_to_take_profit - profitability_after_fees) / funding_rate_diff

                        time_to_next_funding_info_c1 = funding_info_report[connector_1].next_funding_utc_timestamp - self.current_timestamp
                        time_to_next_funding_info_c2 = funding_info_report[connector_2].next_funding_utc_timestamp - self.current_timestamp
                        best_paths_info[f"Min to Funding 1 {combination}"] = time_to_next_funding_info_c1 / 60
                        best_paths_info[f"Min to Funding 2 {combination}"] = time_to_next_funding_info_c2 / 60

                    all_funding_info.append(token_info)
                    all_best_paths.append(best_paths_info)
                funding_rate_status.append(f"\n\n\nMin Funding Rate Profitability: {self.config.min_funding_rate_profitability:.2%}")
                funding_rate_status.append(f"Profitability to Take Profit: {self.config.profitability_to_take_profit:.2%}\n")
                funding_rate_status.append("Funding Rate Info (Funding Profitability in Days): ")
                funding_rate_status.append(format_df_for_printout(df=pd.DataFrame(all_funding_info), table_format="psql",))
                funding_rate_status.append(format_df_for_printout(df=pd.DataFrame(all_best_paths), table_format="psql",))
                for token, funding_arbitrage_info in self.active_funding_arbitrages.items():
                    long_connector = funding_arbitrage_info["connector_1"] if funding_arbitrage_info["side"] == TradeType.BUY else funding_arbitrage_info["connector_2"]
                    short_connector = funding_arbitrage_info["connector_2"] if funding_arbitrage_info["side"] == TradeType.BUY else funding_arbitrage_info["connector_1"]
                    funding_rate_status.append(f"Token: {token}")
                    funding_rate_status.append(f"Long connector: {long_connector} | Short connector: {short_connector}")
                    funding_rate_status.append(f"Funding Payments Collected: {funding_arbitrage_info['funding_payments']}")
                    funding_rate_status.append(f"Executors: {funding_arbitrage_info['executors_ids']}")
                    funding_rate_status.append("-" * 50 + "\n")
            return original_status + "\n".join(funding_rate_status)
        except Exception as e:
            self.logger().error("Error in format_status", exc_info=True)
