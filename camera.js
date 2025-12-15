document.addEventListener('DOMContentLoaded', () => {

    // 1. Element Declarations
    const startButton = document.getElementById('start-camera-btn');
    const stopButton = document.getElementById('stop-camera-btn');
    const video = document.getElementById('video-stream');
    const cameraContainer = document.getElementById('camera-container');
    const canvas = document.getElementById('canvas-capture');
    const photoButton = document.getElementById('take-photo-btn');
    const photoPreview = document.getElementById('photo-preview');
    const recordStartButton = document.getElementById('record-video-btn');
    const recordStopButton = document.getElementById('stop-record-btn');
    const videoPreview = document.getElementById('video-preview');

    // NEW: Upload Buttons and Status Div
    const uploadPhotoBtn = document.getElementById('upload-photo-btn');
    const uploadVideoBtn = document.getElementById('upload-video-btn');
    const uploadStatus = document.getElementById('upload-status');

    let currentStream = null;
    let mediaRecorder = null;
    let recordedChunks = [];
    let capturedPhotoBlob = null;
    let capturedVideoBlob = null;

    // --- Aggressive Debugging Check ---
    if (!photoButton || !recordStartButton || !startButton) {
        console.error("CRITICAL ERROR: One or more key buttons were not found in the HTML. Check your IDs.");
    }
    // ----------------------------------

    // Helper to display status messages
    function setStatus(message, isError = false) {
        if (!uploadStatus) {
            console.error("Upload status element missing.");
            return;
        }
        uploadStatus.textContent = message;
        uploadStatus.style.display = 'block';
        uploadStatus.style.backgroundColor = isError ? '#f8d7da' : '#d4edda';
        uploadStatus.style.color = isError ? '#721c24' : '#155724';

        setTimeout(() => {
            uploadStatus.style.display = 'none';
        }, 5000);
    }

    // Helper to reset all button states
    function resetCaptureButtons() {
        console.log("DEBUG: resetCaptureButtons called. Enabling buttons.");

        // Safely check elements before accessing properties
        if (photoButton) photoButton.style.display = 'inline';
        if (recordStartButton) recordStartButton.style.display = 'inline';
        if (recordStopButton) recordStopButton.style.display = 'none';
        if (uploadPhotoBtn) uploadPhotoBtn.style.display = 'none';
        if (uploadVideoBtn) uploadVideoBtn.style.display = 'none';

        // **CRITICAL:** Force removal of the disabled attribute
        if (photoButton) photoButton.removeAttribute('disabled');
        if (recordStartButton) recordStartButton.removeAttribute('disabled');
        if (stopButton) stopButton.removeAttribute('disabled');

        console.log("DEBUG: Photo button disabled status after reset:", photoButton ? photoButton.disabled : 'N/A');
    }


    const startCamera = async () => {
        if (!startButton || !cameraContainer || !video) {
            console.error("Camera elements not initialized.");
            return;
        }

        // Hide CTA and show camera container
        startButton.style.display = 'none';
        cameraContainer.style.display = 'block';

        // Reset previews
        if (photoPreview) photoPreview.style.display = 'none';
        if (videoPreview) videoPreview.style.display = 'none';

        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                video: true,
                audio: true
            });

            video.srcObject = stream;
            currentStream = stream;

            resetCaptureButtons();
            setStatus("Camera started successfully. You can snap photos or record videos.", false);

        } catch (err) {
            console.error("Error accessing camera: ", err);
            setStatus("Error: Could not access camera. Please check permissions and if you are on localhost/HTTPS.", true);

            startButton.style.display = 'block';
            cameraContainer.style.display = 'none';
        }
    };

    const stopCamera = () => {
        if (currentStream) {
            currentStream.getTracks().forEach(track => track.stop());
            currentStream = null;
        }

        if (mediaRecorder && mediaRecorder.state !== 'inactive') {
            mediaRecorder.stop();
        }

        if (video) video.srcObject = null;
        if (cameraContainer) cameraContainer.style.display = 'none';
        if (startButton) startButton.style.display = 'block';

        if (photoPreview) photoPreview.style.display = 'none';
        if (videoPreview) videoPreview.style.display = 'none';
        resetCaptureButtons();
    };

    const takePhoto = () => {
        if (!currentStream || !canvas || !video || !photoPreview || !photoButton || !recordStartButton || !uploadPhotoBtn || !uploadVideoBtn || !stopButton) return;

        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);

        canvas.toBlob((blob) => {
            capturedPhotoBlob = blob;
            const imageURL = URL.createObjectURL(blob);

            photoPreview.src = imageURL;
            photoPreview.style.display = 'block';

            // Hide capture buttons, show upload button
            photoButton.style.display = 'none';
            recordStartButton.style.display = 'none';
            uploadPhotoBtn.style.display = 'inline';
            uploadVideoBtn.style.display = 'none';

            // FIX: Enable stop button after preview is ready
            stopButton.removeAttribute('disabled');
        }, 'image/png');
    };

    const startRecording = () => {
        if (!currentStream || !recordStartButton || !recordStopButton || !photoButton || !stopButton) return;

        recordedChunks = [];
        capturedVideoBlob = null;
        mediaRecorder = new MediaRecorder(currentStream);
        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                recordedChunks.push(event.data);
            }
        };

        mediaRecorder.onstop = () => {
            if (!videoPreview || !recordStartButton || !recordStopButton || !uploadVideoBtn || !uploadPhotoBtn || !photoButton || !stopButton) return;

            const blob = new Blob(recordedChunks, { type: 'video/webm' });
            capturedVideoBlob = blob;
            const videoURL = URL.createObjectURL(blob);

            videoPreview.src = videoURL;
            videoPreview.style.display = 'block';

            // Hide record buttons, show upload video button
            recordStartButton.style.display = 'none';
            recordStopButton.style.display = 'none';
            uploadVideoBtn.style.display = 'inline';
            uploadPhotoBtn.style.display = 'none';
            photoButton.style.display = 'none';

            // FIX: Enable stop button after preview is ready
            stopButton.removeAttribute('disabled');
            setStatus("Recording stopped. Previewing video...", false);
        };

        mediaRecorder.start();
        recordStartButton.style.display = 'none';
        recordStopButton.style.display = 'inline-block';
        photoButton.setAttribute('disabled', 'true');
        stopButton.removeAttribute('disabled');
        setStatus("Recording started...", false);
    };

    const stopRecording = () => {
        if (mediaRecorder && mediaRecorder.state !== 'inactive') {
            mediaRecorder.stop();
        }
    };

    async function uploadMedia(blob, filename) {
        if (!blob) {
            setStatus("Error: No media captured to upload.", true);
            return;
        }
        if (!uploadPhotoBtn || !uploadVideoBtn || !stopButton) return;

        const formData = new FormData();
        const file = new File([blob], filename, { type: blob.type });
        formData.append('file', file);

        setStatus("Uploading media...", false);

        // Disable upload buttons during upload
        uploadPhotoBtn.setAttribute('disabled', 'true');
        uploadVideoBtn.setAttribute('disabled', 'true');

        try {
            const response = await fetch('/upload-media', {
                method: 'POST',
                body: formData,
            });

            // Re-enable stop button (it might be needed if the upload fails but the user wants to stop the camera)
            stopButton.removeAttribute('disabled');

            if (response.ok || response.status === 303) {
                setStatus("Upload successful! Redirecting to your media gallery...", false);
                setTimeout(() => {
                    window.location.href = '/add-photos-videos?message=Captured media uploaded successfully!';
                }, 1000);
            } else if (response.status === 401 || response.status === 403) {
                setStatus("Upload failed: You must be logged in.", true);
                setTimeout(() => {
                    window.location.href = '/login?next_url=/';
                }, 1000);
            } else {
                const errorText = await response.text();
                console.error("Upload error:", errorText);
                setStatus(`Upload failed: ${response.status} ${response.statusText}`, true);
            }
        } catch (error) {
            console.error("Network error during upload:", error);
            setStatus("Network error. Check your connection or server status.", true);
        }

        // Reset UI after upload attempt (even if failed)
        resetCaptureButtons();
        if (photoPreview) photoPreview.style.display = 'none';
        if (videoPreview) videoPreview.style.display = 'none';
    }


    // --- Event Listeners ---
    if (startButton) startButton.addEventListener('click', startCamera);
    if (stopButton) stopButton.addEventListener('click', stopCamera);
    if (photoButton) photoButton.addEventListener('click', takePhoto);
    if (recordStartButton) recordStartButton.addEventListener('click', startRecording);
    if (recordStopButton) recordStopButton.addEventListener('click', stopRecording);

    // NEW: Upload event listeners
    if (uploadPhotoBtn) {
        uploadPhotoBtn.addEventListener('click', () => {
            uploadMedia(capturedPhotoBlob, `capture_photo_${Date.now()}.png`);
        });
    }

    if (uploadVideoBtn) {
        uploadVideoBtn.addEventListener('click', () => {
            uploadMedia(capturedVideoBlob, `capture_video_${Date.now()}.webm`);
        });
    }
});