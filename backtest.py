# -*- coding: utf-8 -*-
"""
回测模块 - 执行历史数据回测和统计分析
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import pandas as pd

from config import load_config, get_stock_codes
from data import get_stock_data, calculate_ma, get_close_price
from strategy import evaluate_strategy, TradingStrategy


# 交易记录文件路径
TRADES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'trades.json')


class BacktestEngine:
    """回测引擎"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.initial_capital = 1000000  # 初始资金100万
        self.trades: List[Dict] = []  # 交易记录
        self.current_position: Optional[Dict] = None  # 当前持仓
        self.capital = self.initial_capital  # 当前资金
    
    def run_backtest(self, stock_code: str, kline_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """
        对单只股票执行回测
        
        Args:
            stock_code: 股票代码
            kline_data: K线数据字典
            
        Returns:
            回测结果
        """
        self.trades = []
        self.current_position = None
        self.capital = self.initial_capital
        
        stock_name = kline_data.get('stock_name', stock_code)
        daily_data = kline_data.get('daily')
        
        if daily_data is None or len(daily_data) == 0:
            return self._generate_empty_result(stock_code, stock_name)
        
        # 计算常用均线
        ma_periods = [5, 10, 20, 30, 60]
        kline_data['daily'] = calculate_ma(daily_data, ma_periods)
        if kline_data.get('weekly') is not None:
            kline_data['weekly'] = calculate_ma(kline_data['weekly'], ma_periods)
        if kline_data.get('monthly') is not None:
            kline_data['monthly'] = calculate_ma(kline_data['monthly'], ma_periods)
        
        # 确定回测起始日期
        backtest_years = self.config.get('backtest_year', 3)
        today = datetime.now()
        start_date = today - timedelta(days=backtest_years * 365)
        
        # 检查股票上市日期
        first_date = daily_data['date'].min()
        if start_date < first_date:
            start_date = first_date
        
        # 过滤回测期间的数据
        backtest_data = daily_data[daily_data['date'] >= start_date].copy()
        
        if len(backtest_data) == 0:
            return self._generate_empty_result(stock_code, stock_name)
        
        # 遍历每个交易日
        for idx, row in backtest_data.iterrows():
            current_date = row['date']
            if isinstance(current_date, str):
                current_date = pd.to_datetime(current_date)
            
            # 创建截止到当前日期的数据视图（防止未来数据穿越）
            current_kline_data = {
                'daily': kline_data['daily'][kline_data['daily']['date'] <= current_date],
                'weekly': kline_data['weekly'][kline_data['weekly']['date'] <= current_date] if kline_data.get('weekly') is not None else None,
                'monthly': kline_data['monthly'][kline_data['monthly']['date'] <= current_date] if kline_data.get('monthly') is not None else None,
                'stock_name': stock_name
            }
            
            # 评估策略
            signal = evaluate_strategy(
                stock_code, stock_name, current_date,
                current_kline_data, self.config, self.current_position
            )
            
            # 执行交易
            if signal['action'] == 'buy' and signal['price'] is not None:
                self._execute_buy(stock_code, stock_name, current_date, signal['price'])
            elif signal['action'] == 'sell' and signal['price'] is not None:
                self._execute_sell(current_date, signal['price'], signal['reason'])
        
        # 如果回测结束时还有持仓，按最后价格平仓
        if self.current_position is not None:
            last_date = backtest_data['date'].max()
            last_price = get_close_price(kline_data['daily'], last_date)
            if last_price is not None:
                self._execute_sell(last_date, last_price, "回测结束")
        
        # 生成统计结果
        return self._generate_statistics(stock_code, stock_name)
    
    def _execute_buy(self, stock_code: str, stock_name: str, date: datetime, price: float):
        """执行买入"""
        if self.current_position is not None:
            return  # 已有持仓
        
        # 全仓买入
        shares = int(self.capital / price / 100) * 100  # 按手买入
        if shares <= 0:
            return
        
        cost = shares * price
        self.capital -= cost
        
        self.current_position = {
            'stock_code': stock_code,
            'stock_name': stock_name,
            'buy_date': date,
            'buy_price': price,
            'shares': shares,
            'cost': cost
        }
    
    def _execute_sell(self, date: datetime, price: float, reason: str):
        """执行卖出"""
        if self.current_position is None:
            return
        
        pos = self.current_position
        revenue = pos['shares'] * price
        profit = revenue - pos['cost']
        profit_pct = (price - pos['buy_price']) / pos['buy_price'] * 100
        hold_days = (date - pos['buy_date']).days
        
        # 记录交易
        trade = {
            'trade_id': len(self.trades) + 1,
            'stock_code': pos['stock_code'],
            'stock_name': pos['stock_name'],
            'buy_date': pos['buy_date'].strftime('%Y-%m-%d'),
            'buy_price': round(pos['buy_price'], 2),
            'sell_date': date.strftime('%Y-%m-%d'),
            'sell_price': round(price, 2),
            'shares': pos['shares'],
            'profit': round(profit, 2),
            'profit_pct': round(profit_pct, 2),
            'sell_reason': reason,
            'hold_days': hold_days
        }
        self.trades.append(trade)
        
        # 更新资金
        self.capital += revenue
        self.current_position = None
    
    def _generate_empty_result(self, stock_code: str, stock_name: str) -> Dict[str, Any]:
        """生成空结果"""
        return {
            'stock_code': stock_code,
            'stock_name': stock_name,
            'trades': [],
            'statistics': {
                'total_trades': 0,
                'win_count': 0,
                'loss_count': 0,
                'win_rate': 0,
                'total_return': 0,
                'total_return_pct': 0,
                'avg_hold_days': 0
            }
        }
    
    def _generate_statistics(self, stock_code: str, stock_name: str) -> Dict[str, Any]:
        """生成统计结果"""
        total_trades = len(self.trades)
        
        if total_trades == 0:
            return self._generate_empty_result(stock_code, stock_name)
        
        # 统计盈亏
        win_trades = [t for t in self.trades if t['profit'] > 0]
        loss_trades = [t for t in self.trades if t['profit'] <= 0]
        
        win_count = len(win_trades)
        loss_count = len(loss_trades)
        win_rate = win_count / total_trades * 100 if total_trades > 0 else 0
        
        # 计算总收益
        total_profit = sum(t['profit'] for t in self.trades)
        total_return_pct = (self.capital - self.initial_capital) / self.initial_capital * 100
        
        # 计算平均持有天数
        total_hold_days = sum(t['hold_days'] for t in self.trades)
        avg_hold_days = total_hold_days / total_trades if total_trades > 0 else 0
        
        return {
            'stock_code': stock_code,
            'stock_name': stock_name,
            'trades': self.trades,
            'statistics': {
                'total_trades': total_trades,
                'win_count': win_count,
                'loss_count': loss_count,
                'win_rate': round(win_rate, 2),
                'total_return': round(total_profit, 2),
                'total_return_pct': round(total_return_pct, 2),
                'final_capital': round(self.capital, 2),
                'avg_hold_days': round(avg_hold_days, 1)
            }
        }


def run_backtest(config: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """
    执行回测
    
    Args:
        config: 配置字典，如果为None则从文件加载
        
    Returns:
        所有股票的回测结果列表
    """
    if config is None:
        config = load_config()
    
    stock_codes = get_stock_codes(config)
    save_offline = config.get('save_offline_data', True)
    
    results = []
    
    for stock_code in stock_codes:
        print(f"正在回测股票: {stock_code}")
        
        # 获取股票数据
        kline_data = get_stock_data(stock_code, save_offline=save_offline)
        
        if kline_data.get('daily') is None:
            print(f"无法获取股票 {stock_code} 的数据，跳过")
            continue
        
        # 执行回测
        engine = BacktestEngine(config)
        result = engine.run_backtest(stock_code, kline_data)
        results.append(result)
        
        print(f"股票 {stock_code} 回测完成，共 {result['statistics']['total_trades']} 笔交易")
    
    # 保存交易记录
    save_trades(results)
    
    return results


def save_trades(results: List[Dict[str, Any]]):
    """保存交易记录到文件"""
    try:
        with open(TRADES_FILE, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存交易记录失败: {e}")


def load_trades() -> List[Dict[str, Any]]:
    """从文件加载交易记录"""
    if os.path.exists(TRADES_FILE):
        try:
            with open(TRADES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载交易记录失败: {e}")
    return []


def get_combined_statistics(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    计算所有股票的综合统计
    
    Args:
        results: 所有股票的回测结果
        
    Returns:
        综合统计信息
    """
    all_trades = []
    for result in results:
        all_trades.extend(result.get('trades', []))
    
    total_trades = len(all_trades)
    if total_trades == 0:
        return {
            'total_trades': 0,
            'win_count': 0,
            'loss_count': 0,
            'win_rate': 0,
            'total_return': 0,
            'total_return_pct': 0,
            'avg_hold_days': 0
        }
    
    win_trades = [t for t in all_trades if t['profit'] > 0]
    win_count = len(win_trades)
    loss_count = total_trades - win_count
    win_rate = win_count / total_trades * 100
    
    total_profit = sum(t['profit'] for t in all_trades)
    initial_capital = 1000000
    final_capital = initial_capital + total_profit
    total_return_pct = total_profit / initial_capital * 100
    
    avg_hold_days = sum(t['hold_days'] for t in all_trades) / total_trades
    
    return {
        'total_trades': total_trades,
        'win_count': win_count,
        'loss_count': loss_count,
        'win_rate': round(win_rate, 2),
        'total_return': round(total_profit, 2),
        'total_return_pct': round(total_return_pct, 2),
        'final_capital': round(final_capital, 2),
        'avg_hold_days': round(avg_hold_days, 1)
    }


if __name__ == "__main__":
    # 测试回测模块
    print("开始回测...")
    results = run_backtest()
    
    print("\n回测结果摘要:")
    for result in results:
        stats = result['statistics']
        print(f"\n股票: {result['stock_name']} ({result['stock_code']})")
        print(f"  总交易次数: {stats['total_trades']}")
        print(f"  赢率: {stats['win_rate']}%")
        print(f"  总收益: {stats['total_return']}元")
        print(f"  收益率: {stats['total_return_pct']}%")
        print(f"  平均持有天数: {stats['avg_hold_days']}天")
    
    if len(results) > 1:
        combined = get_combined_statistics(results)
        print("\n综合统计:")
        print(f"  总交易次数: {combined['total_trades']}")
        print(f"  赢率: {combined['win_rate']}%")
        print(f"  总收益: {combined['total_return']}元")
        print(f"  收益率: {combined['total_return_pct']}%")
