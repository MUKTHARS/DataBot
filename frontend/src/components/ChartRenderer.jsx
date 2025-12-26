import React, { useEffect, useRef } from 'react';
import { BarChart3, LineChart, PieChart, TrendingUp } from 'lucide-react';
import Chart from 'chart.js/auto';

const ChartRenderer = ({ chartConfig, data }) => {
  const chartRef = useRef(null);
  const chartInstance = useRef(null);

  useEffect(() => {
    // Destroy previous chart
    if (chartInstance.current) {
      chartInstance.current.destroy();
      chartInstance.current = null;
    }

    if (!chartConfig || !chartRef.current) {
      console.log('No chart config or canvas ref');
      return;
    }

    console.log('Chart config received:', chartConfig);
    console.log('Chart labels:', chartConfig.labels);
    console.log('Chart datasets:', chartConfig.datasets);

    renderChart();

    return () => {
      if (chartInstance.current) {
        chartInstance.current.destroy();
      }
    };
  }, [chartConfig]);

  const renderChart = () => {
    try {
      const ctx = chartRef.current.getContext('2d');
      
      // Ensure chart data is properly structured
      let chartData = {
        labels: [],
        datasets: []
      };

      // Handle different chart config structures
      if (chartConfig.labels && Array.isArray(chartConfig.labels)) {
        chartData.labels = chartConfig.labels;
      }

      if (chartConfig.datasets && Array.isArray(chartConfig.datasets)) {
        chartData.datasets = chartConfig.datasets.map(dataset => ({
          label: dataset.label || 'Data',
          data: dataset.data || [],
          backgroundColor: dataset.backgroundColor || getDefaultColors(chartData.labels.length || 1),
          borderColor: chartConfig.type === 'line' ? dataset.backgroundColor || '#3b82f6' : undefined,
          borderWidth: chartConfig.type === 'line' ? 2 : 1,
          fill: chartConfig.type === 'line'
        }));
      } else if (chartConfig.data && Array.isArray(chartConfig.data)) {
        // Handle simple data array
        chartData.datasets = [{
          label: chartConfig.title || 'Data',
          data: chartConfig.data,
          backgroundColor: getDefaultColors(chartData.labels.length || chartConfig.data.length)
        }];
      }

      // Create chart options
      const options = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'top',
          },
          title: {
            display: true,
            text: chartConfig.title || 'Chart',
            font: {
              size: 16
            }
          }
        },
        scales: chartConfig.type !== 'pie' && chartConfig.type !== 'doughnut' ? {
          y: {
            beginAtZero: true,
            ticks: {
              callback: function(value) {
                return formatNumber(value);
              }
            }
          }
        } : undefined
      };

      console.log('Creating chart with:', {
        type: chartConfig.type,
        data: chartData,
        options: options
      });

      chartInstance.current = new Chart(ctx, {
        type: chartConfig.type || 'bar',
        data: chartData,
        options: options
      });

    } catch (error) {
      console.error('Error rendering chart:', error);
      renderFallbackChart(chartConfig);
    }
  };

  const renderFallbackChart = (config) => {
    const ctx = chartRef.current.getContext('2d');
    const canvas = chartRef.current;
    
    // Clear and show message
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = '#f3f4f6';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    ctx.fillStyle = '#6b7280';
    ctx.font = '14px Arial';
    ctx.textAlign = 'center';
    ctx.fillText('Chart Preview', canvas.width / 2, canvas.height / 2 - 30);
    ctx.fillText(`Type: ${config?.type || 'unknown'}`, canvas.width / 2, canvas.height / 2 - 10);
    ctx.fillText(`Title: ${config?.title || 'No title'}`, canvas.width / 2, canvas.height / 2 + 10);
    ctx.fillText(`Labels: ${config?.labels?.length || 0}`, canvas.width / 2, canvas.height / 2 + 30);
    
    // Draw a simple bar for debugging
    if (config?.labels && config.labels.length > 0) {
      ctx.fillStyle = '#3b82f6';
      const barWidth = 30;
      const barSpacing = 10;
      const startX = 50;
      const maxHeight = 100;
      const maxValue = Math.max(...(config.datasets?.[0]?.data || [100]));
      
      config.labels.slice(0, 5).forEach((label, index) => {
        const value = config.datasets?.[0]?.data?.[index] || 50;
        const barHeight = (value / maxValue) * maxHeight;
        const x = startX + (index * (barWidth + barSpacing));
        const y = canvas.height - 100 - barHeight;
        
        ctx.fillRect(x, y, barWidth, barHeight);
      });
    }
  };

  const getDefaultColors = (count) => {
    const colors = [
      '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6',
      '#06b6d4', '#84cc16', '#f97316', '#6366f1', '#ec4899',
      '#14b8a6', '#f43f5e', '#0ea5e9', '#22c55e', '#eab308'
    ];
    
    if (count <= colors.length) {
      return colors.slice(0, count);
    }
    
    // Generate additional colors if needed
    const additional = [];
    for (let i = 0; i < count - colors.length; i++) {
      additional.push(getRandomColor());
    }
    return [...colors, ...additional];
  };

  const getRandomColor = () => {
    const letters = '0123456789ABCDEF';
    let color = '#';
    for (let i = 0; i < 6; i++) {
      color += letters[Math.floor(Math.random() * 16)];
    }
    return color;
  };

  const formatNumber = (value) => {
    if (typeof value !== 'number') return value;
    
    if (value >= 1000000) {
      return '$' + (value / 1000000).toFixed(1) + 'M';
    } else if (value >= 1000) {
      return '$' + (value / 1000).toFixed(1) + 'K';
    } else {
      return '$' + value.toFixed(2);
    }
  };

  const getChartIcon = () => {
    switch(chartConfig?.type) {
      case 'bar': return <BarChart3 size={20} />;
      case 'line': return <LineChart size={20} />;
      case 'pie': return <PieChart size={20} />;
      default: return <TrendingUp size={20} />;
    }
  };

  if (!chartConfig) {
    return (
      <div className="chart-container">
        <div className="chart-header">
          <TrendingUp size={20} />
          <h4>No chart data available</h4>
        </div>
      </div>
    );
  }

  return (
    <div className="chart-renderer">
      <div className="chart-container">
        <div className="chart-header">
          {getChartIcon()}
          <h4>{chartConfig.title || 'Chart'}</h4>
          <span className="chart-type-badge">{chartConfig.type} chart</span>
        </div>
        
        <div className="chart-canvas-container">
          <canvas 
            ref={chartRef} 
            width={600} 
            height={400}
            className="chart-canvas"
          />
        </div>
        
        <div className="chart-info">
          <div className="chart-stats">
            <span className="stat-item">
              <strong>Type:</strong> {chartConfig.type}
            </span>
            <span className="stat-item">
              <strong>Data Points:</strong> {chartConfig.labels?.length || 0}
            </span>
            <span className="stat-item">
              <strong>Datasets:</strong> {chartConfig.datasets?.length || 0}
            </span>
          </div>
          
          {chartConfig.datasets?.[0]?.data && (
            <div className="chart-summary">
              <h5>Data Summary:</h5>
              <div className="data-points">
                {(chartConfig.labels || []).slice(0, 3).map((label, index) => (
                  <div key={index} className="data-point">
                    <span className="label">{label}:</span>
                    <span className="value">
                      {formatNumber(chartConfig.datasets[0].data[index])}
                    </span>
                  </div>
                ))}
                {(chartConfig.labels || []).length > 3 && (
                  <div className="data-point">
                    <span className="label">...and {(chartConfig.labels || []).length - 3} more</span>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ChartRenderer;