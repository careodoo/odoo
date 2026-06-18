/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, onMounted, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";

class GatePassComponent extends Component {
    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");
        this.dialogService = useService("dialog");
        
        this.state = useState({
            gatePassData: null
        });
        
        this.gatePassId = this.props.gatePassId;
        
        onWillStart(async () => {
            await this.fetchGatePassData();
        });
        
        onMounted(() => {
            this.renderGatePass();
        });
    }
    
    async fetchGatePassData() {
        if (!this.gatePassId) {
            return;
        }
        
        try {
            const result = await this.orm.read(
                'security.gate.pass',
                [this.gatePassId],
                [
                    'name', 'visitor_name', 'visitor_phone', 'visitor_email', 
                    'visit_purpose', 'valid_from', 'valid_until', 'state', 
                    'premise_id', 'floor_id', 'unit_id', 'host_id', 'qr_code', 
                    'check_in', 'check_out', 'visit_duration'
                ]
            );
            
            if (result && result.length) {
                this.state.gatePassData = result[0];
            }
        } catch (error) {
            console.error("Error fetching gate pass data:", error);
        }
    }
    
    renderGatePass() {
        if (this.state.gatePassData && this.state.gatePassData.qr_code) {
            this.generateQRCode(this.state.gatePassData.qr_code);
        }
    }
    
    getStatusClass() {
        if (!this.state.gatePassData) return 'badge-secondary';
        
        switch (this.state.gatePassData.state) {
            case 'draft': return 'badge-secondary';
            case 'approved': return 'badge-success';
            case 'checked_in': return 'badge-primary';
            case 'checked_out': return 'badge-info';
            case 'expired': return 'badge-warning';
            case 'rejected': return 'badge-danger';
            default: return 'badge-secondary';
        }
    }
    
    getStatusText() {
        if (!this.state.gatePassData) return '';
        
        switch (this.state.gatePassData.state) {
            case 'draft': return _t('Draft');
            case 'approved': return _t('Approved');
            case 'checked_in': return _t('Checked In');
            case 'checked_out': return _t('Checked Out');
            case 'expired': return _t('Expired');
            case 'rejected': return _t('Rejected');
            default: return this.state.gatePassData.state;
        }
    }
    
    showCheckInButton() {
        return this.state.gatePassData && this.state.gatePassData.state === 'approved';
    }
    
    showCheckOutButton() {
        return this.state.gatePassData && this.state.gatePassData.state === 'checked_in';
    }
    
    showValidateButton() {
        return this.state.gatePassData && this.state.gatePassData.state === 'draft';
    }
    
    showRejectButton() {
        return this.state.gatePassData && this.state.gatePassData.state === 'draft';
    }
    
    showPrintButton() {
        return this.state.gatePassData && this.state.gatePassData.state === 'approved';
    }
    
    generateQRCode(qrCodeData) {
        // Wait for the DOM to be ready
        setTimeout(() => {
            const qrCodeContainer = document.querySelector('.o_gate_pass_qr_code');
            if (qrCodeContainer) {
                qrCodeContainer.innerHTML = '';
                new QRCode(qrCodeContainer, {
                    text: qrCodeData,
                    width: 128,
                    height: 128,
                    colorDark: "#000000",
                    colorLight: "#ffffff",
                    correctLevel: QRCode.CorrectLevel.H
                });
            }
        }, 0);
    }
    
    async onCheckIn() {
        try {
            const result = await this.orm.call(
                'security.gate.pass',
                'action_check_in',
                [[this.gatePassId]]
            );
            
            if (result) {
                this.notification.add(_t('Visitor checked in successfully'), {
                    title: _t('Success'),
                });
                
                await this.fetchGatePassData();
                this.renderGatePass();
            }
        } catch (error) {
            this.notification.add(_t('Failed to check in: ') + error, {
                title: _t('Error'),
            });
        }
    }
    
    async onCheckOut() {
        try {
            const result = await this.orm.call(
                'security.gate.pass',
                'action_check_out',
                [[this.gatePassId]]
            );
            
            if (result) {
                this.notification.add(_t('Visitor checked out successfully'), {
                    title: _t('Success'),
                });
                
                await this.fetchGatePassData();
                this.renderGatePass();
            }
        } catch (error) {
            this.notification.add(_t('Failed to check out: ') + error, {
                title: _t('Error'),
            });
        }
    }
    
    async onValidate() {
        try {
            const result = await this.orm.call(
                'security.gate.pass',
                'action_approve',
                [[this.gatePassId]]
            );
            
            if (result) {
                this.notification.add(_t('Gate pass approved successfully'), {
                    title: _t('Success'),
                });
                
                await this.fetchGatePassData();
                this.renderGatePass();
            }
        } catch (error) {
            this.notification.add(_t('Failed to approve gate pass: ') + error, {
                title: _t('Error'),
            });
        }
    }
    
    onReject() {
        this.dialogService.add(Dialog, {
            title: _t('Reject Gate Pass'),
            size: 'medium',
            body: 'Please provide a reason for rejecting this gate pass:',
            bodyComponent: RejectReasonDialog,
            onConfirm: async (reason) => {
                await this.rejectGatePass(reason);
            },
        });
    }
    
    async rejectGatePass(reason) {
        try {
            const result = await this.orm.call(
                'security.gate.pass',
                'action_reject',
                [[this.gatePassId], reason]
            );
            
            if (result) {
                this.notification.add(_t('Gate pass rejected'), {
                    title: _t('Success'),
                });
                
                await this.fetchGatePassData();
                this.renderGatePass();
            }
        } catch (error) {
            this.notification.add(_t('Failed to reject gate pass: ') + error, {
                title: _t('Error'),
            });
        }
    }
    
    onPrint() {
        this.actionService.doAction({
            type: 'ir.actions.report',
            report_name: 'security_manager.report_gate_pass',
            report_type: 'qweb-pdf',
            data: {
                model: 'security.gate.pass',
                ids: [this.gatePassId],
            },
        });
    }
}

GatePassComponent.template = 'security_management.GatePassComponent';
GatePassComponent.props = {
    gatePassId: { type: Number, optional: true },
    action: { type: Object, optional: true },
    actionId: { type: [Number, String], optional: true },
    className: { type: String, optional: true },
    globalState: { type: Object, optional: true }
};

// Register the client actions
registry.category("actions").add("security_gate_pass_action", GatePassComponent);

// Register the Gate Pass Scanner component
registry.category("actions").add("security_management.gate_pass_component", GatePassComponent);

export default GatePassComponent;

class RejectReasonDialog extends Component {
    setup() {
        this.state = useState({
            reason: '',
        });
    }
    
    onConfirm() {
        this.props.close(this.state.reason);
    }
}

RejectReasonDialog.template = 'security_management.RejectReasonDialog';
RejectReasonDialog.props = {
    close: Function,
};
