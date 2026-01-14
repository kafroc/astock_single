# -*- coding: utf-8 -*-
"""
策略模块 - K线策略和交易策略的解析与执行
"""

import re
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple, List
import pandas as pd
from data import get_ma_value, get_close_price, get_pct_change


class StrategyParser:
    """策略表达式解析器"""
    
    # 均线类型映射
    MA_TYPES = {
        'D': 'daily',   # 日均线
        'W': 'weekly',  # 周均线
        'M': 'monthly'  # 月均线
    }
    
    # K线类型映射
    KLINE_TYPES = {
        'DK': 'daily',   # 日K线
        'WK': 'weekly',  # 周K线
        'MK': 'monthly'  # 月K线
    }
    
    def __init__(self):
        # 正则表达式模式
        # 匹配均线表达式，如 D5MA, D5MA-1, W10MA-2
        self.ma_pattern = re.compile(r'([DWM])(\d+)MA(?:-(\d+))?')
        # 匹配K线涨跌幅表达式，如 DK < -2%, WK > 5%
        self.kline_pattern = re.compile(r'([DWM]K)\s*([<>=!]+)\s*(-?\d+(?:\.\d+)?)\s*%?')
        # 匹配连续条件表达式，如 (...) * 3
        self.repeat_pattern = re.compile(r'\(([^()]+)\)\s*\*\s*(\d+)')
    
    def expand_repeat_expression(self, expression: str) -> str:
        """
        展开连续条件表达式
        例如: (D5MA > D30MA) * 3 展开为 (D5MA > D30MA) && (D5MA-1 > D30MA-1) && (D5MA-2 > D30MA-2)
        """
        def replace_repeat(match):
            inner_expr = match.group(1)
            count = int(match.group(2))
            
            expanded_parts = []
            for i in range(count):
                if i == 0:
                    expanded_parts.append(f"({inner_expr})")
                else:
                    # 替换均线表达式，添加偏移量
                    def add_offset(ma_match):
                        prefix = ma_match.group(1)
                        period = ma_match.group(2)
                        existing_offset = ma_match.group(3)
                        if existing_offset:
                            new_offset = int(existing_offset) + i
                        else:
                            new_offset = i
                        return f"{prefix}{period}MA-{new_offset}"
                    
                    offset_expr = self.ma_pattern.sub(add_offset, inner_expr)
                    expanded_parts.append(f"({offset_expr})")
            
            return " && ".join(expanded_parts)
        
        # 递归展开所有重复表达式
        prev_expression = None
        while prev_expression != expression:
            prev_expression = expression
            expression = self.repeat_pattern.sub(replace_repeat, expression)
        
        return expression
    
    def parse_ma_expression(self, expression: str, kline_data: Dict[str, pd.DataFrame], 
                           date: datetime) -> Optional[float]:
        """
        解析并计算均线表达式的值
        
        Args:
            expression: 均线表达式，如 D5MA, D5MA-1
            kline_data: K线数据字典
            date: 当前日期
            
        Returns:
            均线值
        """
        match = self.ma_pattern.match(expression.strip())
        if not match:
            return None
        
        ma_type = match.group(1)  # D/W/M
        period = int(match.group(2))  # 5/10/20等
        offset = int(match.group(3)) if match.group(3) else 0
        
        kline_type = self.MA_TYPES.get(ma_type)
        if not kline_type or kline_type not in kline_data:
            return None
        
        df = kline_data[kline_type]
        return get_ma_value(df, date, period, offset)
    
    def evaluate_comparison(self, left_val: float, operator: str, right_val: float) -> bool:
        """评估比较表达式"""
        if operator == '>':
            return left_val > right_val
        elif operator == '<':
            return left_val < right_val
        elif operator == '>=':
            return left_val >= right_val
        elif operator == '<=':
            return left_val <= right_val
        elif operator == '==':
            return left_val == right_val
        elif operator == '!=':
            return left_val != right_val
        return False
    
    def evaluate_kline_strategy(self, expression: str, kline_data: Dict[str, pd.DataFrame],
                                date: datetime) -> bool:
        """
        评估K线策略表达式
        
        Args:
            expression: K线策略表达式
            kline_data: K线数据字典
            date: 当前日期
            
        Returns:
            是否满足策略条件
        """
        if not expression or not expression.strip():
            return True
        
        # 先展开重复表达式
        expanded_expr = self.expand_repeat_expression(expression)
        
        # 替换逻辑运算符为Python格式
        py_expr = expanded_expr.replace('&&', ' and ').replace('||', ' or ').replace('!', ' not ')
        
        # 找出所有均线表达式并计算值
        ma_matches = list(self.ma_pattern.finditer(expanded_expr))
        ma_values = {}
        
        for match in ma_matches:
            ma_expr = match.group(0)
            if ma_expr not in ma_values:
                value = self.parse_ma_expression(ma_expr, kline_data, date)
                if value is None:
                    return False  # 如果无法获取均线值，返回False
                ma_values[ma_expr] = value
        
        # 替换表达式中的均线为实际值
        for ma_expr, value in ma_values.items():
            py_expr = py_expr.replace(ma_expr, str(value))
        
        try:
            result = eval(py_expr)
            return bool(result)
        except Exception as e:
            print(f"评估K线策略表达式失败: {e}")
            return False
    
    def evaluate_trade_buy_condition(self, expression: str, kline_data: Dict[str, pd.DataFrame],
                                     date: datetime) -> bool:
        """
        评估交易买入条件
        
        Args:
            expression: 买入条件表达式，如 "DK < -2%"
            kline_data: K线数据字典
            date: 当前日期
            
        Returns:
            是否满足买入条件
        """
        if not expression or not expression.strip():
            return True
        
        match = self.kline_pattern.search(expression)
        if not match:
            return True
        
        kline_type_str = match.group(1)  # DK/WK/MK
        operator = match.group(2)  # <, >, ==, !=
        threshold = float(match.group(3))  # 百分比值
        
        kline_type = self.KLINE_TYPES.get(kline_type_str)
        if not kline_type or kline_type not in kline_data:
            return False
        
        df = kline_data[kline_type]
        pct_change = get_pct_change(df, date)
        
        if pct_change is None:
            return False
        
        return self.evaluate_comparison(pct_change, operator, threshold)


class TradingStrategy:
    """交易策略管理器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.parser = StrategyParser()
        
        # 获取策略配置
        kline_config = config.get('kline_strategy', {})
        self.kline_buy_strategy = kline_config.get('buy', '')
        
        trade_config = config.get('trade_strategy', {})
        self.buy_condition = trade_config.get('BUYS', '')
        
        sell_config = trade_config.get('SELL', {})
        self.gain_pct = sell_config.get('GAIN', 5.0)
        self.loss_pct = sell_config.get('LOSS', 10.0)
        self.hold_period = sell_config.get('PERIOD', 60)
    
    def check_kline_strategy(self, kline_data: Dict[str, pd.DataFrame], date: datetime) -> bool:
        """
        检查K线策略是否满足买入条件
        
        Args:
            kline_data: K线数据字典
            date: 当前日期
            
        Returns:
            是否满足K线策略
        """
        return self.parser.evaluate_kline_strategy(self.kline_buy_strategy, kline_data, date)
    
    def check_buy_signal(self, kline_data: Dict[str, pd.DataFrame], date: datetime,
                         has_position: bool) -> bool:
        """
        检查是否产生买入信号
        
        Args:
            kline_data: K线数据字典
            date: 当前日期
            has_position: 是否已持仓
            
        Returns:
            是否应该买入
        """
        # 已持仓则不买入
        if has_position:
            return False
        
        # 检查K线策略
        if not self.check_kline_strategy(kline_data, date):
            return False
        
        # 检查买入条件
        if not self.parser.evaluate_trade_buy_condition(self.buy_condition, kline_data, date):
            return False
        
        return True
    
    def check_sell_signal(self, kline_data: Dict[str, pd.DataFrame], date: datetime,
                          buy_price: float, buy_date: datetime) -> Tuple[bool, str]:
        """
        检查是否产生卖出信号
        
        Args:
            kline_data: K线数据字典
            date: 当前日期
            buy_price: 买入价格
            buy_date: 买入日期
            
        Returns:
            (是否应该卖出, 卖出原因)
        """
        if kline_data.get('daily') is None:
            return False, ""
        
        current_price = get_close_price(kline_data['daily'], date)
        if current_price is None:
            return False, ""
        
        # 计算收益率
        profit_pct = (current_price - buy_price) / buy_price * 100
        
        # 检查止盈
        if profit_pct >= self.gain_pct:
            return True, "止盈"
        
        # 检查止损
        if profit_pct <= -self.loss_pct:
            return True, "止损"
        
        # 检查持有周期
        hold_days = (date - buy_date).days
        if hold_days >= self.hold_period:
            return True, "到期"
        
        return False, ""
    
    def get_current_price(self, kline_data: Dict[str, pd.DataFrame], date: datetime) -> Optional[float]:
        """获取当前价格"""
        if kline_data.get('daily') is None:
            return None
        return get_close_price(kline_data['daily'], date)


def evaluate_strategy(stock_code: str, stock_name: str, date: datetime,
                     kline_data: Dict[str, pd.DataFrame], config: Dict[str, Any],
                     position: Optional[Dict] = None) -> Dict[str, Any]:
    """
    评估策略并返回交易信号
    
    Args:
        stock_code: 股票代码
        stock_name: 股票名称
        date: 当前日期
        kline_data: K线数据字典
        config: 配置字典
        position: 当前持仓信息
        
    Returns:
        交易信号字典
    """
    strategy = TradingStrategy(config)
    
    result = {
        'action': None,  # 'buy', 'sell', or None
        'stock_code': stock_code,
        'stock_name': stock_name,
        'date': date,
        'price': strategy.get_current_price(kline_data, date),
        'reason': None
    }
    
    if position is None:
        # 没有持仓，检查买入信号
        if strategy.check_buy_signal(kline_data, date, has_position=False):
            result['action'] = 'buy'
    else:
        # 有持仓，检查卖出信号
        should_sell, reason = strategy.check_sell_signal(
            kline_data, date, 
            position['buy_price'], 
            position['buy_date']
        )
        if should_sell:
            result['action'] = 'sell'
            result['reason'] = reason
            result['buy_price'] = position['buy_price']
            result['buy_date'] = position['buy_date']
            result['hold_days'] = (date - position['buy_date']).days
    
    return result


if __name__ == "__main__":
    # 测试策略解析器
    parser = StrategyParser()
    
    # 测试展开重复表达式
    test_expr = "(D5MA > D30MA) * 3"
    expanded = parser.expand_repeat_expression(test_expr)
    print(f"原表达式: {test_expr}")
    print(f"展开后: {expanded}")
    
    # 测试复杂表达式
    test_expr2 = "((D5MA > D10MA) * 2) && (W5MA > W10MA)"
    expanded2 = parser.expand_repeat_expression(test_expr2)
    print(f"\n原表达式: {test_expr2}")
    print(f"展开后: {expanded2}")
