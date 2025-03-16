// Function to show a floating toast notification
function showToast(message, type = 'info') {
    // Remove existing toast if any
    const existingToast = document.querySelector('div[data-toast]');
    if (existingToast) {
        document.body.removeChild(existingToast);
    }

    let toast = document.createElement('div');
    toast.setAttribute('data-toast', 'true');
    toast.innerText = message;
    toast.style.position = 'fixed';
    toast.style.bottom = '20px';
    toast.style.right = '20px';
    toast.style.padding = '10px 15px';
    toast.style.borderRadius = '5px';
    toast.style.fontSize = '14px';
    toast.style.zIndex = '10000';
    toast.style.opacity = '1';
    toast.style.transition = 'opacity 0.5s ease-in-out';

    // Set styles based on message type
    switch (type.toLowerCase()) {
        case 'error':
            toast.style.background = 'rgba(220, 53, 69, 0.9)'; // red
            toast.style.color = 'white';
            break;
        case 'warning':
            toast.style.background = 'rgba(255, 193, 7, 0.9)'; // yellow
            toast.style.color = 'black';
            break;
        case 'info':
        default:
            toast.style.background = 'rgba(0, 0, 0, 0.8)'; // dark
            toast.style.color = 'white';
            break;
    }

    document.body.appendChild(toast);

    // Fade out and remove after 2 seconds
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => document.body.removeChild(toast), 500);
    }, 2000);
}
