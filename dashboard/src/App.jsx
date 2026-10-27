import React, { useState, useEffect } from 'react';
import { categories } from './data';
import { Menu, X, Wifi } from 'lucide-react';

export default function App() {
  const [activeScenario, setActiveScenario] = useState(categories[0].scenarios[0]);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [csvData, setCsvData] = useState([]);

  useEffect(() => {
    fetch(`${import.meta.env.BASE_URL}csv/wifi7_summary_table.csv`)
      .then(res => res.text())
      .then(text => {
        // Split by line and then by comma
        const rows = text.split('\n').filter(r => r.trim());
        const parsed = rows.slice(1).map(r => r.split(','));
        setCsvData(parsed);
      })
      .catch(err => console.error("Could not load CSV data", err));
  }, []);

  return (
    <div className="min-h-screen flex flex-col font-sans selection:bg-blue-200">
      {/* Navbar */}
      <header className="bg-slate-900 text-white p-4 shadow-md sticky top-0 z-20">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <Wifi className="w-6 h-6 text-blue-400" />
            <h1 className="text-xl font-bold tracking-tight">Wi-Fi 7 DSR Field Study</h1>
          </div>
          <button 
            className="md:hidden p-2 bg-slate-800 rounded hover:bg-slate-700 transition"
            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
            aria-label="Toggle Navigation"
          >
            {isSidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </header>

      <div className="flex flex-1 max-w-7xl w-full mx-auto relative">
        {/* Sidebar Navigation */}
        <aside className={`
          absolute md:static top-0 left-0 h-full w-72 bg-white border-r border-gray-200 overflow-y-auto 
          transition-transform duration-300 z-10 md:transform-none shadow-xl md:shadow-none
          ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full'}
        `}>
          <div className="p-5">
            <h2 className="text-xs uppercase font-bold text-gray-400 tracking-wider mb-4">Environment Factors</h2>
            <nav className="space-y-6">
              {categories.map((category) => (
                <div key={category.name}>
                  <h3 className="text-sm font-semibold text-gray-800 mb-2">{category.name}</h3>
                  <ul className="space-y-1 pl-2 border-l-2 border-slate-100">
                    {category.scenarios.map((scenario) => {
                      const isActive = activeScenario.id === scenario.id;
                      return (
                        <li key={scenario.id}>
                          <button
                            onClick={() => {
                              setActiveScenario(scenario);
                              setIsSidebarOpen(false);
                            }}
                            className={`w-full text-left px-3 py-2 rounded-md text-sm transition-colors duration-200
                              ${isActive 
                                ? 'bg-blue-50 text-blue-700 font-medium border-l-2 border-blue-600 -ml-[2px]' 
                                : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                              }
                            `}
                            aria-pressed={isActive}
                          >
                            {scenario.title}
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                </div>
              ))}
            </nav>
          </div>
        </aside>

        {isSidebarOpen && (
          <div className="fixed inset-0 bg-black/20 z-0 md:hidden" onClick={() => setIsSidebarOpen(false)}></div>
        )}

        {/* Main Content Dashboard */}
        <main className="flex-1 p-6 md:p-10 bg-gray-50 overflow-y-auto">
          <div className="max-w-5xl mx-auto space-y-6">
            
            {/* Overview / Introduction Page */}
            {activeScenario.id === 0 && (
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 md:p-8">
                <h1 className="text-2xl font-extrabold text-slate-900 mb-4">Project Overview</h1>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                   <div>
                     <p className="text-gray-400 text-xs font-bold uppercase tracking-wider mb-1">Project</p>
                     <p className="text-slate-800 font-medium">Quantifying (Measuring) the Performance Degradation of Wi-Fi 7</p>
                   </div>
                   <div>
                     <p className="text-gray-400 text-xs font-bold uppercase tracking-wider mb-1">Client</p>
                     <p className="text-slate-800 font-medium">Nurul I. Sarkar</p>
                   </div>
                   <div>
                     <p className="text-gray-400 text-xs font-bold uppercase tracking-wider mb-1">Supervisor</p>
                     <p className="text-slate-800 font-medium">Gavin Zhao</p>
                   </div>
                   <div>
                     <p className="text-gray-400 text-xs font-bold uppercase tracking-wider mb-1">Team Members</p>
                     <p className="text-slate-800 font-medium">Phoebe Cruz, Elin Pitaloka, Spencer Ridley, Liron Rosin</p>
                   </div>
                </div>
                <div className="prose text-gray-600 leading-relaxed border-t border-gray-100 pt-5">
                  <p>
                    This project presents an empirical field study quantifying the performance degradation of IEEE 802.11be (Wi-Fi 7) networks across 17 distinct complex indoor and near-indoor environments. Throughput, Received Signal Strength (RSS), and ambient noise were measured across 2.4 GHz, 5 GHz, 6 GHz, and Multi-Link Operation (MLO) configurations.
                  </p>
                  <p className="mt-4">
                    The results highlight the extreme resilience of the 6 GHz band against electromagnetic interference (EMI) and its susceptibility to structural attenuation. Crucially, empirical testing of current consumer Wi-Fi 7 hardware reveals that MLO fallback mechanisms are currently unconvincing and sub-optimal in high-noise and heavy-obstruction environments, failing to achieve true multi-link aggregation.
                  </p>
                </div>
              </div>
            )}

            {/* Header Content */}
            <div className="border-b border-gray-200 pb-4">
              {activeScenario.id !== 0 && (
                <span className="inline-block px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-xs font-semibold uppercase tracking-wide mb-3">
                  Scenario {activeScenario.id}
                </span>
              )}
              <h2 className="text-3xl font-extrabold text-slate-900">{activeScenario.title}</h2>
            </div>
            
            {/* Graph Card */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 transition-all duration-300 hover:shadow-md">
              <img 
                src={encodeURI(`${import.meta.env.BASE_URL}images/${activeScenario.image}`)}
                alt={`Data graph for ${activeScenario.title}`}
                className="w-full h-auto object-contain rounded-lg"
                onError={(e) => {
                  e.target.src = 'https://via.placeholder.com/800x400?text=Image+Not+Found';
                  e.target.alt = 'Placeholder image due to missing file';
                }}
              />
            </div>

            {/* Analysis Card */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 md:p-8">
              <h3 className="text-lg font-semibold text-slate-900 mb-3 flex items-center">
                <span className="bg-blue-600 w-1 h-5 rounded-full mr-3"></span>
                Empirical Findings
              </h3>
              <p className="text-gray-600 leading-relaxed text-base">
                {activeScenario.analysis}
              </p>
            </div>

            {/* Data Table */}
            {activeScenario.csvId && csvData.filter(row => row[0] === activeScenario.csvId).length > 0 && (
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden mt-6">
                <div className="overflow-x-auto">
                  <table className="min-w-full text-xs text-left text-gray-600 whitespace-nowrap">
                    <thead className="bg-slate-100 border-b border-gray-200 uppercase font-semibold text-slate-700">
                      <tr>
                        <th rowSpan="2" className="px-4 py-3 border-r border-gray-200 align-middle">Band</th>
                        <th rowSpan="2" className="px-4 py-3 border-r border-gray-200 align-middle">Condition</th>
                        <th colSpan="7" className="px-4 py-2 border-r border-b border-gray-200 text-center tracking-wide">Throughput (Mbps)</th>
                        <th colSpan="7" className="px-4 py-2 border-b border-gray-200 text-center tracking-wide">RSSI (dBm)</th>
                      </tr>
                      <tr className="bg-slate-50">
                        <th className="px-3 py-2 border-r border-gray-200">Min</th>
                        <th className="px-3 py-2 border-r border-gray-200">Q1</th>
                        <th className="px-3 py-2 border-r border-gray-200">Avg</th>
                        <th className="px-3 py-2 border-r border-gray-200">Med</th>
                        <th className="px-3 py-2 border-r border-gray-200">Q3</th>
                        <th className="px-3 py-2 border-r border-gray-200">Max</th>
                        <th className="px-3 py-2 border-r border-gray-200 text-blue-800">Deg</th>
                        <th className="px-3 py-2 border-r border-gray-200">Min</th>
                        <th className="px-3 py-2 border-r border-gray-200">Q1</th>
                        <th className="px-3 py-2 border-r border-gray-200">Avg</th>
                        <th className="px-3 py-2 border-r border-gray-200">Med</th>
                        <th className="px-3 py-2 border-r border-gray-200">Q3</th>
                        <th className="px-3 py-2 border-r border-gray-200">Max</th>
                        <th className="px-3 py-2 text-blue-800">Deg</th>
                      </tr>
                    </thead>
                    <tbody>
                      {csvData.filter(row => row[0] === activeScenario.csvId).map((row, idx) => (
                        <React.Fragment key={idx}>
                          {/* LOS Row */}
                          <tr className="border-t border-b border-gray-100 hover:bg-slate-50">
                            <td rowSpan="2" className="px-4 py-3 border-r border-gray-200 font-bold text-slate-800 bg-white align-middle">{row[1]}</td>
                            <td className="px-4 py-2 border-r border-gray-200 bg-slate-50 font-medium">LOS</td>
                            <td className="px-3 py-2">{row[2]}</td><td className="px-3 py-2">{row[3]}</td><td className="px-3 py-2">{row[4]}</td><td className="px-3 py-2">{row[5]}</td><td className="px-3 py-2">{row[6]}</td><td className="px-3 py-2 border-r border-gray-200">{row[7]}</td><td className="px-3 py-2 border-r border-gray-200 bg-slate-50 text-gray-400 text-center">-</td>
                            <td className="px-3 py-2">{row[8]}</td><td className="px-3 py-2">{row[9]}</td><td className="px-3 py-2">{row[10]}</td><td className="px-3 py-2">{row[11]}</td><td className="px-3 py-2">{row[12]}</td><td className="px-3 py-2 border-r border-gray-200">{row[13]}</td><td className="px-3 py-2 bg-slate-50 text-gray-400 text-center">-</td>
                          </tr>
                          {/* Real Row */}
                          <tr className="border-b border-gray-300 bg-white hover:bg-slate-50">
                            <td className="px-4 py-2 border-r border-gray-200 bg-slate-50 font-medium text-blue-700">Real</td>
                            <td className="px-3 py-2">{row[14]}</td><td className="px-3 py-2">{row[15]}</td><td className="px-3 py-2">{row[16]}</td><td className="px-3 py-2">{row[17]}</td><td className="px-3 py-2">{row[18]}</td><td className="px-3 py-2 border-r border-gray-200">{row[19]}</td><td className="px-3 py-2 border-r border-gray-200 bg-blue-50 font-bold text-blue-900">{row[20]}</td>
                            <td className="px-3 py-2">{row[21]}</td><td className="px-3 py-2">{row[22]}</td><td className="px-3 py-2">{row[23]}</td><td className="px-3 py-2">{row[24]}</td><td className="px-3 py-2">{row[25]}</td><td className="px-3 py-2 border-r border-gray-200">{row[26]}</td><td className="px-3 py-2 bg-blue-50 font-bold text-blue-900">{row[27]}</td>
                          </tr>
                        </React.Fragment>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Location Images */}
            {activeScenario.locationImages && activeScenario.locationImages.length > 0 && (
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 md:p-8 mt-6">
                <h3 className="text-lg font-semibold text-slate-900 mb-4 flex items-center">
                  <span className="bg-slate-400 w-1 h-5 rounded-full mr-3"></span>
                  Test Location
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {activeScenario.locationImages.map((img, idx) => (
                    <img 
                      key={idx}
                      src={encodeURI(`${import.meta.env.BASE_URL}images/${img}`)}
                      alt={`Location test site ${idx + 1}`}
                      className="w-full h-48 md:h-64 object-cover rounded-lg border border-gray-200 shadow-sm"
                      onError={(e) => {
                        e.target.style.display = 'none';
                      }}
                    />
                  ))}
                </div>
              </div>
            )}

          </div>
        </main>
      </div>
    </div>
  );
}