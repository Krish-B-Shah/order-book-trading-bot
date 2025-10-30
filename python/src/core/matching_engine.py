import heapq
import time


class MatchingEngine:
    """Handles order matching logic for the order book"""

    @staticmethod
    def match_orders(buy_orders, sell_orders, trade_log, order_map, current_price):
        """Match buy and sell orders"""
        while buy_orders and sell_orders:
            best_buy = buy_orders[0]
            best_sell = sell_orders[0]

            if best_buy.price >= best_sell.price:
                trade_qty = min(best_buy.quantity, best_sell.quantity)
                trade_price = best_sell.price

                trade_log.append({
                    "price": trade_price,
                    "quantity": trade_qty,
                    "timestamp": time.time()
                })

                if best_buy.owner:
                    best_buy.owner.updateProfitAndLoss(trade_price, trade_qty, "buy", current_price)
                if best_sell.owner:
                    best_sell.owner.updateProfitAndLoss(trade_price, trade_qty, "sell", current_price)

                best_buy.quantity -= trade_qty
                best_sell.quantity -= trade_qty

                if best_buy.quantity == 0:
                    heapq.heappop(buy_orders)
                    order_map.pop(best_buy.order_id, None)
                if best_sell.quantity == 0:
                    heapq.heappop(sell_orders)
                    order_map.pop(best_sell.order_id, None)
            else:
                break

    @staticmethod
    def execute_market_order(market_order, book_side, trade_log, order_map, current_price=None):
        """Execute a market order against the order book"""
        original_qty = market_order.quantity

        while market_order.quantity > 0 and book_side:
            resting_order = book_side[0]
            trade_qty = min(market_order.quantity, resting_order.quantity)
            trade_price = resting_order.price

            trade_log.append({
                "price": trade_price,
                "quantity": trade_qty,
                "timestamp": time.time()
            })

            if market_order.owner:
                market_order.owner.updateProfitAndLoss(trade_price, trade_qty, market_order.side, current_price)
            if resting_order.owner:
                resting_order.owner.updateProfitAndLoss(trade_price, trade_qty, resting_order.side, current_price)

            market_order.quantity -= trade_qty
            resting_order.quantity -= trade_qty

            if resting_order.quantity == 0:
                heapq.heappop(book_side)
                order_map.pop(resting_order.order_id, None)

        if market_order.quantity > 0:
            if market_order.quantity < original_qty:
                print(f"⚠️ Market order {market_order.order_id} partially filled, {market_order.quantity} units discarded.")
            else:
                print(f"❌ Market order {market_order.order_id} could not be filled at all.")
