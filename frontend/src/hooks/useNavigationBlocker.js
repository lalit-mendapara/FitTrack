import { useEffect } from 'react';
// import { useBlocker } from 'react-router-dom'; // REMOVED: Requires Data Router

/**
 * Hook to block navigation and user actions when a process is active.
 * @param {boolean} isBlocking - Whether to block navigation.
 * @param {string} message - Message to display when trying to leave.
 */
export const useNavigationBlocker = (isBlocking, message = "Plan generation is in progress. Leaving now may cause the plan to be incomplete.") => {
    
    // 1. Block Internal Navigation (React Router)
    // Since we are using legacy <BrowserRouter>, useBlocker is not available.
    // However, we are rendering a full-screen z-index 100 overlay. 
    // This physically prevents users from clicking any internal links (Navbar, etc.).
    // So explicit router blocking is less critical for "user actions".
    
    // 2. Block Browser Refresh / Close
    useEffect(() => {
        const handleBeforeUnload = (e) => {
            if (isBlocking) {
                e.preventDefault();
                e.returnValue = message;
                return message;
            }
        };

        if (isBlocking) {
            window.addEventListener('beforeunload', handleBeforeUnload);
        }

        return () => {
            window.removeEventListener('beforeunload', handleBeforeUnload);
        };
    }, [isBlocking, message]);

    // 3. Push State to "Neutralize" Back Button (Hard Block)
    // If isBlocking, we push the current state again so back button just pops to same state?
    // Or we listen to popstate and push forward.
    useEffect(() => {
         if (!isBlocking) return;

         const handlePopState = (event) => {
             // If user hits back, we want to stay.
             // We can push the state back in.
             // This effectively "eats" the back button action.
             window.history.pushState(null, document.title, window.location.href);
         };

         // Push state once to create a buffer
         window.history.pushState(null, document.title, window.location.href);
         window.addEventListener('popstate', handlePopState);

         return () => {
             window.removeEventListener('popstate', handlePopState);
             // Note: We don't undo the pushState because that would force navigation. 
             // We just stop listening.
         };
    }, [isBlocking]);

};
