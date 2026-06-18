/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, onMounted, onWillUnmount, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { loadJS } from "@web/core/assets";

class QRScanner extends Component {
    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");
        
        this.state = useState({
            isScanning: false,
            lastResult: null,
            resultMessage: null,
            resultType: null,
            scanResult: null,
        });
        
        this.scanner = null;
        this.videoElement = null;
        this.startButton = null;
        this.stopButton = null;
        this.resultArea = null;
        
        onMounted(() => {
            this.videoElement = document.querySelector('.o_security_qr_video');
            this.startButton = document.querySelector('.o_security_start_scan');
            this.stopButton = document.querySelector('.o_security_stop_scan');
            this.resultArea = document.querySelector('.o_security_scan_result');
            
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                this.showError(_t("Your browser doesn't support camera access. Please use a modern browser like Chrome, Firefox, or Edge."));
                if (this.startButton) {
                    this.startButton.disabled = true;
                }
            }
        });
        
        onWillUnmount(() => {
            this.stopScanning();
        });
    }
    
    startScanning() {
        if (this.state.isScanning) {
            return;
        }
        
        if (this.resultArea) {
            this.resultArea.innerHTML = '';
        }
        this.state.lastResult = null;
        this.state.resultMessage = null;
        this.state.resultType = null;
        
        const startCamera = async () => {
            try {
                // Load the QR code library using loadJS
                if (!window.Html5Qrcode) {
                    await loadJS('https://unpkg.com/html5-qrcode@2.3.8/html5-qrcode.min.js');
                }
                
                // Wait a bit for the library to fully initialize
                await new Promise(resolve => setTimeout(resolve, 100));
                
                // Check if all required classes are available
                if (!window.Html5Qrcode) {
                    throw new Error("QR code library not properly loaded");
                }
                
                // Use Html5Qrcode (note the lowercase 'c' in 'code')
                this.scanner = new Html5Qrcode("o_security_qr_reader");
                
                const qrCodeSuccessCallback = (decodedText, decodedResult) => {
                    if (this.state.lastResult === decodedText) {
                        return;
                    }
                    this.state.lastResult = decodedText;
                    this.processQRCode(decodedText);
                };
                
                const qrCodeErrorCallback = (errorMessage) => {
                    // Only log actual errors, not scanning attempts
                    if (!errorMessage.includes("No MultiFormat Readers") && 
                        !errorMessage.includes("NotFoundException") &&
                        !errorMessage.includes("No code found")) {
                        console.warn("QR Scanner:", errorMessage);
                    }
                };
                
                const config = {
                    fps: 10,
                    qrbox: { width: 250, height: 250 },
                    aspectRatio: 1.0,
                    disableFlip: false,
                    // Simplified configuration - let the library handle format detection
                    experimentalFeatures: {
                        useBarCodeDetectorIfSupported: true
                    }
                };
                
                await this.scanner.start(
                    { facingMode: "environment" },
                    config,
                    qrCodeSuccessCallback,
                    qrCodeErrorCallback
                );
                
                this.state.isScanning = true;
                if (this.startButton) this.startButton.style.display = 'none';
                if (this.stopButton) this.stopButton.style.display = 'inline-block';
                
            } catch (error) {
                this.showError(_t("Failed to load QR scanner library: ") + error);
            }
        };
        
        startCamera();
    }
    
    stopScanning() {
        if (this.scanner && this.state.isScanning) {
            this.scanner.stop().then(() => {
                this.state.isScanning = false;
                if (this.startButton) this.startButton.style.display = 'inline-block';
                if (this.stopButton) this.stopButton.style.display = 'none';
            }).catch(error => {
                console.error("Failed to stop scanner:", error);
            });
        }
    }
    
    async processQRCode(qrCode) {
        this.playBeepSound();
        
        try {
            // Check if this is checkpoint scanning for a patrol
            const scanType = this.props.context && this.props.context.scan_type;
            const patrolId = this.props.context && this.props.context.default_patrol_id;
            
            if (scanType === 'checkpoint' && patrolId) {
                // Handle checkpoint scanning for patrol progress
                const result = await this.orm.call(
                    'security.patrol.point',
                    'process_checkpoint_scan',
                    [qrCode, patrolId]
                );
                
                if (result.error) {
                    this.showResult('error', result.error);
                } else {
                    this.showCheckpointResult(result);
                }
            } else {
                // Default QR code processing
                const result = await this.orm.call(
                    'security.patrol.point',
                    'process_qr_code',
                    [qrCode]
                );
                
                if (result.error) {
                    this.showResult('error', result.error);
                } else {
                    this.showResult('success', result);
                }
            }
        } catch (error) {
            console.error("QR Scanner Error:", error);
            let errorMessage = _t("Failed to process QR code: ");
            
            if (error.message) {
                errorMessage += error.message;
            } else if (typeof error === 'string') {
                errorMessage += error;
            } else {
                errorMessage += _t("Unknown error occurred. Please try again or contact support.");
            }
            
            this.showResult('error', errorMessage);
        }
    }
    
    showCheckpointResult(result) {
        if (!this.resultArea) return;
        
        this.resultArea.innerHTML = '';
        
        const content = document.createElement('div');
        content.className = result.success ? 'alert alert-success' : 'alert alert-danger';
        
        if (result.success) {
            const title = document.createElement('h4');
            title.innerHTML = '<i class="fa fa-check-circle mr-2"></i>' + _t("Checkpoint Scanned Successfully!");
            content.appendChild(title);
            
            const nameP = document.createElement('p');
            nameP.innerHTML = '<strong>' + _t("Checkpoint: ") + '</strong>' + result.checkpoint_name;
            content.appendChild(nameP);
            
            if (result.checkpoint_code) {
                const codeP = document.createElement('p');
                codeP.innerHTML = '<strong>' + _t("Code: ") + '</strong>' + result.checkpoint_code;
                content.appendChild(codeP);
            }
            
            if (result.checkpoint_location) {
                const locationP = document.createElement('p');
                locationP.innerHTML = '<strong>' + _t("Location: ") + '</strong>' + result.checkpoint_location;
                content.appendChild(locationP);
            }
            
            const patrolP = document.createElement('p');
            patrolP.innerHTML = '<strong>' + _t("Patrol: ") + '</strong>' + result.patrol_name;
            content.appendChild(patrolP);
            
            if (result.patrol_route) {
                const routeP = document.createElement('p');
                routeP.innerHTML = '<strong>' + _t("Route: ") + '</strong>' + result.patrol_route;
                content.appendChild(routeP);
            }
            
            if (result.guard_name) {
                const guardP = document.createElement('p');
                guardP.innerHTML = '<strong>' + _t("Guard: ") + '</strong>' + result.guard_name;
                content.appendChild(guardP);
            }
            
            const progressP = document.createElement('p');
            progressP.innerHTML = '<strong>' + _t("Progress: ") + '</strong>' + 
                                result.points_completed + '/' + result.points_total + 
                                ' (' + Math.round(result.completion_rate) + '%)';
            content.appendChild(progressP);
            
            // Progress bar
            const progressContainer = document.createElement('div');
            progressContainer.className = 'progress mb-3';
            progressContainer.style.height = '25px';
            
            const progressBar = document.createElement('div');
            progressBar.className = 'progress-bar bg-success';
            progressBar.style.width = result.completion_rate + '%';
            progressBar.textContent = Math.round(result.completion_rate) + '%';
            progressBar.setAttribute('role', 'progressbar');
            progressBar.setAttribute('aria-valuenow', result.completion_rate);
            progressBar.setAttribute('aria-valuemin', '0');
            progressBar.setAttribute('aria-valuemax', '100');
            
            progressContainer.appendChild(progressBar);
            content.appendChild(progressContainer);
            
            const timeP = document.createElement('p');
            timeP.innerHTML = '<strong>' + _t("Scanned at: ") + '</strong>' + result.scan_time;
            content.appendChild(timeP);
            
            // Show success notification with automatic logging indication
            const notificationMessage = result.auto_logged ? 
                _t("Checkpoint automatically logged!") : 
                result.message;
            
            this.notification.add(notificationMessage, {
                title: _t("Auto-Logged Successfully"),
                type: 'success',
            });
            
            // Auto-close after successful scan (reduced time for automatic logging)
            const closeDelay = result.auto_logged ? 2000 : 3000;
            setTimeout(() => {
                this.actionService.doAction({
                    type: 'ir.actions.act_window_close'
                });
                
                // Trigger dashboard refresh
                this.actionService.doAction({
                    type: 'ir.actions.client',
                    tag: 'reload',
                });
            }, closeDelay);
            
        } else {
            const title = document.createElement('h4');
            title.innerHTML = '<i class="fa fa-exclamation-triangle mr-2"></i>' + 
                            (result.message || _t("Checkpoint Scan Failed"));
            content.appendChild(title);
            
            const errorP = document.createElement('p');
            errorP.textContent = result.error || _t("Unknown error occurred");
            content.appendChild(errorP);
            
            // Show additional information if available
            if (result.previous_scan_time) {
                const prevScanP = document.createElement('p');
                prevScanP.innerHTML = '<strong>' + _t("Previously scanned at: ") + '</strong>' + result.previous_scan_time;
                content.appendChild(prevScanP);
            }
            
            if (result.previous_scan_guard) {
                const prevGuardP = document.createElement('p');
                prevGuardP.innerHTML = '<strong>' + _t("Previously scanned by: ") + '</strong>' + result.previous_scan_guard;
                content.appendChild(prevGuardP);
            }
            
            // Show error notification
            this.notification.add(result.error || result.message, {
                title: _t("Error"),
                type: 'danger',
            });
        }
        
        this.resultArea.appendChild(content);
    }

    showResult(type, result) {
        if (!this.resultArea) return;
        
        this.resultArea.innerHTML = '';
        
        if (type === 'error') {
            const errorDiv = document.createElement('div');
            errorDiv.className = 'alert alert-danger';
            errorDiv.textContent = result;
            this.resultArea.appendChild(errorDiv);
            return;
        }
        
        const content = document.createElement('div');
        content.className = 'alert alert-success';
        
        switch (result.type) {
            case 'patrol_point': {
                const title = document.createElement('h4');
                title.textContent = _t("Patrol Point Scanned");
                content.appendChild(title);
                
                const nameP = document.createElement('p');
                nameP.textContent = _t("Name: ") + result.name;
                content.appendChild(nameP);
                
                const locationP = document.createElement('p');
                locationP.textContent = _t("Location: ") + result.location;
                content.appendChild(locationP);
                
                const logButton = document.createElement('button');
                logButton.className = 'btn btn-primary mt-2';
                logButton.textContent = _t("Log Checkpoint");
                logButton.addEventListener('click', () => {
                    this.logPatrolPoint(result.id);
                });
                content.appendChild(logButton);
                break;
            }
            case 'key': {
                const title = document.createElement('h4');
                title.textContent = _t("Key Scanned");
                content.appendChild(title);
                
                const nameP = document.createElement('p');
                nameP.textContent = _t("Name: ") + result.name;
                content.appendChild(nameP);
                
                const statusP = document.createElement('p');
                statusP.textContent = _t("Status: ") + result.state;
                content.appendChild(statusP);
                
                const hubP = document.createElement('p');
                hubP.textContent = _t("Key Hub: ") + result.key_hub;
                content.appendChild(hubP);
                break;
            }
            case 'premise': {
                const title = document.createElement('h4');
                title.textContent = _t("Premise Scanned");
                content.appendChild(title);
                
                const nameP = document.createElement('p');
                nameP.textContent = _t("Name: ") + result.name;
                content.appendChild(nameP);
                
                const addressP = document.createElement('p');
                addressP.textContent = _t("Address: ") + result.address;
                content.appendChild(addressP);
                
                const clientP = document.createElement('p');
                clientP.textContent = _t("Client: ") + result.client;
                content.appendChild(clientP);
                break;
            }
            case 'gate_pass': {
                const title = document.createElement('h4');
                title.textContent = _t("Gate Pass Scanned");
                content.appendChild(title);
                
                const passP = document.createElement('p');
                passP.textContent = _t("Pass: ") + result.name;
                content.appendChild(passP);
                
                const visitorP = document.createElement('p');
                visitorP.textContent = _t("Visitor: ") + result.visitor;
                content.appendChild(visitorP);
                
                const validP = document.createElement('p');
                validP.textContent = _t("Valid Until: ") + result.valid_until;
                content.appendChild(validP);
                
                const statusP = document.createElement('p');
                statusP.textContent = _t("Status: ") + result.state;
                content.appendChild(statusP);
                break;
            }
            default: {
                const unknownP = document.createElement('p');
                unknownP.textContent = _t("Unknown QR code type");
                content.appendChild(unknownP);
            }
        }
        
        this.resultArea.appendChild(content);
    }
    
    async logPatrolPoint(pointId) {
        try {
            // Get patrol ID from context if available
            const patrolId = this.props.context && this.props.context.default_patrol_id;
            
            const result = await this.orm.call(
                'security.patrol.log',
                'create_from_scan',
                [pointId, patrolId]
            );
            
            if (result.success) {
                if (this.resultArea) {
                    this.resultArea.innerHTML = '';
                    const successDiv = document.createElement('div');
                    successDiv.className = 'alert alert-success';
                    successDiv.textContent = result.message;
                    this.resultArea.appendChild(successDiv);
                    
                    // Close the dialog after successful scan
                    setTimeout(() => {
                        this.actionService.doAction({
                            type: 'ir.actions.act_window_close'
                        });
                        
                        // Refresh the patrol view if we're in a form
                        if (patrolId) {
                            this.actionService.doAction({
                                type: 'ir.actions.client',
                                tag: 'reload',
                            });
                        }
                    }, 2000);
                }
            } else {
                this.showResult('error', result.error || _t("Failed to log patrol point"));
            }
        } catch (error) {
            this.showResult('error', _t("Failed to log patrol point: ") + error);
        }
    }
    
    playBeepSound() {
        const audio = new Audio('/security_management/static/src/sounds/beep.wav');
        audio.play().catch(e => {
            console.log("Could not play beep sound:", e);
        });
    }
    
    showError(message) {
        if (!this.resultArea) return;
        
        this.resultArea.innerHTML = '';
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-danger';
        errorDiv.textContent = message;
        this.resultArea.appendChild(errorDiv);
    }
}

QRScanner.template = 'security_management.QRScanner';
QRScanner.props = {
    // Define the props that can be passed to the component
    context: { type: Object, optional: true },
};

registry.category("actions").add("security_manager.qr_scanner", QRScanner);

export default QRScanner;
