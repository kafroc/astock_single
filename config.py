# -*- coding: utf-8 -*-
"""
配置模块 - 负责配置文件的读写管理
"""

import json
import os
from typing import Dict, Any

# 默认配置文件路径
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')

# 默认配置
DEFAULT_CONFIG = {
    "save_offline_data": True,
    "target_stock_code": "000001",
    "backtest_year": 3,
    "kline_strategy": {
        "buy": "(D5MA > D10MA) && (D10MA > D30MA)"
    },
    "trade_strategy": {
        "BUYS": "DK < -2%",
        "SELL": {
            "GAIN": 5.0,
            "LOSS": 10.0,
            "PERIOD": 60
        }
    }
}


def load_config(config_path: str = None) -> Dict[str, Any]:
    """
    加载配置文件
    
    Args:
        config_path: 配置文件路径，默认使用CONFIG_FILE
        
    Returns:
        配置字典
    """
    if config_path is None:
        config_path = CONFIG_FILE
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # 合并默认配置，确保所有必需字段存在
                merged_config = DEFAULT_CONFIG.copy()
                _deep_merge(merged_config, config)
                return merged_config
        except (json.JSONDecodeError, IOError) as e:
            print(f"加载配置文件失败: {e}，使用默认配置")
            return DEFAULT_CONFIG.copy()
    else:
        # 配置文件不存在，创建默认配置
        save_config(DEFAULT_CONFIG, config_path)
        return DEFAULT_CONFIG.copy()


def save_config(config: Dict[str, Any], config_path: str = None) -> bool:
    """
    保存配置到文件
    
    Args:
        config: 配置字典
        config_path: 配置文件路径，默认使用CONFIG_FILE
        
    Returns:
        是否保存成功
    """
    if config_path is None:
        config_path = CONFIG_FILE
    
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        return True
    except IOError as e:
        print(f"保存配置文件失败: {e}")
        return False


def _deep_merge(base: Dict, override: Dict) -> None:
    """
    深度合并两个字典，将override的值合并到base中
    
    Args:
        base: 基础字典
        override: 覆盖字典
    """
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


def get_stock_codes(config: Dict[str, Any]) -> list:
    """
    获取目标股票代码列表
    
    Args:
        config: 配置字典
        
    Returns:
        股票代码列表
    """
    codes_str = config.get("target_stock_code", "")
    if not codes_str:
        return []
    return [code.strip() for code in codes_str.split(";") if code.strip()]


def validate_config(config: Dict[str, Any]) -> tuple:
    """
    验证配置的有效性
    
    Args:
        config: 配置字典
        
    Returns:
        (是否有效, 错误信息)
    """
    errors = []
    
    # 验证股票代码
    if not config.get("target_stock_code"):
        errors.append("股票代码不能为空")
    
    # 验证回测年数
    backtest_year = config.get("backtest_year", 0)
    if not isinstance(backtest_year, int) or backtest_year <= 0:
        errors.append("回测年数必须是正整数")
    
    # 验证交易策略
    trade_strategy = config.get("trade_strategy", {})
    sell_config = trade_strategy.get("SELL", {})
    
    gain = sell_config.get("GAIN", 0)
    if not isinstance(gain, (int, float)) or gain <= 0:
        errors.append("止盈比例必须是正数")
    
    loss = sell_config.get("LOSS", 0)
    if not isinstance(loss, (int, float)) or loss <= 0:
        errors.append("止损比例必须是正数")
    
    period = sell_config.get("PERIOD", 0)
    if not isinstance(period, int) or period <= 0:
        errors.append("持有周期必须是正整数")
    
    if errors:
        return False, "; ".join(errors)
    return True, ""


if __name__ == "__main__":
    # 测试配置模块
    config = load_config()
    print("当前配置:")
    print(json.dumps(config, ensure_ascii=False, indent=4))
    
    codes = get_stock_codes(config)
    print(f"\n股票代码列表: {codes}")
    
    valid, error = validate_config(config)
    print(f"\n配置验证: {'有效' if valid else f'无效 - {error}'}")
