// lib/apiService.ts

// Fallback to localhost if not specified in environment
const API_BASE_URL = import.meta.env.VITE_API_URL || ''; 

// --- Monitoring & SMS Endpoints ---
// REMOVED IN FAVOR OF CLIENT-SIDE MONITORING

// --- Contact Management ---
// REMOVED FOR DEPLOYMENT ACCESSIBILITY (NON-FREE)


// --- Chatbot Endpoints ---

// 5. Send Chat Message
export const sendChatMessage = async (userId: string, message: string) => {
    const response = await fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, message }),
    });

    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Chatbot communication failed.');
    }
    const data = await response.json();
    return data.response; 
};

// --- Evidence Upload Endpoint ---

// 6. Upload Evidence
export const uploadEvidence = async (userId: string, fileList: FileList) => {
    const formData = new FormData();
    formData.append('user_id', userId);
    
    // Append each file in the list under the key 'files'
    for (let i = 0; i < fileList.length; i++) {
        formData.append('files', fileList[i]); 
    }

    const response = await fetch(`${API_BASE_URL}/upload_evidence`, {
        method: 'POST',
        body: formData, 
    });

    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'File upload failed.');
    }
    return response.json();
};