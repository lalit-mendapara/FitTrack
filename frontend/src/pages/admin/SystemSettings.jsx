import React, { useState, useEffect, useCallback } from 'react';
import AdminLayout from '../../components/admin/AdminLayout';
import { adminAuth } from '../../utils/adminAuth';
import { Robot, Heart, Gear, ArrowsClockwise, PlugsConnected, Info, Check, X, Clock } from '@phosphor-icons/react';

const API = 'http://localhost:8000/api/admin/settings';

const badgeClass = (status) => {
  const map = {
    ok: 'bg-green-100 text-green-800',
    error: 'bg-red-100 text-red-800',
    running: 'bg-green-100 text-green-800',
    no_workers: 'bg-yellow-100 text-yellow-800',
    healthy: 'bg-green-100 text-green-800',
    degraded: 'bg-yellow-100 text-yellow-800',
    unhealthy: 'bg-red-100 text-red-800',
    online: 'bg-green-100 text-green-800',
  };
  return `inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${map[status] || 'bg-gray-100 text-gray-700'}`;
};

const StatusDot = ({ status }) => {
  const color = status === 'ok' || status === 'online' ? 'bg-green-500' : status === 'error' ? 'bg-red-500' : 'bg-yellow-500';
  return <span className={`inline-block w-2.5 h-2.5 rounded-full ${color} mr-2 shrink-0`} />;
};

const TAB_ICONS = {
  llm:       <Robot size={18} weight="duotone" />,
  health:    <Heart size={18} weight="duotone" />,
  celery:    <Gear size={18} weight="duotone" />,
  scheduler: <Clock size={18} weight="duotone" />,
};

const TABS = [
  { id: 'llm',       label: 'LLM Configuration' },
  { id: 'scheduler', label: 'Scheduler' },
  { id: 'health',    label: 'System Health' },
  { id: 'celery',    label: 'Celery Tasks' },
];

const LLM_PROVIDER_OPTIONS = [
  { value: 'ollama',      label: 'Ollama (Local)' },
  { value: 'openrouter',  label: 'OpenRouter' },
  { value: 'openai',      label: 'OpenAI' },
];

const SystemSettings = () => {
  const [activeTab, setActiveTab]     = useState('llm');
  const [settings, setSettings]       = useState({});
  const [editValues, setEditValues]   = useState({});
  const [saving, setSaving]           = useState({});
  const [saveMsg, setSaveMsg]         = useState({});
  const [loadingSettings, setLoadingSettings] = useState(true);

  const [health, setHealth]           = useState(null);
  const [healthLoading, setHealthLoading] = useState(false);

  const [celery, setCelery]           = useState(null);
  const [celeryLoading, setCeleryLoading] = useState(false);

  const [llmTest, setLlmTest]         = useState(null);
  const [llmTesting, setLlmTesting]   = useState(false);

  const headers = adminAuth.getAuthHeader();

  // ── fetch all settings ────────────────────────────────────────────────────
  const fetchSettings = useCallback(async () => {
    setLoadingSettings(true);
    try {
      const res = await fetch(API, { headers });
      if (res.ok) {
        const data = await res.json();
        setSettings(data);
        const vals = {};
        Object.values(data).flat().forEach((s) => {
          vals[s.key] = s.is_sensitive ? '' : (s.value || '');
        });
        setEditValues(vals);
      }
    } catch (e) {
      console.error('Failed to load settings', e);
    } finally {
      setLoadingSettings(false);
    }
  }, []);

  useEffect(() => { fetchSettings(); }, [fetchSettings]);

  // ── fetch health ─────────────────────────────────────────────────────────
  const fetchHealth = useCallback(async () => {
    setHealthLoading(true);
    try {
      const res = await fetch(`${API}/health`, { headers });
      if (res.ok) setHealth(await res.json());
    } catch (e) {
      console.error('Health check failed', e);
    } finally {
      setHealthLoading(false);
    }
  }, []);

  // ── fetch celery status ───────────────────────────────────────────────────
  const fetchCelery = useCallback(async () => {
    setCeleryLoading(true);
    try {
      const res = await fetch(`${API}/celery-status`, { headers });
      if (res.ok) setCelery(await res.json());
    } catch (e) {
      console.error('Celery check failed', e);
    } finally {
      setCeleryLoading(false);
    }
  }, []);

  useEffect(() => {
    if (activeTab === 'health' && !health) fetchHealth();
    if (activeTab === 'celery' && !celery) fetchCelery();
  }, [activeTab]);

  // ── save single setting ───────────────────────────────────────────────────
  const saveSetting = async (key, isSensitive) => {
    if (isSensitive && !editValues[key]) return; // nothing typed — keep existing
    setSaving((p) => ({ ...p, [key]: true }));
    setSaveMsg((p) => ({ ...p, [key]: null }));
    try {
      const res = await fetch(`${API}/${key}`, {
        method: 'PUT',
        headers: { ...headers, 'Content-Type': 'application/json' },
        body: JSON.stringify({ value: editValues[key] }),
      });
      if (res.ok && isSensitive) {
        setEditValues((p) => ({ ...p, [key]: '' }));
      }
      setSaveMsg((p) => ({ ...p, [key]: res.ok ? 'saved' : 'error' }));
      setTimeout(() => setSaveMsg((p) => ({ ...p, [key]: null })), 2500);
    } catch {
      setSaveMsg((p) => ({ ...p, [key]: 'error' }));
    } finally {
      setSaving((p) => ({ ...p, [key]: false }));
    }
  };

  // ── test LLM ──────────────────────────────────────────────────────────────
  const testLLM = async () => {
    setLlmTesting(true);
    setLlmTest(null);
    try {
      const res = await fetch(`${API}/test-llm`, { method: 'POST', headers });
      if (res.ok) setLlmTest(await res.json());
      else setLlmTest({ status: 'error', detail: `HTTP ${res.status}` });
    } catch (e) {
      setLlmTest({ status: 'error', detail: String(e) });
    } finally {
      setLlmTesting(false);
    }
  };

  // ── render a single setting row ────────────────────────────────────────────
  const renderSettingRow = (s) => {
    const isProvider = s.key === 'llm_provider';
    const isScheduleHour = s.key === 'diet_plan_schedule_hour';
    const isSensitive = s.is_sensitive;
    const currentProvider = editValues['llm_provider'] || 'ollama';
    if (s.key === 'ollama_url' && currentProvider !== 'ollama') return null;
    if (s.key === 'ollama_model' && currentProvider !== 'ollama') return null;
    if (s.key === 'llm_api_key' && currentProvider === 'ollama') return null;

    return (
      <div key={s.key} className="flex flex-col sm:flex-row sm:items-center gap-3 py-4 border-b border-gray-100 last:border-0">
        <div className="sm:w-1/3">
          <p className="text-sm font-semibold text-gray-800">{s.key}</p>
          <p className="text-xs text-gray-500 mt-0.5">{s.description}</p>
        </div>
        <div className="sm:flex-1 flex gap-2 items-center">
          {isProvider ? (
            <select
              value={editValues[s.key] || ''}
              onChange={(e) => setEditValues((p) => ({ ...p, [s.key]: e.target.value }))}
              className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
            >
              {LLM_PROVIDER_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          ) : isScheduleHour ? (
            <div className="flex-1 flex items-center gap-2">
              <input
                type="number"
                min="0"
                max="23"
                value={editValues[s.key] || ''}
                onChange={(e) => {
                  const val = parseInt(e.target.value);
                  if (e.target.value === '' || (val >= 0 && val <= 23)) {
                    setEditValues((p) => ({ ...p, [s.key]: e.target.value }));
                  }
                }}
                className="w-24 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 font-mono text-center"
              />
              <span className="text-sm text-gray-600">:00 (24-hour format)</span>
            </div>
          ) : (
            <input
              type={isSensitive ? 'password' : 'text'}
              value={editValues[s.key] || ''}
              onChange={(e) => setEditValues((p) => ({ ...p, [s.key]: e.target.value }))}
              placeholder={isSensitive ? 'Type new value to update (current value is hidden)' : ''}
              className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 font-mono"
            />
          )}
          <button
            onClick={() => saveSetting(s.key, isSensitive)}
            disabled={saving[s.key] || (isSensitive && !editValues[s.key])}
            className="px-4 py-2 bg-purple-600 text-white rounded-lg text-sm hover:bg-purple-700 disabled:opacity-50 transition-colors whitespace-nowrap"
            title={isSensitive && !editValues[s.key] ? 'Type a new value to update' : ''}
          >
            {saving[s.key] ? 'Saving…' : 'Save'}
          </button>
          {saveMsg[s.key] === 'saved' && <span className="inline-flex items-center gap-1 text-green-600 text-xs font-medium"><Check size={13} weight="bold" /> Saved</span>}
          {saveMsg[s.key] === 'error' && <span className="inline-flex items-center gap-1 text-red-600 text-xs font-medium"><X size={13} weight="bold" /> Error</span>}
        </div>
      </div>
    );
  };

  // ── LLM TAB ───────────────────────────────────────────────────────────────
  const LLMTab = () => {
    const llmSettings   = settings['llm'] || [];
    const obsSettings   = settings['observability'] || [];

    return (
      <div className="space-y-4 h-full flex flex-col">
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm text-blue-800 shrink-0">
          <strong className="inline-flex items-center gap-1"><Info size={15} weight="bold" /> How it works:</strong> Changes saved here take effect <strong>immediately</strong> for all new LLM calls — no backend restart needed.
        </div>

        <div className="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-4 overflow-auto">
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 h-fit">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-base font-semibold text-gray-900">LLM Provider</h3>
              <button
                onClick={testLLM}
                disabled={llmTesting}
                className="flex items-center gap-2 px-3 py-1.5 bg-indigo-600 text-white rounded-lg text-xs hover:bg-indigo-700 disabled:opacity-50 transition-colors"
              >
                {llmTesting ? <><ArrowsClockwise size={14} className="animate-spin" /> Testing…</> : <><PlugsConnected size={14} weight="duotone" /> Test</>}
              </button>
            </div>

            {llmTest && (
              <div className={`mb-3 p-2.5 rounded-lg text-xs flex items-start gap-2 ${llmTest.status === 'ok' ? 'bg-green-50 text-green-800 border border-green-200' : 'bg-red-50 text-red-800 border border-red-200'}`}>
                {llmTest.status === 'ok' ? <Check size={14} weight="bold" className="mt-0.5 shrink-0" /> : <X size={14} weight="bold" className="mt-0.5 shrink-0" />}
                <span><strong>{llmTest.status === 'ok' ? 'Connected' : 'Failed'}:</strong> {llmTest.detail}</span>
              </div>
            )}

            {loadingSettings ? (
              <p className="text-gray-400 text-sm">Loading…</p>
            ) : (
              llmSettings.map(renderSettingRow)
            )}
          </div>

          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 h-fit">
            <h3 className="text-base font-semibold text-gray-900 mb-3">Observability (Langfuse)</h3>
            {loadingSettings ? (
              <p className="text-gray-400 text-sm">Loading…</p>
            ) : (
              obsSettings.map(renderSettingRow)
            )}
          </div>
        </div>
      </div>
    );
  };

  // ── HEALTH TAB ────────────────────────────────────────────────────────────
  const HealthTab = () => (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between mb-3 shrink-0">
        <h3 className="text-base font-semibold text-gray-900">Service Health</h3>
        <button
          onClick={fetchHealth}
          disabled={healthLoading}
          className="flex items-center gap-2 px-3 py-1.5 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700 disabled:opacity-50 transition-colors"
        >
          <ArrowsClockwise size={14} className={healthLoading ? 'animate-spin' : ''} />
          {healthLoading ? 'Checking…' : 'Refresh'}
        </button>
      </div>

      {healthLoading && !health && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 text-center text-gray-400">
          Checking services…
        </div>
      )}

      {health && (
        <div className="flex-1 flex flex-col overflow-auto">
          <div className="flex items-center gap-3 mb-3 shrink-0">
            <span className="text-sm font-medium text-gray-600">Overall:</span>
            <span className={badgeClass(health.overall)}>{health.overall.toUpperCase()}</span>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-4 gap-3">
            {health.checks.map((c) => (
              <div key={c.service} className="bg-white rounded-lg shadow-sm border border-gray-200 p-3">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center">
                    <StatusDot status={c.status} />
                    <span className="font-semibold text-sm text-gray-900">{c.service}</span>
                  </div>
                  <span className={badgeClass(c.status)}>{c.status}</span>
                </div>
                {c.latency_ms != null && (
                  <p className="text-xs text-gray-500 mb-1">Latency: <span className="font-mono font-medium text-gray-800">{c.latency_ms} ms</span></p>
                )}
                <p className="text-xs text-gray-500 truncate" title={c.detail}>{c.detail}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );

  // ── SCHEDULER TAB ──────────────────────────────────────────────────────────
  const SchedulerTab = () => {
    const schedulerSettings = settings['scheduler'] || [];

    return (
      <div className="h-full flex flex-col space-y-4">
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm text-blue-800 shrink-0">
          <strong className="inline-flex items-center gap-1"><Info size={15} weight="bold" /> How It Works:</strong> Set the hour (0-23) when diet plans should be generated. The system automatically generates plans for each user at this hour <strong>in their own timezone</strong>.
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 shrink-0">
          <h3 className="text-base font-semibold text-gray-900 mb-3">Daily Plan Generation Time</h3>
          {loadingSettings ? (
            <p className="text-gray-400 text-sm">Loading…</p>
          ) : schedulerSettings.length > 0 ? (
            schedulerSettings.map(renderSettingRow)
          ) : (
            <p className="text-gray-400 text-sm">No scheduler settings available</p>
          )}
        </div>

        <div className="bg-green-50 border border-green-200 rounded-lg p-3 text-sm text-green-800 shrink-0">
          <strong>✓ Automatic Timezone Handling:</strong> Each user's timezone is stored in their profile. The scheduler reads this and generates plans at the configured hour in each user's local time. You don't need to configure timezones — the system handles it automatically.
        </div>
      </div>
    );
  };

  // ── CELERY TAB ────────────────────────────────────────────────────────────
  const CeleryTab = () => (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between mb-3 shrink-0">
        <h3 className="text-base font-semibold text-gray-900">Celery Workers &amp; Beat Scheduler</h3>
        <button
          onClick={fetchCelery}
          disabled={celeryLoading}
          className="flex items-center gap-2 px-3 py-1.5 bg-orange-600 text-white rounded-lg text-sm hover:bg-orange-700 disabled:opacity-50 transition-colors"
        >
          <ArrowsClockwise size={14} className={celeryLoading ? 'animate-spin' : ''} />
          {celeryLoading ? 'Checking…' : 'Refresh'}
        </button>
      </div>

      {celeryLoading && !celery && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 text-center text-gray-400">
          Inspecting Celery…
        </div>
      )}

      {celery && (
        <div className="flex-1 flex flex-col space-y-3 overflow-auto">
          <div className="flex items-center gap-3 shrink-0">
            <span className="text-sm font-medium text-gray-600">Status:</span>
            <span className={badgeClass(celery.status.startsWith('error') ? 'error' : celery.status)}>
              {celery.status.startsWith('error') ? 'ERROR' : celery.status.replace('_', ' ').toUpperCase()}
            </span>
            <span className="text-sm text-gray-500">({celery.workers_found} worker{celery.workers_found !== 1 ? 's' : ''} found)</span>
          </div>

          {celery.workers.length > 0 && (
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden shrink-0">
              <div className="px-4 py-2 border-b border-gray-100 bg-gray-50">
                <h4 className="text-sm font-semibold text-gray-700">Active Workers</h4>
              </div>
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
                  <tr>
                    <th className="px-4 py-2 text-left">Worker</th>
                    <th className="px-4 py-2 text-left">Status</th>
                    <th className="px-4 py-2 text-right">Active Tasks</th>
                    <th className="px-4 py-2 text-right">Scheduled</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {celery.workers.map((w) => (
                    <tr key={w.worker_name} className="hover:bg-gray-50">
                      <td className="px-4 py-2 font-mono text-xs text-gray-800">{w.worker_name}</td>
                      <td className="px-4 py-2"><span className={badgeClass(w.status)}>{w.status}</span></td>
                      <td className="px-4 py-2 text-right font-semibold text-gray-800">{w.active_tasks}</td>
                      <td className="px-4 py-2 text-right font-semibold text-gray-800">{w.scheduled_tasks}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {celery.workers_found === 0 && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 text-yellow-800 text-sm shrink-0">
              <strong>No workers online.</strong> Start the Celery worker with:
              <code className="block mt-2 bg-yellow-100 rounded px-2 py-1.5 font-mono text-xs">
                docker compose up -d celery
              </code>
            </div>
          )}

          {Object.keys(celery.beat_schedule).length > 0 && (
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden shrink-0">
              <div className="px-4 py-2 border-b border-gray-100 bg-gray-50">
                <h4 className="text-sm font-semibold text-gray-700">Beat Schedule (Registered Tasks)</h4>
              </div>
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
                  <tr>
                    <th className="px-4 py-2 text-left">Name</th>
                    <th className="px-4 py-2 text-left">Task</th>
                    <th className="px-4 py-2 text-left">Schedule</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {Object.entries(celery.beat_schedule).map(([name, info]) => (
                    <tr key={name} className="hover:bg-gray-50">
                      <td className="px-4 py-2 font-medium text-sm text-gray-800">{name}</td>
                      <td className="px-4 py-2 font-mono text-xs text-gray-600">{info.task}</td>
                      <td className="px-4 py-2 font-mono text-xs text-gray-600">{info.schedule}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );

  // ── render ─────────────────────────────────────────────────────────────────
  return (
    <AdminLayout>
      <div className="flex flex-col" style={{ height: 'calc(100vh - 3rem)' }}>
        {/* Header */}
        <div className="shrink-0 mb-3">
          <h1 className="text-2xl font-bold text-gray-900">System Settings</h1>
          <p className="text-gray-500 text-sm mt-1">Manage LLM configuration, monitor service health, and inspect Celery workers.</p>
        </div>

        {/* Tab bar */}
        <div className="shrink-0 flex gap-2 border-b border-gray-200 mb-3">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                activeTab === t.id
                  ? 'border-purple-600 text-purple-600'
                  : 'border-transparent text-gray-500 hover:text-gray-800 hover:border-gray-300'
              }`}
            >
              {TAB_ICONS[t.id]}
              {t.label}
            </button>
          ))}
        </div>

        {/* Tab content - takes remaining height */}
        <div className="flex-1 overflow-auto min-h-0">
          {activeTab === 'llm'       && <LLMTab />}
          {activeTab === 'scheduler' && <SchedulerTab />}
          {activeTab === 'health'    && <HealthTab />}
          {activeTab === 'celery'    && <CeleryTab />}
        </div>
      </div>
    </AdminLayout>
  );
};

export default SystemSettings;
