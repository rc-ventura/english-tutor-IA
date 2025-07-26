import React, { useState, useCallback, useEffect } from 'react';
import * as api from '../services/api';

const ProgressTab: React.FC = () => {
  const [progressHtml, setProgressHtml] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const fetchProgress = useCallback(async () => {
    setIsLoading(true);
    try {
      const html = await api.getProgressHtml();
      setProgressHtml(html);
    } catch (error) {
      console.error("Failed to fetch progress:", error);
      setProgressHtml('<p class="text-red-400 text-center">Could not load progress data. Please try again.</p>');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProgress();
  }, [fetchProgress]);

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-white">Progress Dashboard</h1>
        <button
          onClick={fetchProgress}
          disabled={isLoading}
          className="px-4 py-2 bg-indigo-600 text-white font-semibold rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50"
        >
          {isLoading ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>
      <div className="bg-gray-800/50 p-6 rounded-xl shadow-lg border border-gray-700 min-h-[20rem]">
        {isLoading ? (
            <div className="flex justify-center items-center h-64">
                <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-indigo-400"></div>
            </div>
        ) : (
             <div dangerouslySetInnerHTML={{ __html: progressHtml }} />
        )}
      </div>
    </div>
  );
};

export default ProgressTab;