/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component } from "@odoo/owl";

/**
 * TimeAgo widget for integer fields
 * Displays integer values (typically days) as a relative time
 */
export class TimeAgoWidget extends Component {
    static template = "security_management.TimeAgoWidget";
    
    static props = {
        ...standardFieldProps,
        value: { type: Number, optional: true },
    };

    get formattedValue() {
        const value = this.props.value;
        if (value === undefined || value === null || isNaN(value)) {
            return "N/A";
        }
        
        if (value < 0) {
            const days = Math.abs(value);
            return days === 1 ? "1 day ago" : `${days} days ago`;
        } else if (value === 0) {
            return "Today";
        } else {
            return value === 1 ? "In 1 day" : `In ${value} days`;
        }
    }
}

export const timeagoWidget = {
    component: TimeAgoWidget,
    fieldDependencies: [],
};

// Register the widget for integer fields
registry.category("fields").add("timeago", timeagoWidget);
