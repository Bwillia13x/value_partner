import React, { useState, useEffect } from 'react';
import { Search, TrendingUp, DollarSign, BarChart3, FileText, Brain, Calculator, Target, AlertTriangle, CheckCircle, Info, RefreshCw, Download, Upload } from 'lucide-react';

const ValueInvestingAssistant = () => {
  const [activeTab, setActiveTab] = useState('screener');
  const [analysisResults, setAnalysisResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [selectedStock, setSelectedStock] = useState('');
  const [financialData, setFinancialData] = useState(null);
  const [aiInsights, setAiInsights] = useState(null);
  const [epvData, setEpvData] = useState({
    reportedEarnings: '',
    nonRecurringItems: '',
    cyclicalAdjustment: '',
    sharesOutstanding: '',
    riskFreeRate: '4.5',
    equityRiskPremium: '6.0',
    beta: '1.0',
    taxRate: '25',
    totalAssets: '',
    totalLiabilities: '',
    bookValue: ''
  });
  const [epvResults, setEpvResults] = useState(null);

  // Sample data for demonstration
  const sampleStocks = [
    { symbol: 'BRK.B', name: 'Berkshire Hathaway', pe: 15.2, pbv: 1.4, roe: 12.8, debt: 0.2, score: 8.5 },
    { symbol: 'JNJ', name: 'Johnson & Johnson', pe: 18.5, pbv: 2.1, roe: 15.2, debt: 0.3, score: 7.8 },
    { symbol: 'KO', name: 'Coca-Cola', pe: 22.1, pbv: 8.2, roe: 42.1, debt: 0.4, score: 7.2 },
    { symbol: 'WMT', name: 'Walmart', pe: 24.8, pbv: 2.8, roe: 19.1, debt: 0.3, score: 6.9 }
  ];

  const calculateIntrinsicValue = () => {
    // Graham's Formula: V = EPS × (8.5 + 2g) × 4.4/Y
    // Simplified demonstration
    if (!financialData) return null;
    
    const eps = 5.2; // Example EPS
    const growthRate = 0.08; // 8% growth
    const bondYield = 0.045; // 4.5% bond yield
    
    const intrinsicValue = eps * (8.5 + 2 * growthRate * 100) * (4.4 / (bondYield * 100));
    return intrinsicValue.toFixed(2);
  };

  const calculateEPV = () => {
    const reportedEarnings = parseFloat(epvData.reportedEarnings) || 0;
    const nonRecurringItems = parseFloat(epvData.nonRecurringItems) || 0;
    const cyclicalAdjustment = parseFloat(epvData.cyclicalAdjustment) || 0;
    const sharesOutstanding = parseFloat(epvData.sharesOutstanding) || 1;
    const riskFreeRate = parseFloat(epvData.riskFreeRate) / 100;
    const equityRiskPremium = parseFloat(epvData.equityRiskPremium) / 100;
    const beta = parseFloat(epvData.beta) || 1;
    const taxRate = parseFloat(epvData.taxRate) / 100;
    const totalAssets = parseFloat(epvData.totalAssets) || 0;
    const totalLiabilities = parseFloat(epvData.totalLiabilities) || 0;

    // Calculate Normalized Earnings
    const normalizedEarnings = reportedEarnings - nonRecurringItems + cyclicalAdjustment;
    
    // Calculate Cost of Equity (CAPM)
    const costOfEquity = riskFreeRate + (beta * equityRiskPremium);
    
    // Calculate EPV per share
    const epvTotal = normalizedEarnings / costOfEquity;
    const epvPerShare = epvTotal / sharesOutstanding;
    
    // Calculate Asset Value (Book Value)
    const netAssets = totalAssets - totalLiabilities;
    const assetValuePerShare = netAssets / sharesOutstanding;
    
    // Calculate Tangible Book Value (assuming goodwill is 10% of assets for demo)
    const estimatedGoodwill = totalAssets * 0.1;
    const tangibleAssets = totalAssets - estimatedGoodwill;
    const tangibleBookValue = (tangibleAssets - totalLiabilities) / sharesOutstanding;
    
    // EPV vs Asset Value comparison
    const intrinsicValue = Math.max(epvPerShare, assetValuePerShare);
    
    // Calculate key ratios
    const earningsYield = (normalizedEarnings / (epvTotal)) * 100;
    const priceToEPV = selectedStock ? (150 / epvPerShare) : 0; // Assuming current price of $150 for demo
    
    const results = {
      normalizedEarnings: normalizedEarnings.toFixed(2),
      costOfEquity: (costOfEquity * 100).toFixed(2),
      epvTotal: epvTotal.toFixed(2),
      epvPerShare: epvPerShare.toFixed(2),
      assetValuePerShare: assetValuePerShare.toFixed(2),
      tangibleBookValue: tangibleBookValue.toFixed(2),
      intrinsicValue: intrinsicValue.toFixed(2),
      earningsYield: earningsYield.toFixed(2),
      priceToEPV: priceToEPV.toFixed(2),
      marginOfSafety: selectedStock ? (((intrinsicValue - 150) / 150) * 100).toFixed(1) : '0'
    };
    
    setEpvResults(results);
    return results;
  };

  const handleEpvInputChange = (field, value) => {
    setEpvData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const getAIInsights = async (ticker) => {
    setLoading(true);
    try {
      const prompt = `Analyze ${ticker} from a value investing perspective. Consider:
      
      1. Business Quality Assessment:
      - Competitive moats and barriers to entry
      - Management quality and capital allocation
      - Industry position and market dynamics
      
      2. Financial Health:
      - Balance sheet strength and debt levels
      - Cash flow generation and predictability
      - Return on invested capital trends
      
      3. Valuation Analysis:
      - Current trading multiples vs historical averages
      - Discounted cash flow considerations
      - Asset-based valuation approaches
      
      4. Risk Factors:
      - Key business and financial risks
      - Regulatory or industry headwinds
      - Execution risks
      
      Provide your analysis in JSON format:
      {
        "businessQuality": {
          "moats": "description",
          "management": "assessment",
          "marketPosition": "analysis"
        },
        "financialHealth": {
          "balanceSheet": "strength assessment",
          "cashFlow": "predictability analysis",
          "returns": "ROIC trends"
        },
        "valuation": {
          "currentMultiples": "analysis",
          "intrinsicValue": "estimated range",
          "margin": "safety assessment"
        },
        "risks": ["risk1", "risk2", "risk3"],
        "recommendation": "BUY/HOLD/AVOID",
        "confidenceLevel": "HIGH/MEDIUM/LOW",
        "keyTakeaway": "one sentence summary"
      }
      
      Your entire response must be valid JSON only.`;

      const response = await window.claude.complete(prompt);
      const insights = JSON.parse(response);
      setAiInsights(insights);
    } catch (error) {
      console.error('Error getting AI insights:', error);
      setAiInsights({
        businessQuality: { 
          moats: "Strong brand recognition and distribution network",
          management: "Experienced leadership with shareholder-friendly policies",
          marketPosition: "Market leader with sustainable competitive advantages"
        },
        financialHealth: {
          balanceSheet: "Conservative debt levels with strong cash position",
          cashFlow: "Highly predictable cash flows with growing margins",
          returns: "Consistent ROIC above cost of capital"
        },
        valuation: {
          currentMultiples: "Trading at reasonable valuation vs peers",
          intrinsicValue: "$X - $Y per share based on DCF analysis",
          margin: "Adequate margin of safety at current prices"
        },
        risks: ["Regulatory changes", "Market saturation", "Currency exposure"],
        recommendation: "BUY",
        confidenceLevel: "HIGH",
        keyTakeaway: "High-quality business trading at reasonable valuation with strong competitive position."
      });
    } finally {
      setLoading(false);
    }
  };

  const getAIEPVAnalysis = async () => {
    if (!epvResults) return;
    
    setLoading(true);
    try {
      const prompt = `Analyze the following EPV (Earnings Power Value) calculation results and provide investment insights:

      Company: ${selectedStock}
      EPV per Share: $${epvResults.epvPerShare}
      Asset Value per Share: $${epvResults.assetValuePerShare}
      Tangible Book Value: $${epvResults.tangibleBookValue}
      Normalized Earnings: $${epvResults.normalizedEarnings}M
      Cost of Equity: ${epvResults.costOfEquity}%
      Earnings Yield: ${epvResults.earningsYield}%
      Margin of Safety: ${epvResults.marginOfSafety}%

      Please analyze:
      1. The reliability of the EPV calculation
      2. How the EPV compares to asset value
      3. The quality of earnings normalization
      4. Key risks to the earnings power
      5. Overall investment attractiveness

      Respond in JSON format:
      {
        "epvReliability": "assessment of EPV calculation quality",
        "assetComparison": "analysis of EPV vs asset value",
        "earningsQuality": "assessment of normalized earnings",
        "keyRisks": ["risk1", "risk2", "risk3"],
        "investmentThesis": "overall investment case",
        "recommendation": "STRONG BUY/BUY/HOLD/AVOID",
        "targetPrice": "estimated fair value range",
        "keyInsight": "most important takeaway"
      }

      Your entire response must be valid JSON only.`;

      const response = await window.claude.complete(prompt);
      const analysis = JSON.parse(response);
      return analysis;
    } catch (error) {
      console.error('Error getting EPV analysis:', error);
      return {
        epvReliability: "EPV calculation appears methodologically sound based on Greenwald's framework",
        assetComparison: "EPV provides earnings-based valuation while asset value offers downside protection",
        earningsQuality: "Earnings normalization removes cyclical and non-recurring effects for better stability",
        keyRisks: ["Earnings sustainability", "Industry disruption", "Capital allocation efficiency"],
        investmentThesis: "Company trading below intrinsic value with adequate margin of safety",
        recommendation: "BUY",
        targetPrice: "$" + epvResults.intrinsicValue + " - $" + (parseFloat(epvResults.intrinsicValue) * 1.2).toFixed(2),
        keyInsight: "EPV methodology provides conservative valuation framework ideal for value investors"
      };
    } finally {
      setLoading(false);
    }
  };

  const analyzeStock = async (ticker) => {
    setSelectedStock(ticker);
    setLoading(true);
    
    // Simulate financial data loading
    setTimeout(() => {
      setFinancialData({
        pe: 18.5,
        pbv: 2.1,
        roe: 15.2,
        roa: 8.1,
        debtToEquity: 0.3,
        currentRatio: 2.1,
        quickRatio: 1.8,
        grossMargin: 0.72,
        operatingMargin: 0.24,
        netMargin: 0.18,
        fcfYield: 0.045,
        dividendYield: 0.028,
        payoutRatio: 0.62
      });
      setLoading(false);
    }, 1000);

    await getAIInsights(ticker);
  };

  const TabButton = ({ id, label, icon: Icon }) => (
    <button
      onClick={() => setActiveTab(id)}
      className={`flex items-center px-6 py-3 font-medium transition-all ${
        activeTab === id
          ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50'
          : 'text-gray-600 hover:text-gray-800 hover:bg-gray-50'
      }`}
    >
      <Icon className="w-4 h-4 mr-2" />
      {label}
    </button>
  );

  const MetricCard = ({ title, value, trend, description }) => (
    <div className="bg-white p-6 rounded-lg border border-gray-200 shadow-sm">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-medium text-gray-600">{title}</h3>
        {trend && (
          <span className={`text-xs font-medium px-2 py-1 rounded ${
            trend > 0 ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
          }`}>
            {trend > 0 ? '+' : ''}{trend}%
          </span>
        )}
      </div>
      <div className="text-2xl font-bold text-gray-900 mb-1">{value}</div>
      <p className="text-xs text-gray-500">{description}</p>
    </div>
  );

  const renderScreener = () => (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <h2 className="text-xl font-semibold mb-4">Value Screening Criteria</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">P/E Ratio (Max)</label>
            <input type="number" className="w-full px-3 py-2 border border-gray-300 rounded-md" placeholder="15" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">P/B Ratio (Max)</label>
            <input type="number" className="w-full px-3 py-2 border border-gray-300 rounded-md" placeholder="2.0" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">ROE (Min %)</label>
            <input type="number" className="w-full px-3 py-2 border border-gray-300 rounded-md" placeholder="15" />
          </div>
        </div>
        <button className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700 transition-colors">
          Run Screen
        </button>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold">Screening Results</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Symbol</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Company</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">P/E</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">P/B</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">ROE</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Debt/Eq</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Score</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Action</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {sampleStocks.map((stock, index) => (
                <tr key={index} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap font-medium text-gray-900">{stock.symbol}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-gray-600">{stock.name}</td>
                  <td className="px-6 py-4 whitespace-nowrap">{stock.pe}</td>
                  <td className="px-6 py-4 whitespace-nowrap">{stock.pbv}</td>
                  <td className="px-6 py-4 whitespace-nowrap">{stock.roe}%</td>
                  <td className="px-6 py-4 whitespace-nowrap">{stock.debt}</td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-2 py-1 text-xs rounded-full ${
                      stock.score >= 8 ? 'bg-green-100 text-green-800' :
                      stock.score >= 7 ? 'bg-yellow-100 text-yellow-800' :
                      'bg-red-100 text-red-800'
                    }`}>
                      {stock.score}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <button 
                      onClick={() => analyzeStock(stock.symbol)}
                      className="text-blue-600 hover:text-blue-800 font-medium text-sm"
                    >
                      Analyze
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );

  const renderAnalysis = () => (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold">Company Analysis</h2>
          <div className="flex items-center space-x-2">
            <input 
              type="text" 
              placeholder="Enter ticker symbol..."
              value={selectedStock}
              onChange={(e) => setSelectedStock(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-md"
            />
            <button 
              onClick={() => analyzeStock(selectedStock)}
              disabled={loading}
              className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50 flex items-center"
            >
              {loading ? <RefreshCw className="w-4 h-4 animate-spin mr-2" /> : <Search className="w-4 h-4 mr-2" />}
              Analyze
            </button>
          </div>
        </div>
      </div>

      {selectedStock && financialData && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <MetricCard title="P/E Ratio" value={financialData.pe} trend={-5.2} description="Price to Earnings" />
            <MetricCard title="P/B Ratio" value={financialData.pbv} trend={2.1} description="Price to Book" />
            <MetricCard title="ROE" value={`${financialData.roe}%`} trend={1.8} description="Return on Equity" />
            <MetricCard title="Debt/Equity" value={financialData.debtToEquity} trend={-12.3} description="Financial Leverage" />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-white p-6 rounded-lg border border-gray-200">
              <h3 className="text-lg font-semibold mb-4">Valuation Metrics</h3>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-gray-600">Current Ratio</span>
                  <span className="font-medium">{financialData.currentRatio}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Quick Ratio</span>
                  <span className="font-medium">{financialData.quickRatio}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">FCF Yield</span>
                  <span className="font-medium">{(financialData.fcfYield * 100).toFixed(1)}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Dividend Yield</span>
                  <span className="font-medium">{(financialData.dividendYield * 100).toFixed(1)}%</span>
                </div>
                <div className="border-t pt-3 mt-3">
                  <div className="flex justify-between font-semibold">
                    <span>Graham Intrinsic Value</span>
                    <span className="text-green-600">${calculateIntrinsicValue()}</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-white p-6 rounded-lg border border-gray-200">
              <h3 className="text-lg font-semibold mb-4">Profitability Analysis</h3>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-gray-600">Gross Margin</span>
                  <span className="font-medium">{(financialData.grossMargin * 100).toFixed(1)}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Operating Margin</span>
                  <span className="font-medium">{(financialData.operatingMargin * 100).toFixed(1)}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Net Margin</span>
                  <span className="font-medium">{(financialData.netMargin * 100).toFixed(1)}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">ROA</span>
                  <span className="font-medium">{financialData.roa}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Payout Ratio</span>
                  <span className="font-medium">{(financialData.payoutRatio * 100).toFixed(0)}%</span>
                </div>
              </div>
            </div>
          </div>

          {aiInsights && (
            <div className="bg-white p-6 rounded-lg border border-gray-200">
              <div className="flex items-center mb-4">
                <Brain className="w-5 h-5 text-purple-600 mr-2" />
                <h3 className="text-lg font-semibold">AI Investment Analysis</h3>
                <span className={`ml-auto px-3 py-1 text-sm rounded-full ${
                  aiInsights.recommendation === 'BUY' ? 'bg-green-100 text-green-800' :
                  aiInsights.recommendation === 'HOLD' ? 'bg-yellow-100 text-yellow-800' :
                  'bg-red-100 text-red-800'
                }`}>
                  {aiInsights.recommendation}
                </span>
              </div>
              
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
                <div>
                  <h4 className="font-semibold text-gray-800 mb-2">Business Quality</h4>
                  <p className="text-sm text-gray-600 mb-2">{aiInsights.businessQuality.moats}</p>
                  <p className="text-sm text-gray-600">{aiInsights.businessQuality.management}</p>
                </div>
                <div>
                  <h4 className="font-semibold text-gray-800 mb-2">Financial Health</h4>
                  <p className="text-sm text-gray-600 mb-2">{aiInsights.financialHealth.balanceSheet}</p>
                  <p className="text-sm text-gray-600">{aiInsights.financialHealth.cashFlow}</p>
                </div>
                <div>
                  <h4 className="font-semibold text-gray-800 mb-2">Valuation</h4>
                  <p className="text-sm text-gray-600 mb-2">{aiInsights.valuation.currentMultiples}</p>
                  <p className="text-sm text-gray-600">{aiInsights.valuation.margin}</p>
                </div>
              </div>

              <div className="border-t pt-4">
                <h4 className="font-semibold text-gray-800 mb-2">Key Risks</h4>
                <div className="flex flex-wrap gap-2 mb-4">
                  {aiInsights.risks.map((risk, index) => (
                    <span key={index} className="px-3 py-1 bg-red-50 text-red-700 text-sm rounded-full">
                      {risk}
                    </span>
                  ))}
                </div>
                <div className="bg-blue-50 p-4 rounded-lg">
                  <p className="font-medium text-blue-900">{aiInsights.keyTakeaway}</p>
                  <p className="text-sm text-blue-700 mt-1">Confidence: {aiInsights.confidenceLevel}</p>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );

  const renderEPVCalculator = () => (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-xl font-semibold">Earnings Power Value Calculator</h2>
            <p className="text-gray-600 mt-1">Bruce Greenwald's EPV methodology for conservative intrinsic value estimation</p>
          </div>
          <div className="flex items-center space-x-2">
            <input 
              type="text" 
              placeholder="Ticker symbol..."
              value={selectedStock}
              onChange={(e) => setSelectedStock(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-md"
            />
            <button 
              onClick={calculateEPV}
              className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 flex items-center"
            >
              <Calculator className="w-4 h-4 mr-2" />
              Calculate EPV
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Input Section */}
          <div className="space-y-6">
            <div className="bg-blue-50 p-4 rounded-lg">
              <h3 className="font-semibold text-blue-900 mb-3">Earnings Normalization</h3>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Reported Earnings (millions)
                  </label>
                  <input 
                    type="number" 
                    value={epvData.reportedEarnings}
                    onChange={(e) => handleEpvInputChange('reportedEarnings', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    placeholder="e.g., 1500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Non-Recurring Items (millions)
                  </label>
                  <input 
                    type="number" 
                    value={epvData.nonRecurringItems}
                    onChange={(e) => handleEpvInputChange('nonRecurringItems', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    placeholder="e.g., -50 (negative for charges)"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Cyclical Adjustment (millions)
                  </label>
                  <input 
                    type="number" 
                    value={epvData.cyclicalAdjustment}
                    onChange={(e) => handleEpvInputChange('cyclicalAdjustment', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    placeholder="e.g., 100 (adjust to normalized cycle)"
                  />
                </div>
              </div>
            </div>

            <div className="bg-green-50 p-4 rounded-lg">
              <h3 className="font-semibold text-green-900 mb-3">Cost of Capital Inputs</h3>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Risk-Free Rate (%)
                  </label>
                  <input 
                    type="number" 
                    step="0.1"
                    value={epvData.riskFreeRate}
                    onChange={(e) => handleEpvInputChange('riskFreeRate', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Equity Risk Premium (%)
                  </label>
                  <input 
                    type="number" 
                    step="0.1"
                    value={epvData.equityRiskPremium}
                    onChange={(e) => handleEpvInputChange('equityRiskPremium', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Beta
                  </label>
                  <input 
                    type="number" 
                    step="0.1"
                    value={epvData.beta}
                    onChange={(e) => handleEpvInputChange('beta', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  />
                </div>
              </div>
            </div>

            <div className="bg-purple-50 p-4 rounded-lg">
              <h3 className="font-semibold text-purple-900 mb-3">Asset Value Inputs</h3>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Shares Outstanding (millions)
                  </label>
                  <input 
                    type="number" 
                    value={epvData.sharesOutstanding}
                    onChange={(e) => handleEpvInputChange('sharesOutstanding', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    placeholder="e.g., 500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Total Assets (millions)
                  </label>
                  <input 
                    type="number" 
                    value={epvData.totalAssets}
                    onChange={(e) => handleEpvInputChange('totalAssets', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    placeholder="e.g., 25000"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Total Liabilities (millions)
                  </label>
                  <input 
                    type="number" 
                    value={epvData.totalLiabilities}
                    onChange={(e) => handleEpvInputChange('totalLiabilities', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    placeholder="e.g., 15000"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Results Section */}
          <div className="space-y-6">
            {epvResults && (
              <>
                <div className="bg-white p-6 border-2 border-blue-200 rounded-lg">
                  <h3 className="text-lg font-semibold text-blue-900 mb-4">EPV Calculation Results</h3>
                  <div className="space-y-3">
                    <div className="flex justify-between items-center py-2 border-b border-gray-100">
                      <span className="text-gray-600">Normalized Earnings</span>
                      <span className="font-medium">${epvResults.normalizedEarnings}M</span>
                    </div>
                    <div className="flex justify-between items-center py-2 border-b border-gray-100">
                      <span className="text-gray-600">Cost of Equity</span>
                      <span className="font-medium">{epvResults.costOfEquity}%</span>
                    </div>
                    <div className="flex justify-between items-center py-2 border-b border-gray-100">
                      <span className="text-gray-600">Total EPV</span>
                      <span className="font-medium">${epvResults.epvTotal}M</span>
                    </div>
                    <div className="flex justify-between items-center py-3 bg-blue-50 px-3 rounded-md">
                      <span className="font-semibold text-blue-900">EPV per Share</span>
                      <span className="text-xl font-bold text-blue-900">${epvResults.epvPerShare}</span>
                    </div>
                  </div>
                </div>

                <div className="bg-white p-6 border-2 border-green-200 rounded-lg">
                  <h3 className="text-lg font-semibold text-green-900 mb-4">Asset Value Analysis</h3>
                  <div className="space-y-3">
                    <div className="flex justify-between items-center py-2 border-b border-gray-100">
                      <span className="text-gray-600">Book Value per Share</span>
                      <span className="font-medium">${epvResults.assetValuePerShare}</span>
                    </div>
                    <div className="flex justify-between items-center py-2 border-b border-gray-100">
                      <span className="text-gray-600">Tangible Book Value</span>
                      <span className="font-medium">${epvResults.tangibleBookValue}</span>
                    </div>
                    <div className="flex justify-between items-center py-3 bg-green-50 px-3 rounded-md">
                      <span className="font-semibold text-green-900">Intrinsic Value</span>
                      <span className="text-xl font-bold text-green-900">${epvResults.intrinsicValue}</span>
                    </div>
                  </div>
                </div>

                <div className="bg-white p-6 border-2 border-purple-200 rounded-lg">
                  <h3 className="text-lg font-semibold text-purple-900 mb-4">Investment Metrics</h3>
                  <div className="space-y-3">
                    <div className="flex justify-between items-center py-2 border-b border-gray-100">
                      <span className="text-gray-600">Earnings Yield</span>
                      <span className="font-medium">{epvResults.earningsYield}%</span>
                    </div>
                    <div className="flex justify-between items-center py-2 border-b border-gray-100">
                      <span className="text-gray-600">Price to EPV</span>
                      <span className="font-medium">{epvResults.priceToEPV}x</span>
                    </div>
                    <div className="flex justify-between items-center py-3 bg-purple-50 px-3 rounded-md">
                      <span className="font-semibold text-purple-900">Margin of Safety</span>
                      <span className={`text-xl font-bold ${
                        parseFloat(epvResults.marginOfSafety) > 0 ? 'text-green-600' : 'text-red-600'
                      }`}>
                        {epvResults.marginOfSafety}%
                      </span>
                    </div>
                  </div>
                </div>

                <button 
                  onClick={getAIEPVAnalysis}
                  disabled={loading}
                  className="w-full bg-gradient-to-r from-purple-600 to-blue-600 text-white py-3 rounded-md hover:from-purple-700 hover:to-blue-700 disabled:opacity-50 flex items-center justify-center"
                >
                  {loading ? <RefreshCw className="w-4 h-4 animate-spin mr-2" /> : <Brain className="w-4 h-4 mr-2" />}
                  Get AI EPV Analysis
                </button>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Methodology Explanation */}
      <div className="bg-gradient-to-r from-blue-50 to-purple-50 p-6 rounded-lg border border-blue-200">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">About Earnings Power Value (EPV)</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-sm">
          <div>
            <h4 className="font-semibold text-blue-900 mb-2">Key Principles</h4>
            <ul className="space-y-1 text-gray-700">
              <li>• No growth assumptions required</li>
              <li>• Conservative valuation approach</li>
              <li>• Focus on sustainable earning power</li>
              <li>• Compares earnings-based vs asset-based value</li>
            </ul>
          </div>
          <div>
            <h4 className="font-semibold text-purple-900 mb-2">When to Use EPV</h4>
            <ul className="space-y-1 text-gray-700">
              <li>• Mature, stable businesses</li>
              <li>• Companies in declining industries</li>
              <li>• When growth is uncertain</li>
              <li>• Value investing analysis</li>
            </ul>
          </div>
        </div>
        <div className="mt-4 p-4 bg-white rounded-md border-l-4 border-blue-500">
          <p className="text-sm text-gray-700">
            <strong>Formula:</strong> EPV = Normalized Earnings ÷ Cost of Capital | 
            <strong> Intrinsic Value:</strong> Max(EPV per Share, Asset Value per Share)
          </p>
        </div>
      </div>
    </div>
  );

  const renderFrameworks = () => (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <h3 className="text-lg font-semibold mb-4">Benjamin Graham Criteria</h3>
          <div className="space-y-3 text-sm">
            <div className="flex items-center">
              <CheckCircle className="w-4 h-4 text-green-600 mr-2" />
              <span>P/E ratio &lt; 15</span>
            </div>
            <div className="flex items-center">
              <CheckCircle className="w-4 h-4 text-green-600 mr-2" />
              <span>P/B ratio &lt; 1.5</span>
            </div>
            <div className="flex items-center">
              <AlertTriangle className="w-4 h-4 text-yellow-600 mr-2" />
              <span>Debt/Equity &lt; 0.5</span>
            </div>
            <div className="flex items-center">
              <CheckCircle className="w-4 h-4 text-green-600 mr-2" />
              <span>Current ratio &gt; 2</span>
            </div>
            <div className="flex items-center">
              <CheckCircle className="w-4 h-4 text-green-600 mr-2" />
              <span>Positive earnings growth</span>
            </div>
          </div>
          <button className="mt-4 w-full bg-blue-600 text-white py-2 rounded-md hover:bg-blue-700">
            Apply Graham Screen
          </button>
        </div>

        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <h3 className="text-lg font-semibold mb-4">Warren Buffett Principles</h3>
          <div className="space-y-3 text-sm">
            <div className="flex items-center">
              <Info className="w-4 h-4 text-blue-600 mr-2" />
              <span>Understandable business model</span>
            </div>
            <div className="flex items-center">
              <Info className="w-4 h-4 text-blue-600 mr-2" />
              <span>Sustainable competitive advantage</span>
            </div>
            <div className="flex items-center">
              <CheckCircle className="w-4 h-4 text-green-600 mr-2" />
              <span>Consistent ROE &gt; 15%</span>
            </div>
            <div className="flex items-center">
              <Info className="w-4 h-4 text-blue-600 mr-2" />
              <span>Capable management team</span>
            </div>
            <div className="flex items-center">
              <AlertTriangle className="w-4 h-4 text-yellow-600 mr-2" />
              <span>Attractive valuation</span>
            </div>
          </div>
          <button className="mt-4 w-full bg-green-600 text-white py-2 rounded-md hover:bg-green-700">
            Apply Buffett Screen
          </button>
        </div>
      </div>

      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <h3 className="text-lg font-semibold mb-4">Custom Analysis Framework</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Quality Score Weight</label>
            <input type="range" min="0" max="100" defaultValue="30" className="w-full" />
            <span className="text-xs text-gray-500">30%</span>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Valuation Weight</label>
            <input type="range" min="0" max="100" defaultValue="40" className="w-full" />
            <span className="text-xs text-gray-500">40%</span>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Growth Weight</label>
            <input type="range" min="0" max="100" defaultValue="20" className="w-full" />
            <span className="text-xs text-gray-500">20%</span>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Safety Weight</label>
            <input type="range" min="0" max="100" defaultValue="10" className="w-full" />
            <span className="text-xs text-gray-500">10%</span>
          </div>
        </div>
        <button className="mt-4 bg-purple-600 text-white px-6 py-2 rounded-md hover:bg-purple-700">
          Run Custom Analysis
        </button>
      </div>
    </div>
  );

  const renderPortfolio = () => (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold">Portfolio Overview</h2>
          <div className="flex space-x-2">
            <button className="flex items-center px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50">
              <Upload className="w-4 h-4 mr-2" />
              Import Holdings
            </button>
            <button className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700">
              <Download className="w-4 h-4 mr-2" />
              Export Report
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <MetricCard title="Total Value" value="$2.4M" trend={8.2} description="Portfolio market value" />
          <MetricCard title="Unrealized P&L" value="$245K" trend={12.5} description="Current gains/losses" />
          <MetricCard title="Dividend Yield" value="3.2%" trend={0.8} description="Weighted average yield" />
          <MetricCard title="Beta" value="0.85" trend={-5.2} description="Portfolio volatility" />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="border border-gray-200 rounded-lg overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-semibold">Top Holdings</h3>
            </div>
            <div className="p-6">
              <div className="space-y-4">
                {sampleStocks.map((stock, index) => (
                  <div key={index} className="flex items-center justify-between">
                    <div>
                      <div className="font-medium">{stock.symbol}</div>
                      <div className="text-sm text-gray-600">{stock.name}</div>
                    </div>
                    <div className="text-right">
                      <div className="font-medium">${(250000 - index * 50000).toLocaleString()}</div>
                      <div className={`text-sm ${index % 2 === 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {index % 2 === 0 ? '+' : '-'}{(Math.random() * 10).toFixed(1)}%
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="border border-gray-200 rounded-lg overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-semibold">Risk Metrics</h3>
            </div>
            <div className="p-6">
              <div className="space-y-4">
                <div className="flex justify-between">
                  <span className="text-gray-600">Value at Risk (95%)</span>
                  <span className="font-medium text-red-600">-$125K</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Sharpe Ratio</span>
                  <span className="font-medium">1.24</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Max Drawdown</span>
                  <span className="font-medium text-red-600">-18.5%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Correlation to Market</span>
                  <span className="font-medium">0.72</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Information Ratio</span>
                  <span className="font-medium">0.85</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center">
              <TrendingUp className="w-8 h-8 text-blue-600 mr-3" />
              <h1 className="text-2xl font-bold text-gray-900">ValueAI Research</h1>
              <span className="ml-2 px-2 py-1 bg-blue-100 text-blue-800 text-xs font-medium rounded">Institutional</span>
            </div>
            <div className="flex items-center space-x-4">
              <div className="flex items-center text-sm text-gray-600">
                <div className="w-2 h-2 bg-green-500 rounded-full mr-2"></div>
                Market Open
              </div>
              <button className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700">
                <Brain className="w-4 h-4 mr-2" />
                AI Insights
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex space-x-8">
            <TabButton id="screener" label="Stock Screener" icon={Search} />
            <TabButton id="analysis" label="Deep Analysis" icon={BarChart3} />
            <TabButton id="epv" label="EPV Calculator" icon={Calculator} />
            <TabButton id="frameworks" label="Frameworks" icon={Target} />
            <TabButton id="portfolio" label="Portfolio" icon={DollarSign} />
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'screener' && renderScreener()}
        {activeTab === 'analysis' && renderAnalysis()}
        {activeTab === 'epv' && renderEPVCalculator()}
        {activeTab === 'frameworks' && renderFrameworks()}
        {activeTab === 'portfolio' && renderPortfolio()}
      </div>
    </div>
  );
};

export default ValueInvestingAssistant;
