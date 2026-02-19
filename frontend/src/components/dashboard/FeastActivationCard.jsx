import React, { useState, useEffect } from 'react';
import feastModeService from '../../api/feastModeService';
import { format, differenceInDays, parseISO } from 'date-fns';
import FeastProposalCard from '../common/FeastProposalCard';
import ConfirmModal from '../common/ConfirmModal';

const FeastActivationCard = ({ onStatusChange }) => {
  const [status, setStatus] = useState(null); // { is_active, config, effective_targets }
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  // Proposal State
  const [eventName, setEventName] = useState('');
  const [eventDate, setEventDate] = useState('');
  const [proposal, setProposal] = useState(null);

  const [showForm, setShowForm] = useState(false);

  // Modal State
  const [showCancelModal, setShowCancelModal] = useState(false);
  const [cancelModalMessage, setCancelModalMessage] = useState('');
  const [isProcessingCancel, setIsProcessingCancel] = useState(false);

  useEffect(() => {
    fetchStatus();
  }, []);

  const fetchStatus = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await feastModeService.getStatus();
      if (data) {
        const formatted = {
            is_active: true,
            config: data,
            effective_targets: { calories: data.effective_calories }
        };
        setStatus(formatted);
        if (onStatusChange) onStatusChange(formatted);
        // If active, ensure form is "open" (or just show active state logic which overrides form)
        setShowForm(true); 
      } else {
        const inactive = { is_active: false };
        setStatus(inactive);
        if (onStatusChange) onStatusChange(inactive);
        setShowForm(false); // Default to closed if inactive
      }
      
      // Reset proposal if active
      if (data && data.is_active) {
          setProposal(null);
          setEventName('');
          setEventDate('');
      }
    } catch (err) {
      console.error(err);
      setError('Failed to load status');
    } finally {
      setLoading(false);
    }
  };

  const handlePropose = async () => {
    if (!eventName || !eventDate) {
      setError('Please enter event name and date');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const result = await feastModeService.proposeStrategy(eventName, eventDate);
      setProposal(result);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to propose strategy');
    } finally {
      setLoading(false);
    }
  };

  const handleActivate = async () => {
    if (!proposal) return;
    setLoading(true);
    setError('');

    try {
      // 1. Pre-Check Mid-Day Activation
      const todayStr = new Date().toISOString().split('T')[0];
      if (proposal.start_date === todayStr) {
          try {
             const checkResult = await feastModeService.preActivateCheck({
                 start_date: todayStr,
                 daily_deduction: proposal.daily_deduction
             });
             
             if (checkResult && checkResult.warning) {
                 // Use window.confirm for MVP (or custom modal if implemented later)
                 const confirmed = window.confirm(
                     `⚠️ Warning: Low Calorie Budget\n\n` + 
                     `${checkResult.message}\n\n` + 
                     `Do you want to proceed with activation?`
                 );
                 if (!confirmed) {
                     setLoading(false);
                     return;
                 }
             }
          } catch (checkErr) {
              console.warn("Pre-check failed, proceeding anyway", checkErr);
          }
      }

      await feastModeService.activate(proposal);
      await fetchStatus(); // Refresh to show active state
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to activate');
      setLoading(false);
    }
  };

  const initiateCancel = async () => {
    setError('');
    // Don't set main loading, just maybe local processing if needed?
    // Actually we need to fetch preview, so showing loading is good?
    // But button should show loading.
    setLoading(true);
    
    try {
        // 1. Get Preview
        const preview = await feastModeService.deactivatePreview();
        
        // 2. Format Confirmation Message
        const msg = `Cancel Feast Mode for "${preview.event_name}"?\n\n` +
                    `• Target Restored: ${Math.round(preview.restored_daily_calories)} kcal (was ${Math.round(preview.current_daily_calories)})\n` + 
                    `• Banked Calories Lost: ${preview.banked_calories_lost} kcal\n` + 
                    `• Workout: ${preview.workout_status}\n\n` + 
                    `This action cannot be undone.`;
        
        setCancelModalMessage(msg);
        setShowCancelModal(true);

    } catch (err) {
        console.error(err);
        // Fallback if preview fails
        const msg = 'Could not load preview. Cancel Feast Mode anyway?\n\nAll banked progress will be lost.';
        setCancelModalMessage(msg);
        setShowCancelModal(true);
    } finally {
        setLoading(false);
    }
  };

  const confirmCancelAction = async () => {
      setIsProcessingCancel(true);
      try {
         await feastModeService.cancel();
         
         const inactive = { is_active: false };
         setStatus(inactive);
         if (onStatusChange) onStatusChange(inactive);
         setShowForm(false);
         await fetchStatus();
         setShowCancelModal(false);
      } catch (cancelErr) {
          setError(cancelErr.response?.data?.detail || 'Failed to cancel');
          // Don't close modal if error? or close and show error?
          // Close for now
          setShowCancelModal(false); // Or keep open and show error in toast?
      } finally {
          setIsProcessingCancel(false);
      }
  };

  if (error && !status) return (
    <div className="p-4 bg-red-50 text-red-600 rounded-xl border border-red-100 shadow-sm flex items-center justify-between">
      <div>
          <p className="font-semibold text-sm">Feast Mode Unavailable</p>
          <p className="text-xs opacity-80">{error}</p>
      </div>
      <button 
        onClick={fetchStatus}
        className="text-xs font-bold uppercase tracking-wide px-3 py-1 bg-white border border-red-200 text-red-700 rounded-lg hover:bg-red-50 transition-colors"
      >
        Retry
      </button>
    </div>
  );

  if (!status) return <div className="p-4 bg-white rounded-xl shadow-sm animate-pulse">Loading...</div>;

  // COMPACT INACTIVE STATE
  if (!status.is_active && !showForm) {
      return (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4 flex items-center justify-between hover:shadow-md transition-shadow">
            <div className="flex items-center gap-3">
                <div className="p-2 bg-purple-100 text-purple-600 rounded-lg">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" /></svg>
                </div>
                <div>
                    <h3 className="font-semibold text-gray-900 text-sm">Feast Mode</h3>
                    <p className="text-xs text-gray-500 hidden sm:block">Planning a cheat meal? Bank calories ahead of time.</p>
                </div>
            </div>
            <button 
                onClick={() => setShowForm(true)}
                className="px-4 py-2 bg-purple-50 text-purple-700 text-sm font-semibold rounded-lg hover:bg-purple-100 transition-colors"
            >
                Start Planning
            </button>
        </div>
      );
  }

  // EXPANDED / ACTIVE STATE
  return (
    <>
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden animate-in slide-in-from-top-2">
        <div className="p-5 border-b border-gray-50 bg-linear-to-r from-purple-50 to-white">
            <div className="flex justify-between items-center">
            <h2 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
                🎉 Feast Mode
            </h2>
            {status.is_active ? (
                <span className="px-3 py-1 bg-purple-100 text-purple-700 text-xs font-bold uppercase tracking-wide rounded-full">
                Active
                </span>
            ) : (
                <button 
                    onClick={() => setShowForm(false)}
                    className="p-1 text-gray-400 hover:text-gray-600 rounded-full hover:bg-gray-100 transition-colors"
                >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
                </button>
            )}
            </div>
        </div>

        <div className="p-5">
            {error && (
            <div className="mb-4 p-3 bg-red-50 text-red-600 text-sm rounded-lg border border-red-100">
                {typeof error === 'object' ? JSON.stringify(error) : error}
            </div>
            )}

            {/* ACTIVE STATE */}
            {status.is_active && status.config && (
            <div className="space-y-4">
                <div className="flex items-start justify-between">
                <div>
                    <h3 className="font-semibold text-xl text-gray-900">{status.config.event_name}</h3>
                    <p className="text-gray-500 text-sm">
                        {format(parseISO(status.config.event_date), 'MMMM d, yyyy')} 
                        <span className="mx-2">•</span>
                        {differenceInDays(parseISO(status.config.event_date), new Date())} days away
                    </p>
                </div>
                <div className="text-right">
                    <div className="text-2xl font-bold text-purple-600">{status.config.target_bank_calories}</div>
                    <div className="text-xs text-gray-400 uppercase tracking-wide">Target Bank</div>
                </div>
                </div>

                <div className="p-4 bg-purple-50 rounded-lg border border-purple-100 flex justify-between items-center">
                    <div>
                        <span className="block text-xs font-semibold text-purple-800 uppercase">Daily Strategy</span>
                        <span className="text-sm text-purple-700">-{status.config.daily_deduction} kcal / day</span>
                    </div>
                    <div className="h-8 w-px bg-purple-200 mx-4"></div>
                    <div>
                        <span className="block text-xs font-semibold text-purple-800 uppercase">Current Bank</span>
                        <span className="text-sm font-bold text-purple-700">In Progress</span>
                    </div>
                </div>

                <button 
                onClick={initiateCancel}
                disabled={loading}
                className="w-full py-2.5 text-red-600 font-medium hover:bg-red-50 rounded-lg transition-colors border border-transparent hover:border-red-100 text-sm"
                >
                {loading ? 'Loading...' : 'Cancel Feast Mode'}
                </button>
            </div>
            )}

            {/* DETAILS FORM (When Expanded and Inactive) */}
            {!status.is_active && !proposal && (
            <div className="space-y-4">
                <p className="text-gray-600 text-sm">Planning a big meal or event? Bank calories ahead of time to indulge guilt-free.</p>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                        <label className="block text-xs font-medium text-gray-500 mb-1">Event Name</label>
                        <input 
                            type="text" 
                            value={eventName}
                            onChange={(e) => setEventName(e.target.value)}
                            placeholder="e.g. Wedding, Birthday"
                            className="w-full p-2.5 bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent outline-none text-sm transition-all"
                        />
                    </div>
                    <div>
                        <label className="block text-xs font-medium text-gray-500 mb-1">Date</label>
                        <input 
                            type="date"
                            value={eventDate}
                            onChange={(e) => setEventDate(e.target.value)}
                            min={new Date().toISOString().split('T')[0]} // Min today
                            className="w-full p-2.5 bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent outline-none text-sm transition-all"
                        />
                    </div>
                </div>

                <button 
                onClick={handlePropose} 
                disabled={loading || !eventName || !eventDate}
                className="w-full py-3 bg-purple-600 hover:bg-purple-700 text-white font-semibold rounded-lg shadow-md hover:shadow-lg transition-all transform hover:-translate-y-0.5 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                {loading ? 'Calculating...' : 'Create Plan'}
                </button>
            </div>
            )}

            {/* PROPOSAL STATE */}
            {!status.is_active && proposal && (
            <FeastProposalCard 
                proposal={proposal} 
                onConfirm={handleActivate} 
                onCancel={() => setProposal(null)} 
                loading={loading} 
            />
            )}
        </div>
        </div>

        <ConfirmModal 
            isOpen={showCancelModal}
            onClose={() => !isProcessingCancel && setShowCancelModal(false)}
            onConfirm={confirmCancelAction}
            title="Cancel Feast Mode?"
            message={cancelModalMessage}
            confirmText="Yes, Cancel"
            cancelText="Keep Feast Mode"
            isDangerous={true}
            isLoading={isProcessingCancel}
        />
    </>
  );
};

export default FeastActivationCard;
