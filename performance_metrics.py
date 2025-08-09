
"""
Enhanced Performance Metrics Module
Provides accurate calculation of trading performance metrics including Sharpe ratio,
maximum drawdown, win rate, and other key performance indicators.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class PerformanceMetrics:
    """Container for performance metrics"""
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    max_drawdown_duration: int
    win_rate: float
    profit_factor: float
    total_return: float
    annualized_return: float
    volatility: float
    calmar_ratio: float
    var_95: float  # Value at Risk at 95% confidence


class PerformanceCalculator:
    """Advanced performance metrics calculator"""
    
    def __init__(self, risk_free_rate: float = 0.02):
        """
        Initialize performance calculator
        
        Args:
            risk_free_rate: Annual risk-free rate (default: 2%)
        """
        self.risk_free_rate = risk_free_rate
    
    def calculate_returns(self, pnl_series: List[float], starting_capital: float = 10000) -> np.ndarray:
        """
        Calculate returns from P&L series
        
        Args:
            pnl_series: List of cumulative P&L values
            starting_capital: Initial capital amount
            
        Returns:
            Array of period returns
        """
        if len(pnl_series) < 2:
            return np.array([])
        
        # Convert P&L to equity values
        equity_values = [starting_capital + pnl for pnl in pnl_series]
        
        # Calculate returns
        returns = []
        for i in range(1, len(equity_values)):
            prev_equity = equity_values[i-1]
            if prev_equity > 0:
                ret = (equity_values[i] - prev_equity) / prev_equity
                # Protect against division by zero or extreme values
                if np.isfinite(ret):
                    returns.append(ret)
        
        return np.array(returns)
    
    def calculate_sharpe_ratio(self, returns: np.ndarray, periods_per_year: int = 252) -> float:
        """
        Calculate Sharpe ratio with proper annualization and frequency detection
        
        Args:
            returns: Array of period returns
            periods_per_year: Number of periods in a year (auto-detected if not specified)
            
        Returns:
            Annualized Sharpe ratio
        """
        if len(returns) < 2:
            return 0.0
        
        # Auto-detect data frequency if returns are very small (indicating high frequency)
        mean_abs_return = np.mean(np.abs(returns))
        
        if mean_abs_return < 0.001:  # Less than 0.1% average absolute return
            # This looks like high-frequency data (minute or sub-minute)
            # Assume each return represents a few minutes of trading
            estimated_periods_per_year = len(returns) * 10  # Conservative estimate
            print(f"📊 Auto-detected high-frequency data. Using {estimated_periods_per_year} periods/year.")
        else:
            estimated_periods_per_year = periods_per_year
        
        # Calculate excess returns with appropriately scaled risk-free rate
        period_rf_rate = self.risk_free_rate / estimated_periods_per_year
        excess_returns = returns - period_rf_rate
        
        # Calculate Sharpe ratio
        mean_excess = np.mean(excess_returns)
        std_excess = np.std(excess_returns)
        
        if std_excess == 0:
            return 0.0
        
        # Annualized Sharpe ratio
        sharpe = mean_excess / std_excess * np.sqrt(estimated_periods_per_year)
        
        # Sanity check: if Sharpe ratio is extreme, recalculate with conservative assumptions
        if abs(sharpe) > 10:
            print(f"⚠️ Extreme Sharpe ratio detected ({sharpe:.2f}). Recalculating with conservative assumptions...")
            # Use simpler calculation without excess returns for high-frequency data
            mean_return = np.mean(returns)
            std_return = np.std(returns)
            if std_return > 0:
                sharpe = mean_return / std_return * np.sqrt(min(estimated_periods_per_year, 252))
            else:
                sharpe = 0.0
        
        return sharpe
    
    def calculate_sortino_ratio(self, returns: np.ndarray, periods_per_year: int = 252) -> float:
        """
        Calculate Sortino ratio (uses downside deviation instead of total volatility)
        
        Args:
            returns: Array of period returns
            periods_per_year: Number of periods in a year
            
        Returns:
            Annualized Sortino ratio
        """
        if len(returns) < 2:
            return 0.0
        
        daily_rf_rate = self.risk_free_rate / periods_per_year
        excess_returns = returns - daily_rf_rate
        
        # Calculate downside deviation
        downside_returns = excess_returns[excess_returns < 0]
        if len(downside_returns) == 0:
            # No downside deviation, so Sortino is extremely high
            # Cap to a large value for reporting stability
            return 10.0 if np.mean(excess_returns) > 0 else 0.0
        
        downside_std = np.std(downside_returns)
        if downside_std == 0:
            return 0.0
        
        sortino = np.mean(excess_returns) / downside_std * np.sqrt(periods_per_year)
        return sortino
    
    def calculate_max_drawdown(self, equity_curve: List[float]) -> tuple:
        """
        Calculate maximum drawdown and its duration
        
        Args:
            equity_curve: List of equity values over time
            
        Returns:
            Tuple of (max_drawdown_percentage, duration_in_periods)
        """
        if len(equity_curve) < 2:
            return 0.0, 0
        
        peak = equity_curve[0]
        max_dd = 0.0
        max_dd_duration = 0
        current_dd_duration = 0
        
        for value in equity_curve:
            if value > peak:
                peak = value
                current_dd_duration = 0
            else:
                drawdown = (peak - value) / peak
                max_dd = max(max_dd, drawdown)
                current_dd_duration += 1
                max_dd_duration = max(max_dd_duration, current_dd_duration)
        
        return max_dd, max_dd_duration
    
    def calculate_win_rate(self, trade_returns: List[float]) -> float:
        """Calculate win rate from individual trade returns"""
        if not trade_returns:
            return 0.0
        
        winning_trades = sum(1 for ret in trade_returns if ret > 0)
        return winning_trades / len(trade_returns)
    
    def calculate_profit_factor(self, trade_returns: List[float]) -> float:
        """Calculate profit factor (gross profit / gross loss)"""
        if not trade_returns:
            return 0.0
        
        gross_profit = sum(ret for ret in trade_returns if ret > 0)
        gross_loss = abs(sum(ret for ret in trade_returns if ret < 0))
        
        if gross_loss == 0:
            return 1000.0 if gross_profit > 0 else 1.0  # Cap instead of infinity
        
        return gross_profit / gross_loss
    
    def calculate_var(self, returns: np.ndarray, confidence_level: float = 0.95) -> float:
        """Calculate Value at Risk at given confidence level"""
        if len(returns) < 2:
            return 0.0
        
        return np.percentile(returns, (1 - confidence_level) * 100)
    
    def calculate_all_metrics(self, 
                            pnl_series: List[float],
                            trade_returns: Optional[List[float]] = None,
                            starting_capital: float = 10000,
                            periods_per_year: int = 252,
                            time_period_days: Optional[int] = None) -> PerformanceMetrics:
        """
        Calculate comprehensive performance metrics
        
        Args:
            pnl_series: Cumulative P&L over time
            trade_returns: Individual trade returns (optional)
            starting_capital: Starting capital amount
            periods_per_year: Number of periods per year for annualization
            time_period_days: Total days in the backtest period
            
        Returns:
            PerformanceMetrics object with all calculated metrics
        """
        # Calculate returns
        returns = self.calculate_returns(pnl_series, starting_capital)
        
        # Calculate equity curve
        equity_curve = [starting_capital + pnl for pnl in pnl_series]
        
        # Basic metrics
        total_return = (equity_curve[-1] - equity_curve[0]) / equity_curve[0] if equity_curve and equity_curve[0] != 0 else 0.0
        
        # Annualized return
        if time_period_days and time_period_days > 0:
            years = time_period_days / 365.25
            # Protect against math domain errors
            if years > 0 and (1 + total_return) > 0:
                try:
                    annualized_return = (1 + total_return) ** (1/years) - 1
                except (ValueError, OverflowError, ZeroDivisionError):
                    annualized_return = 0.0
            else:
                annualized_return = 0.0
        else:
            annualized_return = total_return * (periods_per_year / len(returns)) if len(returns) > 0 else 0.0
        
        # Risk metrics
        sharpe_ratio = self.calculate_sharpe_ratio(returns, periods_per_year)
        sortino_ratio = self.calculate_sortino_ratio(returns, periods_per_year)
        max_dd, max_dd_duration = self.calculate_max_drawdown(equity_curve)
        volatility = np.std(returns) * np.sqrt(periods_per_year) if len(returns) > 0 else 0.0
        
        # Calmar ratio (annualized return / max drawdown)
        calmar_ratio = annualized_return / max_dd if max_dd > 0 else 0.0
        
        # Trade-based metrics
        if trade_returns:
            win_rate = self.calculate_win_rate(trade_returns)
            profit_factor = self.calculate_profit_factor(trade_returns)
        else:
            win_rate = 0.0
            profit_factor = 0.0
        
        # Value at Risk
        var_95 = self.calculate_var(returns, 0.95)
        # If all returns are positive, VaR is not meaningful (no risk of loss)
        if len(returns) > 0 and np.all(returns >= 0):
            var_95 = 0.0
        
        return PerformanceMetrics(
            sharpe_ratio=round(sharpe_ratio, 3),
            sortino_ratio=round(sortino_ratio, 3),
            max_drawdown=round(max_dd * 100, 2),  # Convert to percentage
            max_drawdown_duration=max_dd_duration,
            win_rate=round(win_rate * 100, 2),  # Convert to percentage
            profit_factor=round(profit_factor, 3),
            total_return=round(total_return * 100, 2),  # Convert to percentage
            annualized_return=round(annualized_return * 100, 2),  # Convert to percentage
            volatility=round(volatility * 100, 2),  # Convert to percentage
            calmar_ratio=round(calmar_ratio, 3),
            var_95=round(var_95 * 100, 3)  # Convert to percentage
        )


def print_performance_report(metrics: PerformanceMetrics):
    """Print a formatted performance report"""
    print("\n" + "="*60)
    print("           PERFORMANCE METRICS REPORT")
    print("="*60)
    
    print(f"\n📈 RETURN METRICS:")
    print(f"   Total Return:        {metrics.total_return:>8.2f}%")
    print(f"   Annualized Return:   {metrics.annualized_return:>8.2f}%")
    
    print(f"\n⚡ RISK-ADJUSTED METRICS:")
    print(f"   Sharpe Ratio:        {metrics.sharpe_ratio:>8.3f}")
    sortino_display = f"{metrics.sortino_ratio:>8.3f}" if metrics.sortino_ratio < 10 else ">10.000"
    print(f"   Sortino Ratio:       {sortino_display}")
    print(f"   Calmar Ratio:        {metrics.calmar_ratio:>8.3f}")
    
    print(f"\n📉 RISK METRICS:")
    print(f"   Max Drawdown:        {metrics.max_drawdown:>8.2f}%")
    print(f"   DD Duration:         {metrics.max_drawdown_duration:>8} periods")
    print(f"   Volatility:          {metrics.volatility:>8.2f}%")
    print(f"   VaR (95%):          {metrics.var_95:>8.3f}%")
    
    print(f"\n🎯 TRADE METRICS:")
    print(f"   Win Rate:            {metrics.win_rate:>8.2f}%")
    profit_factor_display = f"{metrics.profit_factor:>8.3f}" if metrics.profit_factor < 1000 else ">1000.0"
    print(f"   Profit Factor:       {profit_factor_display}")
    
    print("="*60)
    
    # Performance interpretation
    print(f"\n📊 PERFORMANCE ASSESSMENT:")
    if metrics.sharpe_ratio > 2.0:
        print("   Sharpe Ratio: EXCELLENT (>2.0)")
    elif metrics.sharpe_ratio > 1.0:
        print("   Sharpe Ratio: GOOD (1.0-2.0)")
    elif metrics.sharpe_ratio > 0.5:
        print("   Sharpe Ratio: ACCEPTABLE (0.5-1.0)")
    else:
        print("   Sharpe Ratio: POOR (<0.5)")
    
    if metrics.max_drawdown < 5:
        print("   Max Drawdown: EXCELLENT (<5%)")
    elif metrics.max_drawdown < 10:
        print("   Max Drawdown: GOOD (5-10%)")
    elif metrics.max_drawdown < 20:
        print("   Max Drawdown: ACCEPTABLE (10-20%)")
    else:
        print("   Max Drawdown: HIGH RISK (>20%)")


# Example usage and testing
if __name__ == "__main__":
    # Test with sample data
    calculator = PerformanceCalculator(risk_free_rate=0.02)
    
    # Sample P&L series
    sample_pnl = [0, 100, 150, 120, 180, 200, 180, 220, 250, 230, 280, 300]
    sample_trades = [0.05, -0.02, 0.03, 0.01, -0.01, 0.02, 0.04, -0.03, 0.02, 0.01]
    
    print("Testing Performance Calculator...")
    metrics = calculator.calculate_all_metrics(
        pnl_series=sample_pnl,
        trade_returns=sample_trades,
        starting_capital=10000,
        periods_per_year=252,
        time_period_days=30
    )
    
    print_performance_report(metrics)
