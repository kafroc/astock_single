# -*- coding: utf-8 -*-
"""
数据模块 - 通过akshare接口获取股票数据
"""

import os
import pandas as pd
import akshare as ak
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

# 数据存储目录
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')


def ensure_data_dir(stock_code: str) -> str:
    """
    确保股票数据目录存在
    
    Args:
        stock_code: 股票代码
        
    Returns:
        数据目录路径
    """
    stock_dir = os.path.join(DATA_DIR, stock_code)
    if not os.path.exists(stock_dir):
        os.makedirs(stock_dir)
    return stock_dir


def get_stock_name(stock_code: str) -> str:
    """
    获取股票名称
    
    Args:
        stock_code: 股票代码
        
    Returns:
        股票名称
    """
    try:
        # 尝试获取股票信息
        stock_info = ak.stock_individual_info_em(symbol=stock_code)
        if stock_info is not None and len(stock_info) > 0:
            # 查找股票简称
            name_row = stock_info[stock_info['item'] == '股票简称']
            if len(name_row) > 0:
                return name_row['value'].values[0]
    except Exception as e:
        print(f"获取股票名称失败: {e}")
    return stock_code


def fetch_daily_kline(stock_code: str, start_date: str = "19900101") -> Optional[pd.DataFrame]:
    """
    从akshare获取日K线数据
    
    Args:
        stock_code: 股票代码
        start_date: 开始日期，格式YYYYMMDD
        
    Returns:
        日K线DataFrame
    """
    try:
        # 使用东方财富接口获取日K线
        df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", 
                                start_date=start_date, adjust="qfq")
        if df is not None and len(df) > 0:
            df = df.rename(columns={
                '日期': 'date',
                '开盘': 'open',
                '收盘': 'close',
                '最高': 'high',
                '最低': 'low',
                '成交量': 'volume',
                '成交额': 'amount',
                '涨跌幅': 'pct_change'
            })
            df['date'] = pd.to_datetime(df['date'])
            return df
    except Exception as e:
        print(f"获取日K线数据失败 [{stock_code}]: {e}")
    return None


def fetch_weekly_kline(stock_code: str, start_date: str = "19900101") -> Optional[pd.DataFrame]:
    """
    从akshare获取周K线数据
    
    Args:
        stock_code: 股票代码
        start_date: 开始日期，格式YYYYMMDD
        
    Returns:
        周K线DataFrame
    """
    try:
        df = ak.stock_zh_a_hist(symbol=stock_code, period="weekly", 
                                start_date=start_date, adjust="qfq")
        if df is not None and len(df) > 0:
            df = df.rename(columns={
                '日期': 'date',
                '开盘': 'open',
                '收盘': 'close',
                '最高': 'high',
                '最低': 'low',
                '成交量': 'volume',
                '成交额': 'amount',
                '涨跌幅': 'pct_change'
            })
            df['date'] = pd.to_datetime(df['date'])
            return df
    except Exception as e:
        print(f"获取周K线数据失败 [{stock_code}]: {e}")
    return None


def fetch_monthly_kline(stock_code: str, start_date: str = "19900101") -> Optional[pd.DataFrame]:
    """
    从akshare获取月K线数据
    
    Args:
        stock_code: 股票代码
        start_date: 开始日期，格式YYYYMMDD
        
    Returns:
        月K线DataFrame
    """
    try:
        df = ak.stock_zh_a_hist(symbol=stock_code, period="monthly", 
                                start_date=start_date, adjust="qfq")
        if df is not None and len(df) > 0:
            df = df.rename(columns={
                '日期': 'date',
                '开盘': 'open',
                '收盘': 'close',
                '最高': 'high',
                '最低': 'low',
                '成交量': 'volume',
                '成交额': 'amount',
                '涨跌幅': 'pct_change'
            })
            df['date'] = pd.to_datetime(df['date'])
            return df
    except Exception as e:
        print(f"获取月K线数据失败 [{stock_code}]: {e}")
    return None


def save_kline_data(df: pd.DataFrame, stock_code: str, kline_type: str) -> bool:
    """
    保存K线数据到本地
    
    Args:
        df: K线DataFrame
        stock_code: 股票代码
        kline_type: K线类型 (daily/weekly/monthly)
        
    Returns:
        是否保存成功
    """
    try:
        stock_dir = ensure_data_dir(stock_code)
        file_path = os.path.join(stock_dir, f"{kline_type}.csv")
        df.to_csv(file_path, index=False, encoding='utf-8')
        return True
    except Exception as e:
        print(f"保存{kline_type}K线数据失败 [{stock_code}]: {e}")
        return False


def load_kline_data(stock_code: str, kline_type: str) -> Optional[pd.DataFrame]:
    """
    从本地加载K线数据
    
    Args:
        stock_code: 股票代码
        kline_type: K线类型 (daily/weekly/monthly)
        
    Returns:
        K线DataFrame
    """
    try:
        stock_dir = os.path.join(DATA_DIR, stock_code)
        file_path = os.path.join(stock_dir, f"{kline_type}.csv")
        if os.path.exists(file_path):
            df = pd.read_csv(file_path, encoding='utf-8')
            df['date'] = pd.to_datetime(df['date'])
            return df
    except Exception as e:
        print(f"加载{kline_type}K线数据失败 [{stock_code}]: {e}")
    return None


def is_data_up_to_date(df: pd.DataFrame) -> bool:
    """
    检查数据是否更新到最新
    
    Args:
        df: K线DataFrame
        
    Returns:
        是否最新
    """
    if df is None or len(df) == 0:
        return False
    
    last_date = df['date'].max()
    today = datetime.now()
    
    # 如果是交易日且在收盘后，检查是否有当天数据
    # 简化处理：如果最后一条数据是昨天或更早，则认为需要更新
    # 周末和节假日不更新
    if today.weekday() >= 5:  # 周末
        # 检查是否有上周五的数据
        friday = today - timedelta(days=today.weekday() - 4)
        return last_date.date() >= friday.date()
    else:
        # 工作日，如果在15:00后，应该有当天数据
        if today.hour >= 15:
            return last_date.date() >= today.date()
        else:
            # 15:00前，有昨天数据即可
            yesterday = today - timedelta(days=1)
            if yesterday.weekday() >= 5:  # 昨天是周末
                friday = yesterday - timedelta(days=yesterday.weekday() - 4)
                return last_date.date() >= friday.date()
            return last_date.date() >= yesterday.date()


def get_stock_data(stock_code: str, save_offline: bool = True) -> Dict[str, pd.DataFrame]:
    """
    获取股票的所有K线数据
    
    Args:
        stock_code: 股票代码
        save_offline: 是否保存到本地
        
    Returns:
        包含daily, weekly, monthly三种K线的字典
    """
    result = {
        'daily': None,
        'weekly': None,
        'monthly': None,
        'stock_name': get_stock_name(stock_code)
    }
    
    kline_types = ['daily', 'weekly', 'monthly']
    fetch_funcs = {
        'daily': fetch_daily_kline,
        'weekly': fetch_weekly_kline,
        'monthly': fetch_monthly_kline
    }
    
    for kline_type in kline_types:
        df = None
        
        if save_offline:
            # 尝试从本地加载
            df = load_kline_data(stock_code, kline_type)
            
            if df is not None and is_data_up_to_date(df):
                # 本地数据是最新的
                result[kline_type] = df
                continue
        
        # 从网络获取数据
        df = fetch_funcs[kline_type](stock_code)
        
        if df is not None:
            result[kline_type] = df
            
            if save_offline:
                save_kline_data(df, stock_code, kline_type)
    
    return result


def calculate_ma(df: pd.DataFrame, periods: list) -> pd.DataFrame:
    """
    计算均线数据
    
    Args:
        df: K线DataFrame
        periods: 均线周期列表，如[5, 10, 20, 30, 60]
        
    Returns:
        添加了均线列的DataFrame
    """
    if df is None or len(df) == 0:
        return df
    
    df = df.copy()
    for period in periods:
        df[f'MA{period}'] = df['close'].rolling(window=period).mean()
    
    return df


def get_ma_value(df: pd.DataFrame, date: datetime, period: int, offset: int = 0) -> Optional[float]:
    """
    获取指定日期的均线值
    
    Args:
        df: K线DataFrame（需要已计算均线）
        date: 日期
        period: 均线周期
        offset: 偏移量，0表示当天，1表示前一天，以此类推
        
    Returns:
        均线值
    """
    if df is None or len(df) == 0:
        return None
    
    ma_col = f'MA{period}'
    if ma_col not in df.columns:
        df = calculate_ma(df, [period])
    
    # 找到日期对应的索引
    df_filtered = df[df['date'] <= date]
    if len(df_filtered) <= offset:
        return None
    
    idx = len(df_filtered) - 1 - offset
    if idx < 0:
        return None
    
    return df_filtered.iloc[idx][ma_col]


def get_close_price(df: pd.DataFrame, date: datetime, offset: int = 0) -> Optional[float]:
    """
    获取指定日期的收盘价
    
    Args:
        df: K线DataFrame
        date: 日期
        offset: 偏移量，0表示当天，1表示前一天
        
    Returns:
        收盘价
    """
    if df is None or len(df) == 0:
        return None
    
    df_filtered = df[df['date'] <= date]
    if len(df_filtered) <= offset:
        return None
    
    idx = len(df_filtered) - 1 - offset
    if idx < 0:
        return None
    
    return df_filtered.iloc[idx]['close']


def get_pct_change(df: pd.DataFrame, date: datetime) -> Optional[float]:
    """
    获取指定日期的涨跌幅
    
    Args:
        df: K线DataFrame
        date: 日期
        
    Returns:
        涨跌幅（百分比）
    """
    if df is None or len(df) == 0:
        return None
    
    df_filtered = df[df['date'] <= date]
    if len(df_filtered) == 0:
        return None
    
    row = df_filtered.iloc[-1]
    if 'pct_change' in row:
        return row['pct_change']
    
    # 如果没有涨跌幅列，手动计算
    if len(df_filtered) >= 2:
        current_close = row['close']
        prev_close = df_filtered.iloc[-2]['close']
        return (current_close - prev_close) / prev_close * 100
    
    return 0


if __name__ == "__main__":
    # 测试数据模块
    stock_code = "000001"
    print(f"获取股票 {stock_code} 的数据...")
    
    data = get_stock_data(stock_code, save_offline=True)
    
    print(f"\n股票名称: {data['stock_name']}")
    print(f"日K线数据: {len(data['daily']) if data['daily'] is not None else 0} 条")
    print(f"周K线数据: {len(data['weekly']) if data['weekly'] is not None else 0} 条")
    print(f"月K线数据: {len(data['monthly']) if data['monthly'] is not None else 0} 条")
    
    if data['daily'] is not None:
        print(f"\n最近5条日K线数据:")
        print(data['daily'].tail())
