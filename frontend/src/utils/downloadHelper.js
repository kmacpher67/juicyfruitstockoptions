export const downloadFile = (blobData, filename) => {
    try {
        // Ensure we handle both Blob and raw data
        const blob = blobData instanceof Blob
            ? blobData
            : new Blob([blobData], { type: 'text/csv;charset=utf-8;' });

        // For IE10+ (unlikely but good practice)
        if (navigator.msSaveBlob) {
            navigator.msSaveBlob(blob, filename);
            return;
        }

        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.style.display = 'none';
        link.href = url;
        link.setAttribute('download', filename);

        // Append to body to ensure visibility to browser
        document.body.appendChild(link);

        // Trigger click
        link.click();

        // Cleanup
        setTimeout(() => {
            document.body.removeChild(link);
            window.URL.revokeObjectURL(url);
        }, 100);

        console.log(`Download triggered for: ${filename}`);
    } catch (e) {
        console.error("Download helper failed:", e);
        alert("Download helper failed: " + e.message);
    }
};
