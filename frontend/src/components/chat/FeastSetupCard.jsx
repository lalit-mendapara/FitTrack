import React, { useState } from 'react';
import { Calendar, PartyPopper } from 'lucide-react';

const FeastSetupCard = ({ onSubmit, onCancel }) => {
  const [eventName, setEventName] = useState('');
  const [eventDate, setEventDate] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!eventName.trim()) {
      setError("Please enter an event name");
      return;
    }
    if (!eventDate) {
      setError("Please select a date");
      return;
    }
    
    // Basic validation: Date must be in future, max 14 days
    const today = new Date();
    today.setHours(0,0,0,0);
    const selected = new Date(eventDate);
    selected.setHours(0,0,0,0);
    
    const diffTime = selected - today;
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays <= 0) {
      setError("Event must be in the future");
      return;
    }
    if (diffDays > 14) {
      setError("Event cannot be more than 14 days away");
      return;
    }

    onSubmit({ eventName, eventDate });
  };

  return (
    <div className="bg-white p-5 rounded-xl border border-indigo-100 shadow-sm animate-in fade-in slide-in-from-bottom-2 space-y-4 max-w-sm w-full">
      <div className="flex items-center gap-3 border-b border-indigo-50 pb-3">
        <div className="p-2 bg-indigo-100 text-indigo-600 rounded-lg">
          <PartyPopper size={20} />
        </div>
        <div>
           <h3 className="font-bold text-gray-800">Plan Feast Mode</h3>
           <p className="text-xs text-gray-500">Bank calories for a big event</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-xs font-semibold text-gray-700 mb-1">Event Name</label>
          <input
            type="text"
            placeholder="e.g. Birthday Dinner"
            value={eventName}
            onChange={(e) => { setEventName(e.target.value); setError(''); }}
            className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all"
            autoFocus
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-gray-700 mb-1">Event Date</label>
          <div className="relative">
             <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
             <input
                type="date"
                value={eventDate}
                onChange={(e) => { setEventDate(e.target.value); setError(''); }}
                className="w-full pl-9 pr-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all"
                min={new Date().toISOString().split('T')[0]}
              />
          </div>
          <p className="text-[10px] text-gray-400 mt-1 ml-1">Event must be within next 14 days</p>
        </div>

        {error && <p className="text-xs text-red-500 font-medium">{error}</p>}

        <div className="flex gap-2 pt-2">
           <button
             type="button"
             onClick={onCancel}
             className="flex-1 py-2 text-sm text-gray-500 hover:text-gray-700 hover:bg-gray-50 rounded-lg transition-colors"
           >
             Cancel
           </button>
           <button
             type="submit"
             className="flex-[2] py-2 text-sm bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-lg shadow-md transition-colors"
           >
             Check Strategy
           </button>
        </div>
      </form>
    </div>
  );
};

export default FeastSetupCard;
