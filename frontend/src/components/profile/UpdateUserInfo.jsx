import React from 'react';

const UpdateUserInfo = ({ user }) => {
    return (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-8 max-w-2xl"> // Limited width for better form readability
            <h2 className="text-2xl font-bold text-gray-800 mb-6">Update User Information</h2>
            <form className="space-y-6">
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Display Name</label>
                    <input 
                        type="text" 
                        defaultValue={user?.name}
                        className="w-full px-4 py-3 rounded-lg border border-gray-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 outline-none transition-all"
                    />
                </div>
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Email Address</label>
                    <input 
                        type="email" 
                        defaultValue={user?.email}
                        className="w-full px-4 py-3 rounded-lg border border-gray-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 outline-none transition-all"
                    />
                </div>
                <div className="pt-4">
                    <button className="px-6 py-3 bg-indigo-600 text-white font-semibold rounded-lg hover:bg-indigo-700 transition-colors shadow-md hover:shadow-lg">
                        Save Changes
                    </button>
                </div>
            </form>
        </div>
    );
};

export default UpdateUserInfo;
