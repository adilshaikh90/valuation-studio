const ChartConfig = {
    defaults: {
        backgroundColor: 'transparent',
        fontColor: '#9ca3af',
        gridColor: 'rgba(255,255,255,0.06)',
        goldColor: '#f0b429',
        greenColor: '#10b981',
        redColor: '#ef4444',
        blueColor: '#3b82f6',
        purpleColor: '#8b5cf6',
    },
    
    // Apply global Chart.js defaults
    init() {
        if (typeof Chart === 'undefined') return;
        Chart.defaults.color = this.defaults.fontColor;
        Chart.defaults.font.family = "'Inter', sans-serif";
        Chart.defaults.scale.grid.color = this.defaults.gridColor;
    },
    
    createFootballField(canvasId, data, currentPrice, currency) {
        if (typeof Chart === 'undefined') return null;
        const ctx = document.getElementById(canvasId).getContext('2d');
        
        const labels = data.map(d => d.method);
        const ranges = data.map(d => [d.min, d.max]);
        
        return new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Valuation Range',
                    data: ranges,
                    backgroundColor: 'rgba(240, 180, 41, 0.6)',
                    borderColor: '#f0b429',
                    borderWidth: 1,
                    barThickness: 24
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    annotation: {
                        annotations: {
                            line1: {
                                type: 'line',
                                xMin: currentPrice,
                                xMax: currentPrice,
                                borderColor: this.defaults.blueColor,
                                borderWidth: 2,
                                borderDash: [5, 5],
                                label: {
                                    content: `Current: ${currency}${currentPrice}`,
                                    enabled: true,
                                    position: 'end',
                                    backgroundColor: 'rgba(59, 130, 246, 0.8)'
                                }
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { color: this.defaults.gridColor }
                    },
                    y: {
                        grid: { display: false }
                    }
                }
            }
        });
    },
    
    createHistogram(canvasId, binData, percentiles, currentPrice) {
        if (typeof Chart === 'undefined') return null;
        const ctx = document.getElementById(canvasId).getContext('2d');
        
        return new Chart(ctx, {
            type: 'bar',
            data: {
                labels: binData.map(b => b.label),
                datasets: [{
                    label: 'Frequency',
                    data: binData.map(b => b.count),
                    backgroundColor: 'rgba(240, 180, 41, 0.6)',
                    barPercentage: 1.0,
                    categoryPercentage: 1.0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: { grid: { display: false } },
                    y: { grid: { color: this.defaults.gridColor } }
                }
            }
        });
    },
    
    createTornado(canvasId, tornadoData) {
        if (typeof Chart === 'undefined') return null;
        const ctx = document.getElementById(canvasId).getContext('2d');
        
        return new Chart(ctx, {
            type: 'bar',
            data: {
                labels: tornadoData.map(d => d.label),
                datasets: [
                    {
                        label: 'Downside',
                        data: tornadoData.map(d => d.downside),
                        backgroundColor: 'rgba(239, 68, 68, 0.6)',
                        borderColor: '#ef4444',
                        borderWidth: 1
                    },
                    {
                        label: 'Upside',
                        data: tornadoData.map(d => d.upside),
                        backgroundColor: 'rgba(16, 185, 129, 0.6)',
                        borderColor: '#10b981',
                        borderWidth: 1
                    }
                ]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { stacked: false, grid: { color: this.defaults.gridColor } },
                    y: { stacked: true, grid: { display: false } }
                }
            }
        });
    },
    
    destroyChart(chartInstance) {
        if (chartInstance) {
            chartInstance.destroy();
        }
    }
};

// Auto init if Chart.js is loaded
if (typeof Chart !== 'undefined') {
    ChartConfig.init();
}
