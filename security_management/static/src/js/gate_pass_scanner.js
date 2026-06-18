/** @odoo-module **/

import { Component, onMounted, onWillStart, onWillUnmount, useState, useRef, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { session } from "@web/session";
import { browser } from "@web/core/browser/browser";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

/**
 * GatePassScanner component for Security Management module
 * Provides QR code scanning functionality for gate passes
 */
export class GatePassScanner extends Component {
    /**
     * Component setup initializes services, refs, and state
     */
    setup() {
        // Initialize reactive state with useState
        this.state = useState({
            cameras: [],
            scanning: false,
            gatePass: null,
            showResult: false,
            showSuccess: false,
            showError: false,
            successMessage: '',
            errorMessage: '',
            scanHistory: [],
            isLoading: false,
            supported: true,
            usingFallback: false,
            selectedDeviceId: null
        });

        // Safely try to get services - in Odoo 18, we need to handle service availability carefully
        try {
            // Services - these are declared in the static services property
            this.rpc = useService("rpc");
            this.notification = useService("notification");
        } catch (error) {
            console.warn("Services not available, providing fallbacks", error);
            // Provide fallbacks if services aren't available
            this.rpc = {
                async: () => Promise.resolve({}),
                call: async () => Promise.resolve({})
            };
            this.notification = {
                add: () => {}
            };
        }
        
        // DOM refs for accessing elements
        this.video = useRef("video");
        this.canvas = useRef("canvas");
        this.cameraSelect = useRef("cameraSelect");
        this.startButton = useRef("startButton");
        this.stopButton = useRef("stopButton");
        this.scanType = useRef("scanType");

        // Non-reactive state
        this.canvasContext = null;
        this.animationFrameId = null;
        this.barcodeDetector = null;

        // Lifecycle hooks
        onWillStart(async () => {
            // Any async initialization before the component is mounted
            // Nothing specific needed here, but hook is available
        });
        
        onMounted(() => {
            // Initialize the scanner after the component is mounted and DOM is ready
            // Using setTimeout to ensure DOM is fully rendered
            browser.setTimeout(() => this.initScanner(), 100);
        });
        
        onWillUnmount(() => {
            // Clean up resources when the component is unmounted
            this.cleanup();
        });
    }

    async initScanner() {
        if (!this.canvas.el || !this.video.el) return;
        this.canvasContext = this.canvas.el.getContext('2d', { willReadFrequently: true });

        // Check if BarcodeDetector API is available
        if ('BarcodeDetector' in window) {
            try {
                const supportedFormats = await BarcodeDetector.getSupportedFormats();
                if (supportedFormats.includes('qr_code')) {
                    this.barcodeDetector = new BarcodeDetector({ formats: ['qr_code'] });
                    console.log('Using native BarcodeDetector API for QR scanning');
                } else {
                    console.warn('QR code format not supported by BarcodeDetector');
                    this.loadZXingFallback();
                }
            } catch (err) {
                console.error('Error initializing BarcodeDetector:', err);
                this.loadZXingFallback();
            }
        } else {
            console.warn('BarcodeDetector API not available');
            this.loadZXingFallback();
        }

        try {
            const devices = await navigator.mediaDevices.enumerateDevices();
            const videoDevices = devices.filter(device => device.kind === 'videoinput');
            this.state.cameras = videoDevices.map(device => ({
                id: device.deviceId,
                label: device.label || `Camera ${this.state.cameras.length + 1}`
            }));

            if (this.state.cameras.length > 0) {
                this.state.selectedDeviceId = this.state.cameras[0].id;
                
                // Update the camera selection dropdown with available cameras
                if (this.cameraSelect.el) {
                    // Clear existing options
                    while (this.cameraSelect.el.firstChild) {
                        this.cameraSelect.el.removeChild(this.cameraSelect.el.firstChild);
                    }
                    
                    // Add camera options
                    this.state.cameras.forEach(camera => {
                        const option = document.createElement('option');
                        option.value = camera.id;
                        option.text = camera.label;
                        this.cameraSelect.el.appendChild(option);
                    });
                    
                    // Set the first camera as selected
                    this.cameraSelect.el.value = this.state.selectedDeviceId;
                }
            } else {
                // No cameras found
                if (this.cameraSelect.el) {
                    // Clear existing options
                    while (this.cameraSelect.el.firstChild) {
                        this.cameraSelect.el.removeChild(this.cameraSelect.el.firstChild);
                    }
                    
                    // Add a "No cameras found" option
                    const option = document.createElement('option');
                    option.value = "";
                    option.text = "No cameras found";
                    this.cameraSelect.el.appendChild(option);
                }
            }
            
            console.log('Available cameras:', this.state.cameras);
        } catch (error) {
            console.error('Error accessing media devices:', error);
            this.showError('Failed to access camera. Please ensure camera permissions are granted.');
            
            // Update dropdown to show error
            if (this.cameraSelect.el) {
                // Clear existing options
                while (this.cameraSelect.el.firstChild) {
                    this.cameraSelect.el.removeChild(this.cameraSelect.el.firstChild);
                }
                
                // Add an error option
                const option = document.createElement('option');
                option.value = "";
                option.text = "Camera access denied";
                this.cameraSelect.el.appendChild(option);
            }
        }
    }

    loadZXingFallback() {
        this.state.usingFallback = true;
        
        // Load ZXing library as fallback (dynamically)
        const script = document.createElement('script');
        script.src = 'https://unpkg.com/@zxing/library@0.19.1/umd/index.min.js';
        script.onload = () => {
            console.log('ZXing library loaded as fallback for QR scanning');
            this.state.supported = true;
        };
        script.onerror = () => {
            console.error('Failed to load ZXing fallback library');
            this.state.supported = false;
            this.showError('QR scanning not supported in this browser');
        };
        document.head.appendChild(script);
    }

    async startScanning() {
        if (!this.video.el) return;
        
        if (!this.state.supported) {
            this.showError('QR scanning not supported in this browser');
            return;
        }

        try {
            const constraints = {
                audio: false,
                video: {
                    deviceId: this.state.selectedDeviceId ? { exact: this.state.selectedDeviceId } : undefined,
                    width: { ideal: 1280 },
                    height: { ideal: 720 },
                    facingMode: "environment",
                    advanced: [{ focusMode: 'continuous' }]
                }
            };

            const stream = await navigator.mediaDevices.getUserMedia(constraints);
            
            // Set the video source to the camera stream
            this.video.el.srcObject = stream;
            this.video.el.setAttribute('playsinline', true);

            // Start scanning when video is ready
            this.video.el.onloadedmetadata = () => {
                this.video.el.play();
                this.state.scanning = true;
                this.startButton.el.disabled = true;
                this.stopButton.el.disabled = false;
                this.scanCode();
            };
        } catch (error) {
            console.error('Error starting camera:', error);
            this.showError('Failed to start camera. Please ensure camera permissions are granted.');
        }
    }

    async stopScanning() {
        if (this.video.el && this.video.el.srcObject) {
            const tracks = this.video.el.srcObject.getTracks();
            tracks.forEach(track => track.stop());
            this.video.el.srcObject = null;
        }

        if (this.animationFrameId) {
            cancelAnimationFrame(this.animationFrameId);
            this.animationFrameId = null;
        }

        this.startButton.el.disabled = false;
        this.stopButton.el.disabled = true;
        this.state.scanning = false;
    }

    cleanup() {
        this.stopScanning();
    }

    scanCode() {
        try {
            if (!this.state.scanning || !this.canvasContext) {
                console.warn('Scanning attempted while inactive');
                return;
            }
            if (this.video.el.readyState === this.video.el.HAVE_ENOUGH_DATA) {
                // Set canvas dimensions to match video
                this.canvas.el.width = this.video.el.videoWidth;
                this.canvas.el.height = this.video.el.videoHeight;

                // Draw video frame to canvas
                this.canvasContext.drawImage(this.video.el, 0, 0, this.canvas.el.width, this.canvas.el.height);

                if (this.state.usingFallback) {
                    // Use ZXing as fallback
                    this.scanWithZXing();
                } else {
                    // Use native BarcodeDetector
                    this.scanWithBarcodeDetector();
                }
            }

            // Continue scanning
            if (this.state.scanning) {
                this.animationFrameId = requestAnimationFrame(() => this.scanCode());
            }
        } catch (error) {
            console.error('Scanning Error:', error);
            this.showError('Scanning failed. Ensure proper lighting and camera focus');
        }
    }

    async scanWithBarcodeDetector() {
        try {
            const barcodes = await this.barcodeDetector.detect(this.canvas.el);
            
            if (barcodes.length > 0) {
                // Process the first detected QR code
                const barcode = barcodes[0];
                
                // Draw box around the detected QR code
                if (barcode.cornerPoints) {
                    this.drawQRCodeBox(barcode.cornerPoints);
                }
                
                const rawData = barcode.rawValue.trim().toUpperCase();
                console.debug('[BarcodeDetector] Raw decoded:', rawData);
                
                // Process the scanned code
                this.processScannedCode(rawData);
                
                // Pause scanning briefly to prevent multiple scans
                this.state.scanning = false;
                setTimeout(() => {
                    this.state.scanning = true;
                    this.scanCode();
                }, 2000);
            }
        } catch (error) {
            console.error('Barcode detection error:', error);
        }
    }

    scanWithZXing() {
        if (typeof ZXing === 'undefined') {
            console.warn('ZXing library not loaded yet');
            return;
        }
        
        try {
            const imageData = this.canvasContext.getImageData(
                0, 0, this.canvas.el.width, this.canvas.el.height
            );
            
            const hints = new Map();
            hints.set(ZXing.DecodeHintType.POSSIBLE_FORMATS, [ZXing.BarcodeFormat.QR_CODE]);
            hints.set(ZXing.DecodeHintType.TRY_HARDER, true);
            
            const reader = new ZXing.MultiFormatReader();
            reader.setHints(hints);
            
            const luminanceSource = new ZXing.HTMLCanvasElementLuminanceSource(this.canvas.el);
            const binaryBitmap = new ZXing.BinaryBitmap(
                new ZXing.HybridBinarizer(luminanceSource)
            );
            
            try {
                const result = reader.decode(binaryBitmap);
                
                if (result) {
                    const rawData = result.getText().trim().toUpperCase();
                    console.debug('[ZXing] Raw decoded:', rawData);
                    
                    // Process the scanned code
                    this.processScannedCode(rawData);
                    
                    // Pause scanning briefly to prevent multiple scans
                    this.state.scanning = false;
                    setTimeout(() => {
                        this.state.scanning = true;
                        this.scanCode();
                    }, 2000);
                }
            } catch (zxingError) {
                // QR code not found in this frame, continue scanning
            }
        } catch (error) {
            console.error('ZXing scanning error:', error);
        }
    }

    drawQRCodeBox(points) {
        if (!this.canvasContext) return;
        
        this.canvasContext.lineWidth = 4;
        this.canvasContext.strokeStyle = "#FF3B58";
        this.canvasContext.beginPath();
        
        // Draw lines connecting the corner points
        if (Array.isArray(points) && points.length >= 4) {
            this.canvasContext.moveTo(points[0].x, points[0].y);
            for (let i = 1; i < points.length; i++) {
                this.canvasContext.lineTo(points[i].x, points[i].y);
            }
            this.canvasContext.lineTo(points[0].x, points[0].y);
        }
        
        this.canvasContext.stroke();
    }

    async processScannedCode(code) {
        console.log('Raw scanned code:', code);
        
        // Basic validation
        if (!code || typeof code !== 'string') {
            console.error('Invalid QR data type:', typeof code);
            this.showError('Invalid QR code data');
            return;
        }

        // Fix common detection issues - convert RQPASS to QRPASS if needed
        let sanitized = code.trim().toUpperCase();
        if (sanitized.startsWith('RQPASS-')) {
            sanitized = 'QRPASS-' + sanitized.substring(7);
            console.log('Corrected prefix from RQPASS to QRPASS:', sanitized);
        }

        // Validate QR code format
        const QR_REGEX = /^QRPASS-[A-Z0-9]{8}$/;
        if (!QR_REGEX.test(sanitized)) {
            console.error('Invalid QR format:', sanitized);
            this.showError('Invalid code format. Expected QRPASS- followed by 8 alphanumerics');
            return;
        }

        // Get current scan type
        const currentScanType = this.scanType.el.value;

        // Check scan history for duplicate action
        if (this.state.scanHistory.length > 0) {
            const lastScan = this.state.scanHistory[0];
            // Check if gate pass code matches and scan type is the same
            if (lastScan.gatePass && lastScan.gatePass.code === sanitized) {
                const lastScanType = lastScan.scanType;
                if (lastScanType === currentScanType) {
                    const actionType = currentScanType === 'in' ? 'check in' : 'check out';
                    const errorMessage = `Warning: This gate pass was already ${actionType === 'check in' ? 'checked in' : 'checked out'} as the last action. The last scan was at ${this.formatDateTime(lastScan.timestamp)}.`;
                    this.showError(errorMessage);
                    return;
                }
            }
        }

        try {
            this.state.isLoading = true;
            console.log('Processing QR code:', sanitized);

            // Prepare data for the request
            const postData = {
                code: sanitized,
                scan_type: currentScanType
            };

            // Call the backend endpoint
            console.log('Calling RPC endpoint with data:', postData);
            const result = await this.rpc("/security/gate_pass/scan", postData);
            console.log('Scan result:', result);

            this.state.isLoading = false;

            if (result && result.success) {
                this.showSuccess(result);
                this.addToScanHistory({...result, scanType: currentScanType});
            } else {
                const errorMsg = result && result.error ? result.error : 'Unknown error occurred';
                this.showError(errorMsg);
            }
        } catch (error) {
            this.state.isLoading = false;
            console.error('Error processing scan:', error);

            let errorMessage = 'Failed to process scan. Please try again.';
            if (error.message && error.message.includes('404')) {
                errorMessage = 'Server endpoint not found. Please contact your administrator.';
            } else if (error.message) {
                errorMessage = `Error: ${error.message}`;
            }

            this.showError(errorMessage);
        }
    }

    showSuccess(result) {
        this.state.gatePass = result.gate_pass;
        this.state.successMessage = result.message;
        this.state.showResult = true;
        this.state.showSuccess = true;
        this.state.showError = false;
    }

    showError(message) {
        this.state.errorMessage = message;
        this.state.showResult = true;
        this.state.showSuccess = false;
        this.state.showError = true;

        // Resume scanning after showing error
        setTimeout(() => {
            if (this.state.scanning) {
                this.scanCode();
            }
        }, 3000);
    }

    addToScanHistory(result) {
        const historyItem = {
            timestamp: new Date(),
            message: result.message,
            gatePass: result.gate_pass,
            scanType: result.scanType
        };

        this.state.scanHistory.unshift(historyItem);

        // Limit history to 20 items
        if (this.state.scanHistory.length > 20) {
            this.state.scanHistory = this.state.scanHistory.slice(0, 20);
        }
    }

    onCameraChange() {
        if (this.state.scanning) {
            // Stop current stream before switching camera
            this.stopScanning();

            // Update selected device ID
            this.state.selectedDeviceId = this.cameraSelect.el.value;

            // Start scanning with new camera
            this.startScanning();
        } else {
            // Just update the selected device ID
            this.state.selectedDeviceId = this.cameraSelect.el.value;
        }
    }

    formatDateTime(dateTimeStr) {
        if (!dateTimeStr) return '';

        try {
            const date = new Date(dateTimeStr);
            return date.toLocaleString();
        } catch (error) {
            console.error('Error formatting date:', error);
            return dateTimeStr;
        }
    }
}

// Define component properties
GatePassScanner.template = 'security_management.GatePassScanner';

// Define our own props instead of using standardWidgetProps to avoid JSON serialization issues
GatePassScanner.props = {
    // Standard client action props
    action: { type: Object, optional: true },
    actionId: { type: [Number, String], optional: true },
    className: { type: String, optional: true },
    updateActionState: { type: Function, optional: true },
    globalState: { type: Object, optional: true },
    
    // Common widget props, but explicitly defined to avoid issues with Odoo 18's JSON handling
    record: { type: Object, optional: true },
    fieldName: { type: String, optional: true },
    FieldComponent: { type: Function, optional: true },
    readonly: { type: Boolean, optional: true },
    isSmall: { type: Boolean, optional: true },
    decorations: { type: Object, optional: true },
    classNames: { type: String, optional: true },
    // Component specific props
    resId: { type: [Number, String], optional: true },
    resModel: { type: String, optional: true },
    // Override record to make it optional - the error was that it's required by default in standardWidgetProps
    record: { type: Object, optional: true }
};

// In Odoo 18, client actions need to be registered differently
class GatePassScannerAction extends Component {
    setup() {
        // Use the action service to redirect to the actual scanner component
        const action = useService("action");
        
        onMounted(() => {
            // Launch our scanner component with a mock record to satisfy prop validation
            action.doAction({
                type: 'ir.actions.client',
                tag: 'gate_pass_scanner_component',
                params: {
                    // Pass an empty record object to satisfy prop validation
                    record: {}
                }
            });
        });
    }
}

// Simple template for the wrapper
GatePassScannerAction.template = xml`<div class="gate_pass_scanner_container"></div>`;

// Define all props that might be passed by the ActionManager
GatePassScannerAction.props = {
    // Standard client action props
    action: { type: Object, optional: true },
    actionId: { type: [Number, String], optional: true },
    className: { type: String, optional: true },
    updateActionState: { type: Function, optional: true },
    globalState: { type: Object, optional: true },
};

// Define services for the action wrapper
GatePassScannerAction.services = {
    action: "action"
};

// Register the standalone scanner component
registry.category("actions").add("gate_pass_scanner_component", GatePassScanner);

// Register the action wrapper
registry.category("actions").add("gate_pass_scanner", GatePassScannerAction);
