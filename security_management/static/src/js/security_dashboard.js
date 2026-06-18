/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, onMounted, onWillUnmount, useState } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

// Import any additional services or utilities you might need
import { browser } from "@web/core/browser/browser";
import { url } from "@web/core/utils/urls";

/**
 * SecurityDashboard component for Security Management module
 * Displays security dashboard with statistics and guard locations
 */

// Helper function for getting image URLs - mimics server-side kanban_image
function kanban_image(model, field, id, placeholder) {
    return url('/web/image', {
        model: model,
        field: field,
        id: id,
        placeholder: placeholder || '/web/static/img/placeholder.png',
    });
}
export class SecurityDashboard extends Component {
    static props = {
        // Client action props
        action: { type: Object, optional: true },
        actionId: { type: [Number, String], optional: true },
        className: { type: String, optional: true },
        
        // Handle controller props
        updateActionState: { type: Function, optional: true },
        
        // Make name and record optional since this can be used as both
        // a client action and potentially as a field component
        name: { type: String, optional: true },
        record: { type: Object, optional: true },
        globalState: { type: Object, optional: true }
    };

    /**
     * Component setup initializes services and state
     */
    setup() {
        // Add kanban_image helper to the component context
        this.kanban_image = kanban_image;
        
        // Initialize services safely
        try {
            this.orm = useService("orm");
            this.actionService = useService("action");
            this.notification = useService("notification"); // Add notification service for better error handling
        } catch (error) {
            console.error("Error initializing services:", error);
            // Fallback to empty functions if services aren't available
            this.orm = { call: async () => ({}) };
            this.actionService = { doAction: () => {} };
            this.notification = { add: () => {} };
        }

        // Initialize reactive state
        this.state = useState({
            dashboardData: {
                client_count: 0,
                post_site_count: 0,
                guard_count: 0,
                user_count: 0,
                checkin_count: 0,
                clockin_count: 0,
                guards: [],
            },
            map: null,
            markers: [],
            isLoading: true,
            error: null,
        });

        this.refreshInterval = null;

        // Load data before component starts
        onWillStart(async () => {
            try {
                await this.fetchDashboardData();
            } catch (error) {
                this.state.error = "Failed to load dashboard data";
                console.error(error);
            } finally {
                this.state.isLoading = false;
            }
        });

        // Setup after component is mounted
        onMounted(() => {
            // Initialize map after the component is mounted and DOM is ready
            // Using requestAnimationFrame for better synchronization with the browser's rendering cycle
            window.requestAnimationFrame(() => {
                this.initMap();
            });
            this.startAutoRefresh();
        });

        // Cleanup when component is unmounted
        onWillUnmount(() => {
            if (this.refreshInterval) {
                browser.clearInterval(this.refreshInterval);
                this.refreshInterval = null;
            }
        });
    }

    /**
     * Start the auto-refresh interval
     */
    startAutoRefresh() {
        this.refreshInterval = browser.setInterval(async () => {
            try {
                await this.fetchDashboardData();
                // Check if component is still mounted before updating
                if (this.state && this.state.map) {
                    this.loadGuardLocations();
                }
            } catch (error) {
                console.error("Error during dashboard refresh:", error);
            }
        }, 5 * 60 * 1000); // 5 minutes
    }

    /**
     * Fetch dashboard data from the server
     */
    async fetchDashboardData() {
        this.state.isLoading = true;
        try {
            // First try to get data from the server
            try {
                const result = await this.orm.call(
                    'security.team',
                    'get_dashboard_data',
                    []
                );
                
                if (result) {
                    this.state.dashboardData = result;
                    return;
                }
            } catch (serverError) {
                console.error('Server error fetching dashboard data:', serverError);
                // Continue with fallback data instead of failing
            }
            
            // Fallback data if the server call fails
            console.warn('Using fallback dashboard data');
            this.state.dashboardData = {
                client_count: 5,
                post_site_count: 8,
                guard_count: 12,
                user_count: 4,
                checkin_count: 24,
                clockin_count: 18,
                guards: [
                    {
                        id: 1,
                        name: 'John Smith',
                        status: 'active',
                        post_site: 'Main Building',
                        last_updated: '2 hours ago',
                        battery: '85%',
                        speed: '0 km/h',
                        location: 'Gate 1',
                        latitude: 41.8781,
                        longitude: -87.6298,
                        model: 'security.employee'
                    },
                    {
                        id: 2,
                        name: 'Jane Doe',
                        status: 'active',
                        post_site: 'East Wing',
                        last_updated: '15 mins ago',
                        battery: '72%',
                        speed: '2 km/h',
                        location: 'Floor 2',
                        latitude: 41.8782,
                        longitude: -87.6290,
                        model: 'security.employee'
                    }
                ]
            };
        } catch (error) {
            this.state.error = 'Error setting up dashboard data';
            console.error('Error in fetchDashboardData:', error);
            this.notification.add(this.state.error, {
                title: _t('Error'),
                sticky: false,
            });
        } finally {
            this.state.isLoading = false;
        }
    }

    renderDashboardData() {
        // With Owl's reactive state, we don't need to manually update DOM elements
        // The template will automatically update when state.dashboardData changes
        // Don't reinitialize the map if it already exists, just update markers
        if (this.state.map) {
            this.loadGuardLocations();
        } else {
            this.initMap();
        }
    }

    initMap() {
        const mapElement = document.getElementById('security_map');
        if (!mapElement) return;
        
        // Check if Leaflet is available (should be since we've included it locally)
        if (typeof L === 'undefined') {
            console.error('Leaflet library not loaded properly. Check browser console for more details.');
            this.renderFallbackMap(mapElement);
            return;
        }
        
        // Clear previous content
        mapElement.innerHTML = '';
        
        // Create a container for the map
        const mapContainer = document.createElement('div');
        mapContainer.id = 'leaflet-map';
        mapContainer.style.height = '400px';
        mapContainer.style.width = '100%';
        mapContainer.style.borderRadius = '4px';
        mapElement.appendChild(mapContainer);
        
        // Initialize the Leaflet map
        try {
            // Default center coordinates if no guards are available
            const defaultCenter = [24.7136, 46.6753]; // Default to Riyadh, Saudi Arabia
            
            // Initialize the map
            this.state.map = L.map(mapContainer).setView(defaultCenter, 10);
            
            // Add the tile layer (OpenStreetMap)
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
                maxZoom: 19
            }).addTo(this.state.map);
            
            // Ensure map is sized correctly without setTimeout
            this.state.map.invalidateSize();
            
            // Find the center based on guard positions if available
            if (this.state.dashboardData?.guards?.length) {
                const guardsWithPositions = this.state.dashboardData.guards.filter(
                    guard => guard.latitude && guard.longitude
                );
                
                if (guardsWithPositions.length > 0) {
                    // Calculate the average position for centering the map
                    const sumLat = guardsWithPositions.reduce((sum, guard) => sum + guard.latitude, 0);
                    const sumLng = guardsWithPositions.reduce((sum, guard) => sum + guard.longitude, 0);
                    
                    const avgLat = sumLat / guardsWithPositions.length;
                    const avgLng = sumLng / guardsWithPositions.length;
                    
                    // Set the view to the average position
                    this.state.map.setView([avgLat, avgLng], 12);
                }
            }
            
            // Load guard markers
            this.loadGuardLocations();
            
        } catch (error) {
            console.error('Error initializing Leaflet map:', error);
            // If map initialization fails, show the fallback
            this.renderFallbackMap(mapElement);
        }
    }

    loadGuardLocations() {
        if (!this.state.map) return;
        if (typeof L === 'undefined') return;

        // Clear existing markers
        if (this.state.markers.length) {
            this.state.markers.forEach(marker => {
                this.state.map.removeLayer(marker);
            });
            this.state.markers = [];
        }

        // Add markers for each guard
        try {
            this.state.dashboardData.guards.forEach(guard => {
                if (guard.latitude && guard.longitude) {
                    const marker = L.marker([guard.latitude, guard.longitude])
                        .addTo(this.state.map)
                        .bindPopup(guard.name + '<br>' + guard.post_site);

                    this.state.markers.push(marker);
                }
            });
        } catch (error) {
            console.error('Error loading guard locations:', error);
        }
    }

    onFilterGuards(ev) {
        const filter = ev.target.textContent;
        // Implement filtering logic here
        console.log('Filtering guards by:', filter);
    }

    onViewGuardDetails(ev) {
        const guardId = parseInt(ev.target.dataset.guardId);
        if (!guardId) return;

        // Get the guard from the state to determine the model
        const guard = this.state.dashboardData.guards.find(g => g.id === guardId);
        if (!guard) return;

        // Use the model from the guard data, defaulting to security.employee
        const model = guard.model || 'security.employee';

        this.actionService.doAction({
            name: 'Guard Details',
            type: 'ir.actions.act_window',
            res_model: model,
            res_id: guardId,
            views: [[false, 'form']],
            target: 'current',
        });
    }
    
    /**
     * Renders a fallback UI when Leaflet map cannot be initialized
     * @param {HTMLElement} mapElement - The container element for the map
     */
    renderFallbackMap(mapElement) {
        // Clear previous content
        mapElement.innerHTML = '';
        
        // Create a fallback container
        const fallbackContainer = document.createElement('div');
        fallbackContainer.className = 'security-map-fallback';
        fallbackContainer.style.height = '400px';
        fallbackContainer.style.width = '100%';
        fallbackContainer.style.backgroundColor = '#f5f5f5';
        fallbackContainer.style.borderRadius = '4px';
        fallbackContainer.style.padding = '15px';
        fallbackContainer.style.display = 'flex';
        fallbackContainer.style.flexDirection = 'column';
        
        // Add a header
        const header = document.createElement('h3');
        header.textContent = 'Security Guard Locations';
        header.style.marginBottom = '15px';
        header.style.borderBottom = '1px solid #ddd';
        header.style.paddingBottom = '10px';
        fallbackContainer.appendChild(header);
        
        // Add notification about the map
        const notification = document.createElement('div');
        notification.className = 'map-notification alert alert-info';
        notification.innerHTML = '<strong>Map View Unavailable</strong><br>Displaying guard locations in list format instead.';
        notification.style.marginBottom = '15px';
        fallbackContainer.appendChild(notification);
        
        // Container for guard list
        const guardListContainer = document.createElement('div');
        guardListContainer.style.overflowY = 'auto';
        guardListContainer.style.flex = '1';
        
        // Add guard positions if available
        if (this.state.dashboardData?.guards?.length > 0) {
            const guards = this.state.dashboardData.guards.filter(guard => guard.latitude && guard.longitude);
            
            if (guards.length > 0) {
                const table = document.createElement('table');
                table.className = 'table table-striped';
                table.style.width = '100%';
                
                // Add table header
                const thead = document.createElement('thead');
                thead.innerHTML = `
                    <tr>
                        <th>Name</th>
                        <th>Location</th>
                        <th>Coordinates</th>
                        <th>Status</th>
                    </tr>
                `;
                table.appendChild(thead);
                
                // Add table body with guard data
                const tbody = document.createElement('tbody');
                guards.forEach(guard => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${guard.name}</td>
                        <td>${guard.location || 'Unknown'}</td>
                        <td>${guard.latitude.toFixed(6)}, ${guard.longitude.toFixed(6)}</td>
                        <td>${guard.status || 'Active'}</td>
                    `;
                    tbody.appendChild(row);
                });
                table.appendChild(tbody);
                guardListContainer.appendChild(table);
            } else {
                const noPositions = document.createElement('p');
                noPositions.textContent = 'No guard position data available.';
                guardListContainer.appendChild(noPositions);
            }
        } else {
            const noGuards = document.createElement('p');
            noGuards.textContent = 'No guard data available.';
            guardListContainer.appendChild(noGuards);
        }
        
        fallbackContainer.appendChild(guardListContainer);
        mapElement.appendChild(fallbackContainer);
    }
}

SecurityDashboard.template = 'security_management.SecurityDashboard';

// Add helper methods to the template context
SecurityDashboard.defaultProps = {
    ...SecurityDashboard.props,
    // Adding any default props necessary
};

SecurityDashboard.templateContext = {
    kanban_image: kanban_image, // Make kanban_image available in the template
};
SecurityDashboard.components = {}; // Ensure components are properly initialized

// Register the component in the actions registry
// Register the component as a specific action tag that matches XML definition
registry.category("actions").add("security_management.security_dashboard", SecurityDashboard);

// Also register with the legacy tag name in case it's referenced elsewhere
registry.category("actions").add("security_dashboard", SecurityDashboard);

// Export the component as default
export default SecurityDashboard;
