# -*- coding: utf-8 -*-
"""
UI模块 - Web界面
"""

import os
from flask import Flask, render_template, request, jsonify, send_from_directory
from config import load_config, save_config, validate_config
from backtest import run_backtest, load_trades, get_combined_statistics

# 获取当前目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, 
            template_folder=os.path.join(BASE_DIR, 'templates'),
            static_folder=os.path.join(BASE_DIR, 'static'))


@app.route('/')
def index():
    """主页"""
    return render_template('index.html')


@app.route('/api/config', methods=['GET'])
def get_config():
    """获取配置"""
    config = load_config()
    return jsonify({'success': True, 'config': config})


@app.route('/api/config', methods=['POST'])
def update_config():
    """更新配置"""
    try:
        config = request.json
        
        # 验证配置
        valid, error = validate_config(config)
        if not valid:
            return jsonify({'success': False, 'error': error})
        
        # 保存配置
        if save_config(config):
            return jsonify({'success': True, 'message': '配置保存成功'})
        else:
            return jsonify({'success': False, 'error': '保存配置失败'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/backtest', methods=['POST'])
def start_backtest():
    """开始回测"""
    try:
        config = load_config()
        results = run_backtest(config)
        combined_stats = get_combined_statistics(results)
        
        return jsonify({
            'success': True,
            'results': results,
            'combined_statistics': combined_stats
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/trades', methods=['GET'])
def get_trades():
    """获取历史交易记录"""
    try:
        results = load_trades()
        combined_stats = get_combined_statistics(results)
        
        return jsonify({
            'success': True,
            'results': results,
            'combined_statistics': combined_stats
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


def create_templates():
    """创建HTML模板"""
    templates_dir = os.path.join(BASE_DIR, 'templates')
    if not os.path.exists(templates_dir):
        os.makedirs(templates_dir)
    
    # 创建主页模板
    index_html = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>股票回测系统</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <div class="container">
        <header>
            <h1>📈 股票回测系统</h1>
            <p class="subtitle">基于K线策略和交易策略的量化回测工具</p>
        </header>
        
        <div class="main-content">
            <!-- 配置区域 -->
            <section class="config-section">
                <h2>⚙️ 策略配置</h2>
                
                <div class="config-grid">
                    <div class="config-group">
                        <label for="stockCode">股票代码</label>
                        <input type="text" id="stockCode" placeholder="多个股票用分号分隔，如: 000001;600000">
                        <small>支持多只股票回测</small>
                    </div>
                    
                    <div class="config-group">
                        <label for="backtestYear">回测年数</label>
                        <input type="number" id="backtestYear" min="1" max="20" value="3">
                        <small>历史回测的时间跨度</small>
                    </div>
                    
                    <div class="config-group">
                        <label for="saveOffline">
                            <input type="checkbox" id="saveOffline" checked>
                            保存离线数据
                        </label>
                        <small>启用后将缓存股票数据到本地</small>
                    </div>
                </div>
                
                <div class="strategy-section">
                    <h3>📊 K线策略</h3>
                    <div class="config-group">
                        <label for="klineStrategy">买入K线条件</label>
                        <input type="text" id="klineStrategy" placeholder="(D5MA > D10MA) && (D10MA > D30MA)">
                        <small>支持 DMA/WMA/MMA 均线，支持 &&(与)、||(或)、!(非)、*N(连续N天)</small>
                    </div>
                </div>
                
                <div class="strategy-section">
                    <h3>💹 交易策略</h3>
                    <div class="config-grid">
                        <div class="config-group">
                            <label for="buyCondition">买入条件</label>
                            <input type="text" id="buyCondition" placeholder="DK < -2%">
                            <small>当日跌幅条件，如: DK < -2%</small>
                        </div>
                        
                        <div class="config-group">
                            <label for="gainPct">止盈比例 (%)</label>
                            <input type="number" id="gainPct" min="0" max="100" step="0.5" value="5">
                        </div>
                        
                        <div class="config-group">
                            <label for="lossPct">止损比例 (%)</label>
                            <input type="number" id="lossPct" min="0" max="100" step="0.5" value="10">
                        </div>
                        
                        <div class="config-group">
                            <label for="holdPeriod">最长持有周期 (天)</label>
                            <input type="number" id="holdPeriod" min="1" max="365" value="60">
                        </div>
                    </div>
                </div>
                
                <div class="button-group">
                    <button id="saveConfigBtn" class="btn btn-secondary">💾 保存配置</button>
                    <button id="startBacktestBtn" class="btn btn-primary">🚀 开始回测</button>
                </div>
            </section>
            
            <!-- 结果区域 -->
            <section class="result-section" id="resultSection" style="display: none;">
                <h2>📊 回测结果</h2>
                
                <!-- 统计摘要 -->
                <div class="stats-cards" id="statsCards">
                    <div class="stat-card">
                        <div class="stat-value" id="totalTrades">0</div>
                        <div class="stat-label">总交易次数</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="winRate">0%</div>
                        <div class="stat-label">赢率</div>
                    </div>
                    <div class="stat-card profit">
                        <div class="stat-value" id="totalReturn">¥0</div>
                        <div class="stat-label">总收益</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="returnPct">0%</div>
                        <div class="stat-label">收益率</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="avgHoldDays">0</div>
                        <div class="stat-label">平均持有天数</div>
                    </div>
                </div>
                
                <!-- 交易记录表格 -->
                <div class="trades-table-container">
                    <h3>📝 交易明细</h3>
                    <table class="trades-table" id="tradesTable">
                        <thead>
                            <tr>
                                <th>买入日期</th>
                                <th>股票代码</th>
                                <th>股票名称</th>
                                <th>买入价格</th>
                                <th>卖出日期</th>
                                <th>卖出价格</th>
                                <th>盈亏金额</th>
                                <th>盈亏比例</th>
                                <th>卖出原因</th>
                                <th>持有天数</th>
                            </tr>
                        </thead>
                        <tbody id="tradesTableBody">
                        </tbody>
                    </table>
                </div>
            </section>
        </div>
        
        <!-- 加载遮罩 -->
        <div class="loading-overlay" id="loadingOverlay">
            <div class="loading-spinner"></div>
            <div class="loading-text">正在回测中，请稍候...</div>
        </div>
    </div>
    
    <script src="/static/app.js"></script>
</body>
</html>'''
    
    with open(os.path.join(templates_dir, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(index_html)


def create_static_files():
    """创建静态文件"""
    static_dir = os.path.join(BASE_DIR, 'static')
    if not os.path.exists(static_dir):
        os.makedirs(static_dir)
    
    # CSS样式
    css_content = '''/* 基础样式 */
:root {
    --primary-color: #6366f1;
    --primary-hover: #4f46e5;
    --secondary-color: #64748b;
    --success-color: #22c55e;
    --danger-color: #ef4444;
    --warning-color: #f59e0b;
    --bg-color: #0f172a;
    --card-bg: #1e293b;
    --card-border: #334155;
    --text-primary: #f8fafc;
    --text-secondary: #94a3b8;
    --input-bg: #0f172a;
    --input-border: #475569;
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    color: var(--text-primary);
    min-height: 100vh;
    line-height: 1.6;
}

.container {
    max-width: 1400px;
    margin: 0 auto;
    padding: 2rem;
}

/* 头部样式 */
header {
    text-align: center;
    margin-bottom: 3rem;
    padding: 2rem;
    background: linear-gradient(135deg, rgba(99, 102, 241, 0.1) 0%, rgba(139, 92, 246, 0.1) 100%);
    border-radius: 16px;
    border: 1px solid rgba(99, 102, 241, 0.2);
}

header h1 {
    font-size: 2.5rem;
    background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 0.5rem;
}

.subtitle {
    color: var(--text-secondary);
    font-size: 1.1rem;
}

/* 配置区域 */
.config-section, .result-section {
    background: var(--card-bg);
    border-radius: 16px;
    padding: 2rem;
    margin-bottom: 2rem;
    border: 1px solid var(--card-border);
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
}

.config-section h2, .result-section h2 {
    color: var(--text-primary);
    margin-bottom: 1.5rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid var(--card-border);
}

.config-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 1.5rem;
    margin-bottom: 1.5rem;
}

.config-group {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

.config-group label {
    font-weight: 500;
    color: var(--text-primary);
}

.config-group input[type="text"],
.config-group input[type="number"] {
    padding: 0.75rem 1rem;
    border: 1px solid var(--input-border);
    border-radius: 8px;
    background: var(--input-bg);
    color: var(--text-primary);
    font-size: 1rem;
    transition: border-color 0.2s, box-shadow 0.2s;
}

.config-group input:focus {
    outline: none;
    border-color: var(--primary-color);
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2);
}

.config-group small {
    color: var(--text-secondary);
    font-size: 0.85rem;
}

.config-group input[type="checkbox"] {
    width: 18px;
    height: 18px;
    margin-right: 0.5rem;
    accent-color: var(--primary-color);
}

.strategy-section {
    margin-top: 2rem;
    padding-top: 1.5rem;
    border-top: 1px solid var(--card-border);
}

.strategy-section h3 {
    color: var(--text-primary);
    margin-bottom: 1rem;
}

/* 按钮样式 */
.button-group {
    display: flex;
    gap: 1rem;
    margin-top: 2rem;
    justify-content: flex-end;
}

.btn {
    padding: 0.875rem 2rem;
    border: none;
    border-radius: 8px;
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
}

.btn-primary {
    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
    color: white;
}

.btn-primary:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4);
}

.btn-secondary {
    background: var(--secondary-color);
    color: white;
}

.btn-secondary:hover {
    background: #475569;
}

/* 统计卡片 */
.stats-cards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 1.5rem;
    margin-bottom: 2rem;
}

.stat-card {
    background: linear-gradient(135deg, rgba(99, 102, 241, 0.1) 0%, rgba(139, 92, 246, 0.05) 100%);
    border: 1px solid rgba(99, 102, 241, 0.2);
    border-radius: 12px;
    padding: 1.5rem;
    text-align: center;
    transition: transform 0.2s;
}

.stat-card:hover {
    transform: translateY(-4px);
}

.stat-value {
    font-size: 2rem;
    font-weight: 700;
    color: var(--primary-color);
    margin-bottom: 0.5rem;
}

.stat-card.profit .stat-value {
    color: var(--success-color);
}

.stat-card.loss .stat-value {
    color: var(--danger-color);
}

.stat-label {
    color: var(--text-secondary);
    font-size: 0.95rem;
}

/* 交易表格 */
.trades-table-container {
    overflow-x: auto;
}

.trades-table-container h3 {
    margin-bottom: 1rem;
    color: var(--text-primary);
}

.trades-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.95rem;
}

.trades-table th,
.trades-table td {
    padding: 1rem;
    text-align: left;
    border-bottom: 1px solid var(--card-border);
}

.trades-table th {
    background: rgba(99, 102, 241, 0.1);
    color: var(--text-primary);
    font-weight: 600;
    white-space: nowrap;
}

.trades-table tr:hover {
    background: rgba(99, 102, 241, 0.05);
}

.trades-table .profit-positive {
    color: var(--success-color);
    font-weight: 600;
}

.trades-table .profit-negative {
    color: var(--danger-color);
    font-weight: 600;
}

.trades-table .reason-gain {
    background: rgba(34, 197, 94, 0.2);
    color: var(--success-color);
    padding: 0.25rem 0.75rem;
    border-radius: 20px;
    font-size: 0.85rem;
}

.trades-table .reason-loss {
    background: rgba(239, 68, 68, 0.2);
    color: var(--danger-color);
    padding: 0.25rem 0.75rem;
    border-radius: 20px;
    font-size: 0.85rem;
}

.trades-table .reason-expire {
    background: rgba(245, 158, 11, 0.2);
    color: var(--warning-color);
    padding: 0.25rem 0.75rem;
    border-radius: 20px;
    font-size: 0.85rem;
}

/* 加载遮罩 */
.loading-overlay {
    display: none;
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(15, 23, 42, 0.9);
    z-index: 1000;
    justify-content: center;
    align-items: center;
    flex-direction: column;
    gap: 1.5rem;
}

.loading-overlay.active {
    display: flex;
}

.loading-spinner {
    width: 60px;
    height: 60px;
    border: 4px solid rgba(99, 102, 241, 0.2);
    border-top-color: var(--primary-color);
    border-radius: 50%;
    animation: spin 1s linear infinite;
}

@keyframes spin {
    to {
        transform: rotate(360deg);
    }
}

.loading-text {
    color: var(--text-primary);
    font-size: 1.1rem;
}

/* 响应式 */
@media (max-width: 768px) {
    .container {
        padding: 1rem;
    }
    
    header h1 {
        font-size: 1.8rem;
    }
    
    .config-grid {
        grid-template-columns: 1fr;
    }
    
    .button-group {
        flex-direction: column;
    }
    
    .btn {
        width: 100%;
        justify-content: center;
    }
}
'''
    
    with open(os.path.join(static_dir, 'style.css'), 'w', encoding='utf-8') as f:
        f.write(css_content)
    
    # JavaScript
    js_content = '''// 股票回测系统前端脚本

document.addEventListener('DOMContentLoaded', function() {
    // 加载配置
    loadConfig();
    
    // 加载历史交易记录
    loadTrades();
    
    // 绑定事件
    document.getElementById('saveConfigBtn').addEventListener('click', saveConfig);
    document.getElementById('startBacktestBtn').addEventListener('click', startBacktest);
});

// 加载配置
async function loadConfig() {
    try {
        const response = await fetch('/api/config');
        const data = await response.json();
        
        if (data.success) {
            const config = data.config;
            
            document.getElementById('stockCode').value = config.target_stock_code || '';
            document.getElementById('backtestYear').value = config.backtest_year || 3;
            document.getElementById('saveOffline').checked = config.save_offline_data !== false;
            
            // K线策略
            if (config.kline_strategy) {
                document.getElementById('klineStrategy').value = config.kline_strategy.buy || '';
            }
            
            // 交易策略
            if (config.trade_strategy) {
                document.getElementById('buyCondition').value = config.trade_strategy.BUYS || '';
                
                if (config.trade_strategy.SELL) {
                    document.getElementById('gainPct').value = config.trade_strategy.SELL.GAIN || 5;
                    document.getElementById('lossPct').value = config.trade_strategy.SELL.LOSS || 10;
                    document.getElementById('holdPeriod').value = config.trade_strategy.SELL.PERIOD || 60;
                }
            }
        }
    } catch (error) {
        console.error('加载配置失败:', error);
        showMessage('加载配置失败: ' + error.message, 'error');
    }
}

// 保存配置
async function saveConfig() {
    const config = {
        target_stock_code: document.getElementById('stockCode').value,
        backtest_year: parseInt(document.getElementById('backtestYear').value) || 3,
        save_offline_data: document.getElementById('saveOffline').checked,
        kline_strategy: {
            buy: document.getElementById('klineStrategy').value
        },
        trade_strategy: {
            BUYS: document.getElementById('buyCondition').value,
            SELL: {
                GAIN: parseFloat(document.getElementById('gainPct').value) || 5,
                LOSS: parseFloat(document.getElementById('lossPct').value) || 10,
                PERIOD: parseInt(document.getElementById('holdPeriod').value) || 60
            }
        }
    };
    
    try {
        const response = await fetch('/api/config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(config)
        });
        
        const data = await response.json();
        
        if (data.success) {
            showMessage('配置保存成功', 'success');
        } else {
            showMessage('保存失败: ' + data.error, 'error');
        }
    } catch (error) {
        console.error('保存配置失败:', error);
        showMessage('保存配置失败: ' + error.message, 'error');
    }
}

// 开始回测
async function startBacktest() {
    // 先保存配置
    await saveConfig();
    
    showLoading(true);
    
    try {
        const response = await fetch('/api/backtest', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            displayResults(data.results, data.combined_statistics);
            showMessage('回测完成', 'success');
        } else {
            showMessage('回测失败: ' + data.error, 'error');
        }
    } catch (error) {
        console.error('回测失败:', error);
        showMessage('回测失败: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

// 加载历史交易记录
async function loadTrades() {
    try {
        const response = await fetch('/api/trades');
        const data = await response.json();
        
        if (data.success && data.results && data.results.length > 0) {
            displayResults(data.results, data.combined_statistics);
        }
    } catch (error) {
        console.error('加载交易记录失败:', error);
    }
}

// 显示结果
function displayResults(results, combinedStats) {
    const resultSection = document.getElementById('resultSection');
    resultSection.style.display = 'block';
    
    // 更新统计卡片
    document.getElementById('totalTrades').textContent = combinedStats.total_trades;
    document.getElementById('winRate').textContent = combinedStats.win_rate + '%';
    
    const totalReturn = combinedStats.total_return;
    const totalReturnEl = document.getElementById('totalReturn');
    totalReturnEl.textContent = '¥' + formatNumber(totalReturn);
    totalReturnEl.parentElement.className = 'stat-card ' + (totalReturn >= 0 ? 'profit' : 'loss');
    
    const returnPct = combinedStats.total_return_pct;
    const returnPctEl = document.getElementById('returnPct');
    returnPctEl.textContent = (returnPct >= 0 ? '+' : '') + returnPct + '%';
    returnPctEl.parentElement.className = 'stat-card ' + (returnPct >= 0 ? 'profit' : 'loss');
    
    document.getElementById('avgHoldDays').textContent = combinedStats.avg_hold_days + '天';
    
    // 更新交易表格
    const tbody = document.getElementById('tradesTableBody');
    tbody.innerHTML = '';
    
    // 收集所有交易
    const allTrades = [];
    results.forEach(result => {
        if (result.trades) {
            result.trades.forEach(trade => {
                allTrades.push(trade);
            });
        }
    });
    
    // 按日期排序
    allTrades.sort((a, b) => new Date(b.buy_date) - new Date(a.buy_date));
    
    // 渲染表格
    allTrades.forEach(trade => {
        const row = document.createElement('tr');
        
        const profitClass = trade.profit >= 0 ? 'profit-positive' : 'profit-negative';
        let reasonClass = 'reason-expire';
        if (trade.sell_reason === '止盈') reasonClass = 'reason-gain';
        else if (trade.sell_reason === '止损') reasonClass = 'reason-loss';
        
        row.innerHTML = `
            <td>${trade.buy_date}</td>
            <td>${trade.stock_code}</td>
            <td>${trade.stock_name}</td>
            <td>¥${trade.buy_price.toFixed(2)}</td>
            <td>${trade.sell_date}</td>
            <td>¥${trade.sell_price.toFixed(2)}</td>
            <td class="${profitClass}">¥${formatNumber(trade.profit)}</td>
            <td class="${profitClass}">${trade.profit_pct >= 0 ? '+' : ''}${trade.profit_pct.toFixed(2)}%</td>
            <td><span class="${reasonClass}">${trade.sell_reason}</span></td>
            <td>${trade.hold_days}天</td>
        `;
        
        tbody.appendChild(row);
    });
    
    // 滚动到结果区域
    resultSection.scrollIntoView({ behavior: 'smooth' });
}

// 格式化数字
function formatNumber(num) {
    if (num >= 10000 || num <= -10000) {
        return (num / 10000).toFixed(2) + '万';
    }
    return num.toFixed(2);
}

// 显示加载遮罩
function showLoading(show) {
    const overlay = document.getElementById('loadingOverlay');
    overlay.classList.toggle('active', show);
}

// 显示消息
function showMessage(message, type) {
    // 简单的消息提示
    const existingToast = document.querySelector('.toast');
    if (existingToast) {
        existingToast.remove();
    }
    
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        color: white;
        font-weight: 500;
        z-index: 1001;
        animation: slideIn 0.3s ease;
        background: ${type === 'success' ? '#22c55e' : '#ef4444'};
    `;
    toast.textContent = message;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// 添加动画样式
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);
'''
    
    with open(os.path.join(static_dir, 'app.js'), 'w', encoding='utf-8') as f:
        f.write(js_content)


def start_server(host='127.0.0.1', port=5000, debug=False):
    """启动Web服务器"""
    # 创建模板和静态文件
    create_templates()
    create_static_files()
    
    print(f"启动股票回测系统...")
    print(f"请访问: http://{host}:{port}")
    
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    start_server(debug=True)
