// Example: Google Sign-In Button Component for Trial Account Migration
// Place this in your dashboard or profile page

import React, { useState } from 'react';

const GoogleSignInButton = ({ userId, userEmail }) => {
    const [loading, setLoading] = useState(false);

    // Check if this is a trial account
    const isTrialAccount = userEmail?.startsWith('trial_') && userEmail?.endsWith('@trial.local');

    if (!isTrialAccount) {
        return null; // Don't show button for non-trial accounts
    }

    const handleSignInWithGoogle = async () => {
        setLoading(true);

        try {
            const response = await fetch('/api/v1/auth/google/migrate-trial', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    trial_user_id: userId
                })
            });

            const data = await response.json();

            if (response.ok) {
                // Redirect to Google OAuth
                window.location.href = data.auth_url;
            } else {
                alert('Migration failed: ' + (data.detail || 'Unknown error'));
                setLoading(false);
            }
        } catch (error) {
            console.error('Error during migration:', error);
            alert('An error occurred. Please try again.');
            setLoading(false);
        }
    };

    return (
        <div className="trial-migration-banner">
            <div className="banner-icon">🔒</div>
            <div className="banner-content">
                <h3>Fitur Terkunci! 🔑</h3>
                <p>Integrasi Agent hanya tersedia untuk pengguna terdaftar.</p>
                <button
                    onClick={handleSignInWithGoogle}
                    disabled={loading}
                    className="google-signin-button"
                >
                    {loading ? (
                        <span>Loading...</span>
                    ) : (
                        <>
                            <img
                                src="https://www.google.com/favicon.ico"
                                alt="Google"
                                width="20"
                                height="20"
                            />
                            <span>Sign in with Google</span>
                        </>
                    )}
                </button>
                <p className="banner-footer">Tutup</p>
            </div>

            <style jsx>{`
        .trial-migration-banner {
          background: white;
          border: 1px solid #e0e0e0;
          border-radius: 8px;
          padding: 24px;
          margin: 16px 0;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
          display: flex;
          gap: 16px;
          align-items: center;
        }
        
        .banner-icon {
          font-size: 48px;
        }
        
        .banner-content {
          flex: 1;
        }
        
        .banner-content h3 {
          margin: 0 0 8px 0;
          color: #333;
          font-size: 18px;
          font-weight: 600;
        }
        
        .banner-content p {
          margin: 0 0 16px 0;
          color: #666;
          font-size: 14px;
        }
        
        .google-signin-button {
          background: #4285f4;
          color: white;
          border: none;
          border-radius: 4px;
          padding: 10px 24px;
          font-size: 14px;
          font-weight: 500;
          cursor: pointer;
          display: inline-flex;
          align-items: center;
          gap: 8px;
          transition: background 0.2s;
        }
        
        .google-signin-button:hover:not(:disabled) {
          background: #357ae8;
        }
        
        .google-signin-button:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }
        
        .banner-footer {
          margin-top: 8px;
          font-size: 12px;
          color: #999;
          cursor: pointer;
        }
        
        .banner-footer:hover {
          color: #666;
        }
      `}</style>
        </div>
    );
};

export default GoogleSignInButton;

// Usage example:
// import GoogleSignInButton from './components/GoogleSignInButton';
// 
// function Dashboard() {
//   const { user } = useAuth(); // Your auth hook
//   
//   return (
//     <div>
//       <GoogleSignInButton 
//         userId={user.id} 
//         userEmail={user.email}
//       />
//       {/* Rest of your dashboard */}
//     </div>
//   );
// }
