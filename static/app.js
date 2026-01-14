// 股票回测系统前端脚本

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
